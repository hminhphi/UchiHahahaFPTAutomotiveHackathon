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

# --- THÊM LOGIC LOAD AI MODEL (TCN) ---
try:
    import torch
    import numpy as np
    import sys
    sys.path.append(str(Path(__file__).resolve().parent))
    from train_tcn import TCNModel, extract_features
    
    tcn_model = TCNModel(input_dim=9)
    model_path = Path(__file__).resolve().parents[1] / "models" / "tcn_risk_model.pth"
    if model_path.exists():
        tcn_model.load_state_dict(torch.load(model_path, weights_only=True))
        tcn_model.eval()
        print(f"[AI ENGINE] Tải thành công TCN Model từ {model_path}!")
    else:
        tcn_model = None
except Exception as e:
    tcn_model = None
    print(f"[AI ENGINE] Lỗi load TCN: {e}")
# -------------------------------------

KUKSA_HOST = os.environ.get("KUKSA_HOST", "127.0.0.1")
KUKSA_PORT = int(os.environ.get("KUKSA_PORT", 55555))
WARNING_SIGNAL = "Vehicle.Cabin.Infotainment.HMI.Warning"

def compute_trip_score(frame, history_frames=None):
    """
    Trip Safety Score Engine (Phase 1 & 3): 
    Khai thác toàn bộ thông tin từ dataset để chấm điểm (Có lọc nhiễu thời gian).
    """
    # 1. NẾU CÓ AI MODEL (TCN): XUẤT ĐIỂM DỰA TRÊN DEEP LEARNING
    if tcn_model is not None and history_frames is not None and len(history_frames) >= 29:
        frames_window = history_frames[-29:] + [frame]
        X_seq = [extract_features(f) for f in frames_window]
        X_tensor = torch.tensor(np.array([X_seq]), dtype=torch.float32)
        with torch.no_grad():
            score = tcn_model(X_tensor).item()
        return score
        
    # 2. FALLBACK: RULE-BASED ENGINE (Context-Aware)
    ego = frame.get("ego", {})
    driver = frame.get("driver", {})
    min_ttc = frame.get("min_ttc", 99.9)
    if min_ttc is None: min_ttc = 99.9
    headway = frame.get("headway_sec", 99.9)
    if headway is None: headway = 99.9
    events = frame.get("events_active", [])
    
    speed = ego.get("speed_kmh", 0)
    alertness = driver.get("alertness_score", 1.0)
    long_accel = ego.get("longitudinal_accel", 0)
    lat_accel = ego.get("lateral_accel", 0)
    
    # Nhận diện ngữ cảnh thực tế (Context-Aware)
    is_parked = (speed < 2.0)
    is_traffic_jam = (2.0 <= speed < 20.0)
    is_highway = (speed > 70.0)
    
    # --- 1. DRIVER STATE ---
    attention_penalty = (1.0 - alertness) * 25
    driver_state = driver.get("state", "")
    
    if driver_state == "distracted":
        attention_penalty += 15
    elif driver_state == "drowsy":
        attention_penalty += 25

    if history_frames:
        closed_count = sum(1 for f in history_frames if f.get("driver", {}).get("eye_state") == "closed")
        if closed_count >= 3: attention_penalty += 15
            
        yawning_count = sum(1 for f in history_frames if f.get("driver", {}).get("mouth_state") == "yawning")
        if yawning_count >= 10: attention_penalty += 35
        elif yawning_count >= 5: attention_penalty += 20
        elif yawning_count > 0: attention_penalty += 10
        
        down_count = sum(1 for f in history_frames if f.get("driver", {}).get("head_pose") == "down")
        if down_count >= 5: attention_penalty += 25
    else:
        if driver.get("eye_state") == "closed": attention_penalty += 15
        if driver.get("mouth_state") == "yawning": attention_penalty += 10
        if driver.get("head_pose") == "down": attention_penalty += 10

    # Điều chỉnh theo Bối cảnh
    if is_parked: attention_penalty *= 0.2
    elif is_traffic_jam: attention_penalty *= 0.8
    elif is_highway: attention_penalty *= 1.5
        
    # --- 2. COLLISION RISK ---
    collision_risk_penalty = 0
    if not is_parked:
        if min_ttc < 1.5: collision_risk_penalty += 35
        elif min_ttc < 2.5: collision_risk_penalty += 15
            
        # Delta TTC (Phát hiện phanh gấp)
        if history_frames and len(history_frames) >= 5:
            past_ttc = history_frames[-5].get("min_ttc")
            if past_ttc is None: past_ttc = 99.9
            if min_ttc < 3.0 and (past_ttc - min_ttc > 1.5):
                collision_risk_penalty += 40

    # --- 3. COMPOUND RISK ---
    if attention_penalty > 15 and collision_risk_penalty > 0:
        collision_risk_penalty += 20
        
    # --- 4. VEHICLE HANDLING ---
    handling_penalty = 0
    if long_accel < -3.0: handling_penalty += 20
    if abs(lat_accel) > 3.0: handling_penalty += 15

    # --- 5. LANE BEHAVIOR ---
    lane_penalty = 0
    for event in events:
        evt_type = event.get("type", event.get("event_type", "")) if isinstance(event, dict) else str(event)
        if "lane" in evt_type.lower() or "departure" in evt_type.lower():
            lane_penalty += 15
            if is_highway: lane_penalty += 15
            
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
                # Truyền thêm 30 frame lịch sử để chạy TCN model
                history = frames[max(0, index - 30):index]
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
