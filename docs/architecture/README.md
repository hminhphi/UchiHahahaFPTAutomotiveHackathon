# Architecture

Purpose: Defines FleetIQ component boundaries, deployment topology, protocols,
and the generated diagrams used by engineering and pitch materials.

Owner: Platform Engineering with AI workstream review.

- [System architecture](system.md)
- [Repository architecture](repository.md)
- [`diagrams/`](diagrams/) contains committed PlantUML sources and selected
  rendered architecture assets.
- [Versioned protocols](../protocols/README.md)

Commit source diagrams and architecture decisions. Generated experiments and
one-off screenshots belong under `artifacts/renders/`.

Validate with:

```powershell
uv run python -m pytest tests/architecture -v
```
