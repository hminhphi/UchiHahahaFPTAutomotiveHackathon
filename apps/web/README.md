# FleetIQ Web

Next.js App Router operations console for fleet ranking, trip drill-down,
synchronized camera replay, risk evidence, and coaching reports.

The browser talks only to FastAPI HTTP/WSS:

- `FLEETIQ_API_BASE_URL` configures server-side HTTP calls.
- `NEXT_PUBLIC_WS_BASE_URL` configures browser WebSocket calls.

When the API is unavailable or has no analyzed trips, the UI displays fixture
data with visible `Fixture data` or `Model degraded` labels.

Run `pnpm --filter @fleetiq/web dev` for local development.
