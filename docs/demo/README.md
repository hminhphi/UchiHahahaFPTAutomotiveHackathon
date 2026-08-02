# FleetIQ Demo Guide

This directory is the single source for a judge-facing local demonstration.
It documents what is verified locally, what comes from the organizer simulator,
and what is represented by an explicit mock. Do not describe simulator labels
or local mock inference as live production model output.

- [Three-minute demo script](DEMO_SCRIPT.md)
- [Local run and acceptance checklist](LOCAL_E2E.md)

The demo is designed around a historical trip replay. Each organizer trip is
loaded into MinIO once, then the dashboard receives camera packets through the
same WebSocket boundary used by a live stream. The binary packet frame index
updates the road image, current vehicle marker on the world-space route, speed,
longitudinal acceleration, lateral acceleration, DMS label, simulator risk,
and valid TTC/headway values together.
