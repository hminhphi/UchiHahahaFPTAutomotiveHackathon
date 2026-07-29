# FleetIQ Observability

This package is owned by the backend/platform team. It provides service-safe
JSON logging and recursive secret redaction without importing any FleetIQ
application or service.

Inputs are standard logging records and nested Python values. Outputs are
single-line UTC JSON records. Authorization fields, API keys, credential
containers, and presigned URL query strings are redacted. Application metrics
and tracing exporters remain outside this minimal package.

Run its tests from the repository root:

```powershell
uv run --package fleetiq-observability pytest packages/observability/tests -v
```

Source and tests are committed. Log files and credentials are never committed.
