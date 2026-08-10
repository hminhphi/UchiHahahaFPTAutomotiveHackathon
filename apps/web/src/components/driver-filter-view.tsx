"use client";

import Link from "next/link";
import { useState } from "react";
import type { DriverRecord, DriverRiskProfile, FleetTripRecord } from "@/lib/fleet-data";

interface Props {
  drivers: DriverRecord[];
  ranked: DriverRiskProfile[];
  trips: FleetTripRecord[];
  teams: string[];
}

const statusLabels: Record<string, string> = { on_duty: "On duty", off_duty: "Off duty", on_break: "On break" };
const trendIcons: Record<string, string> = { improving: "\u2191", stable: "\u2192", declining: "\u2193" };
const trendColors: Record<string, string> = { improving: "var(--green)", stable: "var(--gold)", declining: "var(--orange)" };

export default function DriverFilterView({ drivers, ranked, trips, teams }: Props) {
  const [activeTeam, setActiveTeam] = useState<string | null>(null);

  const filtered = activeTeam
    ? ranked.filter((p) => drivers.find((d) => d.driverId === p.driverId)?.team === activeTeam)
    : ranked;

  return (
    <>
      <section className="section-heading">
        <div>
          <span className="eyebrow">Teams</span>
          <h2>Filter by team</h2>
        </div>
        <div className="team-chips">
          <span
            className={`team-chip ${!activeTeam ? "active" : ""}`}
            onClick={() => setActiveTeam(null)}
            style={{ cursor: "pointer" }}
          >
            All teams
          </span>
          {teams.map((team) => (
            <span
              className={`team-chip ${activeTeam === team ? "active" : ""}`}
              key={team}
              onClick={() => setActiveTeam(team)}
              style={{ cursor: "pointer" }}
            >
              {team}
            </span>
          ))}
        </div>
      </section>

      <section className="driver-grid" aria-label="Driver ranking">
        {filtered.map((profile, index) => {
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
                  <div
                    className={`score-dial ${driver.aggregateScore < 60 ? "score-critical" : driver.aggregateScore < 75 ? "score-warn" : ""}`}
                    aria-label={`Safety score ${driver.aggregateScore}`}
                  >
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
                    <dd style={{ color: trendColors[profile.riskTrend] }}>
                      {trendIcons[profile.riskTrend]} {profile.riskTrend}
                    </dd>
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
    </>
  );
}
