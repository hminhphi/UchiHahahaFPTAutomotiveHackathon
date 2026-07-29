export type DriverState = "attentive" | "distracted" | "drowsy" | "unknown";
export type ModelStatus = "live" | "mock" | "degraded";

export interface FleetTrip {
  tripId: string;
  driverName: string;
  vehicleId: string;
  score: number;
  severity: 1 | 2 | 3 | 4 | 5;
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
