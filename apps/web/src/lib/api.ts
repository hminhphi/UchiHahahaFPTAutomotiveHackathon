import type { FleetTrip, TripTrajectory } from "./contracts";

const API_BASE_URL = process.env.FLEETIQ_API_BASE_URL ?? "http://localhost:8000";

interface ApiTrip {
  trip_id: string;
  status: "available" | "processing" | "complete" | "failed";
  safety_score: number | null;
  severity: 1 | 2 | 3 | 4 | 5 | null;
  latest_alert: string | null;
  driver_state: string | null;
  max_speed_kmh: number | null;
}

interface TripEnvelope {
  data: {
    items: ApiTrip[];
  };
}

interface ApiTrajectoryPoint {
  frame_index: number;
  timestamp_s: number;
  x_m: number;
  y_m: number;
  speed_kmh: number;
  longitudinal_accel_mps2: number;
  lateral_accel_mps2: number;
  min_ttc_s: number | null;
  headway_s: number | null;
  driver_state: string;
  phone_use: boolean | null;
  driver_alertness: number | null;
  simulator_risk_score: number | null;
  active_event_types: string[];
  events: string[];
}

interface TrajectoryEnvelope {
  data: {
    trip_id: string;
    points: ApiTrajectoryPoint[];
    distance_m: number;
    max_speed_kmh: number;
    max_lateral_accel_mps2: number;
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
      score: trip.safety_score ?? (trip.status === "failed" ? 55 : 85),
      severity: trip.severity ?? (trip.status === "failed" ? 4 : 2),
      latestAlert: trip.latest_alert ?? (trip.status === "failed" ? "Analysis failed" : "Awaiting fused events"),
      speedMps: (trip.max_speed_kmh ?? 0) / 3.6,
      ttcS: null,
      driverState: normalizeDriverState(trip.driver_state),
      modelStatus: trip.status === "failed" ? "degraded" : "reference",
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

function normalizeDriverState(value: string | null): FleetTrip["driverState"] {
  return value === "attentive" || value === "distracted" || value === "drowsy" ? value : "unknown";
}

export async function getTripTrajectory(tripId: string): Promise<TripTrajectory | null> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/trips/${encodeURIComponent(tripId)}/trajectory`,
      { cache: "no-store" },
    );
    if (!response.ok) throw new Error("Trip trajectory unavailable");
    const envelope = (await response.json()) as TrajectoryEnvelope;
    const { data } = envelope;
    return {
      tripId: data.trip_id,
      points: data.points.map((point) => ({
        frameIndex: point.frame_index,
        timestampS: point.timestamp_s,
        xM: point.x_m,
        yM: point.y_m,
        speedKmh: point.speed_kmh,
        longitudinalAccelMps2: point.longitudinal_accel_mps2,
        lateralAccelMps2: point.lateral_accel_mps2,
        minTtcS: point.min_ttc_s,
        headwayS: point.headway_s,
        driverState: point.driver_state,
        phoneUse: point.phone_use,
        driverAlertness: point.driver_alertness,
        simulatorRiskScore: point.simulator_risk_score,
        activeEventTypes: point.active_event_types,
        events: point.events,
      })),
      distanceM: data.distance_m,
      maxSpeedKmh: data.max_speed_kmh,
      maxLateralAccelMps2: data.max_lateral_accel_mps2,
    };
  } catch {
    return null;
  }
}
