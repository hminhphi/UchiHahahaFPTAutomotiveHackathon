#!/usr/bin/env pwsh
# FleetIQ Guardian — 10 Detached Trips Demo Script
# Usage: .\demo-10-trips.ps1

$ErrorActionPreference = "Stop"
$ApiUrl = "http://localhost:8000"
$WebUrl = "http://localhost:3000"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " FleetIQ Guardian — 10 Trip Demo" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify services
Write-Host "[1/6] Verifying Docker services..." -ForegroundColor Yellow
docker compose ps --format "table {{.Service}}\t{{.State}}" | Select-Object -First 8
Write-Host ""

# Step 2: Verify API has 10 trips
Write-Host "[2/6] Checking API: 10 detached trips..." -ForegroundColor Yellow
$trips = Invoke-RestMethod -Uri "$ApiUrl/api/v1/trips" -Method GET
Write-Host "  Found $($trips.data.items.Count) trips:" -ForegroundColor Green
$trips.data.items | ForEach-Object {
    Write-Host "    $($_.trip_id) | score=$($_.safety_score) | sev=$($_.severity) | driver=$($_.driver_state) | max_speed=$($_.max_speed_kmh) km/h"
}
Write-Host ""

# Step 3: Open Fleet Overview
Write-Host "[3/6] Opening Fleet Overview..." -ForegroundColor Yellow
Write-Host "  Navigate to: $WebUrl" -ForegroundColor White
Write-Host "  Expected: 10 trip cards ranked by severity" -ForegroundColor White
Start-Process $WebUrl
Write-Host ""

# Step 4: Show trip detail with next-video
Write-Host "[4/6] Open a trip detail page..." -ForegroundColor Yellow
Write-Host "  Navigate to: $WebUrl/trips/T01d" -ForegroundColor White
Write-Host "  Expected:" -ForegroundColor White
Write-Host "    - Score ring (80/100)" -ForegroundColor White
Write-Host "    - Trip facts panel (5 fields)" -ForegroundColor White
Write-Host "    - Evidence navigation panel" -ForegroundColor White
Write-Host "    - Replay panel with video player + signal cards" -ForegroundColor White
Write-Host "    - Trajectory map" -ForegroundColor White
Write-Host "    - Coaching report panel" -ForegroundColor White
Write-Host ""

# Step 5: Verify trip trajectory + DMS data
Write-Host "[5/6] Checking T01d trajectory (DMS + telemetry)..." -ForegroundColor Yellow
$traj = Invoke-RestMethod -Uri "$ApiUrl/api/v1/trips/T01d/trajectory" -Method GET
Write-Host "  Points: $($traj.data.points.Count)" -ForegroundColor Green
Write-Host "  Max speed: $($traj.data.max_speed_kmh) km/h" -ForegroundColor Green
Write-Host "  Distance: $([math]::Round($traj.data.distance_m)) m" -ForegroundColor Green
$driverStates = $traj.data.points | Group-Object -Property driver_state | ForEach-Object { "$($_.Name): $($_.Count)" }
Write-Host "  Driver states: $($driverStates -join ', ')" -ForegroundColor Green
Write-Host ""

# Step 6: Navigate to all 10 trips
Write-Host "[6/6] Demo trip list (click each):" -ForegroundColor Yellow
$trips.data.items | ForEach-Object {
    Write-Host "    $($WebUrl)/trips/$($_.trip_id)" -ForegroundColor White
}
Write-Host ""

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Demo commands:" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  # Start all services" -ForegroundColor Gray
Write-Host "  docker compose --profile core up -d" -ForegroundColor White
Write-Host ""
Write-Host "  # Regenerate trip data (optional, if needed)" -ForegroundColor Gray
Write-Host "  uv run --package fleetiq-training-dms python services/roadface-worker/tests/generate_trip_data.py" -ForegroundColor White
Write-Host ""
Write-Host "  # Check trip list" -ForegroundColor Gray
Write-Host "  curl $ApiUrl/api/v1/trips | python -m json.tool" -ForegroundColor White
Write-Host ""
Write-Host "  # Open dashboard" -ForegroundColor Gray
Write-Host "  Start-Process $WebUrl" -ForegroundColor White
