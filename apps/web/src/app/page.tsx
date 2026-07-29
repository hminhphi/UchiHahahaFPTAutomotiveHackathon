import { FleetOverview } from "@/components/fleet-overview";
import { getFleetTrips } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function FleetPage() {
  const trips = await getFleetTrips();
  const critical = trips.filter((trip) => trip.severity >= 4).length;
  const average = Math.round(trips.reduce((total, trip) => total + trip.score, 0) / trips.length);

  return (
    <main>
      <section className="operations-hero">
        <div>
          <span className="eyebrow">Live fleet / shift 02</span>
          <h1>Risk, ranked for action.</h1>
          <p>
            Road risk, driver attention and vehicle telemetry aligned into one auditable
            operations view.
          </p>
        </div>
        <div className="hero-stats">
          <article>
            <span>Active trips</span>
            <strong>{trips.length.toString().padStart(2, "0")}</strong>
          </article>
          <article className={critical ? "critical-stat" : ""}>
            <span>Critical now</span>
            <strong>{critical.toString().padStart(2, "0")}</strong>
          </article>
          <article>
            <span>Fleet score</span>
            <strong>{average}</strong>
          </article>
        </div>
      </section>
      <section className="section-heading">
        <div>
          <span className="eyebrow">Priority queue</span>
          <h2>Trips requiring attention</h2>
        </div>
        <p>Sorted by severity, then safety score. Select a trip to inspect evidence.</p>
      </section>
      <FleetOverview trips={trips} />
    </main>
  );
}
