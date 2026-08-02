import { describe, expect, it } from "vitest";

import { buildTripEvidence, buildTripScoreSignals } from "@/lib/trip-evidence";

const trajectory = {
  tripId: "T01-Sample",
  distanceM: 15,
  maxSpeedKmh: 80,
  maxLateralAccelMps2: 4,
  points: [
    {
      frameIndex: 0, timestampS: 0, xM: 0, yM: 0, speedKmh: 50,
      longitudinalAccelMps2: 0, lateralAccelMps2: 0, minTtcS: null, headwayS: null,
      driverState: "attentive", driverAlertness: 0.9, simulatorRiskScore: 10,
      activeEventTypes: [], events: [],
    },
    {
      frameIndex: 12, timestampS: 1.2, xM: 5, yM: 0, speedKmh: 80,
      longitudinalAccelMps2: -5, lateralAccelMps2: 0, minTtcS: 1.2, headwayS: 0.8,
      driverState: "drowsy", driverAlertness: 0.3, simulatorRiskScore: 90,
      activeEventTypes: ["near_miss"], events: ["harsh_brake", "speeding"],
    },
  ],
};

describe("trip evidence", () => {
  it("uses measured frame telemetry instead of fixed demo events", () => {
    const evidence = buildTripEvidence(trajectory);

    expect(evidence[0]).toMatchObject({ label: "TTC entered critical range", time: "00:01.2", severity: 5 });
    expect(evidence.map((item) => item.label)).toContain("Harsh braking detected");
    expect(evidence).toHaveLength(3);
  });

  it("marks unavailable signals as unscored", () => {
    const signals = buildTripScoreSignals({ ...trajectory, points: [] });

    expect(signals.every((signal) => signal.value === null)).toBe(true);
  });
});
