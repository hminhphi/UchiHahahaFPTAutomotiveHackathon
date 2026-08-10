[CmdletBinding()]
param(
    [string]$Version = "v1.1.1",
    [switch]$PrivateReviewerHandoff,
    [switch]$IncludeDataset,
    [switch]$IncludeYolopMasks,
    [switch]$Overwrite
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$releaseRoot = Join-Path $repoRoot "release"
$releaseName = "FleetIQGuardian-$Version"
$stage = Join-Path $releaseRoot $releaseName
$archive = Join-Path $releaseRoot "$releaseName-runtime.zip"

if (-not $PrivateReviewerHandoff) {
    throw "Pass -PrivateReviewerHandoff to acknowledge that this package contains non-public runtime evidence."
}

$worktreeStatus = ((& git -C $repoRoot status --porcelain) -join "`n").Trim()
if ($worktreeStatus) {
    throw "Release worktree is not clean. Commit or remove every tracked and untracked change before packaging."
}
$headCommit = (& git -C $repoRoot rev-parse HEAD).Trim()
$tagCommit = (& git -C $repoRoot rev-parse "$Version^{commit}" 2>$null).Trim()
if (-not $tagCommit -or $headCommit -ne $tagCommit) {
    throw "Tag $Version must resolve to the current committed HEAD before packaging."
}

if ((Test-Path -LiteralPath $stage) -or (Test-Path -LiteralPath $archive)) {
    if (-not $Overwrite) {
        throw "Release output already exists. Re-run with -Overwrite only after preserving the prior package."
    }
    Remove-Item -LiteralPath $stage, $archive -Recurse -Force -ErrorAction SilentlyContinue
}

New-Item -ItemType Directory -Path $stage -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stage "source") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stage "runtime") -Force | Out-Null

function Copy-RequiredPath {
    param([string]$RelativePath)

    $source = Join-Path $repoRoot $RelativePath
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Required release input is missing: $RelativePath"
    }
    $destination = Join-Path $stage (Join-Path "runtime" $RelativePath)
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    if (Test-Path -LiteralPath $source -PathType Container) {
        New-Item -ItemType Directory -Path $destination -Force | Out-Null
        & robocopy $source $destination /E /COPY:DAT /DCOPY:T /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
        if ($LASTEXITCODE -gt 7) {
            throw "robocopy failed for $RelativePath with exit code $LASTEXITCODE"
        }
    }
    else {
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }
}

function Copy-OptionalPath {
    param([string]$RelativePath)

    $source = Join-Path $repoRoot $RelativePath
    if (-not (Test-Path -LiteralPath $source)) {
        Write-Warning "Optional release input is missing: $RelativePath"
        return
    }
    $destination = Join-Path $stage (Join-Path "runtime" $RelativePath)
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    if (Test-Path -LiteralPath $source -PathType Container) {
        New-Item -ItemType Directory -Path $destination -Force | Out-Null
        & robocopy $source $destination /E /COPY:DAT /DCOPY:T /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
        if ($LASTEXITCODE -gt 7) {
            throw "robocopy failed for $RelativePath with exit code $LASTEXITCODE"
        }
    }
    else {
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }
}

# Source is embedded so reviewers can reproduce this exact package offline.
$sourceArchive = Join-Path $stage "source\$releaseName-source.zip"
& git -C $repoRoot archive --format=zip --prefix="$releaseName/" $Version --output=$sourceArchive
if ($LASTEXITCODE -ne 0) {
    throw "git archive failed for tag $Version."
}

Push-Location $repoRoot
try {
    & uv run python tools/dataset/validate_submission.py --predictions-dir predictions/UchiHahaha
    if ($LASTEXITCODE -ne 0) {
        throw "Organizer-format prediction validation failed."
    }
}
finally {
    Pop-Location
}

# Runtime evidence is deliberately separated from source because organizer data
# and trained/generated artifacts are local-only in the Git repository.
@(
    "artifacts/models/dms/best_sequence_model.pt",
    "artifacts/models/dms/face_landmarker.task",
    "artifacts/training/roadface/train_runs/yolo26n_detached_v3/weights/best.pt",
    "artifacts/trips",
    "artifacts/evaluation",
    "artifacts/renders/roadface",
    "predictions/UchiHahaha",
    "submission/UchiHahaha_FleetIQ_Guardian_Round2_Final",
    "docs/submission"
) | ForEach-Object { Copy-RequiredPath $_ }

Copy-OptionalPath "artifacts/fleetiq-carsky-hmi.apk"

if ($IncludeYolopMasks) {
    Copy-RequiredPath "artifacts/training/roadface/yolop_panoptic"
}

if ($IncludeDataset) {
    # Only use for an approved organizer-to-organizer handoff. The data remains
    # excluded from Git and public release assets by default.
    Copy-RequiredPath "data/Practice_Dataset"
    Copy-RequiredPath "data/Hackathon_Dataset_Redacted"
}

$readme = @"
# FleetIQ Guardian $Version Runtime Package

This package is a private, organizer-approved handoff for Automotive Hackathon reviewers. It contains a tagged Git source archive plus the local runtime evidence required by the current final dashboard build.

## Run

1. Extract `source/$releaseName-source.zip`.
2. Put the `runtime/artifacts`, `runtime/predictions`, and `runtime/submission` folders beside the extracted source tree.
3. Provide the organizer dataset under `data/` unless this package was built with `-IncludeDataset`.
4. Follow `docs/runbooks/final-release.md` in the source archive.

## Integrity

Verify every packaged file against `MANIFEST.sha256` before review. The source release intentionally excludes organizer data and generated artifacts; this runtime package supplies them without committing them to Git.
"@
Set-Content -LiteralPath (Join-Path $stage "README.md") -Value $readme -Encoding utf8NoBOM

$manifest = @(
    "# FleetIQ Guardian $Version private runtime handoff",
    "# Source tag commit: $headCommit",
    "# SHA-256 hashes for every packaged file"
) + (Get-ChildItem -LiteralPath $stage -Recurse -File | ForEach-Object {
        $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        $relativePath = $_.FullName.Substring($stage.Length + 1).Replace('\', '/')
        "$hash  $relativePath"
    })
Set-Content -LiteralPath (Join-Path $stage "MANIFEST.sha256") -Value $manifest -Encoding ascii

Push-Location $releaseRoot
try {
    & tar -a -cf $archive $releaseName
    if ($LASTEXITCODE -ne 0) {
        throw "tar failed while creating $archive"
    }
}
finally {
    Pop-Location
}
$sizeMiB = [math]::Round(((Get-Item -LiteralPath $archive).Length / 1MB), 1)
$archiveHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath "$archive.sha256" -Value "$archiveHash  $([IO.Path]::GetFileName($archive))" -Encoding ascii
Write-Host "Created $archive ($sizeMiB MiB)" -ForegroundColor Green
Write-Host "Private package only. Use -IncludeDataset only for an approved organizer handoff." -ForegroundColor Yellow
