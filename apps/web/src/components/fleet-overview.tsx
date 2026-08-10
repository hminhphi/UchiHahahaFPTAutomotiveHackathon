import Link from "next/link";

import type { FleetTrip } from "@/lib/contracts";

const statusCopy = {
  live: "Models live",
  precomputed: "FleetIQ precomputed",
  mock: "Fixture data",
  degraded: "Model degraded",
  reference: "Organizer telemetry",
} as const;

export function FleetOverview({ trips }: { trips: FleetTrip[] }) {
  const ranked = [...trips].sort(
    (left, right) => (right.severity ?? 0) - (left.severity ?? 0)
      || (left.score ?? Number.POSITIVE_INFINITY) - (right.score ?? Number.POSITIVE_INFINITY),
  );

  return (
    <section className="fleet-grid" aria-label="Fleet risk ranking">
      {ranked.map((trip, index) => (
        <Link
          className={`trip-card severity-${trip.severity ?? "unscored"}`}
          data-testid="trip-card"
          href={`/trips/${encodeURIComponent(trip.tripId)}`}
          key={trip.tripId}
        >
          <div className="trip-rank">0{index + 1}</div>
          <div className="trip-main">
            <div className="trip-title-row">
              <div>
                <span className="eyebrow">{trip.vehicleId}</span>
                <h2>{trip.tripId}</h2>
              </div>
              <div className="score-dial" aria-label={trip.score === null ? "Safety score pending validation" : `Safety score ${trip.score}`}>
                {trip.score ?? "--"}
              </div>
            </div>
            <p className="alert-copy">{trip.latestAlert}</p>
            <dl className="trip-metrics">
              <div>
                <dt>TTC</dt>
                <dd>{trip.ttcS === null ? "--" : `${trip.ttcS.toFixed(1)}s`}</dd>
              </div>
              <div>
                <dt>Speed</dt>
                <dd>{Math.round(trip.speedMps * 3.6)} km/h</dd>
              </div>
              <div>
                <dt>Driver</dt>
                <dd>{trip.driverState}</dd>
              </div>
            </dl>
          </div>
          <div className={`model-flag ${trip.modelStatus}`}>{statusCopy[trip.modelStatus]}</div>
        </Link>
      ))}
    </section>
  );
}
