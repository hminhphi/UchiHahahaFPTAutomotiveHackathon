import type { TrajectoryPoint, TripTrajectory } from "./contracts";

export interface TripEvidence {
  detail: string;
  frameIndex: number;
  label: string;
  severity: 1 | 2 | 3 | 4 | 5;
  time: string;
  view: "road_left" | "driver";
}

export interface TripScoreSignal {
  label: string;
  note: string;
  value: number | null;
}

/**
 * Converts raw, per-frame organizer telemetry into conservative UI evidence.
 * A missing measurement is intentionally omitted instead of being inferred.
 */
export function buildTripEvidence(trajectory: TripTrajectory | null): TripEvidence[] {
  if (!trajectory) return [];
  const candidates = trajectory.points.flatMap((point) => evidenceForPoint(point));
  return candidates
    .sort((left, right) => right.severity - left.severity || right.frameIndex - left.frameIndex)
    .filter((candidate, index, all) => all.findIndex((item) => item.label === candidate.label) === index)
    .slice(0, 3);
}

export function buildTripScoreSignals(trajectory: TripTrajectory | null): TripScoreSignal[] {
  const points = trajectory?.points ?? [];
  const riskSamples = points.flatMap((point) => point.simulatorRiskScore === null ? [] : [point.simulatorRiskScore]);
  const alertnessSamples = points.flatMap((point) => point.driverAlertness === null ? [] : [point.driverAlertness]);
  const handlingEvents = points.filter((point) => point.events.includes("harsh_brake") || point.events.includes("fast_corner")).length;
  const speedingFrames = points.filter((point) => point.events.includes("speeding")).length;

  return [
    {
      label: "Road risk exposure",
      value: riskSamples.length ? clamp(100 - average(riskSamples)) : null,
      note: "Organizer simulator risk telemetry",
    },
    {
      label: "Driver attention",
      value: alertnessSamples.length ? clamp(average(alertnessSamples) * 100) : null,
      note: "Average in-cabin alertness",
    },
    {
      label: "Vehicle handling",
      value: points.length ? clamp(100 - (handlingEvents / points.length) * 500) : null,
      note: "Harsh-brake and fast-corner frame rate",
    },
    {
      label: "Speed compliance",
      value: points.length ? clamp(100 - (speedingFrames / points.length) * 500) : null,
      note: "Telemetry speeding frame rate",
    },
  ];
}

function evidenceForPoint(point: TrajectoryPoint): TripEvidence[] {
  const time = formatTime(point.timestampS);
  const evidence: TripEvidence[] = [];
  if (point.minTtcS !== null && point.minTtcS < 2.5) {
    evidence.push({
      frameIndex: point.frameIndex,
      time,
      label: point.minTtcS < 1.5 ? "TTC entered critical range" : "Short TTC detected",
      detail: `TTC ${point.minTtcS.toFixed(1)} s from organizer telemetry`,
      severity: point.minTtcS < 1.5 ? 5 : 4,
      view: "road_left",
    });
  }
  if (point.events.includes("harsh_brake")) {
    evidence.push({
      frameIndex: point.frameIndex,
      time,
      label: "Harsh braking detected",
      detail: `Longitudinal acceleration ${point.longitudinalAccelMps2.toFixed(1)} m/s2`,
      severity: 4,
      view: "road_left",
    });
  }
  if (point.events.includes("fast_corner")) {
    evidence.push({
      frameIndex: point.frameIndex,
      time,
      label: "Fast corner detected",
      detail: `Lateral acceleration ${Math.abs(point.lateralAccelMps2).toFixed(1)} m/s2`,
      severity: 3,
      view: "road_left",
    });
  }
  if (point.events.includes("speeding")) {
    evidence.push({
      frameIndex: point.frameIndex,
      time,
      label: "Speeding telemetry flag",
      detail: `Vehicle speed ${point.speedKmh.toFixed(0)} km/h`,
      severity: 3,
      view: "road_left",
    });
  }
  if (point.driverState === "drowsy" || point.driverState === "distracted") {
    evidence.push({
      frameIndex: point.frameIndex,
      time,
      label: `Driver marked ${point.driverState}`,
      detail: point.driverAlertness === null
        ? "Driver-state telemetry"
        : `Alertness ${Math.round(point.driverAlertness * 100)}%`,
      severity: point.driverState === "drowsy" ? 4 : 3,
      view: "driver",
    });
  }
  if (point.phoneUse === true) {
    evidence.push({
      frameIndex: point.frameIndex,
      time,
      label: "Phone use detected",
      detail: "Stable in-cabin phone detection",
      severity: 3,
      view: "driver",
    });
  }
  if (point.simulatorRiskScore !== null && point.simulatorRiskScore >= 80) {
    evidence.push({
      frameIndex: point.frameIndex,
      time,
      label: "High simulator risk score",
      detail: `Reference risk score ${Math.round(point.simulatorRiskScore)}/100`,
      severity: 4,
      view: "road_left",
    });
  }
  return evidence;
}

function average(values: number[]): number {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function clamp(value: number): number {
  return Math.round(Math.max(0, Math.min(100, value)));
}

function formatTime(timestampS: number): string {
  const minutes = Math.floor(timestampS / 60).toString().padStart(2, "0");
  const seconds = (timestampS % 60).toFixed(1).padStart(4, "0");
  return `${minutes}:${seconds}`;
}
