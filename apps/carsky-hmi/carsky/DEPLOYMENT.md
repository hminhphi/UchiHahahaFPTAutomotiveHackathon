# FleetIQ Guardian CarSky Deployment Guide

## Overview

This guide walks through deploying the FleetIQ Guardian system on CarSky platform, including:
- Android Automotive HMI APK
- Coaching Bridge Container
- KUKSA VSS Signal Broker
- Nydus Blueprint configuration

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CarSky Room                          │
│                                                         │
│  ┌──────────────┐      ┌──────────────┐               │
│  │ Coaching     │      │ KUKSA        │               │
│  │ Bridge       │─────▶│ Broker       │               │
│  │ (Container)  │      │ (VSS)        │               │
│  └──────────────┘      └──────────────┘               │
│         │                      │                       │
│         │                      ▼                       │
│         │              ┌──────────────┐               │
│         │              │ AAOS         │               │
│         │              │ Skycraft VM  │               │
│         │              │ + HMI APK    │               │
│         │              └──────────────┘               │
│         │                      │                       │
│         └──────────────────────┘                       │
│                  Ethernet Bridge                       │
└─────────────────────────────────────────────────────────┘
         │
         ▼
  Fleet Backend API
  (trip analysis, coaching)
```

## Prerequisites

1. **CarSky Account** with access to:
   - Dashboard: `https://hackathon-1.carsky.io`
   - Container Registry: `registry.hackathon-1.carsky.io`
   - Artifact Manager
   - Nydus Blueprint Editor

2. **Built Artifacts** (ready in this repo):
   - `artifacts/fleetiq-carsky-hmi.apk` (21.4 MB) — Android Automotive HMI
   - Docker image: `registry.hackathon-1.carsky.io/fleetiq/carsky-coaching-bridge:0.1.0`

3. **CarSky Base Images** (provided by organizers):
   - AAOS Image: `aosp_trout_arm64-img-eng.zip` (731.9 MB)
   - Host Package: `aaos_trout_cvd-host_package.tar.gz` (463.6 MB)
   - Artifact ID: `aaos` version `0.0.1`

## Step 1: Push Coaching Bridge Container

```bash
# Login to CarSky registry
docker login registry.hackathon-1.carsky.io

# Build and push coaching bridge
cd apps/carsky-hmi
docker build -t registry.hackathon-1.carsky.io/fleetiq/carsky-coaching-bridge:0.1.0 .
docker push registry.hackathon-1.carsky.io/fleetiq/carsky-coaching-bridge:0.1.0
```

## Step 2: Import Nydus Blueprint

1. Navigate to **Nydus** → **Blueprints** → **Import**
2. Upload `apps/carsky-hmi/carsky/blueprint.json`
3. The blueprint defines 4 nodes:

   | Node Key | Type | Purpose |
   |----------|------|---------|
   | `coaching-bridge` | CONTAINER | Python bridge forwarding coaching commands to VSS |
   | `vehicle-signals` | KUKSA_BROKER | VSS signal broker (requires VSS artifact) |
   | `fleetiq-aaos` | SKYCRAFT | Android Automotive VM + HMI APK |
   | `room-l2` | ETHERNET_BRIDGE | Network layer connecting all nodes |

4. **Important:** Before importing, you may need to remove or update the VSS artifact reference if you don't have a custom VSS schema. See troubleshooting below.

## Step 3: Configure Skycraft Node (fleetiq-aaos)

The blueprint specifies the following Skycraft configuration:

```json
{
  "key": "fleetiq-aaos",
  "type": "SKYCRAFT",
  "config": {
    "imageArtifact": "<CARSKY_ANDROID_AUTOMOTIVE_ARTIFACT_ID>",
    "os": "android",
    "architecture": "aarch64",
    "displayWidth": 1920,
    "displayHeight": 1080
  },
  "pins": [
    {"key": "ethernet", "type": "ETHERNET", "direction": "BIDIRECTIONAL"},
    {"key": "vhal", "type": "VHAL", "direction": "INPUT"},
    {"key": "vss", "type": "KUKSA", "direction": "INPUT"},
    {"key": "screen", "type": "SCREEN", "direction": "OUTPUT"}
  ]
}
```

**In the Nydus UI, this maps to:**

- **OS:** `Android`
- **Artifact:** `aaos` (or the actual artifact ID from CarSky)
- **Version:** `0.0.1`
- **Architecture:** `aarch64`
- **Display Width:** `1920`
- **Display Height:** `1080`
- **Display DPI:** (default, e.g., 160)
- **GPU Backend:** (default, e.g., `guest`)
- **Partprefix:** (leave empty or default)

**Pins connected:**
- `ETHERNET` → room-l2 bridge
- `KUKSA` → vehicle-signals VSS broker
- `VHAL` → (optional, for vehicle hardware abstraction)
- `SCREEN` → exposed as widget `fleetiq-screen`

## Step 4: Install HMI APK via ADB

**Important:** The Skycraft node config does **not** include an `apkArtifact` field because CarSky Skycraft does not support pre-installing APKs in the blueprint. APKs must be installed manually after the Room is running.

### After Room Deployment:

1. **Open ADB Tunnel** from CarSky Dashboard:
   - Navigate to your running Room
   - Open the `fleetiq-aaos` Skycraft node
   - Click **ADB Tunnel** → note the endpoint (e.g., `adb connect <room-id>.carsky.io:5555`)

2. **Connect via ADB:**

   ```bash
   # Connect to the Skycraft VM
   adb connect <room-id>.carsky.io:5555
   
   # Verify connection
   adb devices
   
   # Install FleetIQ HMI APK
   adb install artifacts/fleetiq-carsky-hmi.apk
   
   # Launch the app
   adb shell am start -n ai.fleetiq.carsky/.MainActivity
   ```

3. **Verify HMI is running:**
   - Open the `fleetiq-screen` widget in CarSky Dashboard
   - You should see the FleetIQ Guardian HMI interface

## Step 5: Test Coaching Commands

The coaching bridge exposes an HTTP API for testing:

```bash
# Get current coaching command
curl http://<room-ethernet-ip>:8090/v1/coaching/current

# Expected response:
{
  "command": "focus_ahead",
  "severity": "medium",
  "message": "Please keep your attention on the road",
  "timestamp": "2026-08-10T15:30:00Z"
}
```

The HMI APK should subscribe to the VSS signal:
```
Vehicle.Cabin.Infotainment.HMI.CurrentCommand
```

And display coaching alerts in real-time.

## Troubleshooting

### Issue: VSS Artifact Not Found

**Problem:** The blueprint references `<FLEETIQ_VSS_ARTIFACT_ID>` but no custom VSS schema has been uploaded.

**Solution A (Quick):** Remove the VSS broker node entirely and simplify the blueprint:

1. Edit `blueprint.json`:
   - Remove the `vehicle-signals` node
   - Remove VSS-related pins from `fleetiq-aaos` and `coaching-bridge`
   - Update edges to connect directly or use HTTP fallback

2. The coaching bridge can fall back to HTTP polling instead of VSS signals.

**Solution B (Full):** Create and upload a custom VSS schema artifact:

1. Create `fleetiq-vss-schema.json`:

   ```json
   {
     "Vehicle": {
       "Cabin": {
         "Infotainment": {
           "HMI": {
             "CurrentCommand": {
               "type": "string",
               "description": "Current coaching command from fleet backend"
             }
           }
         }
       }
     }
   }
   ```

2. Upload to CarSky as a VSS_SCHEMA artifact
3. Update `blueprint.json` with the artifact ID

### Issue: APK Not Installing

**Symptoms:** `adb install` fails with `INSTALL_FAILED_INSUFFICIENT_STORAGE` or permission errors.

**Solutions:**

1. Check available storage:
   ```bash
   adb shell df -h
   ```

2. Clear cache:
   ```bash
   adb shell pm clear com.android.vending
   ```

3. Install with flags:
   ```bash
   adb install -r -t artifacts/fleetiq-carsky-hmi.apk
   # -r: replace existing
   # -t: allow test packages
   ```

### Issue: HMI Not Launching

**Symptoms:** APK installs but doesn't appear on screen.

**Debug steps:**

1. Check if installed:
   ```bash
   adb shell pm list packages | grep fleetiq
   # Expected: package:ai.fleetiq.carsky
   ```

2. Check logs:
   ```bash
   adb logcat | grep FleetIQ
   ```

3. Manually launch with debugging:
   ```bash
   adb shell am start -W -D -n ai.fleetiq.carsky/.MainActivity
   ```

4. Check app permissions:
   ```bash
   adb shell dumpsys package ai.fleetiq.carsky
   ```

### Issue: Coaching Bridge Not Reachable

**Symptoms:** HMI can't connect to coaching bridge HTTP API.

**Debug steps:**

1. Verify bridge container is running:
   - Check Container status in CarSky Dashboard
   - View logs from `coaching-bridge` node

2. Test from another node in the room:
   ```bash
   # From AAOS VM:
   adb shell curl http://coaching-bridge:8090/v1/coaching/current
   ```

3. Check Ethernet bridge connectivity:
   - Verify all nodes are connected to `room-l2`
   - Check IP assignments in Room network topology

## Configuration Files

- **Blueprint:** `apps/carsky-hmi/carsky/blueprint.json`
- **Coaching Bridge Dockerfile:** `apps/carsky-hmi/Dockerfile`
- **HMI APK:** `artifacts/fleetiq-carsky-hmi.apk`
- **Backend Config:** `apps/carsky-hmi/config.yaml`

## Next Steps

After successful deployment:

1. **Integrate with Fleet Backend:**
   - Configure coaching bridge to poll Trip Analysis API
   - Set webhook for real-time TTC events

2. **Test End-to-End Flow:**
   - Upload trip data via Fleet API
   - Verify coaching commands appear in HMI

3. **Demo Preparation:**
   - Take screenshots of HMI in action
   - Record video of coaching flow
   - Prepare Room URL for judges

## Support

- **CarSky Documentation:** `https://hackathon-1.carsky.io/docs`
- **FleetIQ Guardian Issues:** See `AGENTS.md` and `docs/` for project context
- **Hackathon Support:** FPT Automotive Hackathon Discord/Slack
