import Link from "next/link";

import { RiskTimeline } from "@/components/risk-timeline";
import { TripReplayPanel } from "@/components/trip-replay-panel";
import { getFleetTrips, getTrip, getTripTrajectory } from "@/lib/api";
import { buildTripEvidence, buildTripScoreSignals } from "@/lib/trip-evidence";

export const dynamic = "force-dynamic";

export default async function TripPage({
  params,
}: {
  params: Promise<{ tripId: string }>;
}) {
  const { tripId } = await params;
  const decodedTripId = decodeURIComponent(tripId);
  const [fleetTrips, trajectory] = await Promise.all([getFleetTrips(), getTripTrajectory(decodedTripId)]);
  const trip = getTrip(decodedTripId, fleetTrips);
  const events = buildTripEvidence(trajectory);
  const scoreSignals = buildTripScoreSignals(trajectory);

  return (
    <main className="trip-console">
      <div className="report-heading">
        <div>
          <Link className="back-link" href="/">Fleet overview</Link>
          <h1>Trip report <span>/ {trip.tripId}</span></h1>
          <p>Completed trip replay with auditable road risk, vehicle state, and coaching evidence.</p>
        </div>
        <div className={`risk-stamp severity-${trip.severity}`}><span>Current risk</span><strong>{trip.severity}/5</strong><small>Safety score {trip.score}</small></div>
      </div>

      <section className="trip-facts panel">
        <div><span>Trip ID</span><strong>{trip.tripId}</strong></div>
        <div><span>Driver</span><strong>{trip.driverName}</strong></div>
        <div><span>Vehicle</span><strong>{trip.vehicleId}</strong></div>
        <div><span>Source</span><strong>Practice dataset</strong></div>
        <div><span>Playback</span><strong>Historical / 10 FPS</strong></div>
      </section>

      <section className="report-grid">
        <article className="panel score-panel">
          <span className="eyebrow">Safety score</span>
          <div className="score-content"><div className="score-ring" style={{ background: `conic-gradient(var(--blue) 0 ${trip.score}%, var(--orange) ${trip.score}% ${Math.min(100, trip.score + 8)}%, #e5eaf2 ${Math.min(100, trip.score + 8)}% 100%)` }}><strong>{trip.score}</strong><span>/100</span></div><div><h2>Auditable score signals</h2>{scoreSignals.map((signal) => <ScoreBar key={signal.label} {...signal} />)}</div></div>
        </article>
        <article className="panel deductions-panel">
          <div className="panel-heading"><div><span className="eyebrow">Evidence queue</span><h2>Auditable deductions</h2></div><span className="count-badge">{events.length.toString().padStart(2, "0")} events</span></div>
          {events.length ? events.map((event) => <div className="deduction-row" key={`${event.label}-${event.frameIndex}`}><span className={`event-dot severity-${event.severity}`} /><div><strong>{event.label}</strong><small>{event.detail}</small></div><time>{event.time}</time><b>Frame {event.frameIndex}</b></div>) : <p className="empty-evidence">No scored risk evidence is available for this trip.</p>}
        </article>
      </section>

      <RiskTimeline events={events} />
      <TripReplayPanel tripId={trip.tripId} trajectory={trajectory} evidence={events} />
    </main>
  );
}

function ScoreBar({ label, value, note }: { label: string; value: number | null; note: string }) {
  return <div className="score-bar"><span title={note}>{label}</span><b>{value === null ? "N/A" : `${value}%`}</b><i><em style={{ width: `${value ?? 0}%` }} /></i></div>;
}
