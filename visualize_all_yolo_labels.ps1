#!/usr/bin/env pwsh
# Visualize custom YOLO v3 labels for all trips in Hackathon_Dataset_Redacted.
# Run tools/dataset/export_yolo_labels.py before this script.

Write-Host "Visualizing custom YOLO v3 labels for T01d-T10d..." -ForegroundColor Cyan
Write-Host ""

$trips = @("T01d", "T02d", "T03d", "T04d", "T05d", "T06d", "T07d", "T08d", "T09d", "T10d")
$total = $trips.Count
$current = 0

foreach ($trip in $trips) {
    $current++
    Write-Host "[$current/$total] Processing $trip..." -ForegroundColor Yellow

    uv run python tools/visualization/roadface/visualize_kitti_labels.py `
        --dataset redacted `
        --trip $trip `
        --label-dir-name label2_yolo_v3 `
        --start 0 --max-frames 6 --stride 50 `
        --mode contact-sheet `
        --output "artifacts/renders/roadface/${trip}_yolo_v3.png"

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Created: artifacts/renders/roadface/${trip}_yolo_v3.png" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Failed to process $trip" -ForegroundColor Red
    }
    Write-Host ""
}

Write-Host "Done! Check artifacts/renders/roadface/ for outputs" -ForegroundColor Green
Write-Host ""
Write-Host "To visualize other label sources, use:" -ForegroundColor Cyan
Write-Host "  --label-dir-name label_2          (original KITTI ground truth)" -ForegroundColor White
Write-Host "  --label-dir-name label2_custom    (LocateAnything AI labels)" -ForegroundColor White
Write-Host "  --label-dir-name label2_yolop     (pretrained YOLOP vehicle/mask output)" -ForegroundColor White
Write-Host "  --label-dir-name label2_yolo_v3   (custom YOLO v3 predictions)" -ForegroundColor White
