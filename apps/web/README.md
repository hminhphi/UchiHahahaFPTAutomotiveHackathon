# FleetIQ Web

Next.js App Router operations console for fleet evidence review, trip drill-down,
synchronized camera replay, risk evidence, and coaching reports.

The browser talks only to FastAPI HTTP/WSS:

- `FLEETIQ_API_BASE_URL` configures server-side HTTP calls.
- `NEXT_PUBLIC_WS_BASE_URL` configures browser WebSocket calls.

The trip replay player requests immutable historical frames through a same-origin
Next.js proxy. It supports play/pause, previous/next frame, timeline scrubbing,
full-screen inspection, and one-click jumps from risk evidence to its frame.
The API reads those frames from the configured local dataset or MinIO/S3 store;
the web container does not duplicate the video dataset.

When the API is unavailable or has no analyzed trips, the UI displays fixture
data with visible `Fixture data` or `Model degraded` labels.

Run `pnpm --filter @fleetiq/web dev` for local development.
