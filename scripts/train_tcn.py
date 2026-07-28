import os
import gzip
import json
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from pathlib import Path
from torch.utils.data import DataLoader, TensorDataset

# Tái sử dụng luật Rule-based để tạo nhãn (Teacher-Student Training)
# Sẽ import bên trong hàm để tránh circular import

# --- Kiến trúc Mạng TCN (Temporal Convolutional Network) ---
class TCNModel(nn.Module):
    def __init__(self, input_dim, hidden_dim=32, num_layers=3):
        super().__init__()
        layers = []
        for i in range(num_layers):
            dilation = 2 ** i
            in_channels = input_dim if i == 0 else hidden_dim
            # Causal Convolution (Chỉ nhìn về quá khứ)
            layers.append(nn.Conv1d(in_channels, hidden_dim, kernel_size=3, padding=dilation, dilation=dilation))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.2))
        
        self.network = nn.Sequential(*layers)
        self.fc = nn.Linear(hidden_dim, 1)
        self.sigmoid = nn.Sigmoid()
        
    def forward(self, x):
        # x shape: (batch, seq_len, features) -> Conv1d cần (batch, features, seq_len)
        x = x.transpose(1, 2)
        out = self.network(x)
        # Trích xuất state ở timestep cuối cùng
        out = out[:, :, -1]
        out = self.fc(out)
        return self.sigmoid(out) * 100.0 # Scale đầu ra về thang 0 - 100

def extract_features(frame):
    """Trích xuất 9 thông số đặc trưng (Features) từ mỗi Frame"""
    ego = frame.get("ego", {})
    driver = frame.get("driver", {})
    
    speed = ego.get("speed_kmh", 0) / 120.0 # Chuẩn hóa
    long_accel = ego.get("longitudinal_accel", 0) / 10.0
    lat_accel = ego.get("lateral_accel", 0) / 10.0
    ttc = frame.get("min_ttc", 10.0)
    ttc_norm = max(0, min(10.0, ttc)) / 10.0
    alertness = driver.get("alertness_score", 1.0)
    
    eye_closed = 1.0 if driver.get("eye_state") == "closed" else 0.0
    yawning = 1.0 if driver.get("mouth_state") == "yawning" else 0.0
    distracted = 1.0 if driver.get("state") == "distracted" else 0.0
    drowsy = 1.0 if driver.get("state") == "drowsy" else 0.0
    
    return [speed, long_accel, lat_accel, ttc_norm, alertness, eye_closed, yawning, distracted, drowsy]

def prepare_dataset(window_size=30):
    dataset_dir = Path("data/Practice_Dataset/Practice_Dataset")
    print(f"Loading data from all trips in {dataset_dir}...")
    
    X_list = []
    Y_list = []
    
    # Import ở đây để tránh Circular Import
    from carsky_agent import compute_trip_score
    
    # Duyệt qua T01, T02,...
    for json_file in dataset_dir.glob("T*-Sample/*.json.gz"):
        with gzip.open(json_file, "rt", encoding="utf-8") as f:
            data = json.load(f)
        frames = data.get("frames", [])
        
        for i in range(len(frames)):
            feat = extract_features(frames[i])
            X_list.append(feat)
            
            history = frames[max(0, i-10):i] # Teacher chỉ cần 10 frame lịch sử để tính
            score = compute_trip_score(frames[i], history_frames=history)
            Y_list.append(score)
            
    X_arr = np.array(X_list, dtype=np.float32)
    Y_arr = np.array(Y_list, dtype=np.float32)
    
    # Tạo Sliding Windows (Mỗi sample là 1 đoạn video dài `window_size` frames)
    X_seq = []
    Y_seq = []
    
    for i in range(window_size, len(X_arr)):
        X_seq.append(X_arr[i - window_size: i])
        Y_seq.append(Y_arr[i])
        
    return torch.tensor(np.array(X_seq)), torch.tensor(np.array(Y_seq))

def train():
    window_size = 30 # Tương đương 1.5 giây thời gian thực (ở 20 FPS)
    X, Y = prepare_dataset(window_size)
    dataset = TensorDataset(X, Y)
    loader = DataLoader(dataset, batch_size=32, shuffle=True)
    
    model = TCNModel(input_dim=9)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.01)
    
    print(f"Training TCN Model trên {len(X)} samples chuỗi thời gian...")
    for epoch in range(15):
        epoch_loss = 0
        for batch_x, batch_y in loader:
            optimizer.zero_grad()
            preds = model(batch_x).squeeze()
            loss = criterion(preds, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
        print(f"Epoch {epoch+1:02d}/15 - Loss (Sai số): {epoch_loss/len(loader):.2f}")
        
    os.makedirs("models", exist_ok=True)
    torch.save(model.state_dict(), "models/tcn_risk_model.pth")
    print("\n[SUCCESS] TCN Model đã được huấn luyện xong!")
    print("Saved weights to: models/tcn_risk_model.pth")

if __name__ == "__main__":
    train()
