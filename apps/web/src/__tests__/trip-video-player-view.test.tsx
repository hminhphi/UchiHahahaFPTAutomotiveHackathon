import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TripVideoPlayer } from "@/components/trip-video-player";

describe("trip video evidence source", () => {
  it("shows synchronized road and driver frames with DMS signals", () => {
    render(
      <TripVideoPlayer
        tripId="T01-Sample"
        frameIndexes={[10]}
        selectedFrameIndex={10}
        driverState="distracted"
        phoneUse
        evidence={[]}
        onFrameIndexChange={() => undefined}
      />,
    );

    expect(screen.getByRole("img", { name: /road-facing camera frame 10/i }))
      .toHaveAttribute("src", "/api/trips/T01-Sample/frames/road_left/10");
    expect(screen.getByRole("img", { name: /driver camera frame 10/i }))
      .toHaveAttribute("src", "/api/trips/T01-Sample/frames/driver/10");
    expect(screen.getByText("Driver state")).toBeInTheDocument();
    expect(screen.getByText("distracted")).toBeInTheDocument();
    expect(screen.getByText("Phone use")).toBeInTheDocument();
    expect(screen.getByText("Detected")).toBeInTheDocument();
  });
});
