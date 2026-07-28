import json
import gzip
import os
import shutil
from pathlib import Path
import copy

def main():
    base_dir = Path("data/Practice_Dataset/Practice_Dataset")
    source_trip = base_dir / "T01-Sample"
    target_trip = base_dir / "T07-Synthetic"
    
    if target_trip.exists():
        shutil.rmtree(target_trip)
    
    # Tạo cấu trúc thư mục
    os.makedirs(target_trip / "kitti" / "image_2", exist_ok=True)
    os.makedirs(target_trip / "driver", exist_ok=True)
    
    # Load JSON của T01
    with gzip.open(source_trip / "T01-Sample.json.gz", "rt") as f:
        data = json.load(f)
        
    frames = data["frames"][:1000] # Lấy 1000 frames đầu tiên
    
    print("Generating Synthetic Data...")
    
    for idx, frame in enumerate(frames):
        ego = frame.setdefault("ego", {})
        driver = frame.setdefault("driver", {})
        
        # --- SCENARIO 1: Đỗ xe (Frame 0 - 200) ---
        if 0 <= idx < 200:
            ego["speed_kmh"] = 0.0
            driver["head_pose"] = "down" # Dùng điện thoại
            driver["mouth_state"] = "yawning" # Ngáp ngủ liên tục
            driver["state"] = "drowsy"
            frame["min_ttc"] = 99.9
            
        # --- SCENARIO 2: Tắc đường bò chậm (Frame 200 - 400) ---
        elif 200 <= idx < 400:
            ego["speed_kmh"] = 10.0 # Bò 10km/h
            driver["head_pose"] = "front"
            driver["mouth_state"] = "normal"
            driver["state"] = "alert"
            frame["min_ttc"] = 1.0 # Rất gần xe trước nhưng vì tắc đường nên không phạt
            
        # --- SCENARIO 3: Cao tốc bình thường (Frame 400 - 600) ---
        elif 400 <= idx < 600:
            ego["speed_kmh"] = 90.0 # Chạy cao tốc
            driver["head_pose"] = "front"
            driver["mouth_state"] = "normal"
            driver["state"] = "alert"
            frame["min_ttc"] = 99.9
            
        # --- SCENARIO 4: Cao tốc - Mất tập trung (Frame 600 - 800) ---
        elif 600 <= idx < 800:
            ego["speed_kmh"] = 90.0
            driver["head_pose"] = "down" # Cúi gầm mặt trên cao tốc -> Cực kỳ nguy hiểm
            driver["state"] = "distracted"
            frame["min_ttc"] = 99.9
            
        # --- SCENARIO 5: Phanh gấp phía trước (Frame 800 - 1000) ---
        elif 800 <= idx < 1000:
            ego["speed_kmh"] = 90.0
            driver["head_pose"] = "front"
            driver["state"] = "alert"
            
            # Khởi tạo phanh gấp
            if 800 <= idx < 820:
                # 20 frames đầu TTC giảm từ 5.0 xuống 0.5 rất nhanh
                ttc = 5.0 - ((idx - 800) * (4.5 / 20.0))
                frame["min_ttc"] = ttc
            else:
                frame["min_ttc"] = 0.5 # Giữ nguyên ở mức nguy hiểm
    
    data["frames"] = frames
    
    # Lưu JSON mới
    with gzip.open(target_trip / "T07-Synthetic.json.gz", "wt") as f:
        json.dump(data, f)
        
    print("Copying Images (this might take a few seconds)...")
    # Copy vài ảnh minh họa (để UI không bị lỗi)
    # Vì copy 1000 ảnh khá lâu, ta copy bằng symlink hoặc copy 1 ảnh lặp lại
    src_img = list((source_trip / "kitti" / "image_2").glob("*.jpg"))[0]
    src_drv = list((source_trip / "driver").glob("*.jpg"))[0]
    
    for i in range(1000):
        img_name = f"{i:010d}.png"
        drv_name = f"{i:010d}.jpg"
        # Tạo symlink cho nhanh
        os.symlink(src_img.resolve(), target_trip / "kitti" / "image_2" / img_name)
        os.symlink(src_drv.resolve(), target_trip / "driver" / drv_name)
        
    print("XONG! Đã tạo thư mục T07-Synthetic thành công.")

if __name__ == "__main__":
    main()
