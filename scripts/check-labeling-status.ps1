<#
.SYNOPSIS
  Check progress of the background LocateAnything-3B labeling run over the
  10 detached Hackathon trips (T01d-T10d).

.DESCRIPTION
  Reports whether the labeler process is alive, how many label files exist per
  trip, overall percent complete, throughput, and an ETA. Also surfaces the
  most recent log lines and any errors recorded in the raw JSONL sidecars.

.EXAMPLE
  pwsh -File scripts/check-labeling-status.ps1

.EXAMPLE
  pwsh -File scripts/check-labeling-status.ps1 -Watch
  Refreshes every 60 seconds until the run finishes.
#>
[CmdletBinding()]
param(
  [switch]$Watch,
  [int]$IntervalSeconds = 60
)

$ErrorActionPreference = 'Stop'

$RepoRoot    = Split-Path -Parent $PSScriptRoot
$DatasetRoot = Join-Path $RepoRoot 'data\Hackathon_Dataset_Redacted\Hackathon_Dataset_Redacted'
$LogDir      = Join-Path $RepoRoot 'artifacts\logs'
$LogFile     = Join-Path $LogDir 'locateanything_detached.log'
$ErrFile     = "$LogFile.err"
$PidFile     = Join-Path $LogDir 'locateanything.pid'

function Get-LabelerProcess {
  if (-not (Test-Path -LiteralPath $PidFile)) { return $null }
  $labelerPid = (Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
  if (-not $labelerPid) { return $null }
  return Get-Process -Id ([int]$labelerPid) -ErrorAction SilentlyContinue
}

function Show-Status {
  $now = Get-Date

  Write-Host ''
  Write-Host '================================================================' -ForegroundColor Cyan
  Write-Host " LocateAnything labeling status  $($now.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Cyan
  Write-Host '================================================================' -ForegroundColor Cyan

  # --- Process ---
  $proc = Get-LabelerProcess
  if ($proc) {
    $runtime = $now - $proc.StartTime
    Write-Host ("Process   : RUNNING (PID {0}, up {1:hh\:mm\:ss})" -f $proc.Id, $runtime) -ForegroundColor Green
  }
  else {
    Write-Host 'Process   : NOT RUNNING' -ForegroundColor Yellow
  }

  # --- GPU ---
  $gpu = & nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader 2>$null
  if ($LASTEXITCODE -eq 0 -and $gpu) {
    Write-Host "GPU       : $gpu"
  }

  # --- Per-trip label counts ---
  if (-not (Test-Path -LiteralPath $DatasetRoot)) {
    Write-Host "Dataset root not found: $DatasetRoot" -ForegroundColor Red
    return
  }

  $trips = Get-ChildItem -LiteralPath $DatasetRoot -Directory | Sort-Object Name
  $rows = foreach ($trip in $trips) {
    $imageDir = Join-Path $trip.FullName 'kitti\image_2'
    $labelDir = Join-Path $trip.FullName 'kitti\label2_custom'

    $expected = 0
    if (Test-Path -LiteralPath $imageDir) {
      $expected = @(Get-ChildItem -LiteralPath $imageDir -File -Filter '*.png' -ErrorAction SilentlyContinue).Count
      if ($expected -eq 0) {
        $expected = @(Get-ChildItem -LiteralPath $imageDir -File -ErrorAction SilentlyContinue).Count
      }
    }

    $done = 0
    $withBoxes = 0
    if (Test-Path -LiteralPath $labelDir) {
      $labelFiles = @(Get-ChildItem -LiteralPath $labelDir -File -Filter '*.txt' -ErrorAction SilentlyContinue)
      $done = $labelFiles.Count
      $withBoxes = @($labelFiles | Where-Object { $_.Length -gt 0 }).Count
    }

    [pscustomobject]@{
      Trip      = $trip.Name
      Done      = $done
      Expected  = $expected
      WithBoxes = $withBoxes
      Percent   = if ($expected -gt 0) { [math]::Round(100.0 * $done / $expected, 1) } else { 0 }
    }
  }

  Write-Host ''
  $rows | Format-Table -AutoSize Trip, Done, Expected, Percent, WithBoxes | Out-String | Write-Host

  $totalDone     = ($rows | Measure-Object -Property Done -Sum).Sum
  $totalExpected = ($rows | Measure-Object -Property Expected -Sum).Sum
  $totalBoxes    = ($rows | Measure-Object -Property WithBoxes -Sum).Sum

  if (-not $totalDone) { $totalDone = 0 }
  if (-not $totalExpected) { $totalExpected = 0 }
  if (-not $totalBoxes) { $totalBoxes = 0 }

  $overall = if ($totalExpected -gt 0) { [math]::Round(100.0 * $totalDone / $totalExpected, 2) } else { 0 }
  Write-Host ("Total     : {0} / {1} frames labeled ({2}%)" -f $totalDone, $totalExpected, $overall) -ForegroundColor Cyan
  Write-Host ("Non-empty : {0} label files contain >=1 box" -f $totalBoxes)

  # --- Throughput + ETA from process runtime ---
  if ($proc -and $totalDone -gt 0) {
    $elapsed = ($now - $proc.StartTime).TotalSeconds
    if ($elapsed -gt 0) {
      $perFrame  = $elapsed / $totalDone
      $remaining = [math]::Max(0, $totalExpected - $totalDone)
      $eta       = [timespan]::FromSeconds($perFrame * $remaining)
      Write-Host ("Rate      : {0:N2} s/frame" -f $perFrame)
      Write-Host ("ETA       : {0:hh\:mm\:ss} (finishes ~{1:HH\:mm} on {1:yyyy-MM-dd})" -f $eta, $now.Add($eta))
    }
  }

  # --- Errors from raw sidecars ---
  $errorCount = 0
  foreach ($trip in $trips) {
    $raw = Join-Path $trip.FullName 'kitti\label2_custom\_locateanything_raw.jsonl'
    if (Test-Path -LiteralPath $raw) {
      $errorCount += @(Select-String -LiteralPath $raw -Pattern '"error"' -ErrorAction SilentlyContinue).Count
    }
  }
  if ($errorCount -gt 0) {
    Write-Host ("Errors    : {0} frame(s) recorded an error in _locateanything_raw.jsonl" -f $errorCount) -ForegroundColor Yellow
  }
  else {
    Write-Host 'Errors    : none recorded'
  }

  # --- Recent log output ---
  if (Test-Path -LiteralPath $LogFile) {
    Write-Host ''
    Write-Host '--- last log lines ---' -ForegroundColor DarkGray
    Get-Content -LiteralPath $LogFile -Tail 6 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "  $_" }
  }

  if (Test-Path -LiteralPath $ErrFile) {
    $tracebacks = @(Select-String -LiteralPath $ErrFile -Pattern 'Traceback|Error:' -ErrorAction SilentlyContinue)
    if ($tracebacks.Count -gt 0) {
      Write-Host ''
      Write-Host "--- stderr has $($tracebacks.Count) traceback/error line(s); last 5 ---" -ForegroundColor Yellow
      $tracebacks | Select-Object -Last 5 | ForEach-Object { Write-Host "  $($_.Line)" }
    }
  }

  if (-not $proc) {
    Write-Host ''
    if ($totalExpected -gt 0 -and $totalDone -ge $totalExpected) {
      Write-Host 'Labeling COMPLETE. Ready for the finetune step.' -ForegroundColor Green
    }
    else {
      Write-Host 'Process is not running but labeling is incomplete.' -ForegroundColor Yellow
      Write-Host 'Resume (already-labeled frames are skipped automatically):' -ForegroundColor Yellow
      Write-Host '  uv run --package fleetiq-training-roadface fleetiq-label-roadface --dataset redacted --generation-mode slow --device cuda --continue-on-error'
    }
  }

  return [pscustomobject]@{
    Running  = [bool]$proc
    Done     = $totalDone
    Expected = $totalExpected
  }
}

if ($Watch) {
  while ($true) {
    Clear-Host
    $state = Show-Status
    if (-not $state.Running) { break }
    Start-Sleep -Seconds $IntervalSeconds
  }
}
else {
  Show-Status | Out-Null
}
