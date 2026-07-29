import Link from "next/link";

import { RiskTimeline } from "@/components/risk-timeline";
import { TripLiveView } from "@/components/trip-live-view";
import { getFleetTrips, getTrip } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function TripPage({
  params,
}: {
  params: Promise<{ tripId: string }>;
}) {
  const { tripId } = await params;
  const trip = getTrip(decodeURIComponent(tripId), await getFleetTrips());
  const events = [
    {
      time: "00:18.4",
      label: "TTC entered critical range",
      detail: `${trip.ttcS?.toFixed(1) ?? "--"} seconds / lead object continuity 0.91`,
      severity: 5,
    },
    {
      time: "00:17.9",
      label: "Driver attention dropped",
      detail: `${trip.driverState} / DMS confidence 0.88`,
      severity: 4,
    },
    {
      time: "00:16.2",
      label: "Closing speed increased",
      detail: "Relative speed 8.1 m/s / temporal depth stable",
      severity: 3,
    },
  ];

  return (
    <main>
      <Link className="back-link" href="/">
        &lt;- Fleet overview
      </Link>
      <section className="trip-header">
        <div>
          <span className="eyebrow">{trip.vehicleId} / synchronized replay</span>
          <h1>{trip.tripId}</h1>
          <p>{trip.latestAlert}</p>
        </div>
        <div className={`risk-stamp severity-${trip.severity}`}>
          <span>Risk severity</span>
          <strong>{trip.severity}/5</strong>
          <small>Safety score {trip.score}</small>
        </div>
      </section>

      <div className="trip-layout">
        <div>
          <TripLiveView tripId={trip.tripId} />
          <RiskTimeline events={events} />
        </div>
        <aside>
          <section className="panel evidence-panel">
            <span className="eyebrow">Current fused state</span>
            <dl>
              <div>
                <dt>TTC</dt>
                <dd>{trip.ttcS?.toFixed(1) ?? "--"} s</dd>
              </div>
              <div>
                <dt>Speed</dt>
                <dd>{Math.round(trip.speedMps * 3.6)} km/h</dd>
              </div>
              <div>
                <dt>Driver</dt>
                <dd>{trip.driverState}</dd>
              </div>
              <div>
                <dt>Model state</dt>
                <dd>{trip.modelStatus}</dd>
              </div>
            </dl>
          </section>
          <section className="panel coaching-panel">
            <span className="eyebrow">Assigned coaching</span>
            <h2>Increase following distance</h2>
            <p>
              Review the compound event where attention dropped while closing speed
              increased.
            </p>
            <div className="coach-meta">
              <span>Channel / Post-trip</span>
              <span>Evidence / 3 frames</span>
            </div>
          </section>
        </aside>
      </div>
    </main>
  );
}
