import Link from "next/link";

import { getDrivers, getFleetSummary, getFleetTripsData, getVehicles } from "@/lib/fleet-data";

export const dynamic = "force-dynamic";

export default async function ReportsPage() {
  const [drivers, vehicles, trips] = await Promise.all([getDrivers(), getVehicles(), getFleetTripsData()]);
  const summary = getFleetSummary(drivers, vehicles, trips);

  const reportTypes = [
    { id: "fleet-safety", title: "Fleet Safety Report", description: "Aggregate safety scores, risk distribution, and trend analysis across all vehicles and drivers.", trips: trips.length, period: "Jul 2026", format: "PDF / JSON" },
    { id: "driver-performance", title: "Driver Performance Report", description: "Individual driver scorecards with event breakdowns, coaching recommendations, and trend arrows.", trips: drivers.length, period: "Jul 2026", format: "PDF / CSV" },
    { id: "vehicle-utilization", title: "Vehicle Utilization Report", description: "Fleet asset usage, maintenance status, depot distribution, and trip assignment history.", trips: vehicles.length, period: "Jul 2026", format: "PDF / CSV" },
    { id: "risk-event-log", title: "Risk Event Log", description: "Complete auditable event log with timestamps, severity, confidence, evidence links, and coaching status.", trips: trips.filter((t) => t.severity >= 3).length, period: "Jul 2026", format: "JSON / CSV" },
    { id: "coaching-summary", title: "Coaching Actions Summary", description: "Issued coaching advisories, acknowledgement rates, driver response time, and effectiveness scoring.", trips: trips.filter((t) => t.score !== null && t.score < 70).length, period: "Jul 2026", format: "PDF" },
    { id: "ttc-analysis", title: "TTC & Near-Miss Analysis", description: "Time-to-collision distribution, critical threshold breaches, and near-miss event clustering by route and time.", trips: trips.filter((t) => t.severity >= 4).length, period: "Jul 2026", format: "PDF / JSON" },
  ];

  const topScoringTrips = [...trips].filter((t) => t.score !== null).sort((a, b) => (b.score ?? 0) - (a.score ?? 0)).slice(0, 5);
  const bottomScoringTrips = [...trips].filter((t) => t.score !== null).sort((a, b) => (a.score ?? 0) - (b.score ?? 0)).slice(0, 5);

  return (
    <main>
      <section className="operations-hero">
        <div>
          <span className="eyebrow">Reports &amp; exports / Jul 2026</span>
          <h1>Fleet reports.</h1>
          <p>
            Generate and export auditable fleet safety reports, driver performance scorecards, and risk event logs.
          </p>
        </div>
        <div className="hero-stats">
          <article>
            <span>Reports available</span>
            <strong>{reportTypes.length.toString().padStart(2, "0")}</strong>
          </article>
          <article>
            <span>Total trips</span>
            <strong>{summary.totalTrips.toString().padStart(2, "0")}</strong>
          </article>
          <article>
            <span>Fleet score</span>
            <strong>{summary.averageScore}</strong>
          </article>
        </div>
      </section>

      <section className="section-heading">
        <div>
          <span className="eyebrow">Generate report</span>
          <h2>Available report types</h2>
        </div>
        <p>Select a report to preview or export.</p>
      </section>

      <section className="report-type-grid">
        {reportTypes.map((report) => (
          <article className="panel report-type-card" key={report.id}>
            <div className="report-type-header">
              <span className="eyebrow">{report.format}</span>
              <h2>{report.title}</h2>
            </div>
            <p>{report.description}</p>
            <div className="report-type-meta">
              <span>{report.trips} records</span>
              <span>{report.period}</span>
            </div>
            <div className="report-type-actions">
              <button className="report-btn primary" type="button">Generate</button>
              <button className="report-btn" type="button">Preview</button>
            </div>
          </article>
        ))}
      </section>

      <section className="report-comparison-grid">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Top performers</span>
              <h2>Highest scoring trips</h2>
            </div>
            <span className="count-badge">{topScoringTrips.length.toString().padStart(2, "0")} trips</span>
          </div>
          <div className="report-trip-list">
            {topScoringTrips.map((trip) => (
              <Link className="report-trip-row" href={`/trips/${trip.tripId}`} key={trip.tripId}>
                <div>
                  <strong>{trip.tripId}</strong>
                  <small>{trip.routeName}</small>
                </div>
                <span className="report-trip-score high">{trip.score}/100</span>
              </Link>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Needs attention</span>
              <h2>Lowest scoring trips</h2>
            </div>
            <span className="count-badge">{bottomScoringTrips.length.toString().padStart(2, "0")} trips</span>
          </div>
          <div className="report-trip-list">
            {bottomScoringTrips.map((trip) => (
              <Link className="report-trip-row" href={`/trips/${trip.tripId}`} key={trip.tripId}>
                <div>
                  <strong>{trip.tripId}</strong>
                  <small>{trip.routeName}</small>
                </div>
                <span className="report-trip-score low">{trip.score}/100</span>
              </Link>
            ))}
          </div>
        </article>
      </section>
    </main>
  );
}