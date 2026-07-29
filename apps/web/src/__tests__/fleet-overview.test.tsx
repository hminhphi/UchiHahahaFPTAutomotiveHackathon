import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FleetOverview } from "@/components/fleet-overview";
import type { FleetTrip } from "@/lib/contracts";

const safeTrip: FleetTrip = {
  tripId: "T01-Sample",
  driverName: "Driver A",
  vehicleId: "VH-01",
  score: 94,
  severity: 1,
  latestAlert: "No active alert",
  speedMps: 10,
  ttcS: 6.2,
  driverState: "attentive",
  modelStatus: "live",
};

const riskyTrip: FleetTrip = {
  ...safeTrip,
  tripId: "T06-Sample",
  driverName: "Driver F",
  vehicleId: "VH-06",
  score: 52,
  severity: 5,
  latestAlert: "Short TTC + distraction",
  ttcS: 1.2,
  driverState: "distracted",
  modelStatus: "degraded",
};

describe("FleetOverview", () => {
  it("shows the highest-risk trip first", () => {
    render(<FleetOverview trips={[safeTrip, riskyTrip]} />);

    expect(screen.getAllByTestId("trip-card")[0]).toHaveTextContent("T06-Sample");
  });

  it("shows degraded model state visibly", () => {
    render(<FleetOverview trips={[riskyTrip]} />);

    expect(screen.getByText("Model degraded")).toBeVisible();
  });
});
