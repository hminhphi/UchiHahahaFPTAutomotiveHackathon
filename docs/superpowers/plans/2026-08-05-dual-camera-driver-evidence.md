# Dual-Camera Driver Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show synchronized road and driver frames, with broad driver state and independent phone-use state beside the driver evidence.

**Architecture:** Extend the existing `TripVideoPlayer` with the selected trajectory point's two DMS values. Render two image panes from the existing frame proxy at the same frame index; the existing controls continue to own playback. CSS switches from a single view to a two-pane grid that stacks on narrow screens.

**Tech Stack:** Next.js, React, TypeScript, CSS, Vitest, Testing Library.

---

## File Structure

- Modify: `apps/web/src/components/trip-video-player.tsx` — render both synchronized frame URLs and driver-signal labels.
- Modify: `apps/web/src/components/trip-replay-panel.tsx` — pass the selected point's state and phone-use values to the player.
- Modify: `apps/web/src/app/styles.css` — lay out and label the two camera panes responsively.
- Modify: `apps/web/src/__tests__/trip-video-player-view.test.tsx` — cover both frames and signal labels.

### Task 1: Cover dual-camera driver evidence

**Files:**
- Modify: `apps/web/src/__tests__/trip-video-player-view.test.tsx`

- [ ] **Step 1: Replace the existing test with a failing dual-camera expectation**

```tsx
render(
  <TripVideoPlayer
    tripId="T01-Sample"
    frameIndexes={[10]}
    selectedFrameIndex={10}
    driverState="distracted"
    phoneUse
    evidence={[]}
    onFrameIndexChange={() => undefined}
  />,
);

expect(screen.getByRole("img", { name: /road-facing camera frame 10/i }))
  .toHaveAttribute("src", "/api/trips/T01-Sample/frames/road_left/10");
expect(screen.getByRole("img", { name: /driver camera frame 10/i }))
  .toHaveAttribute("src", "/api/trips/T01-Sample/frames/driver/10");
expect(screen.getByText("Driver state")).toBeInTheDocument();
expect(screen.getByText("distracted")).toBeInTheDocument();
expect(screen.getByText("Phone use")).toBeInTheDocument();
expect(screen.getByText("Detected")).toBeInTheDocument();
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd apps/web && node node_modules/vitest/vitest.mjs run src/__tests__/trip-video-player-view.test.tsx --config vitest.config.ts`

Expected: FAIL because `TripVideoPlayerProps` has no `driverState` or `phoneUse` properties.

- [ ] **Step 3: Commit the failing test**

```bash
git add apps/web/src/__tests__/trip-video-player-view.test.tsx
git commit --only apps/web/src/__tests__/trip-video-player-view.test.tsx -m "test(web): cover dual camera evidence"
```

### Task 2: Render synchronized driver evidence

**Files:**
- Modify: `apps/web/src/components/trip-video-player.tsx`
- Modify: `apps/web/src/components/trip-replay-panel.tsx`

- [ ] **Step 1: Extend the player props and calculate both frame URLs**

```tsx
interface TripVideoPlayerProps {
  tripId: string;
  frameIndexes: number[];
  selectedFrameIndex: number | null;
  driverState: string | null;
  phoneUse: boolean | null;
  evidence: TripEvidence[];
  onFrameIndexChange: (frameIndex: number) => void;
}

const roadImageUrl = currentFrame === null
  ? null
  : `/api/trips/${encodeURIComponent(tripId)}/frames/road_left/${currentFrame}`;
const driverImageUrl = currentFrame === null
  ? null
  : `/api/trips/${encodeURIComponent(tripId)}/frames/driver/${currentFrame}`;
```

Remove `cameraView` state and change an evidence click to only stop playback
and select its frame:

```tsx
onClick={() => { setIsPlaying(false); chooseFrame(event.frameIndex); }}
```

- [ ] **Step 2: Replace the single image block with two named panes and signal labels**

```tsx
<div className="camera-panes">
  <CameraPane label="Road camera" imageUrl={roadImageUrl} currentFrame={currentFrame} />
  <CameraPane label="Driver camera" imageUrl={driverImageUrl} currentFrame={currentFrame} />
</div>
<div className="driver-signals">
  <span><b>Driver state</b>{driverState ?? "unknown"}</span>
  <span className={phoneUse ? "signal-detected" : ""}>
    <b>Phone use</b>{phoneUse === true ? "Detected" : phoneUse === false ? "Not detected" : "Unavailable"}
  </span>
</div>
```

Keep `CameraPane` as a small local function that renders an `<img>` when its
URL exists and a `Camera frame unavailable` placeholder when it does not. The
browser's broken-image affordance covers an unavailable served frame; do not
add per-camera loading state for this display-only change.

- [ ] **Step 3: Pass the selected trajectory values from the replay panel**

```tsx
<TripVideoPlayer
  tripId={tripId}
  frameIndexes={frameIndexes}
  selectedFrameIndex={currentFrameIndex}
  driverState={point?.driverState ?? null}
  phoneUse={point?.phoneUse ?? null}
  evidence={evidence}
  onFrameIndexChange={setCurrentFrameIndex}
/>
```

- [ ] **Step 4: Run the targeted test to verify it passes**

Run: `cd apps/web && node node_modules/vitest/vitest.mjs run src/__tests__/trip-video-player-view.test.tsx --config vitest.config.ts`

Expected: PASS.

- [ ] **Step 5: Commit the implementation**

```bash
git add apps/web/src/components/trip-video-player.tsx apps/web/src/components/trip-replay-panel.tsx
git commit --only apps/web/src/components/trip-video-player.tsx apps/web/src/components/trip-replay-panel.tsx -m "feat(web): show synchronized driver evidence"
```

### Task 3: Add responsive two-pane styling and verify

**Files:**
- Modify: `apps/web/src/app/styles.css`

- [ ] **Step 1: Add the camera-pane and driver-signal styles**

```css
.camera-panes { display: grid; gap: 8px; grid-template-columns: 1.45fr 1fr; height: 100%; }
.camera-pane { min-width: 0; overflow: hidden; position: relative; }
.camera-pane img { height: 100%; object-fit: cover; width: 100%; }
.camera-pane-label { background: rgba(2, 12, 31, .78); color: white; font-size: 9px; font-weight: 800; left: 9px; padding: 5px 7px; position: absolute; text-transform: uppercase; top: 9px; }
.driver-signals { background: #0c1c37; display: flex; gap: 8px; padding: 9px 12px; }
.driver-signals span { color: #dcecff; font-size: 11px; }
.driver-signals b { color: #8eafd9; font-size: 9px; letter-spacing: .06em; margin-right: 6px; text-transform: uppercase; }
.driver-signals .signal-detected { color: #ffb585; }
@media (max-width: 720px) { .camera-panes { grid-template-columns: 1fr; } }
```

- [ ] **Step 2: Run all web verification**

Run: `cd apps/web && node node_modules/vitest/vitest.mjs run --config vitest.config.ts && node node_modules/typescript/bin/tsc --noEmit && node node_modules/eslint/bin/eslint.js src --max-warnings=0`

Expected: all tests pass, TypeScript exits 0, and ESLint reports no warnings.

- [ ] **Step 3: Commit the styling**

```bash
git add apps/web/src/app/styles.css
git commit --only apps/web/src/app/styles.css -m "style(web): lay out dual camera replay"
```
