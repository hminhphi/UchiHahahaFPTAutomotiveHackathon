# Hướng Dẫn Tạo Nydus Blueprint, Container, HMI & Telemetry Streaming cho CarSky Demo

**Mục tiêu:** Dựng một hệ thống demo hoàn chỉnh trên CarSky gồm: Container bridge nhận coaching command, Android Automotive HMI hiển thị cảnh báo, telemetry streaming từ FleetIQ API lên dashboard, và các container phụ trợ.

---

## 1. Tổng Quan Kiến Trúc Demo

```
┌─────────────────────────────────────────────────────────────────────┐
│  CAR SKY ROOM (Kubernetes)                                          │
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐ │
│  │ coaching-     │   │ vehicle-     │   │ fleetiq-aaos             │ │
│  │ bridge        │   │ signals      │   │ (Skycraft VM)            │ │
│  │ (Container)   │   │ (KUKSA)      │   │                          │ │
│  │              │   │              │   │  ┌────────────────────┐  │ │
│  │  Port 8090   │   │  Port 55555  │   │  │ FleetIQ Guardian   │  │ │
│  │  /v1/coaching│◄──│  VSS gRPC    │◄──│  │ APK (AAOS)         │  │ │
│  │  /health     │   │              │   │  │                    │  │ │
│  └──────┬───────┘   └──────┬───────┘   │  │ Poll bridge 1s    │  │ │
│         │                  │           │  │ Show severity      │  │ │
│  ┌──────┴──────────────────┴───────────┴──┐ │ ACKNOWLEDGE btn   │  │ │
│  │         room-l2 (Ethernet Bridge)       │ └────────────────────┘  │ │
│  │         Subnet: 10.99.0.0/24           │                         │ │
│  └────────────────────────────────────────┘                         │
└─────────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌──────────────────┐        ┌──────────────────────┐
│ FleetIQ API      │        │ coaching-worker       │
│ (FastAPI:8000)   │        │ (Python)              │
│                  │        │                      │
│ /api/v1/trips    │        │ CarSkyAdapter        │
│ /api/v1/vehicles │        │ POST /api/rooms/...   │
│ /api/v1/drivers  │        │ X-API-Key header      │
└──────────────────┘        └──────────────────────┘
```

---

## 2. Build & Push Artifacts

### 2.1 Coaching Bridge Container

Bridge là HTTP server Python nhận coaching command từ FleetIQ, lưu trữ, và phục vụ cho HMI Android.

**Build image:**

```powershell
# Từ thư mục gốc dự án
docker build -f apps/carsky-hmi/carsky/bridge/Dockerfile -t fleetiq/carsky-coaching-bridge:0.1.0 apps/carsky-hmi/carsky/bridge
```

**Test local:**

```powershell
docker run --rm -p 8090:8090 fleetiq/carsky-coaching-bridge:0.1.0

# Test health
curl http://localhost:8090/health

# Gửi coaching command
curl -X POST http://localhost:8090/v1/coaching `
  -H "Content-Type: application/json" `
  -d '{"schema_version":"1.0","command_id":"cmd-001","vehicle_id":"vehicle-1","priority":5,"title":"Collision risk","message":"Brake now. Increase distance.","dedupe_key":"demo.cmd-001","expires_at":"2026-12-31T23:59:59Z"}'

# Kiểm tra current command
curl "http://localhost:8090/v1/coaching/current?vehicle_id=vehicle-1"

# Gửi acknowledgement
curl -X POST http://localhost:8090/v1/coaching/cmd-001/ack
```

**Push lên CarSky Registry (Zot):**

```powershell
# Lấy Zot hostname từ CarSky Dashboard → Registry
$ZOT_HOST = "<your-zot-hostname>"

docker tag fleetiq/carsky-coaching-bridge:0.1.0 "$ZOT_HOST/fleetiq/carsky-coaching-bridge:0.1.0"
docker login "$ZOT_HOST" -u "<zot-username>" -p "<zot-api-key>"
docker push "$ZOT_HOST/fleetiq/carsky-coaching-bridge:0.1.0"
```

### 2.2 FleetIQ Guardian HMI APK

**Build APK:**

```powershell
docker build -f apps/carsky-hmi/Dockerfile -t fleetiq/carsky-hmi-builder apps/carsky-hmi
# APK nằm trong image tại /fleetiq-carsky-hmi.apk

# Extract APK ra ngoài
docker create --name tmp-hmi fleetiq/carsky-hmi-builder
docker cp tmp-hmi:/fleetiq-carsky-hmi.apk ./fleetiq-carsky-hmi.apk
docker rm tmp-hmi
```

**Upload APK lên CarSky Artifacts:**

1. Vào CarSky Dashboard → **Artifacts**
2. Chọn **New Artifact** → loại **APK**
3. Upload file `fleetiq-carsky-hmi.apk`
4. Ghi lại **Artifact ID** (VD: `apk-fleetiq-hmi-v1`)

### 2.3 VSS Schema (nếu cần custom signal)

Tạo file `fleetiq-vss.json`:

```json
{
  "Vehicle": {
    "Cabin": {
      "Infotainment": {
        "HMI": {
          "CurrentCommand": {
            "datatype": "string",
            "type": "sensor",
            "description": "Current coaching command from FleetIQ bridge"
          }
        }
      }
    }
  }
}
```

Upload lên CarSky Artifacts → loại **VSS Schema**.

---

## 3. Tạo Nydus Blueprint

### 3.1 Import Template

Vào **Nydus** → **Blueprints** → **Import**, chọn file `apps/carsky-hmi/carsky/blueprint.example.json`.

### 3.2 Thay Placeholder

Sau khi import, thay tất cả placeholder trong JSON:

| Placeholder | Giá trị thực tế |
|---|---|
| `<CARSKY_ANDROID_AUTOMOTIVE_ARTIFACT_ID>` | Artifact ID của Android Automotive image từ organizer |
| `<FLEETIQ_VSS_ARTIFACT_ID>` | Artifact ID của VSS Schema (nếu có) |
| `<FLEETIQ_HMI_APK_ARTIFACT_ID>` | Artifact ID của APK đã upload |
| `<ZOT_HOST>/fleetiq/carsky-coaching-bridge:0.1.0` | Image tag đã push lên Zot |

### 3.3 4 Node Bắt Buộc

| Node Key | Type | Vai trò |
|---|---|---|
| `coaching-bridge` | CONTAINER | HTTP server nhận coaching command, phục vụ HMI |
| `vehicle-signals` | KUKSA_BROKER | VSS signal broker, kết nối bridge ↔ AAOS |
| `fleetiq-aaos` | SKYCRAFT | Android Automotive VM chạy FleetIQ Guardian APK |
| `room-l2` | ETHERNET_BRIDGE | L2 switch ảo, subnet `10.99.0.0/24` |

### 3.4 Cấu Hình Pin & Edge

```
coaching-bridge.ethernet ──► room-l2.bridge
vehicle-signals.ethernet ──► room-l2.bridge
fleetiq-aaos.ethernet    ──► room-l2.bridge
coaching-bridge.coaching-vss ──► vehicle-signals.vss
vehicle-signals.vss       ──► fleetiq-aaos.vss
```

### 3.5 Thêm Screen Widget

Trong phần **widgets**, đảm bảo có Screen widget gắn vào `fleetiq-aaos.screen` để xem màn hình AAOS.

### 3.6 Validate & Deploy

1. Nhấn **Validate** — đảm bảo không có lỗi topology
2. Nhấn **Deploy** → chọn **New Deployment**
3. Đợi tất cả node chuyển sang **Running**

---

## 4. Thêm Telemetry Container cho Demo

Để demo có dữ liệu thực tế, cần thêm container giả lập telemetry streaming vào blueprint.

### 4.1 Telemetry Simulator Container

Tạo file `Dockerfile.telemetry-sim`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN pip install httpx paho-mqtt
COPY telemetry_sim.py /app/
CMD ["python", "/app/telemetry_sim.py"]
```

Tạo file `telemetry_sim.py`:

```python
"""Simulated telemetry producer for CarSky demo."""
import json
import os
import time
from datetime import UTC, datetime
from uuid import uuid4

import httpx

API_URL = os.getenv("FLEETIQ_API_URL", "http://api:8000")
VEHICLE_ID = os.getenv("VEHICLE_ID", "vehicle-1")
DRIVER_ID = os.getenv("DRIVER_ID", "DRV-001")
INTERVAL_S = float(os.getenv("TELEMETRY_INTERVAL_S", "0.5"))


def create_session() -> str:
    session_id = f"LIVE-{uuid4().hex[:8]}"
    resp = httpx.post(
        f"{API_URL}/api/v1/ingest/live-sessions",
        json={
            "session_id": session_id,
            "vehicle_id": VEHICLE_ID,
            "driver_id": DRIVER_ID,
        },
        timeout=10,
    )
    resp.raise_for_status()
    trip_id = resp.json()["data"]["trip_id"]
    print(f"Created live session: {trip_id}")
    return trip_id


def stream_telemetry(trip_id: str):
    frame = 0
    speed = 0.0
    while True:
        speed = min(60, max(0, speed + (0.5 if frame % 20 < 10 else -0.8)))
        payload = {
            "frame_index": frame,
            "timestamp_s": frame * INTERVAL_S,
            "speed_kmh": round(speed, 1),
            "longitudinal_accel_mps2": round(0.5 if frame % 20 < 10 else -0.8, 2),
            "lateral_accel_mps2": round(0.1 if frame % 7 == 0 else 0.0, 2),
            "yaw_deg": round(frame * 0.3 % 360, 1),
        }
        try:
            resp = httpx.post(
                f"{API_URL}/api/v1/ingest/live-sessions/{trip_id}/telemetry",
                json=payload,
                timeout=5,
            )
            if resp.status_code == 202:
                print(f"Frame {frame}: speed={speed:.1f} km/h")
        except Exception as e:
            print(f"Telemetry error: {e}")
        frame += 1
        time.sleep(INTERVAL_S)


if __name__ == "__main__":
    trip = create_session()
    stream_telemetry(trip)
```

### 4.2 Build & Push Telemetry Simulator

```powershell
docker build -f Dockerfile.telemetry-sim -t fleetiq/telemetry-sim:0.1.0 .
docker tag fleetiq/telemetry-sim:0.1.0 "$ZOT_HOST/fleetiq/telemetry-sim:0.1.0"
docker push "$ZOT_HOST/fleetiq/telemetry-sim:0.1.0"
```

### 4.3 Thêm vào Blueprint

Thêm node mới vào `nodes` array:

```json
{
  "key": "telemetry-sim",
  "type": "CONTAINER",
  "config": {
    "image": "<ZOT_HOST>/fleetiq/telemetry-sim:0.1.0",
    "command": ["python", "/app/telemetry_sim.py"],
    "env": {
      "FLEETIQ_API_URL": "http://api:8000",
      "VEHICLE_ID": "vehicle-1",
      "DRIVER_ID": "DRV-001",
      "TELEMETRY_INTERVAL_S": "0.5"
    }
  },
  "pins": [
    {"key": "ethernet", "type": "ETHERNET", "direction": "BIDIRECTIONAL"}
  ]
}
```

Thêm edge: `"from": "telemetry-sim.ethernet", "to": "room-l2.bridge"`

---

## 5. HMI Hiển Thị & Tương Tác

### 5.1 Luồng Hoạt Động

```
coaching-worker                     coaching-bridge               fleetiq-aaos (APK)
     │                                    │                             │
     │ POST /v1/coaching                  │                             │
     │ {priority:5, title:"Collision"}    │                             │
     ├───────────────────────────────────►│                             │
     │                                    │  store + dedupe             │
     │                                    │                             │
     │                                    │        GET /v1/coaching/    │
     │                                    │        current?vehicle_id=  │
     │                                    │◄────────────────────────────┤ (poll 1s)
     │                                    │                             │
     │                                    │  200 {severity:5, title...} │
     │                                    ├─────────────────────────────►
     │                                    │                             │
     │                                    │   POST /v1/coaching/cmd/ack │
     │                                    │◄────────────────────────────┤ (driver tap)
     │                                    │                             │
     │                                    │   200 {acknowledged:true}   │
     │                                    ├─────────────────────────────►
```

### 5.2 APK Build Configuration

Trước khi build APK, cấu hình bridge URL trong `gradle.properties`:

```properties
# Android emulator loopback → bridge container
FLEETIQ_BRIDGE_URL=http://10.0.2.2:8090
```

Trong CarSky, bridge chạy trên cùng Ethernet bridge nên AAOS có thể gọi `http://coaching-bridge:8090`.

### 5.3 Các Mức Severity

| Severity | Màu UI | Hành vi |
|---|---|---|
| 1-2 | Xanh lá | Hiển thị title + message đầy đủ |
| 3 | Vàng | Hiển thị title + message đầy đủ |
| 4 | Cam | Chỉ hiển thị title, message rút gọn |
| 5 | Đỏ | Chỉ hiển thị action phrase ngắn (`allowLongExplanation=false`) |

---

## 6. Streaming Telemetry Lên Hệ Thống

### 6.1 Các Kênh Streaming

| Kênh | Protocol | Dùng cho |
|---|---|---|
| MQTT `fleetiq/v1/vehicles/{id}/telemetry` | MQTT QoS 1 | Vehicle telemetry real-time |
| MQTT `fleetiq/v1/trips/{id}/risk` | MQTT QoS 1 | Risk events |
| WebSocket `ws://api:8000/ws/v1/trips/{id}/camera/{view}` | WebSocket | Live camera frames |
| WebSocket `ws://api:8000/ws/v1/trips/{id}/live` | WebSocket | Live state stream |
| HTTP POST `/api/v1/ingest/live-sessions/{id}/telemetry` | HTTP | Telemetry ingestion |
| HTTP POST `/api/v1/ingest/live-sessions/{id}/media` | HTTP | Media upload |

### 6.2 MQTT Telemetry Format

```json
{
  "schema_version": "1.0",
  "event_id": "evt-001",
  "correlation_id": "demo-correlation",
  "trip_id": "LIVE-abc123",
  "frame_index": 42,
  "producer": "telemetry-sim",
  "occurred_at": "2026-08-10T12:00:00Z",
  "event_type": "vehicle_state",
  "speed_mps": 12.5,
  "longitudinal_accel_mps2": 0.3,
  "lateral_accel_mps2": -0.1,
  "yaw_rate_radps": 0.05
}
```

### 6.3 Camera Frame Streaming (WebSocket)

Frame format: `[4-byte metadata length][JSON metadata][JPEG bytes]`

```python
import struct, json

metadata = json.dumps({
    "schema_version": "1.0",
    "frame_index": 42,
    "occurred_at": "2026-08-10T12:00:00Z",
    "width": 1280,
    "height": 720,
    "correlation_id": "demo-correlation",
}).encode()

packet = struct.pack(">I", len(metadata)) + metadata + jpeg_bytes
# Send via WebSocket to ws://api:8000/ws/v1/trips/{trip_id}/camera/road_left?role=producer
```

### 6.4 Live Session Flow

```python
# 1. Tạo live session
POST /api/v1/ingest/live-sessions
{
  "session_id": "demo-session-01",
  "vehicle_id": "vehicle-1",
  "driver_id": "DRV-001"
}
# Response: {"data": {"trip_id": "LIVE-abc123", ...}}

# 2. Stream telemetry
POST /api/v1/ingest/live-sessions/LIVE-abc123/telemetry
{
  "frame_index": 0,
  "timestamp_s": 0.0,
  "speed_kmh": 42.0,
  ...
}

# 3. Upload media frame
POST /api/v1/ingest/live-sessions/LIVE-abc123/media
{
  "view": "road_left",
  "sequence": 0,
  "content_type": "image/jpeg",
  "media_bytes": "<base64>"
}
```

---

## 7. Docker Compose Local Demo

### 7.1 Khởi Động Full Stack

```powershell
# Core services + CarSky bridge
docker compose --profile full up -d --build

# Kiểm tra trạng thái
docker compose ps

# Chạy smoke test
uv run python infra/compose/smoke_test.py
```

### 7.2 Test Coaching End-to-End

```powershell
# Gửi coaching command severity 5
$commandId = [guid]::NewGuid().ToString()
$body = @{
  schema_version = "1.0"
  command_id = $commandId
  vehicle_id = "vehicle-1"
  priority = 5
  title = "Collision risk"
  message = "Brake now. Increase distance."
  dedupe_key = "demo.$commandId"
  expires_at = (Get-Date).ToUniversalTime().AddMinutes(5).ToString("o")
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8090/v1/coaching" -Method Post -Body $body -ContentType "application/json"

# Kiểm tra current command
Invoke-RestMethod "http://localhost:8090/v1/coaching/current?vehicle_id=vehicle-1"

# Gửi acknowledgement
Invoke-RestMethod -Uri "http://localhost:8090/v1/coaching/$commandId/ack" -Method Post
```

---

## 8. Deploy Lên CarSky

### 8.1 Checklist Trước Khi Deploy

- [ ] Bridge image đã push lên Zot Registry
- [ ] APK đã upload lên CarSky Artifacts
- [ ] Android Automotive image artifact đã được organizer cấp
- [ ] VSS Schema artifact đã upload (nếu dùng custom signal)
- [ ] Blueprint đã import vào Nydus, thay hết placeholder
- [ ] Blueprint validate không lỗi

### 8.2 Các Bước Deploy

1. **Nydus** → Chọn blueprint → **Deploy** → **New Deployment**
2. Đợi tất cả node **Running** (nếu `ImagePullBackOff` → kiểm tra Zot tag)
3. Vào **Devices** → Attach Skycraft `fleetiq-aaos` vào Room
4. Mở **Screen widget** → xác nhận AAOS boot vào FleetIQ Guardian
5. Test bridge health qua conduit:
   ```
   https://<car-sky-host>/conduit/http/<room-id>/coaching-bridge/8090/health
   ```
6. Gửi coaching command test severity 5, xác nhận hiển thị trên HMI
7. Nhấn **ACKNOWLEDGE** trên HMI, xác nhận bridge trả về `acknowledged: true`

### 8.3 Cấu Hình Coaching Worker Production

Set environment variables cho coaching-worker:

```bash
CARSKY_BASE_URL=https://<car-sky-host>
CARSKY_API_KEY=<car-sky-api-key>
CARSKY_ROOM_ID=<room-id>
CARSKY_NODE_KEY=coaching-bridge
```

---

## 9. Troubleshooting

| Vấn đề | Nguyên nhân | Cách fix |
|---|---|---|
| `ImagePullBackOff` | Sai Zot hostname hoặc tag | `docker pull <zot-host>/fleetiq/...` test local |
| Bridge không nhận command | Sai port/pin config | Kiểm tra `exposedPorts` trong blueprint |
| HMI không hiển thị | APK không kết nối được bridge | Kiểm tra `CARSKY_BRIDGE_URL` trong gradle.properties |
| Telemetry không stream | MQTT broker không reachable | Kiểm tra MQTT host/port trong container env |
| APK crash | Android SDK version mismatch | Đảm bảo compileSdk=35, minSdk=29 |
| Screen widget đen | Skycraft VM chưa boot xong | Đợi 2-3 phút, kiểm tra node status |
| Duplicate coaching | Dedupe key không unique | Dùng `{event_id}-{timestamp}` làm dedupe_key |

---

## 10. Tài Liệu Tham Khảo

- **Blueprint template:** `apps/carsky-hmi/carsky/blueprint.example.json`
- **Bridge code:** `apps/carsky-hmi/carsky/bridge/bridge.py`
- **HMI APK code:** `apps/carsky-hmi/app/src/main/java/io/fleetiq/hmi/`
- **Deploy runbook:** `docs/runbooks/carsky-deploy.md`
- **CarSky Platform docs:** `docs/reference/carsky/Car-Sky-Platform.html`
- **Digital Cockpit guide:** `docs/reference/carsky/Digital-Cockpit.html`
- **Coaching adapter:** `services/coaching-worker/src/fleetiq_coaching/carsky.py`
- **Smoke test:** `infra/compose/smoke_test.py`
- **Compose config:** `compose.yaml`