import type { FleetTrip } from "./contracts";

const API_BASE_URL = process.env.FLEETIQ_API_BASE_URL ?? "http://localhost:8000";

interface ApiTrip {
  trip_id: string;
  status: "available" | "processing" | "complete" | "failed";
}

interface TripEnvelope {
  data: {
    items: ApiTrip[];
  };
}

export const demoTrips: FleetTrip[] = [
  {
    tripId: "T06-Sample",
    driverName: "Driver F",
    vehicleId: "VH-06",
    score: 52,
    severity: 5,
    latestAlert: "Short TTC + distraction",
    speedMps: 18.2,
    ttcS: 1.2,
    driverState: "distracted",
    modelStatus: "degraded",
  },
  {
    tripId: "T03-Sample",
    driverName: "Driver C",
    vehicleId: "VH-03",
    score: 71,
    severity: 3,
    latestAlert: "Fast turn / lateral accel",
    speedMps: 15.6,
    ttcS: 3.1,
    driverState: "attentive",
    modelStatus: "mock",
  },
  {
    tripId: "T01-Sample",
    driverName: "Driver A",
    vehicleId: "VH-01",
    score: 94,
    severity: 1,
    latestAlert: "No active alert",
    speedMps: 10.1,
    ttcS: 6.2,
    driverState: "attentive",
    modelStatus: "mock",
  },
];

export async function getFleetTrips(): Promise<FleetTrip[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/trips`, { cache: "no-store" });
    if (!response.ok) throw new Error("Fleet API unavailable");
    const envelope = (await response.json()) as TripEnvelope;
    if (!envelope.data.items.length) return demoTrips;
    return envelope.data.items.map((trip, index) => ({
      tripId: trip.trip_id,
      driverName: `Driver ${String.fromCharCode(65 + index)}`,
      vehicleId: `VH-${String(index + 1).padStart(2, "0")}`,
      score: trip.status === "failed" ? 55 : 85,
      severity: trip.status === "failed" ? 4 : 2,
      latestAlert: trip.status === "failed" ? "Analysis failed" : "Awaiting fused events",
      speedMps: 0,
      ttcS: null,
      driverState: "unknown",
      modelStatus: "degraded",
    }));
  } catch {
    return demoTrips;
  }
}

export function getTrip(tripId: string, trips: FleetTrip[]): FleetTrip {
  return trips.find((trip) => trip.tripId === tripId) ?? {
    ...demoTrips[2],
    tripId,
    latestAlert: "Trip data unavailable",
    modelStatus: "degraded",
  };
}
