import type { FleetTrip, TripTrajectory } from "./contracts";
import type { EventMarker, FusionTripSummary, RoadVideoDescriptor, TripOperationsDetail } from "./operations";

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

interface RoadVideoEnvelope {
  data: {
    trip_id: string;
    asset_url: string;
    fps: number;
    duration_s: number;
    frame_map: Array<{ frame_index: number; time_s: number }>;
  };
}

interface OperationsEnvelope {
  data: {
    trip: Record<string, unknown>;
    vehicle: Record<string, unknown> | null;
    driver: Record<string, unknown> | null;
    orders: Array<Record<string, unknown>>;
  };
}

interface EventsEnvelope {
  data: Array<{
    event_id: string;
    trip_id: string;
    frame_index: number;
    severity: 1 | 2 | 3 | 4 | 5;
    event_type: string;
    title: string;
    confidence: number;
  }>;
}

interface FusionSummaryResponse {
  trip_id: string;
  producer: "fusion-worker";
  safety_score: number;
  component_safety_scores: {
    road: number | null;
    dms: number | null;
    telemetry: number | null;
    lane: number | null;
  };
}

export const demoTrips: FleetTrip[] = [
  {
    tripId: "T01d",
    driverName: "Driver A",
    vehicleId: "VH-01",
    score: 57,
    severity: 4,
    latestAlert: "106 harsh-brake event(s)",
    speedMps: 24.4,
    ttcS: null,
    driverState: "drowsy",
    modelStatus: "reference",
  },
  {
    tripId: "T02d",
    driverName: "Driver B",
    vehicleId: "VH-02",
    score: 60,
    severity: 4,
    latestAlert: "117 harsh-brake event(s)",
    speedMps: 18.4,
    ttcS: null,
    driverState: "drowsy",
    modelStatus: "reference",
  },
  {
    tripId: "T03d",
    driverName: "Driver C",
    vehicleId: "VH-03",
    score: 61,
    severity: 3,
    latestAlert: "42 harsh-brake event(s)",
    speedMps: 8.4,
    ttcS: null,
    driverState: "attentive",
    modelStatus: "reference",
  },
  {
    tripId: "T04d",
    driverName: "Driver D",
    vehicleId: "VH-04",
    score: 59,
    severity: 4,
    latestAlert: "106 harsh-brake event(s)",
    speedMps: 24.4,
    ttcS: null,
    driverState: "attentive",
    modelStatus: "reference",
  },
  {
    tripId: "T05d",
    driverName: "Driver E",
    vehicleId: "VH-05",
    score: 69,
    severity: 3,
    latestAlert: "117 harsh-brake event(s)",
    speedMps: 21.8,
    ttcS: null,
    driverState: "attentive",
    modelStatus: "reference",
  },
  {
    tripId: "T06d",
    driverName: "Driver F",
    vehicleId: "VH-06",
    score: 60,
    severity: 4,
    latestAlert: "50 harsh-brake event(s)",
    speedMps: 8.4,
    ttcS: null,
    driverState: "attentive",
    modelStatus: "reference",
  },
  {
    tripId: "T07d",
    driverName: "Driver G",
    vehicleId: "VH-07",
    score: 58,
    severity: 4,
    latestAlert: "54 harsh-brake event(s)",
    speedMps: 24.4,
    ttcS: null,
    driverState: "distracted",
    modelStatus: "reference",
  },
  {
    tripId: "T08d",
    driverName: "Driver H",
    vehicleId: "VH-08",
    score: 60,
    severity: 4,
    latestAlert: "49 harsh-brake event(s)",
    speedMps: 8.4,
    ttcS: null,
    driverState: "attentive",
    modelStatus: "reference",
  },
  {
    tripId: "T09d",
    driverName: "Driver I",
    vehicleId: "VH-09",
    score: 60,
    severity: 4,
    latestAlert: "53 harsh-brake event(s)",
    speedMps: 10.0,
    ttcS: null,
    driverState: "attentive",
    modelStatus: "reference",
  },
  {
    tripId: "T10d",
    driverName: "Driver J",
    vehicleId: "VH-10",
    score: 58,
    severity: 4,
    latestAlert: "138 harsh-brake event(s)",
    speedMps: 23.5,
    ttcS: null,
    driverState: "attentive",
    modelStatus: "reference",
  },
];

export async function getFleetTrips(): Promise<FleetTrip[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/trips`, { cache: "no-store" });
    if (!response.ok) throw new Error("Fleet API unavailable");
    const envelope = (await response.json()) as TripEnvelope;
    if (!envelope.data.items.length) return [];
    return envelope.data.items.map((trip, index) => ({
      tripId: trip.trip_id,
      driverName: `Driver ${String.fromCharCode(65 + index)}`,
      vehicleId: `VH-${String(index + 1).padStart(2, "0")}`,
      // Artifact scores are not fleet-validated yet, so they must not be ranked or averaged.
      score: null,
      severity: null,
      latestAlert: trip.latest_alert ?? "Awaiting validated analysis",
      speedMps: (trip.max_speed_kmh ?? 0) / 3.6,
      ttcS: null,
      driverState: normalizeDriverState(trip.driver_state),
      modelStatus: trip.status === "failed" ? "degraded" : trip.status === "complete" ? "precomputed" : "reference",
    }));
  } catch {
    return [];
  }
}

export function getTrip(tripId: string, trips: FleetTrip[]): FleetTrip {
  return trips.find((trip) => trip.tripId === tripId) ?? {
    tripId,
    driverName: "Unavailable",
    vehicleId: "Unavailable",
    score: null,
    severity: null,
    latestAlert: "Trip data unavailable",
    speedMps: 0,
    ttcS: null,
    driverState: "unknown",
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

export async function getRoadVideoDescriptor(tripId: string): Promise<RoadVideoDescriptor | null> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/trips/${encodeURIComponent(tripId)}/road-video`,
      { cache: "no-store" },
    );
    if (!response.ok) throw new Error("Road video unavailable");
    const { data } = (await response.json()) as RoadVideoEnvelope;
    return {
      tripId: data.trip_id,
      assetUrl: data.asset_url,
      fps: data.fps,
      durationS: data.duration_s,
      frameMap: data.frame_map.map((entry) => ({ frameIndex: entry.frame_index, timeS: entry.time_s })),
    };
  } catch {
    return null;
  }
}

export async function getTripOperations(tripId: string): Promise<TripOperationsDetail | null> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/trips/${encodeURIComponent(tripId)}/logistics`,
      { cache: "no-store" },
    );
    if (!response.ok) throw new Error("Trip logistics unavailable");
    const { data } = (await response.json()) as OperationsEnvelope;
    const trip = data.trip;
    const vehicle = data.vehicle;
    const driver = data.driver;
    return {
      trip: {
        tripId: String(trip.trip_id),
        vehicleId: String(trip.vehicle_id),
        driverId: String(trip.driver_id),
        source: trip.source === "live" ? "live" : "historical",
        status: String(trip.status),
        orderCount: Number(trip.order_count),
        cargoClass: String(trip.cargo_class),
        vehicleClass: String(trip.vehicle_class),
        routeName: trip.route_name ? String(trip.route_name) : null,
      },
      vehicle: vehicle ? {
        vehicleId: String(vehicle.vehicle_id),
        vehicleClass: String(vehicle.vehicle_class),
        licensePlate: String(vehicle.license_plate),
        lengthM: Number(vehicle.length_m),
        widthM: Number(vehicle.width_m),
        heightM: Number(vehicle.height_m),
        payloadCapacityKg: Number(vehicle.payload_capacity_kg),
        depotName: vehicle.depot_name ? String(vehicle.depot_name) : null,
      } : null,
      driver: driver ? {
        driverId: String(driver.driver_id),
        displayName: String(driver.display_name),
        employeeCode: driver.employee_code ? String(driver.employee_code) : null,
        licenseClass: driver.license_class ? String(driver.license_class) : null,
        homeDepot: driver.home_depot ? String(driver.home_depot) : null,
      } : null,
      orders: data.orders.map((order) => ({
        orderId: String(order.order_id),
        status: String(order.status),
        packageCount: Number(order.package_count),
        destination: order.destination ? String(order.destination) : null,
      })),
    };
  } catch {
    return null;
  }
}

export async function getTripEventMarkers(tripId: string): Promise<EventMarker[]> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/trips/${encodeURIComponent(tripId)}/events`,
      { cache: "no-store" },
    );
    if (!response.ok) throw new Error("Trip events unavailable");
    const { data } = (await response.json()) as EventsEnvelope;
    return data.map((event) => ({
      eventId: event.event_id,
      tripId: event.trip_id,
      frameIndex: event.frame_index,
      severity: event.severity,
      eventType: event.event_type,
      title: event.title,
      confidence: event.confidence,
    }));
  } catch {
    return [];
  }
}

export async function getTripFusionSummary(tripId: string): Promise<FusionTripSummary | null> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/trips/${encodeURIComponent(tripId)}/analysis/fusion/summary`,
      { cache: "no-store" },
    );
    if (!response.ok) throw new Error("Fusion summary unavailable");
    const summary = (await response.json()) as FusionSummaryResponse;
    return {
      tripId: summary.trip_id,
      producer: summary.producer,
      safetyScore: summary.safety_score,
      componentSafetyScores: summary.component_safety_scores,
    };
  } catch {
    return null;
  }
}
