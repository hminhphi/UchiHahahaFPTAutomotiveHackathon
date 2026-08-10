# FleetIQ Guardian - Quick Start for New Team Members

**Last Updated:** 2026-08-10  
**Release Version:** v1.0.0

## What You Need to Know

FleetIQ Guardian is a complete Driver Intelligence Platform that analyzes fleet safety using AI-powered driver monitoring, road object detection, and collision risk assessment.

**Current Status:**
- ✅ All models trained and ready to use
- ✅ 9 trips fully analyzed (T01d-T09d) with pre-computed artifacts
- ✅ Dark mode dashboard deployed
- ✅ API and web dashboard working end-to-end
- 🔄 Trajectory coordinate bug (in progress)

## Step 1: Get the Code

```bash
# Clone the repository
git clone git@github.com:hminhphi/UchiHahahaFPTAutomotiveHackathon.git
cd UchiHahahaFPTAutomotiveHackathon

# Pull latest changes
git pull origin main
```

## Step 2: Download the Release Package

**Option A: From GitHub Release (Recommended)**
1. Go to: https://github.com/hminhphi/UchiHahahaFPTAutomotiveHackathon/releases
2. Download `fleetiq-guardian-v1.0.0-lite.zip` (23.97 MB)
3. Extract to project root

**Option B: Ask a Team Member**
If the GitHub release isn't created yet, ask a team member for the ZIP file.

## Step 3: Install Models

```powershell
# Create directories
New-Item -ItemType Directory -Path artifacts\models\dms -Force
New-Item -ItemType Directory -Path artifacts\models\checkpoints -Force

# Copy models from release package
Copy-Item release-lite\models\dms_sequence_model.pt artifacts\models\dms\best_sequence_model.pt -Force
Copy-Item release-lite\models\face_landmarker.task artifacts\models\dms\face_landmarker.task -Force
Copy-Item release-lite\models\yolo_road_detector_v3_best.pt artifacts\models\checkpoints\yolo26n.pt -Force
```

## Step 4: Get the Dataset

You need the full Hackathon dataset from the organizers (not included in the release package).

**Expected structure:**
```
data/
├── Practice_Dataset/
│   └── Practice_Dataset/
│       ├── T01-Sample/
│       ├── T02-Sample/
│       ├── T03-Sample/
│       └── ... (up to T10-Sample)
```

Ask the team lead or check the Hackathon portal if you don't have this.

## Step 5: Install Dependencies

### Python Dependencies
```bash
# Install uv package manager (if not already installed)
pip install uv

# Install project dependencies
uv sync
```

### Web Dependencies
```bash
cd apps/web
pnpm install
cd ../..
```

**Note:** If `pnpm` is not installed:
```bash
npm install -g pnpm
```

## Step 6: Start the Platform

Open **two terminal windows**.

**Terminal 1: Start API Server**
```bash
cd apps/api
uv run uvicorn fleetiq_api.main:app --reload --port 8000
```

**Terminal 2: Start Web Dashboard**
```bash
cd apps/web
pnpm dev
```

## Step 7: Access the Dashboard

Open your browser to: **http://localhost:3000**

You should see:
- Fleet overview with 9 trips
- Driver rankings
- Trip detail pages with video playback
- TTC timelines and driver state analysis

## What Models Are Included?

### 1. DMS (Driver Monitoring System)
- **Performance:** 95.17% validation accuracy
- **Training Data:** 17,999 frames across T01d-T10d
- **Detects:** Attentive, Drowsy, Distracted, Phone Use
- **File:** `artifacts/models/dms/best_sequence_model.pt`

### 2. YOLO v3 (Road Object Detector) ⭐ RECOMMENDED
- **Performance:** mAP50 = 0.40952 (best)
- **Classes:** Car, Bus, LongVehicle, Motorcycle, Cyclist, Pedestrian
- **File:** `artifacts/models/checkpoints/yolo26n.pt`
- **Status:** Use this for production

### 3. YOLO v4 (Road Object Detector)
- **Performance:** mAP50 = 0.39259 (lower than v3)
- **File:** `release-lite/models/yolo_road_detector_v4_best.pt`
- **Status:** Experimental, don't use unless testing

### 4. MediaPipe Face Landmarker
- **Purpose:** Face landmark detection for DMS
- **File:** `artifacts/models/dms/face_landmarker.task`

## What Trip Artifacts Are Included?

The release includes **pre-computed analysis** for trips T01d-T09d. You don't need to regenerate these.

Each trip has:
- **Original KITTI data:** `T0Xd.json.gz`
- **Enriched analysis:** `trip_data.json` with:
  - TTC timeline
  - Driver state events
  - Object detections
  - Trajectory with speed heatmap
  - Risk scores and coaching recommendations

**Location:** `artifacts/trips/T01d/` through `artifacts/trips/T09d/`

## Common Commands

### Run Tests
```bash
# API tests
cd apps/api
uv run pytest

# Web tests (if available)
cd apps/web
pnpm test
```

### Check Model Status
```powershell
# Check if models are in place
Get-ChildItem artifacts\models\dms
Get-ChildItem artifacts\models\checkpoints
```

### Check Trip Artifacts
```powershell
# List all trips
Get-ChildItem artifacts\trips
```

### Generate Artifacts for a New Trip (Advanced)
```bash
# If you need to analyze a new trip (e.g., T10d)
cd services/roadface-worker/tests
uv run python generate_trip_data.py --trip-id T10d
```

## Project Structure

```
AutomotiveHacathon/
├── apps/
│   ├── api/              # FastAPI backend
│   ├── web/              # Next.js dashboard
│   └── carsky-hmi/       # Android HMI app
├── ml/
│   ├── training/
│   │   ├── dms/          # Driver monitoring training
│   │   └── roadface/     # Object detection training
├── services/
│   └── roadface-worker/  # Artifact generation pipeline
├── artifacts/
│   ├── models/           # Trained model checkpoints
│   └── trips/            # Pre-computed trip analysis
├── data/                 # Hackathon dataset (not in repo)
├── docs/                 # Documentation
└── tools/                # Utility scripts
```

## Key Files to Know

| File | Purpose |
|------|---------|
| `AGENTS.md` | Project status, progress, and next actions |
| `RELEASE_INSTRUCTIONS.md` | How to create GitHub releases |
| `prepare-release-lite.ps1` | Script to package release |
| `apps/api/README.md` | API documentation |
| `apps/web/README.md` | Dashboard guide |

## Troubleshooting

### Problem: Models not found
**Solution:** Re-run Step 3 to copy models from the release package.

### Problem: Trip data missing
**Solution:** Check that you extracted the release package and have `artifacts/trips/T01d/` etc.

### Problem: API server fails to start
**Solution:**
1. Check that port 8000 is not already in use
2. Ensure `uv sync` completed successfully
3. Check that models are in `artifacts/models/`

### Problem: Dashboard shows "No trips found"
**Solution:**
1. Verify API server is running at http://localhost:8000
2. Check that trip artifacts exist in `artifacts/trips/`
3. Try accessing http://localhost:8000/api/trips directly

### Problem: Video playback not working
**Solution:**
1. Ensure you have the full Hackathon dataset in `data/`
2. Check that the path structure matches what's expected
3. Verify the API can access the dataset

## Development Workflow

1. **Create a branch** for your work:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make your changes** and test locally

3. **Commit and push**:
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin feature/my-feature
   ```

4. **Create a Pull Request** on GitHub

5. **Get review** from team members before merging

## Next Steps After Setup

Once you have the platform running, check `AGENTS.md` for:
- Current project status
- In-progress tasks
- Next milestones
- Known issues

**Priority tasks:**
1. Fix trajectory coordinate flip bug
2. Verify Challenge #2 TTC/near-miss implementation
3. Prepare final demo script
4. Test end-to-end with all trips

## Getting Help

- **Team Lead:** Check AGENTS.md for contact info
- **Documentation:** See `docs/` folder
- **Issues:** Check GitHub Issues or ask in team chat
- **Code Questions:** Ask in team Slack/Discord

## Model Performance Reference

### DMS Training Results
- Training frames: 17,999 (T01d-T10d)
- Best epoch: 7
- Validation accuracy: 95.17%
- States detected: Attentive, Drowsy, Distracted, Phone Use

### YOLO Training Comparison
| Model | Best mAP50 | Best Epoch | Status |
|-------|-----------|------------|---------|
| YOLO v2 | 0.40952 | 43/100 | Good |
| **YOLO v3** | **0.40952** | **43/100** | **RECOMMENDED** ✅ |
| YOLO v4 | 0.39259 | 13/50 | Lower performance |

**Recommendation:** Always use YOLO v3 (`yolo26n.pt`) for object detection.

## Hardware Requirements

### Minimum
- CPU: 4 cores
- RAM: 8 GB
- Disk: 20 GB free space
- GPU: Not required (CPU inference works)

### Recommended
- CPU: 8+ cores
- RAM: 16 GB
- Disk: 50 GB free space
- GPU: NVIDIA GPU with 4+ GB VRAM (for faster inference)

## Important Notes

1. **Video frames are NOT in the release package** - you need the full Hackathon dataset
2. **Trip JSON artifacts ARE included** - pre-computed analysis is ready to use
3. **YOLO v3 is the best model** - don't use v4 unless experimenting
4. **Models work on CPU** - GPU is optional but faster
5. **Pre-computed artifacts** - no need to regenerate for T01d-T09d

---

**Questions?** Check `AGENTS.md` or ask the team lead.

**Ready to contribute?** See the "Development Workflow" section above.

**Good luck! 🚀**
