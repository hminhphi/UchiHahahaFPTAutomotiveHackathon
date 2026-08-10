# FleetIQ Guardian - CarSky HMI Integration

**Android Automotive Human-Machine Interface for FleetIQ Guardian Fleet Safety Platform**

---

## Overview

This package contains the CarSky platform integration for FleetIQ Guardian, enabling in-vehicle driver coaching and trip intelligence display through Android Automotive OS (AAOS).

### What's Included

- **Android Automotive HMI APK** — In-vehicle dashboard for driver coaching alerts, trip scores, and evidence review
- **Coaching Bridge Container** — Python microservice bridging fleet backend API to in-room vehicle signals
- **Nydus Blueprints** — CarSky Room topology definitions (simple & full VSS versions)
- **Deployment Documentation** — Quick start guide, full deployment reference, troubleshooting

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CarSky Room                          │
│                                                         │
│  ┌──────────────┐      ┌──────────────┐               │
│  │ Coaching     │ HTTP │ Android Auto │               │
│  │ Bridge       │─────▶│ Skycraft VM  │               │
│  │ (Container)  │      │              │               │
│  │ :8090        │      │ + HMI APK    │               │
│  └──────────────┘      └──────────────┘               │
│         │                      │                       │
│         └──────────────────────┘                       │
│          Ethernet Bridge (L2)                          │
└─────────────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
   Fleet Backend         ADB Tunnel
   (Trip Analysis)       (Install/Debug)
```

### Components

| Component | Type | Purpose |
|-----------|------|---------|
| **HMI APK** | Android App | Driver-facing UI for coaching alerts, trip scores, evidence frames |
| **Coaching Bridge** | Docker Container | Polls fleet backend API, exposes REST API for HMI consumption |
| **AAOS Skycraft VM** | Virtual Machine | Android Automotive OS runtime hosted on CarSky platform |
| **Ethernet Bridge** | Network Node | L2 network connecting all Room components |

---

## Quick Start

### Prerequisites

- CarSky account with Dashboard access
- Docker installed and configured
- ADB tools installed
- 20 minutes for first deployment

### 5-Minute Deployment

```bash
# 1. Push coaching bridge container
cd apps/carsky-hmi
docker login registry.hackathon-1.carsky.io
docker build -t registry.hackathon-1.carsky.io/fleetiq/carsky-coaching-bridge:0.1.0 .
docker push registry.hackathon-1.carsky.io/fleetiq/carsky-coaching-bridge:0.1.0

# 2. Import blueprint to CarSky Dashboard
# Upload: apps/carsky-hmi/carsky/blueprint-simple.json

# 3. Deploy Room from blueprint
# Name: fleetiq-demo-room

# 4. Install HMI APK via ADB
adb connect <room-id>.carsky.io:5555
adb install -r artifacts/fleetiq-carsky-hmi.apk
adb shell am start -n ai.fleetiq.carsky/.MainActivity
```

**👉 See [QUICKSTART.md](./carsky/QUICKSTART.md) for detailed steps**

---

## File Structure

```
apps/carsky-hmi/
├── carsky/
│   ├── blueprint.json              # Full blueprint with KUKSA VSS
│   ├── blueprint-simple.json       # Simplified HTTP-only blueprint
│   ├── DEPLOYMENT.md               # Full deployment guide + troubleshooting
│   ├── QUICKSTART.md               # 5-minute quick start guide
│   └── SUMMARY.md                  # Integration summary & checklist
├── src/
│   └── bridge.py                   # Coaching bridge Python service
├── Dockerfile                      # Coaching bridge container
├── requirements.txt                # Python dependencies
└── README.md                       # This file

artifacts/
└── fleetiq-carsky-hmi.apk         # Android Automotive HMI (21.4 MB)
```

---

## Features

### HMI Capabilities

- ✅ **Real-time Coaching Alerts** — Visual/audio notifications for unsafe driving behavior
- ✅ **Trip Score Display** — Breakdown by driver attention, collision risk, vehicle handling
- ✅ **Evidence Review** — Synchronized multi-view camera + depth + TTC overlay
- ✅ **Driver Dashboard** — At-a-glance metrics, recent trips, risk trends
- ✅ **HTTP Polling** — Fetches latest coaching commands from bridge API every 2 seconds

### Coaching Bridge Capabilities

- ✅ **Fleet Backend Integration** — Polls trip analysis API for latest events
- ✅ **HTTP REST API** — Exposes `/v1/coaching/current` for HMI consumption
- ✅ **Event Aggregation** — Consolidates TTC, near-miss, driver state into unified commands
- ✅ **Priority Queue** — Ensures critical alerts surface first
- ✅ **Health Monitoring** — `/health` endpoint for Room status checks

---

## Deployment Options

### Option 1: Simple Blueprint (Recommended for Demo)

**Use:** `blueprint-simple.json`

**Topology:**
- 1 Container (coaching-bridge)
- 1 Skycraft VM (AAOS + HMI APK)
- 1 Ethernet Bridge

**Pros:**
- ✅ No VSS artifact required
- ✅ Faster deployment
- ✅ Easier debugging

**Best for:** Hackathon demo, proof-of-concept

### Option 2: Full Blueprint (Production)

**Use:** `blueprint.json`

**Topology:**
- 1 Container (coaching-bridge)
- 1 KUKSA VSS Broker
- 1 Skycraft VM (AAOS + HMI APK)
- 1 Ethernet Bridge

**Pros:**
- ✅ Standard automotive signal architecture
- ✅ Vehicle signal passthrough (VHAL → VSS → HMI)
- ✅ Scalable for multi-ECU scenarios

**Requires:** Custom VSS schema artifact

**Best for:** Production deployment, OEM integration

---

## API Reference

### Coaching Bridge API

#### `GET /v1/coaching/current`

Get the current coaching command for display in HMI.

**Response:**
```json
{
  "command": "reduce_speed",
  "severity": "high",
  "message": "Approaching curve at high speed",
  "timestamp": "2026-08-10T15:30:00Z",
  "metadata": {
    "tripId": "T01d",
    "frameIndex": 1234,
    "ttc": 1.8
  }
}
```

**Severity Levels:**
- `low` — Informational (green)
- `medium` — Warning (orange)
- `high` — Critical (red)
- `critical` — Immediate action required (flashing red)

#### `GET /health`

Health check endpoint for Room monitoring.

**Response:**
```json
{
  "status": "healthy",
  "fleetBackendReachable": true,
  "lastPollSuccess": "2026-08-10T15:29:58Z"
}
```

---

## Configuration

### Coaching Bridge Environment Variables

Edit blueprint before deploying:

```json
{
  "env": {
    "FLEET_BACKEND_URL": "https://your-fleet-api.com",
    "POLL_INTERVAL_SECONDS": "5",
    "LOG_LEVEL": "INFO"
  }
}
```

| Variable | Default | Description |
|----------|---------|-------------|
| `FLEET_BACKEND_URL` | `http://localhost:3000` | Fleet API endpoint |
| `POLL_INTERVAL_SECONDS` | `5` | Polling frequency |
| `MODE` | `http-only` | `http-only` or `vss` |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

### Skycraft Node Configuration

| Field | Value | Notes |
|-------|-------|-------|
| OS | `android` | Fixed |
| Artifact | `aaos` | Base AAOS image v0.0.1 |
| Architecture | `aarch64` | ARM64 |
| Display | `1920x1080` | Full HD |
| DPI | `160` | Standard density |

---

## Testing

### Test Coaching Alert

```bash
# Get Room's external IP from CarSky Dashboard
ROOM_IP=<room-external-ip>

# Fetch current coaching command
curl http://$ROOM_IP:8090/v1/coaching/current

# Expected: JSON response with command, severity, message
```

### Test HMI Connectivity

```bash
# Connect via ADB
adb connect <room-id>.carsky.io:5555

# Check if HMI is running
adb shell pm list packages | grep fleetiq

# View HMI logs
adb logcat | grep FleetIQ

# Restart HMI
adb shell am force-stop ai.fleetiq.carsky
adb shell am start -n ai.fleetiq.carsky/.MainActivity
```

---

## Troubleshooting

### HMI Not Appearing

**Symptoms:** Screen widget is blank or shows AAOS launcher

**Solutions:**
1. Wait 30 seconds for cold boot
2. Check if APK is installed: `adb shell pm list packages | grep fleetiq`
3. Manually launch: `adb shell am start -n ai.fleetiq.carsky/.MainActivity`
4. View logs: `adb logcat | grep -i fleetiq`

### Coaching API Not Reachable

**Symptoms:** HMI shows "Unable to connect to coaching service"

**Solutions:**
1. Verify coaching-bridge container status in Dashboard
2. Check container logs for errors
3. Test from host: `curl http://<room-ip>:8090/v1/coaching/current`
4. Verify Ethernet bridge connectivity

### APK Install Fails

**Symptoms:** `adb install` returns error

**Solutions:**
```bash
# Check storage
adb shell df -h /data

# Force reinstall with flags
adb install -r -t -d artifacts/fleetiq-carsky-hmi.apk
```

**👉 See [DEPLOYMENT.md](./carsky/DEPLOYMENT.md) for full troubleshooting guide**

---

## Demo Preparation

### Checklist

- [ ] Room deployed and status = Running
- [ ] HMI visible on screen widget
- [ ] Coaching alert tested and displaying
- [ ] Screenshots captured (3-5 key screens)
- [ ] Demo video recorded (30-60 seconds)
- [ ] Backup static demo prepared

### Screenshots to Capture

1. **Driver Dashboard** — Overview with score, alerts, recent trips
2. **Coaching Alert** — Active alert card with severity and message
3. **Trip Detail** — Score breakdown with evidence frames
4. **Risk Timeline** — TTC chart with event markers
5. **Evidence Panel** — Multi-view synchronized frames

---

## Integration with Fleet Backend

The coaching bridge expects the following API endpoints on the fleet backend:

### `GET /api/v1/trips/{tripId}/coaching`

Returns coaching commands for a specific trip.

**Expected Response:**
```json
{
  "tripId": "T01d",
  "commands": [
    {
      "timestamp": "2026-08-10T15:30:00Z",
      "command": "reduce_speed",
      "severity": "high",
      "message": "Approaching curve at high speed",
      "metadata": {
        "frameIndex": 1234,
        "ttc": 1.8,
        "speed": 65
      }
    }
  ]
}
```

### `GET /api/v1/driver/{driverId}/latest-trip`

Returns the latest trip for a driver (for real-time monitoring).

---

## Roadmap

### Current (v0.1.0)

- ✅ HTTP-based coaching alert display
- ✅ Trip score breakdown
- ✅ Basic evidence frame viewer
- ✅ CarSky Room deployment

### Next (v0.2.0)

- ⏳ KUKSA VSS integration
- ⏳ Vehicle signal passthrough (VHAL → VSS → HMI)
- ⏳ Audio alerts (text-to-speech)
- ⏳ Driver profile management

### Future (v0.3.0)

- 🔮 Video streaming (live road camera feed)
- 🔮 In-HMI coaching history
- 🔮 Driver acknowledgment/feedback
- 🔮 Multi-language support

---

## Contributing

This is a hackathon project for **FPT Automotive Hackathon 2026**.

**Team:** FleetIQ Guardian  
**Challenge:** Driver Intelligence Platform (Challenge #3)

---

## License

Proprietary — FPT Automotive Hackathon 2026

---

## Support

- **Quick Start:** [QUICKSTART.md](./carsky/QUICKSTART.md)
- **Full Deployment:** [DEPLOYMENT.md](./carsky/DEPLOYMENT.md)
- **Integration Summary:** [SUMMARY.md](./carsky/SUMMARY.md)
- **Project Context:** See `AGENTS.md` and `docs/` at repository root
- **CarSky Platform:** https://hackathon-1.carsky.io

---

**Last Updated:** 2026-08-10  
**Version:** 0.1.0  
**Status:** ✅ Ready for Deployment
