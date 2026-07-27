import os
import time
import gzip
import json
import logging
from pathlib import Path
from kuksa_client.grpc import VSSClient
from kuksa_client.grpc import Datapoint

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

KUKSA_HOST = os.environ.get("KUKSA_HOST", "127.0.0.1")
KUKSA_PORT = int(os.environ.get("KUKSA_PORT", 55555))
WARNING_SIGNAL = "Vehicle.Cabin.Infotainment.HMI.Warning"

def compute_trip_score(frame, history_frames=None):
    """
    Trip Safety Score Engine (Phase 1 & 3): 
    Khai thác toàn bộ thông tin từ dataset để chấm điểm (Có lọc nhiễu thời gian).
    """
    ego = frame.get("ego", {})
    driver = frame.get("driver", {})
    min_ttc = frame.get("min_ttc")
    headway = frame.get("headway_sec")
    events = frame.get("events_active", [])
    
    speed = ego.get("speed_kmh", 0)
    alertness = driver.get("alertness_score", 1.0)
    long_accel = ego.get("longitudinal_accel", 0)
    lat_accel = ego.get("lateral_accel", 0)
    
    # 1. Driver State (25%) - Dựa trên độ tập trung và trạng thái mắt, miệng
    attention_penalty = (1.0 - alertness) * 25
    
    driver_state = driver.get("state", "")
    if driver_state == "distracted":
        attention_penalty += 15
    elif driver_state == "drowsy":
        attention_penalty += 25

    # Lọc nhiễu chớp mắt (Blinking): Chỉ trừ điểm nếu nhắm mắt liên tục
    if driver.get("eye_state") == "closed":
        if history_frames:
            # Đếm số lần nhắm mắt trong các frame quá khứ
            closed_count = sum(1 for f in history_frames if f.get("driver", {}).get("eye_state") == "closed")
            # Nếu nhắm mắt > 3 frame (~0.15s) thì coi là ngủ gật/mất tập trung thực sự
            if closed_count >= 3:
                attention_penalty += 15
        else:
            attention_penalty += 15
            
    if driver.get("mouth_state") == "yawning":
        attention_penalty += 10
        
    # 2. Collision Risk & TTC (35%)
    collision_risk_penalty = 0
    if min_ttc is not None and min_ttc > 0:
        if min_ttc < 1.5: collision_risk_penalty = 35 # Critical
        elif min_ttc < 2.5: collision_risk_penalty = 20 # High
        elif min_ttc < 4.0: collision_risk_penalty = 10 # Medium
        
    # Phạt bám đuôi (Tailgating) nếu tốc độ > 40km/h mà cách xe trước < 1 giây
    if headway is not None and 0 < headway < 1.0 and speed > 40:
        collision_risk_penalty += 15
        
    # 3. Vehicle Handling (25%) - Kiểm tra phanh gấp, thốc ga, đánh lái gắt
    handling_penalty = 0
    if abs(long_accel) > 4.0:
        handling_penalty += 15 # Harsh braking / acceleration
    if abs(lat_accel) > 3.5:
        handling_penalty += 10 # Harsh steering
        
    # 4. Lane Behavior & Speeding (15%)
    lane_penalty = 0
    if speed > 80:
        lane_penalty += 10 # Chạy quá tốc độ
        
    # Kiểm tra các sự kiện (VD: Lệch làn)
    for event in events:
        evt_type = event.get("type", event.get("event_type", "")) if isinstance(event, dict) else str(event)
        if "lane" in evt_type.lower() or "departure" in evt_type.lower():
            lane_penalty += 15
            
    # 5. Mức độ nhân đôi rủi ro (Compound Risk)
    if alertness < 0.5 and (min_ttc is not None and 0 < min_ttc < 2.5):
        collision_risk_penalty += 20
        
    if speed > 80 and lane_penalty >= 15:
        lane_penalty += 10
        
    final_score = 100 - attention_penalty - collision_risk_penalty - handling_penalty - lane_penalty
    return max(0, min(100, final_score))

def run_fusion_agent():
    dataset_path = Path("data/Practice_Dataset/Practice_Dataset/T01-Sample/T01-Sample.json.gz")
    if not dataset_path.exists():
        logger.error(f"Dataset not found at {dataset_path}. Run with correct working directory.")
        return
        
    logger.info(f"Loading full dataset from {dataset_path}...")
    with gzip.open(dataset_path, "rt", encoding="utf-8") as f:
        data = json.load(f)
    frames = data.get("frames", [])
    
    logger.info(f"Connecting to KUKSA Broker at {KUKSA_HOST}:{KUKSA_PORT}...")
    try:
        with VSSClient(KUKSA_HOST, KUKSA_PORT) as client:
            logger.info("Connected successfully! Starting dataset playback (Fusion Engine)...")
            
            try:
                client.set_current_values({WARNING_SIGNAL: Datapoint("")})
            except Exception: pass
            
            for index, frame in enumerate(frames):
                # Truyền thêm 10 frame lịch sử để lọc nhiễu chớp mắt
                history = frames[max(0, index - 10):index]
                # 1. Tính điểm an toàn
                score = compute_trip_score(frame, history_frames=history)
                speed = frame.get("ego", {}).get("speed_kmh", 0)
                driver_state = frame.get("driver", {}).get("state", "unknown")
                min_ttc = frame.get("min_ttc", 99.9)
                
                logger.info(f"Frame {index:04d} | Speed: {speed:.1f} | State: {driver_state} | TTC: {min_ttc:.1f}s -> SAFETY SCORE: {score:.1f}/100")
                
                # 2. Phát cảnh báo nếu điểm an toàn rớt xuống thấp
                if score < 50:
                    try:
                        client.set_current_values({WARNING_SIGNAL: Datapoint("COLLISION_WARNING")})
                    except Exception: pass
                else:
                    try:
                        client.set_current_values({WARNING_SIGNAL: Datapoint("")})
                    except Exception: pass
                    
                time.sleep(0.2) # Chạy mô phỏng ở 5 FPS
                
    except Exception as e:
        logger.error(f"KUKSA Error: {e}")

if __name__ == "__main__":
    run_fusion_agent()
