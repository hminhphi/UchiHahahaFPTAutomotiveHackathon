import type { DmsFrameAnalysis, NormalizedPoint } from "@/lib/operations";

export function DmsAnalysisOverlay({ analysis }: { analysis: DmsFrameAnalysis | null }) {
  const state = analysis?.driver_state;
  if (!state) return <span className="analysis-provenance">DMS artifact unavailable</span>;
  const box = state.face_bounding_box;
  return (
    <div className="analysis-overlay dms-overlay" aria-label="FleetIQ driver monitoring overlay">
      <svg viewBox="0 0 1 1" preserveAspectRatio="none">
        {box ? <rect x={box.x_min} y={box.y_min} width={box.x_max - box.x_min} height={box.y_max - box.y_min} /> : null}
        {state.face_hull.length ? <polygon points={points(state.face_hull)} /> : null}
        {state.left_eye_contour.length ? <polyline points={points(state.left_eye_contour)} /> : null}
        {state.right_eye_contour.length ? <polyline points={points(state.right_eye_contour)} /> : null}
        {state.mouth_contour.length ? <polyline points={points(state.mouth_contour)} /> : null}
        {state.head_axis.length === 2 ? <line x1={state.head_axis[0].x} y1={state.head_axis[0].y} x2={state.head_axis[1].x} y2={state.head_axis[1].y} /> : null}
      </svg>
      <div className="dms-features">
        <strong>{state.state} / {state.subtype ?? "unknown"}</strong>
        <span>EAR {format(state.ear)} · MAR {format(state.mar)} · PERCLOS {format(state.perclos)}</span>
        <span>yaw {format(state.head_yaw_deg)}° · pitch {format(state.head_pitch_deg)}°</span>
      </div>
      <span className="analysis-provenance">{analysis.producer} / {state.model_version ?? "model N/A"}</span>
    </div>
  );
}

function points(values: NormalizedPoint[]) { return values.map((point) => `${point.x},${point.y}`).join(" "); }
function format(value: number | null) { return value === null ? "N/A" : value.toFixed(2); }