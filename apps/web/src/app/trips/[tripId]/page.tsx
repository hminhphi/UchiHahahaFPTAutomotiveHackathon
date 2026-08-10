import Link from "next/link";

import { TripOperationsView } from "@/components/trip-operations-view";
import { getFleetTrips, getRoadVideoDescriptor, getTrip, getTripEventMarkers, getTripFusionSummary, getTripOperations, getTripTrajectory } from "@/lib/api";
import { buildTripEvidence, buildTripScoreSignals } from "@/lib/trip-evidence";

export const dynamic = "force-dynamic";

export default async function TripPage({
  params,
}: {
  params: Promise<{ tripId: string }>;
}) {
  const { tripId } = await params;
  const decodedTripId = decodeURIComponent(tripId);
  const [fleetTrips, trajectory, roadVideo, operations, eventMarkers, fusionSummary] = await Promise.all([
    getFleetTrips(),
    getTripTrajectory(decodedTripId),
    getRoadVideoDescriptor(decodedTripId),
    getTripOperations(decodedTripId),
    getTripEventMarkers(decodedTripId),
    getTripFusionSummary(decodedTripId),
  ]);
  const trip = getTrip(decodedTripId, fleetTrips);
  const localEvidence = buildTripEvidence(trajectory);
  const events = eventMarkers.length ? eventMarkers.map((event) => {
    const point = trajectory?.points.find((candidate) => candidate.frameIndex === event.frameIndex);
    return {
      frameIndex: event.frameIndex,
      time: formatTime(point?.timestampS ?? event.frameIndex / (roadVideo?.fps ?? 10)),
      label: event.title,
      detail: `${Math.round(event.confidence * 100)}% confidence`,
      severity: event.severity,
    };
  }) : localEvidence;
  const scoreSignals = buildTripScoreSignals(fusionSummary);

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

      <TripOperationsView trip={trip} operations={operations} trajectory={trajectory} roadVideo={roadVideo} events={events} scoreSignals={scoreSignals} />
    </main>
  );
}

function formatTime(timestampS: number): string {
  const minutes = Math.floor(timestampS / 60).toString().padStart(2, "0");
  const seconds = (timestampS % 60).toFixed(1).padStart(4, "0");
  return `${minutes}:${seconds}`;
}