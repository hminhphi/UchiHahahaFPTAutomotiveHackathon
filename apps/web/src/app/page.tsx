import { FleetOverview } from "@/components/fleet-overview";
import { getFleetTrips } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function FleetPage() {
  const trips = await getFleetTrips();
  const critical = trips.filter((trip) => (trip.severity ?? 0) >= 4).length;
  const scores = trips.flatMap((trip) => trip.score === null ? [] : [trip.score]);
  const average = scores.length ? Math.round(scores.reduce((total, score) => total + score, 0) / scores.length) : null;

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
            <span>Validated scores</span>
            <strong>{average ?? "--"}</strong>
          </article>
        </div>
      </section>
      <section className="section-heading">
        <div>
          <span className="eyebrow">Priority queue</span>
          <h2>Trips requiring attention</h2>
        </div>
        <p>Scores remain unranked until fleet validation is complete. Select a trip to inspect evidence.</p>
      </section>
      <FleetOverview trips={trips} />
    </main>
  );
}
