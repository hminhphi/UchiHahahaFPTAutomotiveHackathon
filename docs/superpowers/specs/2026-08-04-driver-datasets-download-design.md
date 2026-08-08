# Driver Dataset Downloader

## Goal

Extend FleetIQ's dataset tooling with one registry-driven downloader for DMD,
UTA-RLDD, YawDD, NTHU-DDD, and AUC Distracted Driver data.

## Access Model

The script accepts direct URLs supplied by the user after accepting each
dataset's terms. It never scrapes portals, automates consent, embeds tokens,
or bypasses login/license controls. Dataset entries include official landing
pages and a short access note so `--list` remains useful when a direct archive
URL is unavailable.

## Storage and Safety

Each dataset is extracted below `data/external/<dataset>/`. Downloads are
resumable, optional SHA-256 values are checked, and ZIP/TAR members are
validated against path traversal and archive links before extraction.

## Notebook

The DMS notebook's optional section will show the registry, official pages,
the direct-URL command, and the manifest format needed by generalized training.
The existing six-trip workflow remains independent of external datasets.

## Non-goals

No automatic download from protected portals, no dataset conversion into a
single mixed manifest, and no licensed data committed to the repository.
