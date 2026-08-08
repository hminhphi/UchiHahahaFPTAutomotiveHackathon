"use client";

import { useState } from "react";

import { TripTrajectory, findTrajectoryPoint } from "@/components/trip-trajectory";
import { TripVideoPlayer } from "@/components/trip-video-player";
import type { TripTrajectory as TripTrajectoryData } from "@/lib/contracts";
import type { TripEvidence } from "@/lib/trip-evidence";

export function TripReplayPanel({ tripId, trajectory, evidence }: { tripId: string; trajectory: TripTrajectoryData | null; evidence: TripEvidence[] }) {
  const frameIndexes = trajectory?.points.map((point) => point.frameIndex) ?? [];
  const [currentFrameIndex, setCurrentFrameIndex] = useState<number | null>(frameIndexes[0] ?? null);
  const point = currentFrameIndex === null || !trajectory ? null : findTrajectoryPoint(trajectory.points, currentFrameIndex);

  return (
    <>
      <section className="evidence-grid">
        <article className="video-panel panel">
          <div className="panel-heading">
            <div><span className="eyebrow">Contextual video evidence</span><h2>Camera replay</h2></div>
            <span className="replay-chip">Frame-synchronised</span>
          </div>
          <TripVideoPlayer tripId={tripId} frameIndexes={frameIndexes} selectedFrameIndex={currentFrameIndex} driverState={point?.driverState ?? null} phoneUse={point?.phoneUse ?? null} evidence={evidence} onFrameIndexChange={setCurrentFrameIndex} />
        </article>
        <aside className="signal-stack" aria-label="Frame synchronised telemetry">
          <ReplaySignal label="Replay time" value={point ? formatTime(point.timestampS) : "Waiting"} detail={point ? `Frame ${point.frameIndex}` : "Waiting for camera frame"} tone="blue" />
          <ReplaySignal label="Current speed" value={point ? `${point.speedKmh.toFixed(0)} km/h` : "-- km/h"} detail="Organizer ego telemetry" tone="blue" />
          <ReplaySignal label="Longitudinal accel" value={point ? `${point.longitudinalAccelMps2.toFixed(2)} m/s2` : "-- m/s2"} detail={handlingDetail(point, "longitudinal")} tone="warning" />
          <ReplaySignal label="Lateral accel" value={point ? `${point.lateralAccelMps2.toFixed(2)} m/s2` : "-- m/s2"} detail={handlingDetail(point, "lateral")} tone="warning" />
          <ReplaySignal label="TTC / headway" value={ttcValue(point)} detail={ttcDetail(point)} tone="warning" />
          <ReplaySignal label="Driver state" value={point?.driverState ?? "unknown"} detail={driverDetail(point)} tone="blue" />
          <ReplaySignal
            label="Phone use"
            value={point?.phoneUse === true ? "Detected" : point?.phoneUse === false ? "Not detected" : "Unavailable"}
            detail={point?.phoneUse === true ? "Stable 3-of-5 frame detection" : "Independent DMS signal"}
            tone={point?.phoneUse === true ? "warning" : "blue"}
          />
        </aside>
      </section>
      <section className="bottom-grid">
        <TripTrajectory trajectory={trajectory} currentFrameIndex={currentFrameIndex} />
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

function ttcValue(point: TripTrajectoryData["points"][number] | null) {
  if (!point) return "--";
  if (point.minTtcS !== null) return `${point.minTtcS.toFixed(1)} s`;
  if (point.headwayS !== null) return `${point.headwayS.toFixed(1)} s headway`;
  return "No valid TTC";
}

function ttcDetail(point: TripTrajectoryData["points"][number] | null) {
  if (!point) return "Waiting for camera frame";
  if (point.activeEventTypes.length) return point.activeEventTypes.join(", ");
  return "No target in simulator collision cone";
}

function driverDetail(point: TripTrajectoryData["points"][number] | null) {
  if (!point || point.driverAlertness === null) return "DMS telemetry unavailable";
  return `Alertness ${(point.driverAlertness * 100).toFixed(0)}% / simulator risk ${(point.simulatorRiskScore ?? 0).toFixed(0)}`;
}

function coachingHeadline(point: TripTrajectoryData["points"][number] | null) {
  if (point?.events.includes("harsh_brake")) return "Review harsh-brake response";
  if (point?.events.includes("fast_corner")) return "Reduce speed through the corner";
  if (point?.driverState === "distracted" || point?.driverState === "drowsy") return "Restore road attention";
  return "Maintain safe following distance";
}

function coachingDetail(point: TripTrajectoryData["points"][number] | null) {
  if (!point) return "Replay the trip to inspect frame-synchronised road video, route position, driver state, and vehicle telemetry.";
  if (point.events.length || point.activeEventTypes.length) return `Frame ${point.frameIndex} carries ${[...point.events, ...point.activeEventTypes].join(", ")}. Keep this evidence window linked to the coaching record.`;
  return `At ${formatTime(point.timestampS)}, the vehicle is travelling at ${point.speedKmh.toFixed(0)} km/h with driver state ${point.driverState}.`;
}
