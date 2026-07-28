# FleetIQ Protocols

This directory contains the documented, versioned boundaries shared by every
FleetIQ application and service. The `schemas/events-v1.json` file is generated
from `fleetiq-contracts`; do not edit it manually.

Regenerate it with:

```powershell
uv run --package fleetiq-contracts python packages/contracts/scripts/export_schema.py
```
