import Link from "next/link";

import { getFleetTripsData, getVehicles } from "@/lib/fleet-data";

export const dynamic = "force-dynamic";

export default async function VehiclesPage() {
  const [vehicles, trips] = await Promise.all([getVehicles(), getFleetTripsData()]);
  const depots = [...new Set(vehicles.map((v) => v.depot))].sort();

  const statusLabels: Record<string, string> = { active: "Active", idle: "Idle", maintenance: "Maintenance", offline: "Offline" };
  const classLabels: Record<string, string> = { delivery_van: "Delivery Van", truck: "Truck", sedan: "Sedan" };

  const activeCount = vehicles.filter((v) => v.status === "active").length;
  const idleCount = vehicles.filter((v) => v.status === "idle").length;
  const maintenanceCount = vehicles.filter((v) => v.status === "maintenance").length;
  const offlineCount = vehicles.filter((v) => v.status === "offline").length;

  return (
    <main>
      <section className="operations-hero">
        <div>
          <span className="eyebrow">Vehicle fleet / HCM depots</span>
          <h1>Vehicle operations.</h1>
          <p>
            Fleet status, vehicle specifications, depot assignments, and trip history for every asset.
          </p>
        </div>
        <div className="hero-stats">
          <article>
            <span>Total fleet</span>
            <strong>{vehicles.length.toString().padStart(2, "0")}</strong>
          </article>
          <article className={activeCount > 0 ? "" : "critical-stat"}>
            <span>Active</span>
            <strong>{activeCount.toString().padStart(2, "0")}</strong>
          </article>
          <article>
            <span>Available</span>
            <strong>{idleCount.toString().padStart(2, "0")}</strong>
          </article>
        </div>
      </section>

      <section className="section-heading">
        <div>
          <span className="eyebrow">Status breakdown</span>
          <h2>Fleet availability</h2>
        </div>
        <div className="status-bar-container">
          <div className="status-bar">
            <div className="status-segment active" style={{ width: `${(activeCount / vehicles.length) * 100}%` }} />
            <div className="status-segment idle" style={{ width: `${(idleCount / vehicles.length) * 100}%` }} />
            <div className="status-segment maintenance" style={{ width: `${(maintenanceCount / vehicles.length) * 100}%` }} />
            <div className="status-segment offline" style={{ width: `${(offlineCount / vehicles.length) * 100}%` }} />
          </div>
          <div className="status-bar-legend">
            <span><i className="dot active" /> Active {activeCount}</span>
            <span><i className="dot idle" /> Idle {idleCount}</span>
            <span><i className="dot maintenance" /> Maint. {maintenanceCount}</span>
            <span><i className="dot offline" /> Offline {offlineCount}</span>
          </div>
        </div>
      </section>

      <section className="section-heading">
        <div>
          <span className="eyebrow">Depots</span>
          <h2>Filter by depot</h2>
        </div>
        <div className="team-chips">
          <span className="team-chip active">All depots</span>
          {depots.map((depot) => (
            <span className="team-chip" key={depot}>{depot}</span>
          ))}
        </div>
      </section>

      <section className="vehicle-grid" aria-label="Vehicle fleet">
        {vehicles.map((vehicle) => {
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
    </main>
  );
}