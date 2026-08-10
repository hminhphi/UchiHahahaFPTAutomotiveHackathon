# Final Submission Cleanup Design

## Goal

Make the captioned demo video the only final video asset, remove obsolete/private
submission leftovers, simplify the judge-facing deck, and make the root README
useful as a public project entry point.

## Scope

- Use `FleetIQ_Guardian_Round2_Demo_caption.mp4` as the final source video.
- Normalize the final packet filename to `FleetIQ_Guardian_Round2_Demo.mp4`.
- Remove silent draft media and caption/edit-map notes from the final packet.
- Remove the unused `submission/UchiHahaha_FleetIQ_Guardian_R2` folder.
- Reduce the delivery deck to ten judge-facing slides by removing internal model
  training, benchmark, and implementation caveat slides.
- Keep technical limitations and provenance in the report and model docs.
- Embed a committed, public-safe frame-1010 dashboard screenshot in `README.md`.

## Non-Goals

- Do not publish organizer data, weights, generated trip media, or the private
  runtime handoff.
- Do not alter prediction CSV values or scoring behavior.
- Do not expose the local video URL as if it were a reviewer-accessible upload.

## Acceptance Criteria

- Final packet contains one MP4 under the reserved filename and no caption/edit-map
  notes in `VIDEO/`.
- Old `submission/UchiHahaha_FleetIQ_Guardian_R2` is absent and has no references.
- Delivery deck contains only product, evidence, architecture, workflow, and closing
  content; internal training metrics and source paths are absent.
- README embeds the frame-1010 dashboard screenshot and links the final video asset
  without claiming public accessibility.
- CSV validator, deck generation, PDF export, PPTX text scan, archive manifest, and
  Git status checks pass.
