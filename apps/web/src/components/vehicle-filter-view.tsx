"use client";

import Link from "next/link";
import { useState } from "react";
import type { VehicleRecord, FleetTripRecord } from "@/lib/fleet-data";

interface Props {
  vehicles: VehicleRecord[];
  trips: FleetTripRecord[];
  depots: string[];
}

const statusLabels: Record<string, string> = { active: "Active", idle: "Idle", maintenance: "Maintenance", offline: "Offline" };
const classLabels: Record<string, string> = { delivery_van: "Delivery Van", truck: "Truck", sedan: "Sedan" };

export default function VehicleFilterView({ vehicles, trips, depots }: Props) {
  const [activeDepot, setActiveDepot] = useState<string | null>(null);

  const filtered = activeDepot ? vehicles.filter((v) => v.depot === activeDepot) : vehicles;

  return (
    <>
      <section className="section-heading">
        <div>
          <span className="eyebrow">Depots</span>
          <h2>Filter by depot</h2>
        </div>
        <div className="team-chips">
          <span
            className={`team-chip ${!activeDepot ? "active" : ""}`}
            onClick={() => setActiveDepot(null)}
            style={{ cursor: "pointer" }}
          >
            All depots
          </span>
          {depots.map((depot) => (
            <span
              className={`team-chip ${activeDepot === depot ? "active" : ""}`}
              key={depot}
              onClick={() => setActiveDepot(depot)}
              style={{ cursor: "pointer" }}
            >
              {depot}
            </span>
          ))}
        </div>
      </section>

      <section className="vehicle-grid" aria-label="Vehicle fleet">
        {filtered.map((vehicle) => {
          const vehicleTrips = trips.filter((t) => t.vehicleId === vehicle.vehicleId).slice(0, 2);
          return (
            <article className={`vehicle-card status-${vehicle.status}`} key={vehicle.vehicleId}>
              <div className="vehicle-header">
                <div>
                  <span className="eyebrow">{vehicle.vehicleId}</span>
                  <h2>{vehicle.plate}</h2>
                </div>
                <span className={`status-badge ${vehicle.status}`}>{statusLabels[vehicle.status]}</span>
              </div>
              <div className="vehicle-class-badge">{classLabels[vehicle.vehicleClass] ?? vehicle.vehicleClass}</div>
              <dl className="vehicle-specs">
                <div>
                  <dt>Dimensions</dt>
                  <dd>{vehicle.lengthM} x {vehicle.widthM} x {vehicle.heightM} m</dd>
                </div>
                <div>
                  <dt>Payload</dt>
                  <dd>{vehicle.payloadKg} kg</dd>
                </div>
                <div>
                  <dt>Depot</dt>
                  <dd>{vehicle.depot}</dd>
                </div>
                <div>
                  <dt>Trips</dt>
                  <dd>{vehicle.tripCount}</dd>
                </div>
              </dl>
              {vehicle.assignedDriverId && (
                <div className="vehicle-driver">
                  <span className="eyebrow">Assigned driver</span>
                  <strong>{vehicle.assignedDriverId}</strong>
                </div>
              )}
              <div className="vehicle-trips">
                <span className="eyebrow">Recent trips</span>
                {vehicleTrips.length === 0 && <span className="no-trips">No trips recorded</span>}
                {vehicleTrips.map((trip) => (
                  <Link className={`driver-trip-row severity-${trip.severity}`} href={`/trips/${trip.tripId}`} key={trip.tripId}>
                    <span>{trip.tripId}</span>
                    <span>{trip.routeName}</span>
                    <span className={`severity-tag severity-${trip.severity}`}>S{trip.severity}</span>
                    <span>{trip.score ?? "--"}/100</span>
                  </Link>
                ))}
              </div>
            </article>
          );
        })}
      </section>
    </>
  );
}
