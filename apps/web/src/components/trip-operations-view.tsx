"use client";

import { useState } from "react";

import { TripReplayPanel } from "@/components/trip-replay-panel";
import type { FleetTrip, TripTrajectory } from "@/lib/contracts";
import type { RoadVideoDescriptor, TripOperationsDetail } from "@/lib/operations";
import type { TripEvidence, TripScoreSignal } from "@/lib/trip-evidence";

interface TripOperationsViewProps {
  trip: FleetTrip;
  operations: TripOperationsDetail | null;
  trajectory: TripTrajectory | null;
  roadVideo: RoadVideoDescriptor | null;
  events: TripEvidence[];
  scoreSignals: TripScoreSignal[];
}

export function TripOperationsView({
  trip,
  operations,
  trajectory,
  roadVideo,
  events,
  scoreSignals,
}: TripOperationsViewProps) {
  const driverName = operations?.driver?.displayName ?? trip.driverName;
  const vehicle = operations?.vehicle;
  const orderCount = operations?.trip.orderCount ?? 0;
  const initialFrame = roadVideo?.frameMap[0]?.frameIndex ?? trajectory?.points[0]?.frameIndex ?? null;
  const [currentFrameIndex, setCurrentFrameIndex] = useState<number | null>(initialFrame);

  return (
    <>
      <section className="trip-facts panel" aria-label="Trip logistics facts">
        <div><span>Driver</span><strong>{driverName}</strong><small>{operations?.driver?.employeeCode ?? "Historical profile"}</small></div>
        <div><span>Vehicle</span><strong>{vehicle?.licensePlate ?? trip.vehicleId}</strong><small>{operations?.trip.vehicleClass ?? "Fleet vehicle"}</small></div>
        <div><span>Route</span><strong>{operations?.trip.routeName ?? "Practice route"}</strong><small>{operations?.vehicle?.depotName ?? "Local demo"}</small></div>
        <div><span>Orders</span><strong>{orderCount} deliveries</strong><small>{operations?.trip.cargoClass ?? "Dataset evidence"}</small></div>
        <div><span>Vehicle size</span><strong>{vehicle ? `${vehicle.lengthM.toFixed(1)} x ${vehicle.widthM.toFixed(1)} m` : "Not provided"}</strong><small>{vehicle ? `${vehicle.payloadCapacityKg.toFixed(0)} kg payload` : "Awaiting operations data"}</small></div>
      </section>

      <section className="report-grid">
        <article className="panel score-panel">
          <span className="eyebrow">Safety score</span>
          <div className="score-content">
            <div className="score-ring" style={{ background: `conic-gradient(var(--blue) 0 ${trip.score}%, var(--orange) ${trip.score}% ${Math.min(100, trip.score + 8)}%, #e5eaf2 ${Math.min(100, trip.score + 8)}% 100%)` }}><strong>{trip.score}</strong><span>/100</span></div>
            <div><h2>Auditable score signals</h2>{scoreSignals.map((signal) => <ScoreBar key={signal.label} {...signal} />)}</div>
          </div>
        </article>
        <article className="panel deductions-panel" aria-label="Frame-linked review">
          <span className="eyebrow">Evidence navigation</span>
          <h2>Frame-linked review</h2>
          {events.length ? (
            <div className="frame-event-list">
              {events.map((event) => (
                <button
                  key={`${event.label}-${event.frameIndex}`}
                  type="button"
                  className={`frame-event-button severity-${event.severity}${currentFrameIndex === event.frameIndex ? " selected" : ""}`}
                  onClick={() => setCurrentFrameIndex(event.frameIndex)}
                  title={event.detail}
                >
                  <b>{event.time}</b><span>{event.label}</span><small>Frame {event.frameIndex}</small>
                </button>
              ))}
            </div>
          ) : <p className="empty-evidence">No risk event was recorded for this trip.</p>}
        </article>
      </section>

      <TripReplayPanel tripId={trip.tripId} trajectory={trajectory} evidence={events} roadVideo={roadVideo} currentFrameIndex={currentFrameIndex} onFrameIndexChange={setCurrentFrameIndex} />
    </>
  );
}

function ScoreBar({ label, value, note }: TripScoreSignal) {
  return <div className="score-bar"><span title={note}>{label}</span><b>{value === null ? "N/A" : `${value}%`}</b><i><em style={{ width: `${value ?? 0}%` }} /></i></div>;
}