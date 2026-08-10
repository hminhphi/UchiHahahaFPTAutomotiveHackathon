import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TripOperationsView } from "@/components/trip-operations-view";

vi.mock("next-video", () => ({ default: () => <video controls aria-label="Road video" /> }));

describe("trip operations event ownership", () => {
  it("renders events in frame review and marks them on the trip trajectory", () => {
    render(
      <TripOperationsView
        trip={{ tripId: "T01-Sample", driverName: "Driver A", vehicleId: "VH-01", score: 80, severity: 4, latestAlert: "Review", speedMps: 0, ttcS: null, driverState: "attentive", modelStatus: "reference" }}
        operations={null}
        trajectory={{
          tripId: "T01-Sample",
          points: [
            { frameIndex: 0, timestampS: 0, xM: 0, yM: 0, speedKmh: 0, longitudinalAccelMps2: 0, lateralAccelMps2: 0, minTtcS: null, headwayS: null, driverState: "attentive", driverAlertness: 1, simulatorRiskScore: 0, activeEventTypes: [], events: [] },
            { frameIndex: 8, timestampS: 0.4, xM: 3, yM: 2, speedKmh: 36, longitudinalAccelMps2: -1, lateralAccelMps2: 0.2, minTtcS: 1.2, headwayS: null, driverState: "attentive", driverAlertness: 1, simulatorRiskScore: 4, activeEventTypes: ["short_ttc"], events: ["short_ttc"] },
          ],
          distanceM: 3.6,
          maxSpeedKmh: 36,
          maxLateralAccelMps2: 0.2,
        }}
        roadVideo={{ tripId: "T01-Sample", assetUrl: "/api/video", fps: 20, durationS: 0.45, frameMap: [{ frameIndex: 0, timeS: 0 }, { frameIndex: 8, timeS: 0.4 }] }}
        events={[{ detail: "TTC 1.2 s", frameIndex: 8, label: "Short TTC detected", severity: 4, time: "00:00.0" }]}
        scoreSignals={[]}
      />,
    );

    expect(screen.getAllByText("Short TTC detected")).toHaveLength(1);
    expect(screen.getByLabelText("Frame-linked review")).toBeInTheDocument();
    expect(screen.queryByLabelText("Road-left event track")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Risk event: Short TTC detected at frame 8")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Short TTC detected/i }));
    expect(within(screen.getByLabelText("Frame synchronized follower cameras")).getAllByText("Frame 8")).toHaveLength(3);
    expect(within(screen.getByLabelText("Frame synchronised telemetry")).getByText("Frame 8")).toBeInTheDocument();
  });
});