"use client";

import { useEffect, useState } from "react";
import { RoadLeftVideo } from "@/components/road-left-video";
import { TripTrajectory, findTrajectoryPoint } from "@/components/trip-trajectory";
import { SynchronizedFollowers } from "@/components/synchronized-followers";
import type { TripTrajectory as TripTrajectoryData } from "@/lib/contracts";
import { fetchFrameAnalysis, type DmsFrameAnalysis, type FusionFrameAnalysis, type RoadFrameAnalysis, type RoadVideoDescriptor } from "@/lib/operations";
import type { TripEvidence } from "@/lib/trip-evidence";

export function TripReplayPanel({ tripId, trajectory, evidence, roadVideo, currentFrameIndex, onFrameIndexChange }: { tripId: string; trajectory: TripTrajectoryData | null; evidence: TripEvidence[]; roadVideo: RoadVideoDescriptor | null; currentFrameIndex: number | null; onFrameIndexChange: (frameIndex: number) => void }) {
  const point = currentFrameIndex === null || !trajectory ? null : findTrajectoryPoint(trajectory.points, currentFrameIndex);
  const [roadAnalysis, setRoadAnalysis] = useState<RoadFrameAnalysis | null>(null);
  const [dmsAnalysis, setDmsAnalysis] = useState<DmsFrameAnalysis | null>(null);
  const [fusionAnalysis, setFusionAnalysis] = useState<FusionFrameAnalysis | null>(null);

  useEffect(() => {
    if (currentFrameIndex === null) return;
    const controller = new AbortController();
    Promise.all([
      fetchFrameAnalysis<RoadFrameAnalysis>(tripId, "road", currentFrameIndex, controller.signal),
      fetchFrameAnalysis<DmsFrameAnalysis>(tripId, "dms", currentFrameIndex, controller.signal),
      fetchFrameAnalysis<FusionFrameAnalysis>(tripId, "fusion", currentFrameIndex, controller.signal),
    ]).then(([road, dms, fusion]) => {
      setRoadAnalysis(road);
      setDmsAnalysis(dms);
      setFusionAnalysis(fusion);
    }).catch((error: unknown) => {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setRoadAnalysis(null);
      setDmsAnalysis(null);
      setFusionAnalysis(null);
    });
    return () => controller.abort();
  }, [currentFrameIndex, tripId]);

  return (
    <>
      <section className="evidence-grid">
        <article className="video-panel panel">
          <div className="panel-heading">
            <div><span className="eyebrow">Contextual video evidence</span><h2>Road-facing replay</h2></div>
            <span className="replay-chip">Frame-synchronised</span>
          </div>
          {roadVideo ? (
            <RoadLeftVideo descriptor={roadVideo} selectedFrameIndex={currentFrameIndex} onFrameIndexChange={onFrameIndexChange} analysis={roadAnalysis} />
          ) : (
            <div className="camera-placeholder road-video-unavailable"><strong>Road-left video unavailable</strong><span>Run the media packaging step for this trip.</span></div>
          )}
        </article>
        <SynchronizedFollowers tripId={tripId} frameIndex={currentFrameIndex} dmsAnalysis={dmsAnalysis} />
        <aside className="signal-stack" aria-label="Frame synchronised telemetry">
          <ReplaySignal label="Replay time" value={point ? formatTime(point.timestampS) : "Waiting"} detail={point ? `Frame ${point.frameIndex}` : "Waiting for camera frame"} tone="blue" />
          <ReplaySignal label="Current speed" value={point ? `${point.speedKmh.toFixed(0)} km/h` : "-- km/h"} detail="Organizer ego telemetry" tone="blue" />
          <ReplaySignal label="Longitudinal accel" value={point ? `${point.longitudinalAccelMps2.toFixed(2)} m/s2` : "-- m/s2"} detail={handlingDetail(point, "longitudinal")} tone="warning" />
          <ReplaySignal label="Lateral accel" value={point ? `${point.lateralAccelMps2.toFixed(2)} m/s2` : "-- m/s2"} detail={handlingDetail(point, "lateral")} tone="warning" />
          <ReplaySignal label="Fused analysis" value={fusionAnalysis ? "Ready" : "N/A"} detail={fusionAnalysis ? `${fusionAnalysis.producer} · rule score ready` : "Precomputed fusion unavailable"} tone="blue" />
          <ReplaySignal label="Object TTC" value={ttcValue(roadAnalysis)} detail={ttcDetail(roadAnalysis)} tone="warning" />
          <ReplaySignal label="Driver state" value={dmsAnalysis?.driver_state?.state ?? "unknown"} detail={driverDetail(dmsAnalysis)} tone="blue" />
        </aside>
      </section>
      <section className="bottom-grid">
        <TripTrajectory trajectory={trajectory} currentFrameIndex={currentFrameIndex} events={evidence} />
        <article className="panel coaching-panel">
          <span className="eyebrow">Driver coaching plan</span>
          <h2>{coachingHeadline(point)}</h2>
          <p>{coachingDetail(point)}</p>
          <div className="coach-meta"><span>Delivery / CarSky post-trip</span><span>Evidence / frame-linked telemetry</span></div>
        </article>
      </section>
    </>
  );
}

function ReplaySignal({ label, value, detail, tone }: { label: string; value: string; detail: string; tone: "warning" | "blue" }) {
  return <article className={`signal-card ${tone}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small><i><em /></i></article>;
}

function formatTime(timestampS: number) {
  const minutes = Math.floor(timestampS / 60);
  const seconds = timestampS % 60;
  return `${String(minutes).padStart(2, "0")}:${seconds.toFixed(1).padStart(4, "0")}`;
}

function handlingDetail(point: TripTrajectoryData["points"][number] | null, axis: "longitudinal" | "lateral") {
  if (!point) return "Waiting for camera frame";
  if (point.events.includes("harsh_brake")) return "Harsh-brake threshold crossed";
  if (point.events.includes("fast_corner")) return "Fast-corner threshold crossed";
  return axis === "longitudinal" ? "Forward and braking dynamics" : "Cornering dynamics";
}

function ttcValue(analysis: RoadFrameAnalysis | null) {
  const values = analysis?.detections.flatMap((item) => item.ttc_s === null || item.lane_relation !== "in_lane" ? [] : [item.ttc_s]) ?? [];
  return values.length ? `${Math.min(...values).toFixed(1)} s` : "N/A";
}

function ttcDetail(analysis: RoadFrameAnalysis | null) {
  if (!analysis) return "FleetIQ road artifact unavailable";
  return `${analysis.detections.length} tracked object(s) · ${analysis.producer}`;
}

function driverDetail(analysis: DmsFrameAnalysis | null) {
  const state = analysis?.driver_state;
  if (!state) return "DMS artifact unavailable";
  return `${analysis.producer} · confidence ${(state.confidence * 100).toFixed(0)}%`;
}

function coachingHeadline(point: TripTrajectoryData["points"][number] | null) {
  if (point?.events.includes("harsh_brake")) return "Review harsh-brake response";
  if (point?.events.includes("fast_corner")) return "Reduce speed through the corner";
  if (point?.driverState === "distracted" || point?.driverState === "drowsy") return "Restore road attention";
  return "Maintain safe following distance";
}

function coachingDetail(point: TripTrajectoryData["points"][number] | null) {
  if (!point) return "Replay the trip to inspect frame-synchronised road video, route position, driver state, and vehicle telemetry.";
  return `At ${formatTime(point.timestampS)}, the vehicle is travelling at ${point.speedKmh.toFixed(0)} km/h. Review this synchronized evidence before assigning coaching.`;
}
