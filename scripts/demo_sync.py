import os
import sys
import time
import cv2
from pathlib import Path

# Tái sử dụng giao diện và thuật toán có sẵn
from render_trip_dashboard import TripRenderer, parse_args, resolve_trip, discover_trips
from carsky_agent import compute_trip_score
from kuksa_client.grpc import VSSClient, Datapoint

KUKSA_PORT = int(os.environ.get("KUKSA_PORT", 55555))
WARNING_SIGNAL = "Vehicle.Cabin.Infotainment.HMI.Warning"

def run_sync_demo(renderer, start, end, fps, speed):
    title = f"FleetIQ Sync Demo - {renderer.trip_dir.name}"
    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(title, 1440, 810)
    
    # Dùng một dict (state) để lưu trữ vị trí khung hình hiện tại, cho phép thay đổi từ UI Trackbar
    state = {'index': start, 'paused': False}
    
    def on_trackbar(val):
        state['index'] = val

    # Tính năng 1: Thanh trượt (Trackbar) để tua video tự do
    cv2.createTrackbar("Tua Video", title, start, end, on_trackbar)
    delay_ms = max(1, int(1000 / max(0.1, fps * speed)))
    
    print(f"Connecting to local KUKSA Databroker at 127.0.0.1:{KUKSA_PORT}...")
    try:
        with VSSClient("127.0.0.1", KUKSA_PORT) as client:
            print("Connected! Starting synchronized playback...")
            try: client.set_current_values({WARNING_SIGNAL: Datapoint("")})
            except Exception: pass
            
            while True:
                idx = state['index']
                
                # 1. Vẽ giao diện phức tạp từ Dataset (Lấy frame thứ idx)
                frame_img = renderer.render(idx)
                
                # 2. Tính điểm rủi ro bằng AI (Cũng lấy đúng frame thứ idx)
                frame_data = renderer.frames[idx]
                history = renderer.frames[max(0, idx - 30):idx]
                score = compute_trip_score(frame_data, history_frames=history)
                
                # 3. Kích hoạt Back-to-Car alert
                if score < 50:
                    try: client.set_current_values({WARNING_SIGNAL: Datapoint("COLLISION_WARNING")})
                    except Exception: pass
                    cv2.putText(frame_img, "VSS: COLLISION WARNING SENT!", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (50, 50, 255), 3, cv2.LINE_AA)
                else:
                    try: client.set_current_values({WARNING_SIGNAL: Datapoint("")})
                    except Exception: pass
                    
                if state['paused']:
                    cv2.putText(frame_img, "[ PAUSED ]", (100, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 200, 0), 3, cv2.LINE_AA)

                # 4. Cập nhật vị trí của thanh trượt (Trackbar) theo video đang chạy
                cv2.setTrackbarPos("Tua Video", title, idx)
                cv2.imshow(title, frame_img)
                
                # 5. Xử lý các phím bấm (Tua video bằng bàn phím)
                key = cv2.waitKey(0 if state['paused'] else delay_ms) & 0xFF
                
                if key in (27, ord("q")): # ESC / Q để thoát
                    break
                elif key == ord(" "): # SPACE để Tạm dừng / Phát tiếp
                    state['paused'] = not state['paused']
                elif key == ord("a"): # Phím A: Lùi nhanh 10 frames
                    state['index'] = max(start, state['index'] - 10)
                elif key == ord("d"): # Phím D: Tiến nhanh 10 frames
                    state['index'] = min(end, state['index'] + 10)
                    
                # 6. Tự động chuyển frame kế tiếp nếu không bị Pause
                if not state['paused']:
                    state['index'] = start if state['index'] >= end else state['index'] + 1
                    
    except Exception as e:
        print(f"Lỗi kết nối VSS (Đảm bảo KUKSA đang chạy): {e}")
        
    cv2.destroyAllWindows()


def select_trip_interactive(root):
    """
    Tính năng 2: Menu chọn bộ dataset (chọn test)
    """
    trips = discover_trips(root)
    if not trips:
        print("Không tìm thấy Trip nào trong Dataset!")
        sys.exit(1)
        
    print("\n" + "="*45)
    print(" TÍNH NĂNG CHỌN DATASET (TRIP) ĐỂ TEST")
    print("="*45)
    for i, t in enumerate(trips):
        print(f" [{i+1}] {t.name}")
    print("="*45)
        
    while True:
        try:
            choice = int(input("\nNhập số thứ tự bộ Dataset muốn test (VD: 1): "))
            if 1 <= choice <= len(trips):
                return trips[choice-1]
            print("Số không hợp lệ!")
        except ValueError:
            print("Vui lòng nhập một số.")

if __name__ == "__main__":
    args = parse_args()
    root = args.dataset_root.resolve()
    
    # Nếu chạy lệnh không có tham số --trip, hệ thống sẽ mở menu chọn Test
    if len(sys.argv) == 1:
        trip_dir = select_trip_interactive(root)
    else:
        trip_dir = resolve_trip(root, args.trip)
        
    renderer = TripRenderer(trip_dir)
    run_sync_demo(renderer, 0, len(renderer.frames) - 1, 20.0, args.speed)
