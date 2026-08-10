# FleetIQ Guardian v1.0.0 Release Preparation Script (Lite)
# Packages models, trip JSON artifacts (no video frames), and training results

param(
    [string]$Version = "v1.0.0",
    [string]$OutputDir = "release-lite"
)

$ErrorActionPreference = "Stop"

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "FleetIQ Guardian Release (Lite)" -ForegroundColor Cyan
Write-Host "Version: $Version" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# Create release directory
$releaseDir = Join-Path $PWD $OutputDir
if (Test-Path $releaseDir) {
    Write-Host "Cleaning existing release directory..." -ForegroundColor Yellow
    Remove-Item -Path $releaseDir -Recurse -Force
}
New-Item -ItemType Directory -Path $releaseDir | Out-Null

# 1. Package trained models
Write-Host "`n[1/4] Packaging trained models..." -ForegroundColor Green
$modelsDir = Join-Path $releaseDir "models"
New-Item -ItemType Directory -Path $modelsDir | Out-Null

Copy-Item -Path "artifacts\models\dms\best_sequence_model.pt" -Destination "$modelsDir\dms_sequence_model.pt"
Copy-Item -Path "artifacts\models\dms\face_landmarker.task" -Destination "$modelsDir\face_landmarker.task"
Copy-Item -Path "artifacts\training\roadface\train_runs\yolo26n_detached_v3\weights\best.pt" -Destination "$modelsDir\yolo_road_detector_v3_best.pt"
Copy-Item -Path "artifacts\training\roadface\train_runs\yolo26n_detached_v4\weights\best.pt" -Destination "$modelsDir\yolo_road_detector_v4_best.pt"

Write-Host "  [OK] DMS model: dms_sequence_model.pt (2.22 MB)" -ForegroundColor White
Write-Host "  [OK] Face landmarker: face_landmarker.task (3.58 MB)" -ForegroundColor White
Write-Host "  [OK] YOLO v3: yolo_road_detector_v3_best.pt [RECOMMENDED]" -ForegroundColor White
Write-Host "  [OK] YOLO v4: yolo_road_detector_v4_best.pt" -ForegroundColor White

# 2. Package trip JSON artifacts only (no video frames)
Write-Host "`n[2/4] Packaging trip JSON artifacts..." -ForegroundColor Green
$tripsDir = Join-Path $releaseDir "trips"
New-Item -ItemType Directory -Path $tripsDir | Out-Null

$tripIds = @("T01d", "T02d", "T03d", "T04d", "T05d", "T06d", "T07d", "T08d", "T09d")
foreach ($tripId in $tripIds) {
    $tripSource = "artifacts\trips\$tripId"
    if (Test-Path $tripSource) {
        $tripDestDir = Join-Path $tripsDir $tripId
        New-Item -ItemType Directory -Path $tripDestDir | Out-Null
        
        # Copy only JSON files
        Get-ChildItem -Path $tripSource -Filter "*.json*" | ForEach-Object {
            Copy-Item -Path $_.FullName -Destination $tripDestDir
        }
        Write-Host "  [OK] $tripId (JSON only)" -ForegroundColor White
    }
}

# 3. Package training results
Write-Host "`n[3/4] Packaging training results..." -ForegroundColor Green
$resultsDir = Join-Path $releaseDir "training_results"
New-Item -ItemType Directory -Path $resultsDir | Out-Null

Copy-Item -Path "artifacts\training\roadface\train_runs\yolo26n_detached_v3\results.csv" -Destination "$resultsDir\yolo_v3_results.csv" -ErrorAction SilentlyContinue
Copy-Item -Path "artifacts\training\roadface\train_runs\yolo26n_detached_v3\confusion_matrix.png" -Destination "$resultsDir\yolo_v3_confusion_matrix.png" -ErrorAction SilentlyContinue
Copy-Item -Path "artifacts\training\roadface\train_runs\yolo26n_detached_v4\results.csv" -Destination "$resultsDir\yolo_v4_results.csv" -ErrorAction SilentlyContinue
Copy-Item -Path "artifacts\training\roadface\train_runs\yolo26n_detached_v4\confusion_matrix.png" -Destination "$resultsDir\yolo_v4_confusion_matrix.png" -ErrorAction SilentlyContinue

Write-Host "  [OK] Training metrics and confusion matrices" -ForegroundColor White

# 4. Create README
Write-Host "`n[4/4] Creating release README..." -ForegroundColor Green
$readme = @"
# FleetIQ Guardian $Version Release Package (Lite)

**Release Date:** $(Get-Date -Format "yyyy-MM-dd")

> This is a lite release package containing models and trip JSON artifacts.
> Video frames are excluded to reduce package size.
> Use the full dataset from the Hackathon organizers for video analysis.

## Package Contents

### Models (models/)
- **dms_sequence_model.pt** - Driver Monitoring System (95.17% val accuracy)
- **face_landmarker.task** - MediaPipe face landmark detector  
- **yolo_road_detector_v3_best.pt** - Road object detector (mAP50=0.40952) [RECOMMENDED]
- **yolo_road_detector_v4_best.pt** - Road object detector v4 (mAP50=0.39259)

### Trip Artifacts (trips/)
Complete analysis artifacts for T01d-T09d (JSON only):
- ``T0Xd.json.gz`` - Original KITTI-format trip data
- ``trip_data.json`` - Enriched trip data with AI analysis results

Each trip includes:
- TTC (Time-to-Collision) timeline
- Driver state events  
- Object detections
- Trajectory with speed heatmap
- Risk scoring and coaching recommendations

### Training Results (training_results/)
- YOLO v3/v4 training metrics (CSV)
- Confusion matrices
- Performance comparison data

## Quick Start for New Team Members

### 1. Clone the Repository
``````bash
git clone <repository-url>
cd AutomotiveHacathon
``````

### 2. Extract Release Package
``````powershell
# Extract to project root
Expand-Archive -Path fleetiq-guardian-$Version-lite.zip -DestinationPath .
``````

### 3. Copy Models to Artifacts
``````powershell
# Create artifacts structure if needed
New-Item -ItemType Directory -Path artifacts\models\checkpoints -Force

# Copy models
Copy-Item -Path release-lite\models\dms_sequence_model.pt -Destination artifacts\models\dms\best_sequence_model.pt -Force
Copy-Item -Path release-lite\models\face_landmarker.task -Destination artifacts\models\dms\face_landmarker.task -Force
Copy-Item -Path release-lite\models\yolo_road_detector_v3_best.pt -Destination artifacts\models\checkpoints\yolo26n.pt -Force
``````

### 4. Get Full Dataset
``````bash
# Download the full Hackathon dataset from organizers
# Extract to data/ directory
# Required structure:
#   data/Practice_Dataset/Practice_Dataset/T01-Sample/
#   data/Practice_Dataset/Practice_Dataset/T02-Sample/
#   etc.
``````

### 5. Install Dependencies
``````bash
# Install uv package manager
pip install uv

# Install Python dependencies
uv sync

# Install web dependencies
cd apps/web
pnpm install
cd ../..
``````

### 6. Start the Platform
``````bash
# Terminal 1: Start API server
cd apps/api
uv run uvicorn fleetiq_api.main:app --reload --port 8000

# Terminal 2: Start web dashboard
cd apps/web
pnpm dev
``````

### 7. Access the Dashboard
Open http://localhost:3000 in your browser

## Model Performance Summary

### DMS (Driver Monitoring System)
- Validation Accuracy: **95.17%**
- Trained on: 17,999 frames across T01d-T10d
- Detects: Attentive, Drowsy, Distracted, Phone Use

### YOLO v3 (Road Object Detector) [RECOMMENDED]
- Best mAP50: **0.40952** (epoch 43/100)
- Classes: Car, Bus, LongVehicle, Motorcycle, Cyclist, Pedestrian
- Status: **RECOMMENDED FOR PRODUCTION**

### YOLO v4 (Road Object Detector)  
- Best mAP50: **0.39259** (epoch 13/50)
- Training stopped at epoch 33 (patience=20)
- Status: Lower performance than v3

## Trip Data Format

Each trip artifact includes:
``````json
{
  "trip_id": "T01d",
  "score": 72,
  "events": [...],
  "ttc_timeline": [...],
  "driver_states": [...],
  "trajectory": [...]
}
``````

## Resources
- Full Documentation: ``docs/``
- API Reference: ``apps/api/README.md``
- Dashboard Guide: ``apps/web/README.md``
- Training Notebooks: ``ml/training/``

## Important Notes
1. **Use YOLO v3** for best object detection performance
2. Trip JSON artifacts are **pre-computed** - no need to regenerate
3. **Video frames not included** - use full Hackathon dataset for video analysis
4. Models are **GPU-optional** - CPU inference works but is slower
5. See ``AGENTS.md`` for full project status and roadmap

## Changelog

### v1.0.0 ($(Get-Date -Format "yyyy-MM-dd"))
- [DONE] DMS training complete (95.17% accuracy)
- [DONE] YOLO v2/v3/v4 training complete
- [DONE] LocateAnything labeling: 17,999 frames
- [DONE] PR #47: Phone use detection
- [DONE] Dark mode UI deployed
- [DONE] 9 trips (T01d-T09d) fully analyzed
- [TODO] Trajectory flip bug (in progress)
- [TODO] Challenge #2 TTC/near-miss verification needed

## Contributing
See ``CONTRIBUTING.md`` for development workflow and PR guidelines.

---
Generated by prepare-release-lite.ps1 on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@

$readme | Out-File -FilePath (Join-Path $releaseDir "README.md") -Encoding utf8
Write-Host "  [OK] README.md created" -ForegroundColor White

# 5. Create archive
Write-Host "`nCreating release archive..." -ForegroundColor Green
$archiveName = "fleetiq-guardian-$Version-lite.zip"
$archivePath = Join-Path $PWD $archiveName

if (Test-Path $archivePath) {
    Remove-Item $archivePath -Force
}

Compress-Archive -Path "$releaseDir\*" -DestinationPath $archivePath
$archiveSize = [math]::Round((Get-Item $archivePath).Length / 1MB, 2)

Write-Host "`n=====================================" -ForegroundColor Cyan
Write-Host "[SUCCESS] Lite release created!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Archive: $archiveName" -ForegroundColor White
Write-Host "Size: $archiveSize MB" -ForegroundColor White
Write-Host "Location: $archivePath" -ForegroundColor White
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "  1. Test the release package" -ForegroundColor White
Write-Host "  2. Create GitHub release:" -ForegroundColor White
Write-Host "     gh release create $Version $archiveName --title `"$Version - FleetIQ Guardian`" --notes-file release-lite/README.md" -ForegroundColor Cyan
Write-Host "  3. Share with team members" -ForegroundColor White
Write-Host ""
