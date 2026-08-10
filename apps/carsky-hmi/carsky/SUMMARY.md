# FleetIQ Guardian - CarSky Integration Summary

## 📦 Deliverables

### ✅ Ready to Deploy

| Artifact | Location | Size | Status |
|----------|----------|------|--------|
| **HMI APK** | `artifacts/fleetiq-carsky-hmi.apk` | 21.4 MB | ✅ Built |
| **Coaching Bridge Image** | `registry.hackathon-1.carsky.io/fleetiq/carsky-coaching-bridge:0.1.0` | ~150 MB | ⏳ Ready to push |
| **Simple Blueprint** | `apps/carsky-hmi/carsky/blueprint-simple.json` | 1.2 KB | ✅ Ready |
| **Full Blueprint** | `apps/carsky-hmi/carsky/blueprint.json` | 2.4 KB | ✅ Ready (requires VSS) |

### 📖 Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| **QUICKSTART.md** | 5-minute deployment guide | Developers, Demo |
| **DEPLOYMENT.md** | Full deployment reference with troubleshooting | DevOps, Production |
| **README.md** | Architecture overview | Judges, Technical reviewers |

---

## 🏗️ Architecture Overview

### Components

```
┌─────────────────────────────────────────────────┐
│              CarSky Room (Nydus)                │
│                                                 │
│  ┌─────────────────┐      ┌─────────────────┐ │
│  │ Coaching Bridge │      │ Android Auto    │ │
│  │ (Container)     │◄────►│ Skycraft VM     │ │
│  │                 │ HTTP │                 │ │
│  │ Port: 8090      │      │ + HMI APK       │ │
│  └─────────────────┘      └─────────────────┘ │
│         │                         │            │
│         └─────────┬───────────────┘            │
│                   │                            │
│         ┌─────────▼─────────┐                  │
│         │ Ethernet Bridge   │                  │
│         │ (L2 Network)      │                  │
│         └───────────────────┘                  │
└─────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
   Fleet Backend API    ADB Tunnel (5555)
   (trip analysis)      (APK install/debug)
```

### Data Flow

1. **Fleet Backend** → Coaching Bridge: Trip analysis results, TTC events, driver state
2. **Coaching Bridge** → HMI: HTTP REST API with coaching commands
3. **HMI** → Driver: Visual/audio alerts, trip score, evidence frames
4. **Optional**: Coaching Bridge → KUKSA VSS → HMI (for full VSS integration)

---

## 🎯 Deployment Options

### Option 1: Quick Demo (Recommended)

**Use:** `blueprint-simple.json`

**Pros:**
- ✅ No VSS artifact required
- ✅ HTTP-only communication (simpler)
- ✅ Faster deployment (2 nodes instead of 4)
- ✅ Easier debugging

**Cons:**
- ❌ No KUKSA VSS integration
- ❌ No vehicle signal passthrough

**Best for:** Hackathon demo, proof-of-concept, judging

### Option 2: Full Production

**Use:** `blueprint.json`

**Pros:**
- ✅ Full KUKSA VSS integration
- ✅ Standard automotive signal architecture
- ✅ Vehicle signal passthrough (VHAL → VSS → HMI)
- ✅ Scalable for multi-ECU scenarios

**Cons:**
- ❌ Requires custom VSS schema artifact
- ❌ More complex topology (4 nodes)
- ❌ Harder to debug

**Best for:** Production deployment, OEM integration

---

## 🚀 Deployment Checklist

### Pre-Deployment

- [ ] CarSky account credentials ready
- [ ] Docker installed and logged into `registry.hackathon-1.carsky.io`
- [ ] ADB tools installed (`adb --version`)
- [ ] APK built and verified at `artifacts/fleetiq-carsky-hmi.apk`
- [ ] Choose blueprint: `simple` or `full`

### Step 1: Container Registry

- [ ] Build coaching bridge: `docker build -t registry.hackathon-1.carsky.io/fleetiq/carsky-coaching-bridge:0.1.0 apps/carsky-hmi`
- [ ] Push image: `docker push registry.hackathon-1.carsky.io/fleetiq/carsky-coaching-bridge:0.1.0`
- [ ] Verify image appears in CarSky Dashboard → Container Registry

### Step 2: Blueprint Import

- [ ] Open CarSky Dashboard → Nydus → Blueprints
- [ ] Click **Import Blueprint**
- [ ] Upload `blueprint-simple.json` (or `blueprint.json` for full version)
- [ ] Verify blueprint shows correct node count (2 for simple, 4 for full)

### Step 3: Room Deployment

- [ ] Select blueprint → **Deploy Room**
- [ ] Room name: `fleetiq-demo-room`
- [ ] Wait for status: **Running**
- [ ] Verify widget `hmi-screen` shows Android boot

### Step 4: APK Installation

- [ ] Open `fleetiq-aaos` node → **ADB Tunnel**
- [ ] Copy tunnel endpoint: `<room-id>.carsky.io:5555`
- [ ] Connect: `adb connect <room-id>.carsky.io:5555`
- [ ] Install: `adb install -r artifacts/fleetiq-carsky-hmi.apk`
- [ ] Launch: `adb shell am start -n ai.fleetiq.carsky/.MainActivity`
- [ ] Verify HMI appears on `hmi-screen` widget

### Step 5: Integration Testing

- [ ] Test coaching API: `curl http://<room-ip>:8090/v1/coaching/current`
- [ ] Verify HMI polls API and displays alerts
- [ ] Test with mock trip data from fleet backend
- [ ] Capture screenshots for documentation

### Demo Preparation

- [ ] Screenshot: Driver dashboard with score
- [ ] Screenshot: Coaching alert in action
- [ ] Screenshot: Trip detail with evidence frames
- [ ] Video: HMI responding to coaching commands (30 sec)
- [ ] Share Room URL with judges (if supported)

---

## 🔧 Configuration Reference

### Environment Variables (Coaching Bridge)

| Variable | Default | Description |
|----------|---------|-------------|
| `FLEET_BACKEND_URL` | `http://localhost:3000` | Fleet API endpoint |
| `POLL_INTERVAL_SECONDS` | `5` | How often to poll fleet API |
| `MODE` | `http-only` | `http-only` or `vss` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Skycraft Node Config

| Field | Value | Notes |
|-------|-------|-------|
| OS | `android` | Fixed |
| Artifact | `aaos` | Base AAOS image (v0.0.1) |
| Architecture | `aarch64` | ARM64 |
| Display Width | `1920` | Pixels |
| Display Height | `1080` | Pixels |
| Display DPI | `160` | Standard density |

### Network Ports

| Service | Port | Protocol | Exposed |
|---------|------|----------|---------|
| Coaching Bridge API | 8090 | HTTP | Yes (external) |
| ADB Tunnel | 5555 | TCP | Yes (external) |
| KUKSA VSS (if enabled) | 55555 | WebSocket | Internal only |

---

## 🧪 Testing Scenarios

### Scenario 1: Coaching Alert Display

**Goal:** Verify HMI receives and displays coaching commands

**Steps:**
1. Deploy Room with blueprint
2. Install HMI APK
3. Send test command to coaching API:
   ```bash
   curl -X POST http://<room-ip>:8090/v1/coaching/command \
     -H "Content-Type: application/json" \
     -d '{"command":"reduce_speed","severity":"high","message":"Approaching curve at high speed"}'
   ```
4. Verify alert appears in HMI within 2 seconds

**Expected:** Orange/red alert card with message and severity indicator

### Scenario 2: Trip Score Display

**Goal:** Verify HMI can fetch and display trip score breakdown

**Steps:**
1. Send trip analysis to fleet backend API
2. HMI polls coaching bridge for latest trip
3. Verify trip score appears with breakdown:
   - Driver attention: 85/100
   - Collision risk: 70/100
   - Vehicle handling: 90/100
   - Overall: 82/100

**Expected:** Score card with color-coded categories

### Scenario 3: Evidence Frame Sync

**Goal:** Verify HMI can load and display evidence frames

**Steps:**
1. Upload trip with near-miss event to fleet backend
2. HMI receives event notification
3. User taps event card
4. HMI fetches evidence frame URLs
5. Displays road camera + depth + TTC overlay

**Expected:** Synchronized multi-view evidence panel

---

## 📊 Success Metrics

### Deployment Success

- ✅ Room status = `Running`
- ✅ All nodes healthy (green status)
- ✅ Widget shows HMI interface (not blank/black)
- ✅ Coaching API returns valid JSON response
- ✅ HMI displays coaching alert within 2 seconds of API update

### Demo Quality

- ✅ HMI loads in under 5 seconds
- ✅ Coaching alerts are readable and visually clear
- ✅ No visible crashes or ANR (Application Not Responding)
- ✅ Screen recording captures fluid UI (30+ fps)

### Integration Health

- ✅ Coaching bridge logs show successful fleet backend polling
- ✅ HMI logs show successful HTTP requests to coaching bridge
- ✅ Network latency < 100ms between nodes
- ✅ No 404 or 500 errors in logs

---

## 🐛 Known Issues

### Issue 1: HMI Slow to Launch

**Symptom:** APK installed but takes 10+ seconds to appear

**Cause:** AAOS cold boot + app initialization

**Workaround:** Wait 30 seconds after `am start` before checking screen widget

### Issue 2: Coaching API 404

**Symptom:** HMI can't reach `http://coaching-bridge:8090`

**Cause:** DNS not resolving container name within Room network

**Workaround:** Use container IP instead:
```bash
# Inside AAOS VM
adb shell ip route | grep default
# Use bridge IP (e.g., 10.0.2.1)
```

Update HMI config to use `http://10.0.2.1:8090` instead of hostname.

### Issue 3: Screen Widget Refresh

**Symptom:** Widget shows stale/frozen frame

**Cause:** CarSky Dashboard caching

**Workaround:** Click **Refresh** button on widget every 10 seconds during demo

---

## 📞 Support & References

### Documentation

- **Quick Start:** `QUICKSTART.md` (5 minutes)
- **Full Deployment:** `DEPLOYMENT.md` (with troubleshooting)
- **Project Context:** `AGENTS.md`, `docs/`

### External Resources

- **CarSky Platform:** https://hackathon-1.carsky.io
- **KUKSA VSS:** https://github.com/eclipse/kuksa.val
- **Android Automotive:** https://source.android.com/devices/automotive

### Hackathon Contact

- **Organizer:** FPT Automotive Hackathon Team
- **Platform Support:** CarSky Discord/Slack channel
- **Project Repository:** (private repo URL)

---

## ✅ Final Checklist

Before presenting to judges:

- [ ] Room deployed and running
- [ ] HMI visible on screen widget
- [ ] Coaching alert tested and working
- [ ] Trip score displays correctly
- [ ] Screenshots captured (3-5 key screens)
- [ ] Demo video recorded (30-60 seconds)
- [ ] Backup static demo ready (in case Room fails)
- [ ] Architecture diagram printed/displayed
- [ ] Team roles assigned for live demo

---

**Last Updated:** 2026-08-10  
**Version:** 1.0  
**Status:** ✅ Ready for Deployment
