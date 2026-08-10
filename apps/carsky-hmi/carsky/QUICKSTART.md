# FleetIQ Guardian - CarSky Quick Start

## 🚀 Fast Deployment (5 minutes)

Use this guide for fastest deployment using the simplified blueprint.

---

## Prerequisites

✅ **CarSky Account** with Dashboard access  
✅ **Docker** installed and configured  
✅ **ADB tools** installed (`adb --version`)  
✅ **Artifacts ready** in this repo:
  - `artifacts/fleetiq-carsky-hmi.apk` (21.4 MB)
  - `apps/carsky-hmi/carsky/blueprint-simple.json`

---

## Step 1: Push Container Image (2 min)

```bash
# Navigate to HMI directory
cd apps/carsky-hmi

# Login to CarSky registry
docker login registry.hackathon-1.carsky.io
# Username: <your-carsky-username>
# Password: <your-carsky-password>

# Build coaching bridge
docker build -t registry.hackathon-1.carsky.io/fleetiq/carsky-coaching-bridge:0.1.0 .

# Push to registry
docker push registry.hackathon-1.carsky.io/fleetiq/carsky-coaching-bridge:0.1.0
```

**✅ Verify:** Image appears in CarSky Dashboard → Container Registry

---

## Step 2: Import Blueprint (1 min)

1. Open CarSky Dashboard → **Nydus** → **Blueprints**
2. Click **Import Blueprint**
3. Upload: `apps/carsky-hmi/carsky/blueprint-simple.json`
4. Blueprint name: `fleetiq-guardian-simple`
5. Click **Save**

**What gets deployed:**

| Node | Type | Description |
|------|------|-------------|
| `coaching-bridge` | Container | Python HTTP API serving coaching commands |
| `fleetiq-aaos` | Skycraft | Android Automotive OS VM (base image) |
| `room-network` | Ethernet Bridge | L2 network connecting nodes |

**✅ Verify:** Blueprint appears in list with 3 nodes, 2 edges

---

## Step 3: Deploy Room (1 min)

1. In Nydus, select `fleetiq-guardian-simple` blueprint
2. Click **Deploy Room**
3. Room name: `fleetiq-demo-room`
4. Wait for status: **Running** (typically 30-60 seconds)

**✅ Verify:** 
- Room status = `Running`
- Widget `hmi-screen` shows Android boot animation

---

## Step 4: Install HMI APK via ADB (1 min)

### Open ADB Tunnel

1. In Room view, click on `fleetiq-aaos` node
2. Click **ADB** button → Copy tunnel endpoint
3. Format: `<room-id>.carsky.io:5555`

### Connect and Install

```bash
# Connect to Skycraft VM
adb connect <room-id>.carsky.io:5555

# Wait for "connected to <room-id>.carsky.io:5555"
adb devices

# Install FleetIQ HMI
adb install -r artifacts/fleetiq-carsky-hmi.apk

# Launch HMI
adb shell am start -n ai.fleetiq.carsky/.MainActivity
```

**✅ Verify:** Widget `hmi-screen` shows FleetIQ Guardian interface

---

## Step 5: Test Coaching API (30 sec)

### From your local machine:

```bash
# Get Room's external IP from CarSky Dashboard
# Navigate to Room → coaching-bridge node → Exposed Ports → Copy URL

curl http://<room-external-ip>:8090/v1/coaching/current
```

**Expected Response:**

```json
{
  "command": "focus_ahead",
  "severity": "medium",
  "message": "Please keep your attention on the road",
  "timestamp": "2026-08-10T15:30:00Z"
}
```

### From HMI (inside AAOS):

The HMI should automatically poll `http://coaching-bridge:8090/v1/coaching/current` every 2 seconds and display alerts.

**✅ Verify:** Coaching alert card appears in HMI

---

## 🎯 Demo Ready

Your FleetIQ Guardian system is now live:

- **HMI Screen:** CarSky Dashboard → Room → Widget `hmi-screen`
- **Coaching API:** `http://<room-ip>:8090/v1/coaching/current`
- **ADB Access:** `adb connect <room-id>.carsky.io:5555`

---

## Troubleshooting

### ❌ APK Install Fails

```bash
# Check storage
adb shell df -h /data

# Force reinstall
adb install -r -t -d artifacts/fleetiq-carsky-hmi.apk
```

### ❌ HMI Not Launching

```bash
# Check if installed
adb shell pm list packages | grep fleetiq

# View logs
adb logcat | grep -i fleetiq

# Force stop and restart
adb shell am force-stop ai.fleetiq.carsky
adb shell am start -n ai.fleetiq.carsky/.MainActivity
```

### ❌ Coaching Bridge Not Reachable

1. Check Container logs in CarSky Dashboard → `coaching-bridge` node → Logs
2. Verify port 8090 is exposed in node config
3. Check Ethernet bridge connectivity: all nodes should be on same L2 network

### ❌ Screen Widget Blank/Black

1. Wait 30 seconds for AAOS to fully boot
2. Click **Refresh** on widget
3. Check Skycraft node status = `Running`
4. Restart Skycraft node if needed

---

## Next Steps

### Connect to Real Fleet Backend

Edit `blueprint-simple.json` before deploying:

```json
"env": {
  "FLEET_BACKEND_URL": "https://your-actual-fleet-api.com",
  "POLL_INTERVAL_SECONDS": "5"
}
```

### Add VSS Support (Advanced)

For full KUKSA integration, use `blueprint.json` instead of `blueprint-simple.json`:

1. Create VSS schema artifact (see `DEPLOYMENT.md`)
2. Update blueprint with VSS artifact ID
3. Redeploy Room

### Prepare for Judging

1. **Take screenshots** of HMI showing:
   - Driver dashboard
   - Coaching alert
   - Trip detail view

2. **Record demo video:**
   - Show HMI responding to coaching API
   - Demonstrate trip scoring
   - Show evidence frames

3. **Share Room URL** with judges (if CarSky supports public Room links)

---

## Files Reference

- **Simple Blueprint:** `apps/carsky-hmi/carsky/blueprint-simple.json`
- **Full Blueprint:** `apps/carsky-hmi/carsky/blueprint.json`
- **Deployment Guide:** `apps/carsky-hmi/carsky/DEPLOYMENT.md`
- **HMI APK:** `artifacts/fleetiq-carsky-hmi.apk`
- **Bridge Dockerfile:** `apps/carsky-hmi/Dockerfile`

---

## Support

- **Full Documentation:** See `DEPLOYMENT.md`
- **Project Context:** See `AGENTS.md`, `docs/`
- **CarSky Docs:** https://hackathon-1.carsky.io/docs
