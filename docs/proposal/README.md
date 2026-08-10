# Proposal

Purpose: Stores the team-owned FleetIQ Hackathon proposal deck and its exported
PDF.

Owner: Product and Pitch Lead.

The PPTX is the editable source; the PDF is the presentation-safe export.
Persistent final-deck source images belong in `assets/`; temporary renders
belong in `artifacts/presentations/`.

Use `tools/presentation/` for proposal asset and deck automation.

Regenerate the final judge deck with:

```powershell
pnpm deck:final
```
