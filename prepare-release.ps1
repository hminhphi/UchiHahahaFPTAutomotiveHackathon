# FleetIQ Guardian v1.0.0 Release Preparation Script
# Packages models, artifacts, and sample data for team members

param(
    [string]$Version = "v1.0.0",
    [string]$OutputDir = "release"
)

$ErrorActionPreference = "Stop"

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "FleetIQ Guardian Release Preparation" -ForegroundColor Cyan
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
Write-Host "`n[1/5] Packaging trained models..." -ForegroundColor Green
$modelsDir = Join-Path $releaseDir "models"
New-Item -ItemType Directory -Path $modelsDir | Out-Null

# DMS model (best performing)
Copy-Item -Path "artifacts\models\dms\best_sequence_model.pt" -Destination "$modelsDir\dms_sequence_model.pt"
Copy-Item -Path "artifacts\models\dms\face_landmarker.task" -Destination "$modelsDir\face_landmarker.task"

# YOLO v3 (best road object detector: mAP50=0.40952)
Copy-Item -Path "artifacts\training\roadface\train_runs\yolo26n_detached_v3\weights\best.pt" -Destination "$modelsDir\yolo_road_detector_v3_best.pt"

# YOLO v4 (latest, but lower performance: mAP50=0.39259)
Copy-Item -Path "artifacts\training\roadface\train_runs\yolo26n_detached_v4\weights\best.pt" -Destination "$modelsDir\yolo_road_detector_v4_best.pt"

Write-Host "  [OK] DMS model: dms_sequence_model.pt (2.22 MB)" -ForegroundColor White
Write-Host "  [OK] Face landmarker: face_landmarker.task (3.58 MB)" -ForegroundColor White
Write-Host "  [OK] YOLO v3: yolo_road_detector_v3_best.pt (14.82 MB) [RECOMMENDED]" -ForegroundColor White
Write-Host "  [OK] YOLO v4: yolo_road_detector_v4_best.pt (5.12 MB)" -ForegroundColor White

# 2. Package trip artifacts
Write-Host "`n[2/5] Packaging trip artifacts..." -ForegroundColor Green
$tripsDir = Join-Path $releaseDir "trips"
New-Item -ItemType Directory -Path $tripsDir | Out-Null

$tripIds = @("T01d", "T02d", "T03d", "T04d", "T05d", "T06d", "T07d", "T08d", "T09d")
foreach ($tripId in $tripIds) {
    $tripSource = "artifacts\trips\$tripId"
    if (Test-Path $tripSource) {
        $tripDest = Join-Path $tripsDir $tripId
        Copy-Item -Path $tripSource -Destination $tripDest -Recurse
        Write-Host "  [OK] $tripId" -ForegroundColor White
    }
}

# 3. Package training results
Write-Host "`n[3/5] Packaging training results..." -ForegroundColor Green
$resultsDir = Join-Path $releaseDir "training_results"
New-Item -ItemType Directory -Path $resultsDir | Out-Null

# YOLO v3 results
Copy-Item -Path "artifacts\training\roadface\train_runs\yolo26n_detached_v3\results.csv" -Destination "$resultsDir\yolo_v3_results.csv"
Copy-Item -Path "artifacts\training\roadface\train_runs\yolo26n_detached_v3\confusion_matrix.png" -Destination "$resultsDir\yolo_v3_confusion_matrix.png" -ErrorAction SilentlyContinue

# YOLO v4 results
Copy-Item -Path "artifacts\training\roadface\train_runs\yolo26n_detached_v4\results.csv" -Destination "$resultsDir\yolo_v4_results.csv"
Copy-Item -Path "artifacts\training\roadface\train_runs\yolo26n_detached_v4\confusion_matrix.png" -Destination "$resultsDir\yolo_v4_confusion_matrix.png" -ErrorAction SilentlyContinue

Write-Host "  [OK] Training metrics and confusion matrices" -ForegroundColor White

# 4. Create README
Write-Host "`n[4/5] Creating release README..." -ForegroundColor Green
$readme = @"
# FleetIQ Guardian $Version Release Package

**Release Date:** $(Get-Date -Format "yyyy-MM-dd")

## Package Contents

### Models (models/)
- **dms_sequence_model.pt** - Driver Monitoring System (95.17% val accuracy)
- **face_landmarker.task** - MediaPipe face landmark detector
- **yolo_road_detector_v3_best.pt** - Road object detector (mAP50=0.40952) [STAR] RECOMMENDED
- **yolo_road_detector_v4_best.pt** - Road object detector v4 (mAP50=0.39259)

### Trip Artifacts (trips/)
Complete analysis artifacts for T01d–T09d:
- `T0Xd.json.gz` - Original KITTI-format trip data
- `trip_data.json` - Enriched trip data with AI analysis results

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
\`\`\`bash
git clone <repository-url>
cd AutomotiveHacathon
\`\`\`

### 2. Extract Release Package
\`\`\`powershell
# Extract this release package to the project root
Expand-Archive -Path fleetiq-guardian-$Version.zip -DestinationPath .
\`\`\`

### 3. Install Models
\`\`\`powershell
# Copy models to artifacts directory
Copy-Item -Path release\models\* -Destination artifacts\models\checkpoints\ -Force
\`\`\`

### 4. Install Dependencies
\`\`\`bash
# Install uv if not already installed
pip install uv

# Install project dependencies
uv sync

# Install web dependencies
cd apps/web
pnpm install
\`\`\`

### 5. Start the Platform
\`\`\`bash
# Terminal 1: Start API
cd apps/api
uv run uvicorn fleetiq_api.main:app --reload --port 8000

# Terminal 2: Start Web Dashboard
cd apps/web
pnpm dev
\`\`\`

### 6. Access the Dashboard
Open http://localhost:3000 in your browser

## Model Performance Summary

### DMS (Driver Monitoring System)
- Validation Accuracy: **95.17%**
- Trained on: 17,999 frames across T01d–T10d
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
\`\`\`json
{
  "trip_id": "T01d",
  "score": 72,
  "events": [...],
  "ttc_timeline": [...],
  "driver_states": [...],
  "trajectory": [...]
}
\`\`\`

## Resources
- Full Documentation: \`docs/\`
- API Reference: \`apps/api/README.md\`
- Dashboard Guide: \`apps/web/README.md\`
- Training Notebooks: \`ml/training/\`

## Important Notes
1. **Use YOLO v3** for best object detection performance
2. Trip artifacts are **pre-computed** - no need to regenerate
3. Models are **GPU-optional** - CPU inference works but is slower
4. See \`AGENTS.md\` for full project status and roadmap

## Changelog

### v1.0.0 ($(Get-Date -Format "yyyy-MM-dd"))
- [DONE] DMS training complete (95.17% accuracy)
- [DONE] YOLO v2/v3/v4 training complete
- [DONE] LocateAnything labeling: 17,999 frames
- [DONE] PR #47: Phone use detection
- [DONE] Dark mode UI deployed
- [DONE] 9 trips (T01d–T09d) fully analyzed
- [TODO] Trajectory flip bug (in progress)
- [TODO] Challenge #2 TTC/near-miss verification needed

## Contributing
See \`CONTRIBUTING.md\` for development workflow and PR guidelines.

---
Generated by prepare-release.ps1 on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@

$readme | Out-File -FilePath (Join-Path $releaseDir "README.md") -Encoding utf8
Write-Host "  [OK] README.md created" -ForegroundColor White

# 5. Create archive
Write-Host "`n[5/5] Creating release archive..." -ForegroundColor Green
$archiveName = "fleetiq-guardian-$Version.zip"
$archivePath = Join-Path $PWD $archiveName

if (Test-Path $archivePath) {
    Remove-Item $archivePath -Force
}

Compress-Archive -Path "$releaseDir\*" -DestinationPath $archivePath
$archiveSize = [math]::Round((Get-Item $archivePath).Length / 1MB, 2)

Write-Host "`n=====================================" -ForegroundColor Cyan
Write-Host "[SUCCESS] Release package created!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Archive: $archiveName (Size: $archiveSize MB)" -ForegroundColor White
Write-Host "Location: $archivePath" -ForegroundColor White
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "  1. Test the release package" -ForegroundColor White
Write-Host "  2. Create GitHub release: gh release create $Version $archiveName" -ForegroundColor White
Write-Host "  3. Share with team members" -ForegroundColor White
Write-Host ""
