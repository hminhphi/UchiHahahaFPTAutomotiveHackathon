# Final Submission Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the captioned video the final submission asset, remove obsolete packet material, simplify the organizer-facing deck, and publish a clear README-backed package.

**Architecture:** Keep private organizer data and runtime evidence in ignored local packages. Treat the captioned MP4 as the only final video, use the generated frame-1010 dashboard capture as a committed README visual, and generate a concise ten-slide delivery deck from the existing PPTX generator.

**Tech Stack:** PowerShell, Git, PptxGenJS, PowerPoint COM PDF export, FFmpeg/FFprobe, Python `uv`, GitHub REST API.

## Global Constraints

- Do not publish organizer data, weights, generated trip media, or the private runtime handoff.
- Do not alter prediction CSV values or scoring behavior.
- Do not expose the local video URL as if it were reviewer-accessible.
- Final packet contains one MP4 under `FleetIQ_Guardian_Round2_Demo.mp4` and no caption/edit-map notes in `VIDEO/`.
- Delivery deck contains only product, evidence, architecture, workflow, and closing content.

---

### Task 1: Normalize Final Video And Remove Obsolete Packet

**Files:**
- Modify: `submission/UchiHahaha_FleetIQ_Guardian_Round2_Final/VIDEO/`
- Delete: `submission/UchiHahaha_FleetIQ_Guardian_R2/`

**Interfaces:**
- Consumes: `FleetIQ_Guardian_Round2_Demo_caption.mp4`.
- Produces: `FleetIQ_Guardian_Round2_Demo.mp4` as the only MP4 in the final packet.

- [ ] **Step 1: Validate the captioned source**

Run:

```powershell
ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height -of default=noprint_wrappers=1 submission/UchiHahaha_FleetIQ_Guardian_Round2_Final/VIDEO/FleetIQ_Guardian_Round2_Demo_caption.mp4
```

Expected: H.264/AAC, 1728x1080, approximately 211 seconds.

- [ ] **Step 2: Replace the prior video in the packet**

Remove the silent `FleetIQ_Guardian_Round2_Demo.mp4`, rename the captioned source to that reserved filename, and remove `DEMO_VIDEO_CAPTIONS.md`, `DEMO_VIDEO_PLACEHOLDER.md`, and the old `VIDEO/README.md` from the packet.

- [ ] **Step 3: Remove the unused old packet**

Confirm `rg -n -uu 'UchiHahaha_FleetIQ_Guardian_R2' .` returns no tracked references, then remove `submission/UchiHahaha_FleetIQ_Guardian_R2`.

- [ ] **Step 4: Verify the packet video inventory**

Run:

```powershell
Get-ChildItem submission/UchiHahaha_FleetIQ_Guardian_Round2_Final/VIDEO -File
```

Expected: only `FleetIQ_Guardian_Round2_Demo.mp4` remains.

### Task 2: Simplify Delivery Deck

**Files:**
- Modify: `tools/presentation/generate_final_deck.cjs`
- Regenerate: `docs/proposal/UchiHahaha_FleetIQGuardian_Final_Round2.pptx`
- Regenerate: `docs/proposal/UchiHahaha_FleetIQGuardian_Final_Round2.pdf`

**Interfaces:**
- Consumes: existing product, evidence, architecture, and dashboard assets.
- Produces: ten-slide PPTX/PDF without internal training metrics, source paths, or repeated caveat banners.

- [ ] **Step 1: Remove internal-only slide blocks**

Delete the current slides 9-12 covering detailed event penalties, model provenance metrics, offline checkpoint scores, hidden-test caveats, and source-gap disclosure. Retain report/model docs for those details.

- [ ] **Step 2: Renumber delivery slides**

Change the current delivery slide footer from 13 to 9 and the close slide footer from 14 to 10. Remove source-path citations and replace them with audience-facing statements.

- [ ] **Step 3: Remove internal delivery wording from retained slides**

Replace exact frame-count/source-gap/corridor/source-path footers with short product claims. Keep the frame-1010 evidence values because they demonstrate the actual product output.

- [ ] **Step 4: Regenerate and export**

Run `pnpm deck:final`, then export the PPTX to PDF with PowerPoint COM on Windows.

- [ ] **Step 5: Verify deck content and visual output**

Scan PPTX XML for `mAP50`, `checkpoint`, `T08d`, `1615`, `artifacts/`, `predictions/`, `frame-551`, and `000551`; render slides to JPEG and inspect all ten slides for overflow, overlap, and title wrapping.

### Task 3: Clean README And Submission Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/Automotive Hackthon - Final Vòng 2.docx.md`
- Modify: `docs/submission/README.md`
- Modify: `docs/submission/MANUAL_SUBMISSION_CHECKLIST.md`
- Add: `docs/proposal/assets/t01d-frame-1010-dashboard.png`
- Delete: `docs/submission/DEMO_VIDEO_CAPTIONS.md`
- Delete: `docs/submission/DEMO_VIDEO_PLACEHOLDER.md`

**Interfaces:**
- Consumes: final captioned MP4 and frame-1010 dashboard screenshot.
- Produces: public README with an embedded visual and no draft-video notes.

- [ ] **Step 1: Add the public-safe dashboard image**

Copy the verified frame-1010 dashboard capture to `docs/proposal/assets/t01d-frame-1010-dashboard.png` and embed it below the Evidence section in `README.md`.

- [ ] **Step 2: Update final video references**

Use `FleetIQ_Guardian_Round2_Demo.mp4` as the final filename, report the measured 03:31 duration, and state only that reviewer upload/access URL remains to be filled.

- [ ] **Step 3: Remove draft-note references**

Delete caption/edit-map documentation references from README and submission indexes. Keep the manual checklist focused on upload access, contact details, final timestamps, validator, and evidence URL.

- [ ] **Step 4: Preserve factual caveats in the report**

Keep technical provenance and limitations in the BTC report, but remove provisional timestamp language now that the captioned video is final. Use the recorded video filename without inventing a public URL.

### Task 4: Rebuild, Validate, Commit, And Publish

**Files:**
- Modify: ignored portal packet manifest and ZIP.
- Modify: ignored private runtime package.

**Interfaces:**
- Consumes: normalized video, ten-slide deck, cleaned docs, and validated predictions.
- Produces: final portal ZIP, private runtime ZIP, Git tag/release, and clean worktree.

- [ ] **Step 1: Rebuild portal manifest and ZIP**

Run the validator, regenerate `MANIFEST.sha256`, archive the packet, and assert the archive contains exactly one final MP4 and no draft notes.

- [ ] **Step 2: Build private runtime handoff**

Run `tools/release/create_release_package.ps1 -Version v1.1.3 -PrivateReviewerHandoff` after the tagged clean HEAD is ready.

- [ ] **Step 3: Run quality checks**

Run CSV validation, `git diff --check`, release script parse, deck text scan, and FFprobe validation.

- [ ] **Step 4: Commit and tag**

Commit the tracked cleanup as `release: finalize captioned submission`, tag `v1.1.3`, and push `main --follow-tags`.

- [ ] **Step 5: Publish public release**

Create the `v1.1.3` GitHub release with only the PPTX/PDF deck pair. Do not attach the MP4, runtime ZIP, packet ZIP, weights, or organizer data.
