import Link from "next/link";

import { getDriverRiskProfiles, getDrivers, getFleetTripsData } from "@/lib/fleet-data";

export const dynamic = "force-dynamic";

export default async function DriversPage() {
  const [drivers, trips] = await Promise.all([getDrivers(), getFleetTripsData()]);
  const profiles = getDriverRiskProfiles(drivers, trips);
  const ranked = [...profiles].sort((a, b) => b.score - a.score);
  const teams = [...new Set(drivers.map((d) => d.team))].sort();

  const statusLabels: Record<string, string> = { on_duty: "On duty", off_duty: "Off duty", on_break: "On break" };
  const trendIcons: Record<string, string> = { improving: "\u2191", stable: "\u2192", declining: "\u2193" };
  const trendColors: Record<string, string> = { improving: "var(--green)", stable: "var(--gold)", declining: "var(--orange)" };

  return (
    <main>
      <section className="operations-hero">
        <div>
          <span className="eyebrow">Driver management / shift 02</span>
          <h1>Driver intelligence.</h1>
          <p>
            Ranked by safety score with risk profiles, event history, and coaching readiness.
          </p>
        </div>
        <div className="hero-stats">
          <article>
            <span>Active drivers</span>
            <strong>{drivers.filter((d) => d.status === "on_duty").length.toString().padStart(2, "0")}</strong>
          </article>
          <article className={drivers.filter((d) => d.riskLevel === "critical" || d.riskLevel === "high").length > 0 ? "critical-stat" : ""}>
            <span>At risk</span>
            <strong>{drivers.filter((d) => d.riskLevel === "critical" || d.riskLevel === "high").length.toString().padStart(2, "0")}</strong>
          </article>
          <article>
            <span>Fleet avg</span>
            <strong>{Math.round(drivers.reduce((s, d) => s + d.aggregateScore, 0) / drivers.length)}</strong>
          </article>
        </div>
      </section>

      <section className="section-heading">
        <div>
          <span className="eyebrow">Teams</span>
          <h2>Filter by team</h2>
        </div>
        <div className="team-chips">
          <span className="team-chip active">All teams</span>
          {teams.map((team) => (
            <span className="team-chip" key={team}>{team}</span>
          ))}
        </div>
      </section>

      <section className="driver-grid" aria-label="Driver ranking">
        {ranked.map((profile, index) => {
          const driver = drivers.find((d) => d.driverId === profile.driverId)!;
          const driverTrips = trips.filter((t) => t.driverId === driver.driverId).slice(0, 3);
          return (
            <article className={`driver-card risk-${driver.riskLevel}`} key={profile.driverId}>
              <div className="driver-rank">{(index + 1).toString().padStart(2, "0")}</div>
              <div className="driver-main">
                <div className="driver-header">
                  <div>
                    <span className="eyebrow">{driver.driverId}</span>
                    <h2>{driver.displayName}</h2>
                  </div>
                  <div className={`score-dial ${driver.aggregateScore < 60 ? "score-critical" : driver.aggregateScore < 75 ? "score-warn" : ""}`} aria-label={`Safety score ${driver.aggregateScore}`}>
                    {driver.aggregateScore}
                  </div>
                </div>
                <div className="driver-meta">
                  <span className={`status-badge ${driver.status}`}>{statusLabels[driver.status]}</span>
                  <span className="team-badge">{driver.team}</span>
                  <span className="license-badge">License {driver.licenseClass}</span>
                </div>
                <dl className="driver-metrics">
                  <div>
                    <dt>Trips</dt>
                    <dd>{driver.tripCount}</dd>
                  </div>
                  <div>
                    <dt>Distance</dt>
                    <dd>{driver.totalDistanceKm} km</dd>
                  </div>
                  <div>
                    <dt>TTC events</dt>
                    <dd className={profile.ttcEvents > 0 ? "metric-warn" : ""}>{profile.ttcEvents}</dd>
                  </div>
                  <div>
                    <dt>Risk trend</dt>
                    <dd style={{ color: trendColors[profile.riskTrend] }}>{trendIcons[profile.riskTrend]} {profile.riskTrend}</dd>
                  </div>
                </dl>
                <div className="driver-trips">
                  <span className="eyebrow">Recent trips</span>
                  {driverTrips.map((trip) => (
                    <Link className={`driver-trip-row severity-${trip.severity}`} href={`/trips/${trip.tripId}`} key={trip.tripId}>
                      <span>{trip.tripId}</span>
                      <span>{trip.routeName}</span>
                      <span className={`severity-tag severity-${trip.severity}`}>S{trip.severity}</span>
                      <span>{trip.score ?? "--"}/100</span>
                    </Link>
                  ))}
                </div>
              </div>
            </article>
          );
        })}
      </section>
    </main>
  );
}