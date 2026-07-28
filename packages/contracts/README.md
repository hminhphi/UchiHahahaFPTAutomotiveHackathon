# FleetIQ Contracts

`fleetiq-contracts` is the sole owner of versioned Pydantic payloads and MQTT
topic construction shared by FleetIQ applications and services.

It has no application or service dependencies. MQTT payloads contain typed
metadata and artifact references only; camera bytes travel over the dedicated
streaming path.

Validate the package with:

```powershell
uv run --package fleetiq-contracts pytest packages/contracts/tests -v
```
