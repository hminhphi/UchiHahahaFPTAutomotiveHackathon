export interface VideoFrameMapEntry {
  frameIndex: number;
  timeS: number;
}

export interface RoadVideoDescriptor {
  tripId: string;
  assetUrl: string;
  fps: number;
  durationS: number;
  frameMap: VideoFrameMapEntry[];
}

export interface EventMarker {
  eventId: string;
  tripId: string;
  frameIndex: number;
  severity: 1 | 2 | 3 | 4 | 5;
  eventType: string;
  title: string;
  confidence: number;
}

export interface FrameDetection {
  track_id: string;
  label: string;
  bounding_box: { x_min: number; y_min: number; x_max: number; y_max: number };
  confidence: number;
  distance_m: number | null;
  relative_speed_mps: number | null;
  relative_accel_mps2: number | null;
  ttc_s: number | null;
  distance_confidence: number | null;
  distance_source: string;
  lane_relation: "in_lane" | "adjacent" | "unknown";
  risk_level: "none" | "monitor" | "high" | "critical";
}

export interface RoadFrameAnalysis {
  frame_index: number;
  producer: string;
  detections: FrameDetection[];
  lane_state: { detected: boolean; lane_offset_m: number | null; confidence: number } | null;
  depth_state: { source: string; valid_coverage: number; confidence: number } | null;
}

export interface NormalizedPoint { x: number; y: number }

export interface DmsFrameAnalysis {
  frame_index: number;
  producer: string;
  driver_state: {
    state: "attentive" | "distracted" | "drowsy" | "unknown";
    subtype: string | null;
    confidence: number;
    face_detected: boolean | null;
    ear: number | null;
    mar: number | null;
    perclos: number | null;
    head_pitch_deg: number | null;
    head_yaw_deg: number | null;
    face_bounding_box: { x_min: number; y_min: number; x_max: number; y_max: number } | null;
    face_hull: NormalizedPoint[];
    left_eye_contour: NormalizedPoint[];
    right_eye_contour: NormalizedPoint[];
    mouth_contour: NormalizedPoint[];
    head_axis: NormalizedPoint[];
    model_version: string | null;
  } | null;
}

export interface FusionFrameAnalysis {
  frame_index: number;
  producer: string;
  risk_index: number;
  safety_score: number;
  severity: number;
  components: Record<string, number | null>;
  provenance: Record<string, string | boolean>;
}

export interface FusionTripSummary {
  tripId: string;
  producer: "fusion-worker";
  safetyScore: number | null;
  componentSafetyScores: {
    road: number | null;
    dms: number | null;
    telemetry: number | null;
    lane: number | null;
  };
}

export async function fetchFrameAnalysis<T>(tripId: string, kind: "road" | "dms" | "fusion", frameIndex: number, signal?: AbortSignal): Promise<T | null> {
  const response = await fetch(`/api/trips/${encodeURIComponent(tripId)}/analysis/${kind}/${frameIndex}`, { signal });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Frame analysis request failed: ${response.status}`);
  return response.json() as Promise<T>;
}

export interface TripOperationsDetail {
  trip: {
    tripId: string;
    vehicleId: string;
    driverId: string;
    source: "historical" | "live";
    status: string;
    orderCount: number;
    cargoClass: string;
    vehicleClass: string;
    routeName: string | null;
  };
  vehicle: {
    vehicleId: string;
    vehicleClass: string;
    licensePlate: string;
    lengthM: number;
    widthM: number;
    heightM: number;
    payloadCapacityKg: number;
    depotName: string | null;
  } | null;
  driver: {
    driverId: string;
    displayName: string;
    employeeCode: string | null;
    licenseClass: string | null;
    homeDepot: string | null;
  } | null;
  orders: Array<{ orderId: string; status: string; packageCount: number; destination: string | null }>;
}

export function frameAtTime(frameMap: readonly VideoFrameMapEntry[], timeS: number): number | null {
  if (!frameMap.length) return null;
  return frameMap.reduce((closest, candidate) =>
    Math.abs(candidate.timeS - timeS) < Math.abs(closest.timeS - timeS) ? candidate : closest,
  ).frameIndex;
}

export function timeAtFrame(frameMap: readonly VideoFrameMapEntry[], frameIndex: number): number | null {
  if (!frameMap.length) return null;
  return frameMap.reduce((closest, candidate) =>
    Math.abs(candidate.frameIndex - frameIndex) < Math.abs(closest.frameIndex - frameIndex) ? candidate : closest,
  ).timeS;
}
