# DMS Phone-Use Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Detect stable driver phone use independently of the broad DMS state, feed it into bounded fusion scoring, and show it on the saved-trip dashboard with synchronized frame evidence.

**Architecture:** Run the current state classifier and a pretrained YOLO cell-phone detector in parallel over saved driver frames. Smooth raw detections with a three-of-five vote, overlay the prediction CSV at the filesystem API boundary, then pass the tri-state signal through fusion and the existing trajectory UI.

**Tech Stack:** Python 3.12, PyTorch, Ultralytics YOLO, pandas, Pydantic, pytest, FastAPI, TypeScript, React, Vitest.

## Global Constraints

- Keep distracted broad; never derive phone_use from the broad label.
- phone_use is true, false, or null with the meanings in the approved design.
- Default model: yolo11n.pt. Default confidence: 0.40. Keep only COCO cell phone detections.
- Require three positive detections within the latest five valid frames.
- Never overwrite the original DMS state.
- Apply at most one attention penalty for broad distraction and phone use together.
- Missing weights, unreadable frames, or detector errors preserve DMS output and yield null.
- Do not add a dashboard page or copy evidence images.
- Do not edit or commit the existing staged DMS generalization/downloader work.
- Use git commit --only with each task's owned files.
- Keep Ultralytics a lazy import for this offline MVP. Run the demo with uv run --with ultralytics instead of touching the already-modified DMS manifest and lockfile.

---

## File Map

- Create ml/training/dms/src/fleetiq_training_dms/phone_detector.py: detector and smoother.
- Create ml/training/dms/tests/test_phone_detector.py: fake-model unit checks.
- Modify ml/training/dms/src/fleetiq_training_dms/predict.py: emit phone_use.
- Create ml/training/dms/tests/test_predict_phone_use.py: prediction integration.
- Modify services/fusion-worker/src/fleetiq_fusion/scoring.py and worker.py: bounded phone scoring.
- Modify services/fusion-worker/tests/test_scoring.py and test_compound_risk.py.
- Modify apps/api/src/fleetiq_api/config.py, historical_replay.py, schemas.py, trajectory.py: CSV overlay and API output.
- Modify apps/api/tests/test_config.py, test_historical_replay.py, and test_trajectory.py.
- Modify apps/web/src/lib/api.ts, contracts.ts, trip-evidence.ts, components/trip-replay-panel.tsx, and components/trip-video-player.tsx.
- Modify apps/web/src/__tests__/trip-evidence.test.ts and trip-trajectory.test.ts.
- Create apps/web/src/__tests__/trip-video-player-view.test.tsx.
- Modify ml/training/dms/README.md: repeatable demo commands.

---

### Task 1: Phone Detector and Temporal Smoother

**Files:**
- Create: ml/training/dms/src/fleetiq_training_dms/phone_detector.py
- Create: ml/training/dms/tests/test_phone_detector.py

**Interfaces:**
- Consumes: local checkpoint Path, driver-frame Path, Ultralytics-compatible model results.
- Produces: PhoneUseDetector.detect(image_path: Path) -> bool | None.
- Produces: PhoneUseSmoother.update(detected: bool | None) -> bool | None.

- [ ] **Step 1: Write failing smoother tests**

~~~python
from fleetiq_training_dms.phone_detector import PhoneUseSmoother


def test_phone_smoother_requires_three_positive_valid_frames():
    smoother = PhoneUseSmoother()
    assert [smoother.update(value) for value in (True, None, True)] == [None, None, None]
    assert smoother.update(True) is True


def test_phone_smoother_returns_false_after_three_valid_negative_frames():
    smoother = PhoneUseSmoother()
    assert [smoother.update(False) for _ in range(3)] == [None, None, False]
~~~

- [ ] **Step 2: Run the tests and verify failure**

Run:

~~~bash
uv run --package fleetiq-training-dms pytest ml/training/dms/tests/test_phone_detector.py -v
~~~

Expected: collection fails because fleetiq_training_dms.phone_detector does not exist.

- [ ] **Step 3: Implement the minimal smoother**

~~~python
from collections import deque


class PhoneUseSmoother:
    def __init__(self, window_size: int = 5, min_positive: int = 3) -> None:
        if min_positive < 1 or window_size < min_positive:
            raise ValueError('phone smoothing requires 1 <= min_positive <= window_size')
        self._values: deque[bool] = deque(maxlen=window_size)
        self._min_positive = min_positive

    def update(self, detected: bool | None) -> bool | None:
        if detected is not None:
            self._values.append(detected)
        if len(self._values) < self._min_positive:
            return None
        return sum(self._values) >= self._min_positive
~~~

- [ ] **Step 4: Add failing detector tests with a fake result**

~~~python
from pathlib import Path
from types import SimpleNamespace

from fleetiq_training_dms.phone_detector import PhoneUseDetector


class Values:
    def __init__(self, values):
        self.values = values

    def tolist(self):
        return self.values


class FakeModel:
    def __init__(self, result):
        self.result = result

    def predict(self, **kwargs):
        return [self.result]


def test_detector_keeps_only_confident_cell_phone(tmp_path: Path):
    image = tmp_path / 'frame.jpg'
    image.write_bytes(b'frame')
    result = SimpleNamespace(
        names={0: 'person', 67: 'cell phone'},
        boxes=SimpleNamespace(cls=Values([0, 67]), conf=Values([0.99, 0.72])),
    )
    detector = PhoneUseDetector(tmp_path / 'unused.pt', model=FakeModel(result))
    assert detector.detect(image) is True


def test_detector_returns_none_when_unavailable(tmp_path: Path):
    assert PhoneUseDetector(tmp_path / 'missing.pt').detect(tmp_path / 'frame.jpg') is None
~~~

- [ ] **Step 5: Implement lazy loading and result parsing**

~~~python
from pathlib import Path
from typing import Any


class PhoneUseDetector:
    def __init__(self, model_path: Path, confidence: float = 0.40, model: Any = None) -> None:
        if not 0 <= confidence <= 1:
            raise ValueError('phone confidence must be between zero and one')
        self._confidence = confidence
        self._model = model
        if self._model is None and model_path.is_file():
            try:
                from ultralytics import YOLO
                self._model = YOLO(str(model_path))
            except Exception:
                self._model = None

    def detect(self, image_path: Path) -> bool | None:
        if self._model is None or not image_path.is_file():
            return None
        try:
            result = self._model.predict(source=str(image_path), verbose=False)[0]
            return any(
                result.names[int(class_id)] == 'cell phone' and score >= self._confidence
                for class_id, score in zip(
                    result.boxes.cls.tolist(),
                    result.boxes.conf.tolist(),
                    strict=True,
                )
            )
        except Exception:
            return None
~~~

Keep both classes in phone_detector.py. Do not import Ultralytics at module import time.

- [ ] **Step 6: Run focused tests**

~~~bash
uv run --package fleetiq-training-dms pytest ml/training/dms/tests/test_phone_detector.py -v
~~~

Expected: all tests pass.

- [ ] **Step 7: Commit only owned files**

~~~bash
git add ml/training/dms/src/fleetiq_training_dms/phone_detector.py ml/training/dms/tests/test_phone_detector.py
git commit --only ml/training/dms/src/fleetiq_training_dms/phone_detector.py ml/training/dms/tests/test_phone_detector.py -m 'feat(dms): detect stable phone use'
~~~

---

### Task 2: Offline Trip Prediction Output

**Files:**
- Modify: ml/training/dms/src/fleetiq_training_dms/predict.py:16-116
- Create: ml/training/dms/tests/test_predict_phone_use.py

**Interfaces:**
- Consumes: PhoneUseDetector and PhoneUseSmoother from Task 1.
- Produces: predict_sequence_trip(..., phone_detector: PhoneUseDetector | None = None) -> pd.DataFrame with phone_use.
- Produces CLI flags --phone-model and --phone-confidence.

- [ ] **Step 1: Write the failing integration test**

~~~python
from pathlib import Path

import pandas as pd
import torch

from fleetiq_training_dms.dataset import FEATURE_COLS
from fleetiq_training_dms.predict import predict_sequence_trip


class StateModel(torch.nn.Module):
    def forward(self, value):
        return torch.tensor([[1.0, 0.0, 0.0, 0.0, 0.0]])


class PhoneDetector:
    def detect(self, image_path: Path):
        return True


def test_trip_prediction_emits_smoothed_phone_use(monkeypatch, tmp_path: Path):
    driver = tmp_path / 'Phone-Test' / 'driver'
    driver.mkdir(parents=True)
    for frame_id in range(3):
        (driver / f'frame_{frame_id:06d}.jpg').write_bytes(b'frame')
    features = pd.DataFrame([
        {'frame_id': frame_id, 'timestamp': frame_id / 20, **dict.fromkeys(FEATURE_COLS, 0.0)}
        for frame_id in range(3)
    ])
    monkeypatch.setattr(
        'fleetiq_training_dms.predict.extract_features_from_trip',
        lambda *args, **kwargs: features,
    )

    result = predict_sequence_trip(
        StateModel(),
        driver.parent,
        seq_len=1,
        phone_detector=PhoneDetector(),
    )

    assert result['phone_use'].tolist() == [None, None, True]
~~~

- [ ] **Step 2: Run the test and verify the missing-argument failure**

~~~bash
uv run --package fleetiq-training-dms pytest ml/training/dms/tests/test_predict_phone_use.py -v
~~~

Expected: predict_sequence_trip rejects phone_detector.

- [ ] **Step 3: Add detection to the existing frame loop**

Import PhoneUseDetector and PhoneUseSmoother, add the optional argument, construct one smoother per trip, and append:

~~~python
phone_smoother = PhoneUseSmoother()

frame_id = int(df_feat.iloc[i]['frame_id'])
raw_phone_use = (
    phone_detector.detect(trip_dir / 'driver' / f'frame_{frame_id:06d}.jpg')
    if phone_detector is not None
    else None
)
phone_use = phone_smoother.update(raw_phone_use)

results.append({
    'frame_id': frame_id,
    'timestamp': df_feat.iloc[i]['timestamp'],
    'predicted_driver_state': pred_state,
    'phone_use': phone_use,
})
~~~

- [ ] **Step 4: Add CLI construction**

~~~python
parser.add_argument('--phone-model', type=Path, default=Path('yolo11n.pt'))
parser.add_argument('--phone-confidence', type=float, default=0.40)

phone_detector = PhoneUseDetector(args.phone_model, confidence=args.phone_confidence)
~~~

Pass phone_detector to predict_sequence_trip. Keep the broad state logic unchanged.

- [ ] **Step 5: Run DMS tests**

~~~bash
uv run --package fleetiq-training-dms pytest ml/training/dms/tests/test_phone_detector.py ml/training/dms/tests/test_predict_phone_use.py -v
~~~

Expected: all pass. Empty phone values serialize as empty CSV cells.

- [ ] **Step 6: Commit only prediction files**

~~~bash
git add ml/training/dms/src/fleetiq_training_dms/predict.py ml/training/dms/tests/test_predict_phone_use.py
git commit --only ml/training/dms/src/fleetiq_training_dms/predict.py ml/training/dms/tests/test_predict_phone_use.py -m 'feat(dms): emit phone use in trip predictions'
~~~

---

### Task 3: Bounded Fusion Scoring

**Files:**
- Modify: services/fusion-worker/src/fleetiq_fusion/scoring.py:17-60
- Modify: services/fusion-worker/src/fleetiq_fusion/worker.py:38-46
- Modify: services/fusion-worker/tests/test_scoring.py
- Modify: services/fusion-worker/tests/test_compound_risk.py

**Interfaces:**
- Consumes: DriverState.phone_use: bool | None.
- Produces: RiskScorer.score(..., phone_use: bool | None = None) and explanation code phone_use.

- [ ] **Step 1: Write failing score tests**

~~~python
def test_phone_use_is_actionable_without_overwriting_state() -> None:
    result = RiskScorer().score(
        ttc_s=None,
        driver_state='attentive',
        phone_use=True,
        speed_mps=10.0,
        lane_offset_m=None,
    )
    assert result.penalties['attention'] == 15
    assert result.explanation_codes == ['phone_use']


def test_phone_use_does_not_duplicate_distraction_penalty() -> None:
    result = RiskScorer().score(
        ttc_s=None,
        driver_state='distracted',
        phone_use=True,
        speed_mps=10.0,
        lane_offset_m=None,
    )
    assert result.penalties['attention'] == 15
    assert result.explanation_codes == ['driver_distraction', 'phone_use']
~~~

- [ ] **Step 2: Run and verify failure**

~~~bash
uv run --package fleetiq-fusion-worker pytest services/fusion-worker/tests/test_scoring.py -v
~~~

Expected: phone_use is not accepted.

- [ ] **Step 3: Implement one bounded attention penalty**

Add phone_use: bool | None = None to RiskScorer.score, then replace the attention block with:

~~~python
attention_penalty = 0
if driver_state == 'drowsy':
    attention_penalty = 25
    codes.append('driver_drowsiness')
    severity = max(severity, 3)
elif driver_state == 'distracted':
    attention_penalty = 15
    codes.append('driver_distraction')
    severity = max(severity, 2)

if phone_use is True:
    attention_penalty = max(attention_penalty, 15)
    codes.append('phone_use')
    severity = max(severity, 2)
~~~

The existing collision_penalty and attention_penalty compound-risk condition remains unchanged.

- [ ] **Step 4: Forward the contract field**

In FusionWorker.fuse:

~~~python
phone_use=dms.driver_state.phone_use,
~~~

Place it beside driver_state in the RiskScorer call.

- [ ] **Step 5: Add a worker compound-risk check**

Use DriverState(state='attentive', confidence=0.9, phone_use=True) with the existing TTC 1.4 fixture:

~~~python
assert event.event_type == 'compound_risk'
assert 'phone_use' in event.explanation
assert 'compound_risk' in event.explanation
~~~

- [ ] **Step 6: Run all fusion tests**

~~~bash
uv run --package fleetiq-fusion-worker pytest services/fusion-worker/tests -v
~~~

Expected: all pass; existing distraction and drowsiness scores are unchanged.

- [ ] **Step 7: Commit the fusion slice**

~~~bash
git add services/fusion-worker/src/fleetiq_fusion/scoring.py services/fusion-worker/src/fleetiq_fusion/worker.py services/fusion-worker/tests/test_scoring.py services/fusion-worker/tests/test_compound_risk.py
git commit --only services/fusion-worker/src/fleetiq_fusion/scoring.py services/fusion-worker/src/fleetiq_fusion/worker.py services/fusion-worker/tests/test_scoring.py services/fusion-worker/tests/test_compound_risk.py -m 'feat(fusion): score confirmed phone use'
~~~

---

### Task 4: Historical API Prediction Overlay

**Files:**
- Modify: apps/api/src/fleetiq_api/config.py:12-133
- Modify: apps/api/src/fleetiq_api/historical_replay.py:49-83,314-323
- Modify: apps/api/src/fleetiq_api/schemas.py:63-77
- Modify: apps/api/src/fleetiq_api/trajectory.py:54-71
- Modify: apps/api/tests/test_historical_replay.py
- Modify: apps/api/tests/test_trajectory.py
- Modify: apps/api/tests/test_config.py

**Interfaces:**
- Consumes: artifacts/predictions/dms/<trip_id>_twostage.csv with frame_id and phone_use.
- Produces: in-memory driver.phone_use and API TrajectoryPoint.phone_use: bool | None.

- [ ] **Step 1: Write a failing filesystem overlay test**

~~~python
import gzip
import json


def test_filesystem_store_overlays_phone_predictions(tmp_path) -> None:
    dataset = tmp_path / 'data'
    predictions = tmp_path / 'predictions'
    trip = dataset / 'T01-Sample'
    trip.mkdir(parents=True)
    predictions.mkdir()
    document = {'frames': [{'frame_id': 7, 'driver': {'state': 'alert'}}]}
    (trip / 'T01-Sample.json.gz').write_bytes(
        gzip.compress(json.dumps(document).encode())
    )
    (predictions / 'T01-Sample_twostage.csv').write_text(
        'frame_id,phone_use\n7,True\n',
        encoding='utf-8',
    )

    async def scenario():
        store = FilesystemTripMediaStore(dataset, predictions)
        return await store.read_trip_document('T01-Sample')

    result = asyncio.run(scenario())
    assert result['frames'][0]['driver']['phone_use'] is True
~~~

- [ ] **Step 2: Run and verify constructor failure**

~~~bash
uv run --package fleetiq-api pytest apps/api/tests/test_historical_replay.py -v
~~~

Expected: FilesystemTripMediaStore does not accept prediction root.

- [ ] **Step 3: Implement the stdlib CSV overlay**

Add prediction_root: Path | None = None to FilesystemTripMediaStore. After reading the trip document, call:

~~~python
import csv


def _overlay_phone_predictions(document: dict[str, object], path: Path) -> dict[str, object]:
    frames = document.get('frames')
    if not path.is_file() or not isinstance(frames, list):
        return document
    with path.open(newline='', encoding='utf-8') as stream:
        predictions = {
            int(row['frame_id']): row.get('phone_use', '').strip().casefold() == 'true'
            for row in csv.DictReader(stream)
            if row.get('frame_id', '').isdigit()
            and row.get('phone_use', '').strip().casefold() in {'true', 'false'}
        }
    for frame in frames:
        if not isinstance(frame, dict) or frame.get('frame_id') not in predictions:
            continue
        driver = frame.setdefault('driver', {})
        if isinstance(driver, dict):
            driver['phone_use'] = predictions[frame['frame_id']]
    return document
~~~

Blank/invalid values and missing CSV files leave the raw document unchanged.

- [ ] **Step 4: Configure the prediction root**

Add to ApiSettings:

~~~python
dms_prediction_root: Path = Path('artifacts/predictions/dms')
~~~

Parse FLEETIQ_DMS_PREDICTION_ROOT in from_environment. For filesystem replay construct:

~~~python
media = FilesystemTripMediaStore(settings.dataset_root, settings.dms_prediction_root)
~~~

Keep S3 behavior unchanged in this offline MVP.

- [ ] **Step 5: Verify environment parsing**

Add to test_config.py:

~~~python
def test_environment_parses_dms_prediction_root() -> None:
    settings = ApiSettings.from_environment(
        {
            'FLEETIQ_TESTING': 'true',
            'FLEETIQ_DMS_PREDICTION_ROOT': 'artifacts/test-dms',
        }
    )
    assert settings.dms_prediction_root == Path('artifacts/test-dms')
~~~

Import Path from pathlib in that test file.

- [ ] **Step 6: Write a failing trajectory test**

Add phone_use: True to the existing driver fixture, then assert:

~~~python
assert result.points[1].phone_use is True
assert result.points[0].phone_use is None
~~~

- [ ] **Step 7: Expose strict tri-state phone use**

In TrajectoryPoint:

~~~python
phone_use: bool | None = None
~~~

In build_trajectory:

~~~python
phone_use=_optional_bool(_mapping_value(driver, 'phone_use')),
~~~

Helper:

~~~python
def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None
~~~

- [ ] **Step 8: Run API tests**

~~~bash
uv run --package fleetiq-api pytest apps/api/tests/test_historical_replay.py apps/api/tests/test_trajectory.py apps/api/tests/test_config.py -v
~~~

Expected: all pass, including no-prediction paths.

- [ ] **Step 9: Commit the API slice**

~~~bash
git add apps/api/src/fleetiq_api/config.py apps/api/src/fleetiq_api/historical_replay.py apps/api/src/fleetiq_api/schemas.py apps/api/src/fleetiq_api/trajectory.py apps/api/tests/test_config.py apps/api/tests/test_historical_replay.py apps/api/tests/test_trajectory.py
git commit --only apps/api/src/fleetiq_api/config.py apps/api/src/fleetiq_api/historical_replay.py apps/api/src/fleetiq_api/schemas.py apps/api/src/fleetiq_api/trajectory.py apps/api/tests/test_config.py apps/api/tests/test_historical_replay.py apps/api/tests/test_trajectory.py -m 'feat(api): overlay trip phone-use predictions'
~~~

---

### Task 5: Dashboard Phone Evidence

**Files:**
- Modify: apps/web/src/lib/api.ts:20-38,126-150
- Modify: apps/web/src/lib/contracts.ts:30-52
- Modify: apps/web/src/lib/trip-evidence.ts:63-119
- Modify: apps/web/src/components/trip-replay-panel.tsx:26-36,78-95
- Modify: apps/web/src/components/trip-video-player.tsx:25-119
- Modify: apps/web/src/__tests__/trip-evidence.test.ts
- Modify: apps/web/src/__tests__/trip-trajectory.test.ts
- Create: apps/web/src/__tests__/trip-video-player-view.test.tsx

**Interfaces:**
- Consumes: API phone_use: boolean | null.
- Produces: TrajectoryPoint.phoneUse, source-aware phone evidence, and synchronized driver-frame replay.

- [ ] **Step 1: Add a failing evidence test**

Create a minimal phone-only trajectory so the existing top-three evidence limit cannot hide the assertion:

~~~typescript
const phoneTrajectory = {
  ...trajectory,
  points: [{
    ...trajectory.points[0],
    frameIndex: 10,
    phoneUse: true,
  }],
};
const evidence = buildTripEvidence(phoneTrajectory);
expect(evidence).toEqual(expect.arrayContaining([
  expect.objectContaining({
    label: 'Phone use detected',
    frameIndex: 10,
    severity: 3,
    view: 'driver',
  }),
]));
~~~

Add phoneUse: null to the original typed fixtures.

- [ ] **Step 2: Run and verify failure**

~~~bash
npm --prefix apps/web test -- --run src/__tests__/trip-evidence.test.ts
~~~

Expected: phone evidence is missing.

- [ ] **Step 3: Thread the field through types and API mapping**

Add to ApiTrajectoryPoint:

~~~typescript
phone_use: boolean | null;
~~~

Add to TrajectoryPoint:

~~~typescript
phoneUse: boolean | null;
~~~

Map in getTripTrajectory:

~~~typescript
phoneUse: point.phone_use,
~~~

Update every TrajectoryPoint test literal with phoneUse: null unless the case is phone-positive.

- [ ] **Step 4: Add frame-linked evidence**

Add view: 'road_left' to existing evidence records. Inside evidenceForPoint, add:

~~~typescript
if (point.phoneUse === true) {
  evidence.push({
    frameIndex: point.frameIndex,
    time,
    label: 'Phone use detected',
    detail: 'Stable in-cabin phone detection',
    severity: 3,
    view: 'driver',
  });
}
~~~

- [ ] **Step 5: Make evidence select its camera source**

Add to TripEvidence:

~~~typescript
view: 'road_left' | 'driver';
~~~

In TripVideoPlayer, keep cameraView state, use it in the frame URL, and switch it when an evidence trace is clicked:

~~~tsx
const [cameraView, setCameraView] = useState<'road_left' | 'driver'>('road_left');
const imageUrl = currentFrame === null
  ? null
  : '/api/trips/' + encodeURIComponent(tripId) + '/frames/' + cameraView + '/' + currentFrame;

onClick={() => {
  setIsPlaying(false);
  setCameraView(event.view);
  chooseFrame(event.frameIndex);
}}
~~~

Use cameraView in the image alt text and diagnostics label.
Change the surrounding replay heading from Road-facing replay to Camera replay
so it remains accurate after a phone event selects the driver view.

- [ ] **Step 6: Add a driver-frame selection test**

Render TripVideoPlayer in trip-video-player-view.test.tsx with one phone event whose view is driver. Click the trace button and assert the image source:

~~~tsx
render(
  <TripVideoPlayer
    tripId='T01-Sample'
    frameIndexes={[10]}
    selectedFrameIndex={10}
    evidence={[{
      detail: 'Stable in-cabin phone detection',
      frameIndex: 10,
      label: 'Phone use detected',
      severity: 3,
      time: '00:00.5',
      view: 'driver',
    }]}
    onFrameIndexChange={() => undefined}
  />,
);
fireEvent.click(screen.getByRole('button', { name: /Phone use detected/ }));
expect(screen.getByRole('img')).toHaveAttribute(
  'src',
  '/api/trips/T01-Sample/frames/driver/10',
);
~~~

Import render, fireEvent, and screen from @testing-library/react.

- [ ] **Step 7: Show the synchronized replay signal**

Add beside Driver state:

~~~tsx
<ReplaySignal
  label='Phone use'
  value={point?.phoneUse === true ? 'Detected' : point?.phoneUse === false ? 'Not detected' : 'Unavailable'}
  detail={point?.phoneUse === true ? 'Stable 3-of-5 frame detection' : 'Independent DMS signal'}
  tone={point?.phoneUse === true ? 'warning' : 'blue'}
/>
~~~

- [ ] **Step 8: Run web checks**

~~~bash
npm --prefix apps/web test
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
~~~

Expected: every command exits successfully.

- [ ] **Step 9: Commit the web slice**

~~~bash
git add apps/web/src/lib/api.ts apps/web/src/lib/contracts.ts apps/web/src/lib/trip-evidence.ts apps/web/src/components/trip-replay-panel.tsx apps/web/src/components/trip-video-player.tsx apps/web/src/__tests__/trip-evidence.test.ts apps/web/src/__tests__/trip-trajectory.test.ts apps/web/src/__tests__/trip-video-player-view.test.tsx
git commit --only apps/web/src/lib/api.ts apps/web/src/lib/contracts.ts apps/web/src/lib/trip-evidence.ts apps/web/src/components/trip-replay-panel.tsx apps/web/src/components/trip-video-player.tsx apps/web/src/__tests__/trip-evidence.test.ts apps/web/src/__tests__/trip-trajectory.test.ts apps/web/src/__tests__/trip-video-player-view.test.tsx -m 'feat(web): show phone-use evidence'
~~~

---

### Task 6: Documentation and End-to-End Verification

**Files:**
- Modify: ml/training/dms/README.md:38-53

**Interfaces:**
- Consumes: Tasks 1-5.
- Produces: repeatable demo commands and a verified T01 prediction artifact.

- [ ] **Step 1: Document model preparation and prediction**

Add:

~~~bash
uv run --with ultralytics python -c 'from ultralytics import YOLO; YOLO("yolo11n.pt")'
uv run --with ultralytics --package fleetiq-training-dms python -c 'from fleetiq_training_dms.predict import main; main()' --trip-dir data/Practice_Dataset/T01-Sample --phone-model yolo11n.pt --phone-confidence 0.40 --output artifacts/predictions/dms/T01-Sample_twostage.csv
~~~

State that the first command may use network once. Empty phone_use means unavailable/warming up, not false.

- [ ] **Step 2: Run focused Python checks**

~~~bash
uv run pytest ml/training/dms/tests/test_phone_detector.py ml/training/dms/tests/test_predict_phone_use.py services/fusion-worker/tests apps/api/tests/test_historical_replay.py apps/api/tests/test_trajectory.py apps/api/tests/test_config.py -v
~~~

Expected: all pass.

- [ ] **Step 3: Run web checks**

~~~bash
npm --prefix apps/web test
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
~~~

Expected: all pass.

- [ ] **Step 4: Cache the model once**

~~~bash
uv run --with ultralytics python -c 'from ultralytics import YOLO; YOLO("yolo11n.pt")'
~~~

Expected: yolo11n.pt exists locally. This is the only network-dependent step.

- [ ] **Step 5: Generate T01 predictions**

~~~bash
uv run --with ultralytics --package fleetiq-training-dms python -c 'from fleetiq_training_dms.predict import main; main()' --trip-dir data/Practice_Dataset/T01-Sample --phone-model yolo11n.pt --phone-confidence 0.40 --output artifacts/predictions/dms/T01-Sample_twostage.csv
~~~

Expected columns: frame_id,timestamp,predicted_driver_state,phone_use.

- [ ] **Step 6: Audit six frames**

Compare CSV rows with distracted frames 50, 150, 250 and alert frames 350, 450, 550. Keep 0.40 when phone frames are true and alert frames are false. If not, change only --phone-confidence and record the chosen value in the README command.

If no reasonable confidence threshold separates the reviewed frames, keep the signal null in the demo and record phone-detector fine-tuning as a separate follow-up; do not map distracted labels to phone use.

- [ ] **Step 7: Verify API output**

Start the API with FLEETIQ_DATASET_ROOT=data/Practice_Dataset and FLEETIQ_DMS_PREDICTION_ROOT=artifacts/predictions/dms, then run:

~~~bash
curl http://localhost:8000/api/v1/trips/T01-Sample/trajectory
~~~

Expected: phone_use matches the CSV by frame.

- [ ] **Step 8: Commit documentation only**

~~~bash
git add ml/training/dms/README.md
git commit --only ml/training/dms/README.md -m 'docs(dms): document phone-use demo'
~~~

Do not commit yolo11n.pt or generated prediction CSV artifacts.
