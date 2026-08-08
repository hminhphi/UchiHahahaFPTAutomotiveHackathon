# DMS Phone-Use Detection Design

## Goal

Add phone use as an optional, independently observed DMS signal while keeping
`distracted` as the broad driver-attention state. Validate the feature first in
the saved-trip analysis and dashboard flow, then reuse it for live inference if
needed.

## Semantics

- `state` remains `attentive`, `distracted`, `drowsy`, or `unknown` at service
  boundaries.
- `phone_use=true` means phone presence was detected consistently across a
  short frame window.
- `phone_use=false` means detection ran successfully and found no consistent
  phone presence.
- `phone_use=null` means detection was unavailable, failed, or has not yet
  accumulated enough frames.
- Phone use may imply effective distraction inside fusion, but it never
  overwrites the original DMS classifier output.
- Existing five-state offline outputs remain responsible for their current
  boundary normalization: `alert` becomes `attentive`, while `yawning` and
  `microsleep` become `drowsy`. Phone detection is independent of that mapping.

The supplied `distracted` labels are not treated as phone ground truth. Sampled
T01, T04, and T06 distracted frames visibly contain phones, but the source
metadata does not annotate phone use separately.

## Architecture

Each saved driver frame follows two parallel paths:

```text
Driver frame
├─ Existing DMS classifier → broad state + confidence
└─ Pretrained YOLO → raw cell-phone detection
                         ↓
                 3-of-5 frame smoothing
                         ↓
state + phone_use + existing frame evidence
                         ↓
Fusion engine → effective distraction, score, compound risk
                         ↓
Trip JSON/API → dashboard timeline and evidence
```

The implementation uses the workspace's existing Ultralytics dependency and a
pretrained model's COCO `cell phone` class. It does not add another detector or
train a new model for the MVP.

## Components and Data Flow

### Phone detector

A small DMS module loads the configured Ultralytics checkpoint once, keeps only
`cell phone` detections above the `--phone-confidence` threshold, initially
`0.40`, and returns the tri-state phone result. `--phone-model` selects the
checkpoint, initially `yolo11n.pt`. Detector confidence remains internal for
threshold selection; the existing `DriverState.phone_use: bool | None`
contract is sufficient for the MVP.

The detector applies a three-positive-votes-in-five-valid-frames rule. Before
three valid observations, the output is `null`. Afterward, three or more
positive observations produce `true`; otherwise the result is `false`.

### Offline trip prediction

The existing DMS trip prediction command runs the broad classifier and phone
detector on the same driver frames. Its output adds a `phone_use` column without
changing the existing predicted-state column. The trip ID and frame ID already
identify the evidence image, so the pipeline does not copy image files.

### Service contract

`DriverState` already contains `phone_use: bool | None`. No contract version or
new payload type is required.

### Fusion scoring

Fusion derives effective distraction when either the broad state is
`distracted` or confirmed phone use is true. It adds `phone_use` to the
explanation codes when applicable.

Attention penalties are mutually exclusive and bounded: broad distraction and
phone use together receive one distraction penalty, while drowsiness retains
the existing higher attention penalty. Confirmed phone use combined with a TTC
risk creates the existing `compound_risk` outcome.

### Dashboard

The trip timeline and evidence panel show a `Phone use` badge when the signal is
true and use the existing synchronized driver frame as evidence. No new page is
added.

## Failure Behavior

- Missing weights, unreadable frames, unavailable detection, and detector
  errors produce `phone_use=null`; broad DMS prediction continues.
- A successful detection pass without a stable phone produces `false`.
- The model checkpoint is downloaded during explicit demo preparation and
  cached locally. Trip analysis never downloads weights implicitly; a missing
  local checkpoint produces `phone_use=null`.
- The confidence threshold is configurable because phone size, occlusion, and
  cabin-camera position vary.
- Phone use cannot add a duplicate attention penalty.
- The system does not report detector accuracy using broad `distracted` labels.

## Testing and Acceptance

Automated checks cover:

1. The three-of-five smoothing rule using injected detection results without
   loading model weights.
2. `attentive + phone_use` producing one distraction penalty.
3. `distracted + phone_use` not producing a duplicate penalty.
4. `phone_use + short TTC` producing compound risk.
5. `phone_use=null` preserving existing scoring behavior.

The offline acceptance run processes T01 end to end and shows a stable phone-use
segment on the trip timeline with its synchronized driver frame. A small manual
review of phone and non-phone frames selects the demo confidence threshold.

Fine-tuning is deferred unless that review shows the pretrained detector is not
adequate for the supplied cabin images.

## Non-goals

- Redefining every distracted frame as phone use.
- Adding a phone-specific training head or annotation workflow.
- Adding a second attention penalty for the same behavior.
- Building a new dashboard page.
- Deploying real-time phone detection before the saved-trip path is validated.
