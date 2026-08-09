import Link from "next/link";

import { getDriverRiskProfiles, getDrivers, getFleetSummary, getFleetTripsData, getRiskInsights, getVehicles } from "@/lib/fleet-data";

export const dynamic = "force-dynamic";

export default async function RiskInsightsPage() {
  const [drivers, vehicles, trips] = await Promise.all([getDrivers(), getVehicles(), getFleetTripsData()]);
  const summary = getFleetSummary(drivers, vehicles, trips);
  const insights = getRiskInsights(trips);
  const profiles = getDriverRiskProfiles(drivers, trips);
  const rankedByRisk = [...profiles].sort((a, b) => b.totalEvents - a.totalEvents).slice(0, 5);

  const severityLabels: Record<number, string> = { 1: "Low", 2: "Moderate", 3: "Elevated", 4: "High", 5: "Critical" };
  const severityDistribution = [1, 2, 3, 4, 5].map((sev) => ({
    severity: sev,
    count: trips.filter((t) => t.severity === sev).length,
    label: severityLabels[sev],
  }));

  return (
    <main>
      <section className="operations-hero">
        <div>
          <span className="eyebrow">Risk analytics / shift 02</span>
          <h1>Risk insights.</h1>
          <p>
            Fleet-wide risk distribution, event categories, driver risk profiles, and trend analysis.
          </p>
        </div>
        <div className="hero-stats">
          <article>
            <span>Fleet health</span>
            <strong>{summary.fleetHealth}%</strong>
          </article>
          <article className={summary.criticalAlerts > 0 ? "critical-stat" : ""}>
            <span>Critical alerts</span>
            <strong>{summary.criticalAlerts.toString().padStart(2, "0")}</strong>
          </article>
          <article>
            <span>Avg score</span>
            <strong>{summary.averageScore}</strong>
          </article>
        </div>
      </section>

      <section className="risk-grid">
        <article className="panel risk-distribution-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Severity distribution</span>
              <h2>Trip severity breakdown</h2>
            </div>
          </div>
          <div className="severity-bars">
            {severityDistribution.map((item) => (
              <div className="severity-bar-row" key={item.severity}>
                <span className={`severity-tag severity-${item.severity}`}>{item.label}</span>
                <div className="severity-bar-track">
                  <div className={`severity-bar-fill severity-${item.severity}`} style={{ width: `${(item.count / trips.length) * 100}%` }} />
                </div>
                <strong>{item.count}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="panel risk-categories-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Event categories</span>
              <h2>Risk event types</h2>
            </div>
          </div>
          <div className="risk-category-list">
            {insights.map((insight) => (
              <div className="risk-category-row" key={insight.category}>
                <div className="risk-category-info">
                  <strong>{insight.category}</strong>
                  <span>{insight.count} trips affected</span>
                </div>
                <div className="risk-category-meter">
                  <div className={`risk-meter-fill severity-${insight.severity}`} style={{ width: `${insight.percentage}%` }} />
                </div>
                <b>{insight.percentage}%</b>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="section-heading">
        <div>
          <span className="eyebrow">Driver risk profiles</span>
          <h2>Top 5 drivers by event count</h2>
        </div>
        <p>Drivers with the highest number of risk events across all trips.</p>
      </section>

      <section className="driver-risk-table">
        <div className="panel">
          <div className="risk-table-header">
            <span>Driver</span>
            <span>Score</span>
            <span>TTC</span>
            <span>Brake</span>
            <span>Speed</span>
            <span>Drowsy</span>
            <span>Trend</span>
            <span />
          </div>
          {rankedByRisk.map((profile) => (
            <div className="risk-table-row" key={profile.driverId}>
              <div>
                <strong>{profile.displayName}</strong>
                <small>{profile.driverId}</small>
              </div>
              <span className={`risk-score ${profile.score < 60 ? "critical" : profile.score < 75 ? "warn" : ""}`}>{profile.score}</span>
              <span className={profile.ttcEvents > 0 ? "metric-warn" : ""}>{profile.ttcEvents}</span>
              <span className={profile.harshBrakeEvents > 0 ? "metric-warn" : ""}>{profile.harshBrakeEvents}</span>
              <span>{profile.speedingEvents}</span>
              <span className={profile.drowsinessEvents > 0 ? "metric-warn" : ""}>{profile.drowsinessEvents}</span>
              <span className={`trend-badge ${profile.riskTrend}`}>{profile.riskTrend}</span>
              <Link className="table-link" href={`/drivers#${profile.driverId}`}>View</Link>
            </div>
          ))}
        </div>
      </section>

      <section className="section-heading">
        <div>
          <span className="eyebrow">Fleet overview</span>
          <h2>Summary metrics</h2>
        </div>
      </section>

      <section className="summary-metrics-grid">
        <article className="panel summary-metric-card">
          <span className="eyebrow">Total trips analyzed</span>
          <strong>{summary.totalTrips}</strong>
          <small>Across {summary.totalVehicles} vehicles and {summary.totalDrivers} drivers</small>
        </article>
        <article className="panel summary-metric-card">
          <span className="eyebrow">Active vehicles</span>
          <strong>{summary.activeTrips}</strong>
          <small>Out of {summary.totalVehicles} total fleet assets</small>
        </article>
        <article className="panel summary-metric-card">
          <span className="eyebrow">Fleet average score</span>
          <strong>{summary.averageScore}/100</strong>
          <small>Weighted across all completed trips</small>
        </article>
        <article className="panel summary-metric-card">
          <span className="eyebrow">Critical alerts</span>
          <strong className={summary.criticalAlerts > 3 ? "critical" : ""}>{summary.criticalAlerts}</strong>
          <small>Trips with severity 4 or 5</small>
        </article>
      </section>
    </main>
  );
}