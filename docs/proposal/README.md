# Proposal

Purpose: Stores the team-owned FleetIQ Hackathon proposal deck and its exported
PDF.

Owner: Product and Pitch Lead.

The final Round 2 pair is:

- `UchiHahaha_FleetIQGuardian_Final_Round2.pptx`
- `UchiHahaha_FleetIQGuardian_Final_Round2.pdf`

The PPTX is the editable source; the PDF is the presentation-safe export. Keep
only this pair in the submission packet.
Persistent final-deck source images belong in `assets/`; temporary renders
belong in `artifacts/presentations/`.

Use `tools/presentation/` for proposal asset and deck automation.

Regenerate the final judge deck with:

```powershell
pnpm deck:final
```
