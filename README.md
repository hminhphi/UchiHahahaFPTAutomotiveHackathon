# FleetIQ Guardian: Remote Driver Intelligence & Collision Risk Platform

> **FPT Automotive Hackathon 2026 — Team UchiHahaha**  
> Main Challenge Target: **Challenge #3 — Driver Intelligence Platform**  
> Core Integrated Modules: **Challenge #1 (Safe Driving Score)** & **Challenge #2 (Vision Collision Risk)**

---

## 🚘 Overview

**FleetIQ Guardian** is an out-car remote fleet intelligence platform designed for Fleet Managers and OEM Analytics teams. It converts multi-view road-facing RGB cameras, in-cabin driver monitoring streams, depth maps, camera calibration, and simulated sensor-fusion telemetry into explainable, timestamped safety insights.

The platform answers three fundamental fleet management questions:
1. **Which driver, vehicle, or trip is currently risky?**
2. **Why is the risk high, backed by timestamped visual and sensor evidence?**
3. **What coaching or operational action should be taken next?**

---

## ✨ Key Capabilities

- **Explainable Safe-Driving Score Engine (0–100):** Combines a Temporal Convolutional Network (TCN AI) with a Context-Aware Rule Engine to score trips while providing auditable deduction breakdowns for driver distraction, drowsiness, harsh braking/accel, tailgating, and lane drift.
- **Vision-Based Collision Risk Monitor:** Computes frame-level Time-To-Collision (TTC) using stereo RGB cameras, depth maps, lead-object ROI tracking, and ego vehicle telemetry.
- **Driver Intelligence Signal Fusion:** Aligns cabin driver state (`attentive`, `distracted`, `drowsy`) with road-facing collision risks to detect high-severity compound events.
- **CarSky Nydus SDV Integration:** Native deployment as a Docker container on the CarSky SDV platform, communicating with in-vehicle gateways via **COVESA KUKSA VSS Databroker** (`Vehicle.Speed`, `Vehicle.Cabin.Infotainment.HMI.Warning`).
- **Embedded Web Dashboard & REST API:** Self-contained HTTP server (port `8080`) providing a dark-mode real-time Fleet Operations UI and `/api/telemetry` JSON endpoints.

---

## 🏗️ System Architecture

```text
[ Multi-view Road RGB ]    [ Cabin Camera ]    [ Depth Map ]    [ Ego Telemetry ]
          │                       │                  │                  │
          └───────────────────────┴─────────┬────────┴──────────────────┘
                                            ▼
                           ┌─────────────────────────────────┐
                           │   FleetIQ Guardian AI Engine    │
                           │  (TCN Risk + Perception Fusion) │
                           └────────────────┬────────────────┘
                                            │
                      ┌─────────────────────┴─────────────────────┐
                      ▼                                           ▼
          ┌───────────────────────┐                   ┌───────────────────────┐
          │ Embedded Web Dashboard│                   │  COVESA KUKSA VSS     │
          │ & REST API (Port 8080)│                   │ Databroker Network    │
          └───────────────────────┘                   └───────────┬───────────┘
                                                                  ▼
                                                      ┌───────────────────────┐
                                                      │  Android IVI HMI /    │
                                                      │  AGL Cluster Warning  │
                                                      └───────────────────────┘
```

---

## 📁 Repository Structure

```text
UchiHahahaFPTAutomotiveHackathon/
├── Dockerfile                   # Multi-stage Docker build optimized for CPU/GPU
├── README.md                    # Project documentation & execution guide
├── pyproject.toml               # Python 3.12 project configuration and dependencies
├── models/
│   └── tcn_risk_model.pth       # Trained TCN AI Safety Risk Model weights
├── scripts/
│   ├── carsky_agent.py          # Main CarSky Nydus Agent, Web Dashboard & KUKSA sync
│   ├── render_trip_dashboard.py # Synchronized multi-camera dataset visualizer
│   ├── live_carsky_dashboard.py # OpenCV live telemetry window
│   ├── train_tcn.py             # PyTorch TCN Model definition and training script
│   └── roadface/                # Detection, relabeling, depth, tracking, and TTC pipeline
├── data/                        # Sample & Full trip datasets (ignored by Git)
├── docs/                        # Proposal plans, signal mappings, and architecture docs
└── tests/                       # Unit tests for parsers, scoring, and TTC logic
```

---

## 🛠️ Requirements & Environment Setup

- **Python:** 3.12
- **Package Manager:** `uv` (recommended) or `pip`
- **Containerization:** Docker Desktop / Docker Engine

### 1. Local Environment Setup

Clone the repository and sync dependencies using `uv`:

```bash
# Install dependencies
uv sync

# (Optional) Install CUDA and perception extras for model training / relabeling
uv sync --extra cu130 --extra roadface
```

### 2. Dataset Placement

Place the provided dataset under the `data/` folder:

```text
data/
  Practice_Dataset/
    Practice_Dataset/
      T01-Sample/
        T01-Sample.json.gz
        driver/
        kitti/
          image_2/
          image_3/
          depth/
          calib/
          label_2/
```

---

## 🚀 How to Run

### Option A: Run the Main CarSky Agent & Web Dashboard (Recommended)

To launch the perception engine, KUKSA auto-discovery worker, and embedded Web Dashboard:

```bash
uv run python scripts/carsky_agent.py
```

Once started:
- **Console:** Live safety stream log (Speed, TTC, Driver State, Score, Risk Level).
- **Web Dashboard:** Open `http://localhost:8080` in your web browser.
- **REST API:** Request `http://localhost:8080/api/telemetry` for live JSON state.

---

### Option B: Deploy on CarSky Nydus Platform

1. **Build and push Docker Image:**

```bash
docker build -t registry.hackathon-1.carsky.io/uchi/fleetiq-guardian:v1.9 .
docker push registry.hackathon-1.carsky.io/uchi/fleetiq-guardian:v1.9
```

2. **CarSky Blueprint Configuration:**
   - Add a `Container` node (labeled `FleetIQ Guardian`).
   - Set image to `registry.hackathon-1.carsky.io/uchi/fleetiq-guardian:v1.9`.
   - Command: `.venv/bin/python scripts/carsky_agent.py`.
   - Connect the Ethernet pin (`eth`) to the in-vehicle switch.

3. **Deploy & Monitor:**
   - Click **Deploy** / **Redeploy** on the CarSky UI.
   - View live logs under **Logs: Container 1**.

---

### Option C: Run Synchronized Dataset Visualizer Player

To inspect road cameras, driver camera, depth map, and telemetry side-by-side:

```bash
# List available trips
uv run python scripts/render_trip_dashboard.py --list-trips

# Play trip T01-Sample in interactive window mode
uv run python scripts/render_trip_dashboard.py --trip T01-Sample --mode window
```

---

## 📡 VSS Signals & Alert Schema

FleetIQ Guardian interacts with the vehicle via COVESA Vehicle Signal Specification (VSS):

| VSS Path | Direction | Description |
| :--- | :--- | :--- |
| `Vehicle.Speed` | Published | Real-time vehicle speed (km/h) |
| `Vehicle.Cabin.Infotainment.HMI.Warning` | Actuated / Published | Back-to-car HMI alert message |

### Warning Alert Types:
- `CAUTION`: Minor risk / distraction detected at low speed.
- `COLLISION_WARNING`: High collision risk (TTC < 2.5s).
- `DROWSINESS_ALERT`: Driver asleep or severely drowsy.
- `CRITICAL_COLLISION_ALERT`: Imminent collision hazard (TTC < 1.5s).

---

## 🧪 Running Tests

Run the test suite to verify scoring rules, TTC computation, and dataset parsers:

```bash
uv run python -m unittest discover -s tests -v
```

---

## 📄 License & Team

- **Team:** UchiHahaha
- **Event:** FPT Automotive Hackathon 2026
- **Documentation:** For complete proposal details, see [docs/FULL_VERTICAL_PROPOSAL_PLAN.md](docs/FULL_VERTICAL_PROPOSAL_PLAN.md).
