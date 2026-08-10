import type { RoadFrameAnalysis } from "@/lib/operations";

export function RoadAnalysisOverlay({ frameIndex, analysis }: { frameIndex: number | null; analysis: RoadFrameAnalysis | null }) {
  if (frameIndex === null) return null;
  return (
    <div className="analysis-overlay" aria-label="FleetIQ road perception overlay">
      <svg viewBox="0 0 640 360" preserveAspectRatio="none" role="img">
        {analysis?.detections.filter((detection) => detection.lane_relation === "in_lane").map((detection) => {
          const box = detection.bounding_box;
          const label = formatDetection(detection);
          return (
            <g key={detection.track_id} className={`road-detection risk-${detection.risk_level}`}>
              <rect x={box.x_min} y={box.y_min} width={box.x_max - box.x_min} height={box.y_max - box.y_min} />
              <rect className="label-bg" x={box.x_min} y={Math.max(0, box.y_min - 20)} width={Math.min(260, Math.max(105, label.length * 6.4))} height="20" />
              <text x={box.x_min + 5} y={Math.max(14, box.y_min - 6)}>{label}</text>
            </g>
          );
        })}
      </svg>
      <span className="analysis-provenance">{analysis ? `${analysis.producer} / ${analysis.depth_state?.source ?? "depth N/A"}` : "AI artifact unavailable"}</span>
    </div>
  );
}

function formatDetection(detection: RoadFrameAnalysis["detections"][number]) {
  const distance = detection.distance_m === null ? "N/A" : `${detection.distance_m.toFixed(1)}m`;
  const ttc = detection.ttc_s === null ? "TTC N/A" : `TTC ${detection.ttc_s.toFixed(1)}s`;
  return `#${detection.track_id} ${detection.label} ${distance} ${ttc}`;
}
