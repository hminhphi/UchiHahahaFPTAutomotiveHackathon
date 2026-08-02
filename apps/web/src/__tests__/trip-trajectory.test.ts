import { describe, expect, it } from "vitest";

import { findTrajectoryPoint } from "@/components/trip-trajectory";
import type { TrajectoryPoint } from "@/lib/contracts";

const points: TrajectoryPoint[] = [
  {
    frameIndex: 0,
    timestampS: 0,
    xM: 0,
    yM: 0,
    speedKmh: 0,
    longitudinalAccelMps2: 0,
    lateralAccelMps2: 0,
    minTtcS: null,
    headwayS: null,
    driverState: "alert",
    driverAlertness: 1,
    simulatorRiskScore: 0,
    activeEventTypes: [],
    events: [],
  },
  {
    frameIndex: 10,
    timestampS: 0.5,
    xM: 2,
    yM: 1,
    speedKmh: 20,
    longitudinalAccelMps2: 1,
    lateralAccelMps2: 0.2,
    minTtcS: 3,
    headwayS: 4,
    driverState: "distracted",
    driverAlertness: 0.45,
    simulatorRiskScore: 12,
    activeEventTypes: ["near_miss"],
    events: [],
  },
];

describe("trajectory playback alignment", () => {
  it("uses the latest telemetry point at or before the incoming camera frame", () => {
    expect(findTrajectoryPoint(points, 7).frameIndex).toBe(0);
    expect(findTrajectoryPoint(points, 10).frameIndex).toBe(10);
    expect(findTrajectoryPoint(points, 99).frameIndex).toBe(10);
  });
});
