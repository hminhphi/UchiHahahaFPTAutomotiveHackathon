# FleetIQ Guardian v1.0.0 Release Instructions

## Release Package Ready

**Archive:** `fleetiq-guardian-v1.0.0-lite.zip` (23.97 MB)  
**Location:** Project root directory  
**Repository:** `git@github.com:hminhphi/UchiHahahaFPTAutomotiveHackathon.git`

## Manual GitHub Release Steps

Since GitHub CLI (`gh`) is not installed, follow these steps to create the release manually:

### 1. Commit and Push Current State

```bash
git add .
git commit -m "Release v1.0.0: Models, trip artifacts, and documentation"
git push origin main
```

### 2. Create GitHub Release

1. Go to: https://github.com/hminhphi/UchiHahahaFPTAutomotiveHackathon/releases/new

2. **Tag version:** `v1.0.0`

3. **Release title:** `v1.0.0 - FleetIQ Guardian`

4. **Description:** (Copy from `release-lite/README.md` or use below)

```markdown
# FleetIQ Guardian v1.0.0 - Production Release

Complete Driver Intelligence Platform with trained models and analyzed trip data.

## 🎯 What's Included

- **Trained Models** (4 models, ready to use)
  - DMS (Driver Monitoring): 95.17% validation accuracy
  - YOLO v3 Road Detector: mAP50 0.40952 ⭐ RECOMMENDED
  - YOLO v4 Road Detector: mAP50 0.39259
  - MediaPipe Face Landmarker

- **Trip Artifacts** (9 trips: T01d-T09d)
  - Pre-computed TTC timelines
  - Driver state analysis
  - Risk scores and coaching recommendations
  - Object detections and trajectories

- **Training Results**
  - Performance metrics (CSV)
  - Confusion matrices
  - Model comparison data

## 🚀 Quick Start

### For New Team Members

1. **Clone the repository**
   ```bash
   git clone git@github.com:hminhphi/UchiHahahaFPTAutomotiveHackathon.git
   cd UchiHahahaFPTAutomotiveHackathon
   ```

2. **Download and extract this release**
   ```powershell
   # Download fleetiq-guardian-v1.0.0-lite.zip from this release
   Expand-Archive -Path fleetiq-guardian-v1.0.0-lite.zip -DestinationPath .
   ```

3. **Copy models to artifacts**
   ```powershell
   New-Item -ItemType Directory -Path artifacts\models\dms -Force
   New-Item -ItemType Directory -Path artifacts\models\checkpoints -Force
   
   Copy-Item release-lite\models\dms_sequence_model.pt artifacts\models\dms\best_sequence_model.pt -Force
   Copy-Item release-lite\models\face_landmarker.task artifacts\models\dms\face_landmarker.task -Force
   Copy-Item release-lite\models\yolo_road_detector_v3_best.pt artifacts\models\checkpoints\yolo26n.pt -Force
   ```

4. **Install dependencies**
   ```bash
   # Python dependencies
   pip install uv
   uv sync
   
   # Web dependencies
   cd apps/web
   pnpm install
   cd ../..
   ```

5. **Start the platform**
   ```bash
   # Terminal 1: API Server
   cd apps/api
   uv run uvicorn fleetiq_api.main:app --reload --port 8000
   
   # Terminal 2: Web Dashboard
   cd apps/web
   pnpm dev
   ```

6. **Access dashboard:** http://localhost:3000

## 📊 Model Performance

### DMS (Driver Monitoring System)
- **Validation Accuracy:** 95.17%
- **Training Data:** 17,999 frames (T01d-T10d)
- **Detects:** Attentive, Drowsy, Distracted, Phone Use
- **Architecture:** Sequence model with temporal features

### YOLO v3 (Road Object Detector) ⭐ RECOMMENDED
- **mAP50:** 0.40952 (epoch 43/100)
- **Classes:** Car, Bus, LongVehicle, Motorcycle, Cyclist, Pedestrian
- **Status:** Production-ready, best performance

### YOLO v4 (Road Object Detector)
- **mAP50:** 0.39259 (epoch 13/50)
- **Status:** Experimental, lower performance than v3

## 📦 Package Contents

```
release-lite/
├── models/
│   ├── dms_sequence_model.pt           (2.22 MB)
│   ├── face_landmarker.task            (3.58 MB)
│   ├── yolo_road_detector_v3_best.pt   (14.82 MB) ⭐
│   └── yolo_road_detector_v4_best.pt   (5.12 MB)
├── trips/
│   ├── T01d/
│   │   ├── T01d.json.gz
│   │   └── trip_data.json
│   ├── T02d/ ... T09d/
├── training_results/
│   ├── yolo_v3_results.csv
│   ├── yolo_v3_confusion_matrix.png
│   ├── yolo_v4_results.csv
│   └── yolo_v4_confusion_matrix.png
└── README.md
```

## ⚠️ Important Notes

1. **Use YOLO v3** for production - it has the best mAP50 score
2. Trip JSON artifacts are **pre-computed** - no regeneration needed
3. **Video frames NOT included** in this lite package to reduce size
4. Models work on **CPU or GPU** (GPU recommended for real-time)
5. Full Hackathon dataset required for video frame access

## 🔗 Resources

- **Full Documentation:** `docs/`
- **API Reference:** `apps/api/README.md`
- **Dashboard Guide:** `apps/web/README.md`
- **Training Notebooks:** `ml/training/`
- **Project Status:** `AGENTS.md`

## 📝 Changelog

### v1.0.0 (2026-08-10)

**Completed:**
- ✅ DMS training: 95.17% accuracy on 17,999 frames
- ✅ YOLO v2/v3/v4 training complete
- ✅ LocateAnything labeling: 17,999 frames across 10 trips
- ✅ PR #47: Driver phone use detection
- ✅ Dark mode UI deployed
- ✅ 9 trips (T01d-T09d) fully analyzed with artifacts
- ✅ Custom dataset export with 80/10/10 split

**In Progress:**
- 🔄 Trajectory coordinate flip bug fix
- 🔄 Challenge #2 TTC/near-miss verification

**Next Milestones:**
- [ ] Prepare final demo script and presentation
- [ ] Complete Challenge #3 driver intelligence fusion
- [ ] Generate artifacts for T10d
- [ ] Final testing and validation

## 🤝 Contributing

See `CONTRIBUTING.md` for development workflow and PR guidelines.

## 📧 Support

For issues or questions, contact the team or open an issue on GitHub.

---

**Generated:** 2026-08-10  
**Package Size:** 23.97 MB  
**Total Models:** 4  
**Total Trips:** 9 (T01d-T09d)
```

5. **Upload the release asset:**
   - Drag and drop `fleetiq-guardian-v1.0.0-lite.zip` into the release assets section

6. **Publish the release**

### 3. Verify Release

After publishing, verify:
- Release is visible at: https://github.com/hminhphi/UchiHahahaFPTAutomotiveHackathon/releases
- ZIP file is downloadable
- README renders correctly

### 4. Share with Team

Send team members:
```
🎉 FleetIQ Guardian v1.0.0 is released!

Download: https://github.com/hminhphi/UchiHahahaFPTAutomotiveHackathon/releases/tag/v1.0.0

This package includes:
✅ All trained models (DMS + YOLO v3/v4)
✅ 9 analyzed trips with pre-computed artifacts
✅ Training results and metrics
✅ Complete setup instructions

Just download, extract, and follow the Quick Start guide!
```

## Alternative: Install GitHub CLI

To automate releases in the future, install GitHub CLI:

### Windows (via winget)
```powershell
winget install --id GitHub.cli
```

### Windows (via Chocolatey)
```powershell
choco install gh
```

### After installation
```bash
gh auth login
gh release create v1.0.0 fleetiq-guardian-v1.0.0-lite.zip --title "v1.0.0 - FleetIQ Guardian" --notes-file release-lite/README.md
```

## Package Contents Summary

**Total Size:** 23.97 MB  
**Models:** 4 files (25.74 MB uncompressed)  
**Trip Artifacts:** 9 trips (JSON only, no video frames)  
**Training Results:** Metrics and confusion matrices

## What's NOT Included

To keep the package size manageable, the following are **excluded**:
- Video frames (use full Hackathon dataset)
- Raw training data
- Intermediate checkpoints
- Development artifacts

Team members will need the full Hackathon dataset for video frame access.

## Next Steps After Release

1. ✅ Models and artifacts shared via GitHub release
2. ⏭️ Fix trajectory coordinate flip bug
3. ⏭️ Verify Challenge #2 TTC/near-miss implementation
4. ⏭️ Prepare final demo presentation
5. ⏭️ Complete end-to-end testing

---
Generated: 2026-08-10
