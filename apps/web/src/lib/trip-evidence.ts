import type { TrajectoryPoint, TripTrajectory } from "./contracts";
import type { FusionTripSummary } from "./operations";

export interface TripEvidence {
  detail: string;
  frameIndex: number;
  label: string;
  severity: 1 | 2 | 3 | 4 | 5;
  time: string;
  view?: "driver" | "road";
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

export function buildTripScoreSignals(summary: FusionTripSummary | TripTrajectory | null): TripScoreSignal[] {
  const scores = summary && "componentSafetyScores" in summary
    ? summary.componentSafetyScores
    : undefined;
  return [
    {
      label: "Collision margin",
      value: roundScore(scores?.road),
      note: "FleetIQ roadface-worker / stereo TTC",
    },
    {
      label: "Driver attention",
      value: roundScore(scores?.dms),
      note: scores?.dms == null
        ? "DMS unavailable until a verified checkpoint is supplied"
        : "FleetIQ dms-worker / verified sequence checkpoint",
    },
    {
      label: "Vehicle handling",
      value: roundScore(scores?.telemetry),
      note: "FleetIQ fusion of speed and longitudinal/lateral acceleration",
    },
    {
      label: "Lane discipline",
      value: roundScore(scores?.lane),
      note: "FleetIQ lane association and offset",
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
    });
  }
  if (point.events.includes("harsh_brake")) {
    evidence.push({
      frameIndex: point.frameIndex,
      time,
      label: "Harsh braking detected",
      detail: `Longitudinal acceleration ${point.longitudinalAccelMps2.toFixed(1)} m/s2`,
      severity: 4,
    });
  }
  if (point.events.includes("fast_corner")) {
    evidence.push({
      frameIndex: point.frameIndex,
      time,
      label: "Fast corner detected",
      detail: `Lateral acceleration ${Math.abs(point.lateralAccelMps2).toFixed(1)} m/s2`,
      severity: 3,
    });
  }
  if (point.events.includes("speeding")) {
    evidence.push({
      frameIndex: point.frameIndex,
      time,
      label: "Speeding telemetry flag",
      detail: `Vehicle speed ${point.speedKmh.toFixed(0)} km/h`,
      severity: 3,
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
    });
  }
  if (point.phoneUse === true) {
    evidence.push({
      frameIndex: point.frameIndex,
      time,
      label: "Phone use detected",
      detail: "Driver camera phone-use signal",
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
    });
  }
  return evidence;
}

function roundScore(value: number | null | undefined): number | null {
  return value == null ? null : Math.round(Math.max(0, Math.min(100, value)));
}

function formatTime(timestampS: number): string {
  const minutes = Math.floor(timestampS / 60).toString().padStart(2, "0");
  const seconds = (timestampS % 60).toFixed(1).padStart(4, "0");
  return `${minutes}:${seconds}`;
}
