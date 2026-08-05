# Dual-Camera Driver Evidence Design

## Goal

Show the road-facing and driver-camera frames for the same replay frame at
once, with the driver's broad attention state and optional `phone_use` signal
beside the driver evidence.

## UI

- The existing replay view becomes a two-pane layout: road camera first,
  driver camera second.
- Both panes use the selected frame index and the existing Next.js frame
  proxy. Playback, scrubbing, stepping, and fullscreen remain shared.
- The driver pane shows compact labels for `Driver state` and `Phone use`.
  `phone_use` is `Detected`, `Not detected`, or `Unavailable`.
- A missing driver frame renders a local placeholder and does not interrupt
  the road-camera pane or playback.
- On narrow screens the panes stack vertically.

## Data and Boundaries

`TripReplayPanel` already owns the selected trajectory point. It will pass its
driver-state and phone-use values to the existing replay component. No API,
model, or event-schema changes are needed.

## Verification

Add a component test that renders a selected frame and checks both camera
URLs and the driver-state and phone-use labels. Run the web test suite,
TypeScript type-check, and lint.
