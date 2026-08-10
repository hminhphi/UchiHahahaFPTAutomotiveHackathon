"use client";

import { useEffect, useState } from "react";
import { DmsAnalysisOverlay } from "@/components/dms-analysis-overlay";
import type { DmsFrameAnalysis } from "@/lib/operations";

const FOLLOWERS = [
  { view: "road_right", label: "Road-right stereo" },
  { view: "driver", label: "Driver monitoring" },
  { view: "depth", label: "Depth map" },
] as const;

export function SynchronizedFollowers({ tripId, frameIndex, dmsAnalysis = null }: { tripId: string; frameIndex: number | null; dmsAnalysis?: DmsFrameAnalysis | null }) {
  return (
    <aside className="synchronized-followers" aria-label="Frame synchronized follower cameras">
      {FOLLOWERS.map(({ view, label }) => (
        <Follower key={view} tripId={tripId} view={view} label={label} frameIndex={frameIndex} dmsAnalysis={view === "driver" ? dmsAnalysis : null} />
      ))}
    </aside>
  );
}

function Follower({ tripId, view, label, frameIndex, dmsAnalysis }: { tripId: string; view: string; label: string; frameIndex: number | null; dmsAnalysis: DmsFrameAnalysis | null }) {
  const source = frameIndex === null ? null : `/api/trips/${encodeURIComponent(tripId)}/frames/${view}/${frameIndex}`;
  const [failedSource, setFailedSource] = useState<string | null>(null);
  useEffect(() => setFailedSource(null), [source]);
  const unavailable = source === null || failedSource === source;
  return (
    <section className="follower-panel">
      <header><span>{label}</span><small>{frameIndex === null ? "Waiting" : `Frame ${frameIndex}`}</small></header>
      {!unavailable ? (
        <div className="follower-media">
          {/* Exact evidence frames must remain untransformed and frame-addressable. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={source} alt={`${label} at frame ${frameIndex}`} onError={() => setFailedSource(source)} />
          {view === "driver" ? <DmsAnalysisOverlay analysis={dmsAnalysis} /> : null}
        </div>
      ) : <p>{frameIndex === null ? "Waiting for road-left playback" : `Unavailable at frame ${frameIndex}`}</p>}
    </section>
  );
}