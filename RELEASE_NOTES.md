# FleetIQ Guardian Release v0.1.0-alpha

**Release Date:** 2026-08-10  
**Status:** Alpha - Internal Team Review

## Overview

This release contains all trained models, generated artifacts, and analysis results for the FleetIQ Guardian Driver Intelligence Platform. The system successfully processes 10 demo trips (T01d–T10d) with multi-modal analysis including DMS (Driver Monitoring System), road object detection, depth estimation, and trajectory tracking.

---

## 📦 Release Contents

### Models

| Model | Purpose | Performance | Size | Path |
|-------|---------|-------------|------|------|
| **DMS Sequence Model** | Driver state detection (attentive/distracted/drowsy/phone) | 95.17% val accuracy | 2.2 MB | `artifacts/models/dms/best_sequence_model.pt` |
| **YOLO v2** | Road object detection (6 classes) | mAP50: 0.40952 | 14.8 MB | `artifacts/training/roadface/train_runs/yolo26n_detached_v3/weights/best.pt` |
| **YOLO v4** | Fine-tuned detector (early stopped) | mAP50: 0.39259 | 5.1 MB | `artifacts/training/roadface/train_runs/yolo26n_detached_v4/weights/best.pt` |

**Total Model Size:** 22.2 MB

### Trip Artifacts

All 10 demo trips have been fully processed with analysis outputs:

- **Trips:** T01d, T02d, T03d, T04d, T05d, T06d, T07d, T08d, T09d, T10d
- **Per-trip artifacts:**
  - `analysis/trip_summary.json` - Trip metrics and events
  - `analysis/dms_analysis.json` - Driver state timeline
  - `analysis/ttc_analysis.json` - Time-to-collision events
  - `media/road_video.mp4` - Road-facing camera stream
  - `media/driver_video.mp4` - Driver-facing camera stream

### Visualizations

Located in `artifacts/renders/roadface/`:

- `label_comparison.png` - Side-by-side comparison of ground truth, AI labels, and YOLO predictions
- `T01_original_kitti.png` - Original KITTI ground truth visualization
- `T01_locateanything.png` - LocateAnything AI-generated labels
- `T01_yolop.png` - YOLO model predictions
- `yolo_train_sample.png` - Training data samples
- `yolo_small_boxes.png` - Small object detection challenges

---

## 🎯 Training Results

### DMS Training

- **Dataset:** Driver camera sequences with 4-state classification
- **Architecture:** CNN + LSTM sequence model
- **Best Epoch:** 7
- **Validation Accuracy:** 95.17%
- **Status:** ✅ Production-ready

### Road Object Detection

#### LocateAnything Labeling
- **Frames Labeled:** 17,999 across T01d–T10d
- **Frames with Objects:** 14,291 (79.4%)
- **Total Boxes:** 38,772
- **Method:** Grounding DINO + SAM2 foundation models

#### YOLO Training Results

**YOLO v2 (Baseline - 100 epochs):**
- Best mAP50: **0.40952** at epoch 43
- Final mAP50: 0.38376
- Training time: ~8 hours
- Status: ✅ **Recommended for deployment**

**YOLO v4 (Fine-tune - 33/50 epochs):**
- Best mAP50: 0.39259 at epoch 13
- Final mAP50: 0.30268 (declined)
- Early stopped with patience=20
- Status: ⚠️ Underperformed, not recommended

#### Class Distribution
```
Car:          25,223 (65.1%)
Pedestrian:    7,071 (18.2%)
Motorcycle:    2,862 (7.4%)
LongVehicle:   2,051 (5.3%)
Bus:           1,137 (2.9%)
Cyclist:         428 (1.1%)
```

---

## 🔍 Known Issues & Limitations

### YOLO Performance Issues

**Problem:** YOLO v4 underperformed compared to v2 despite fine-tuning.

**Root Cause Analysis:**
1. **Small Object Challenge:**
   - 34% of labeled boxes are < 0.1% of image area (13,195 / 38,772 boxes)
   - YOLO struggles with objects < 32×32 pixels
   - Far-distance vehicles and pedestrians hard to detect

2. **Label Quality:**
   - LocateAnything labels include very distant objects that are hard to verify
   - No minimum size filter during dataset creation
   - Training data may include false positives from AI labeling

3. **Class Imbalance:**
   - 65% Car vs 1% Cyclist creates learning bias
   - Rare classes (Bus, Cyclist) have low recall

**Recommendations:**
- Use YOLO v2 for production (mAP50: 0.41)
- Filter training data to exclude boxes < 0.2% image area
- Consider focal loss for class imbalance
- Collect more human-verified labels for rare classes

### Dataset Limitations

- **Practice Dataset Only:** Current training uses Practice_Dataset (T01-Sample to T04-Sample)
- **No Hackathon Dataset Integration:** Main Hackathon_Dataset_Redacted not yet processed
- **Limited Trip Diversity:** Only 10 demo trips processed

---

## 🚀 System Status

### Working Features ✅

- DMS analysis with real-time driver state detection
- Road video streaming via API
- Trip summary generation
- Event timeline visualization
- Dark mode UI with professional design tokens
- Flask API endpoints for all major services

### In Progress 🔄

- Dashboard trajectory visualization (coordinate mapping issue)
- Object detection integration on trip detail pages
- TTC visualization on timeline
- Challenge #2 near-miss event detection

### Not Started ❌

- Back-to-car advisory messages
- Coaching recommendation engine
- Fleet-wide risk ranking
- Driver comparison analytics
- PDF report generation

---

## 📊 Visualization Tools

### Using the Label Visualization Script

Located at: `tools/visualization/roadface/visualize_kitti_labels.py`

**Usage:**
```bash
uv run python tools/visualization/roadface/visualize_kitti_labels.py \
  --dataset practice \
  --trip T01-Sample \
  --label-dir-name [label_2|label2_custom|label2_yolop] \
  --start 0 --max-frames 6 --stride 30 \
  --mode contact-sheet \
  --output artifacts/renders/roadface/output.png
```

**Label Sources:**
- `label_2`: Original KITTI ground truth (human annotated)
- `label2_custom`: LocateAnything AI labels (training data)
- `label2_yolop`: YOLO model predictions (inference output)

**Modes:**
- `contact-sheet`: Grid of frames (default)
- `frame`: Single frame
- `video`: MP4 video output
- `window`: Interactive viewer

---

## 🔧 Technical Stack

**Backend:**
- Python 3.11
- Flask API server
- PyTorch for DMS and YOLO
- OpenCV for video processing
- NumPy for trajectory and TTC calculation

**Frontend:**
- React 18
- TypeScript
- Dark mode design system
- Geist Sans font

**Training Infrastructure:**
- Ultralytics YOLO framework
- Grounding DINO + SAM2 for auto-labeling
- CUDA GPU acceleration

---

## 📝 Next Steps

### For Demo (Priority 1)
1. Fix trajectory coordinate mapping on dashboard
2. Integrate YOLO detections on trip detail pages
3. Verify TTC calculation and display
4. Prepare 3-minute demo script
5. Create presentation slides

### For Production (Priority 2)
1. Retrain YOLO with filtered dataset (remove small boxes)
2. Process Hackathon_Dataset_Redacted for more trips
3. Implement Challenge #2 near-miss detection
4. Build coaching recommendation engine
5. Add fleet-wide risk ranking

### For Scale (Priority 3)
1. Optimize video streaming performance
2. Add caching layer for analysis results
3. Implement batch processing pipeline
4. Add user authentication
5. Deploy to cloud infrastructure

---

## 📥 Download Instructions

**For Team Members:**

All artifacts are tracked in Git LFS. Clone the repository:

```bash
git clone <repository-url>
git lfs pull
```

**Models are located at:**
- `artifacts/models/dms/best_sequence_model.pt`
- `artifacts/training/roadface/train_runs/yolo26n_detached_v3/weights/best.pt`
- `artifacts/training/roadface/train_runs/yolo26n_detached_v4/weights/best.pt`

**To verify download:**
```bash
ls -lh artifacts/models/dms/best_sequence_model.pt
# Should show ~2.2 MB

ls -lh artifacts/training/roadface/train_runs/yolo26n_detached_v3/weights/best.pt
# Should show ~14.8 MB
```

---

## 🤝 Team Notes

**What's Working Well:**
- DMS model performs excellently (95% accuracy)
- Trip processing pipeline is stable
- API architecture is clean and extensible
- Dark mode UI looks professional

**What Needs Attention:**
- YOLO performance below expectations
- Need better training data quality
- Trajectory visualization has coordinate bug
- Challenge #2 implementation incomplete

**Recommended Review Points:**
1. Check label visualizations in `artifacts/renders/roadface/`
2. Review YOLO v2 vs v4 comparison
3. Inspect trip artifacts for T01d–T10d
4. Test API endpoints with Postman/curl
5. Review dark mode UI in browser

---

## 📞 Contact

For questions about this release:
- Check `AGENTS.md` for project architecture
- Review `docs/` for Rainier standards
- Inspect `tools/visualization/` for analysis scripts

**Release prepared by:** OpenCode AI Assistant  
**Date:** 2026-08-10  
**Version:** v0.1.0-alpha
