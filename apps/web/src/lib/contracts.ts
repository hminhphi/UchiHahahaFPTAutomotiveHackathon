export type DriverState = "attentive" | "distracted" | "drowsy" | "unknown";
export type ModelStatus = "live" | "precomputed" | "mock" | "degraded" | "reference";

export interface FleetTrip {
  tripId: string;
  driverName: string;
  vehicleId: string;
  score: number | null;
  severity: 1 | 2 | 3 | 4 | 5 | null;
  latestAlert: string;
  speedMps: number;
  ttcS: number | null;
  driverState: DriverState;
  modelStatus: ModelStatus;
}

export interface CameraFrameMetadata {
  schema_version: "1.0";
  frame_index: number;
  occurred_at: string;
  width: number;
  height: number;
  correlation_id: string;
}

export interface DecodedCameraFrame {
  metadata: CameraFrameMetadata;
  jpeg: Uint8Array;
}

export interface TrajectoryPoint {
  frameIndex: number;
  timestampS: number;
  xM: number;
  yM: number;
  speedKmh: number;
  longitudinalAccelMps2: number;
  lateralAccelMps2: number;
  minTtcS: number | null;
  headwayS: number | null;
  driverState: string;
  phoneUse?: boolean | null;
  driverAlertness: number | null;
  simulatorRiskScore: number | null;
  activeEventTypes: string[];
  events: string[];
}

export interface TripTrajectory {
  tripId: string;
  points: TrajectoryPoint[];
  distanceM: number;
  maxSpeedKmh: number;
  maxLateralAccelMps2: number;
}
