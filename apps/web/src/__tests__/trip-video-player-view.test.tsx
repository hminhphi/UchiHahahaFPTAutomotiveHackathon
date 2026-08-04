import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TripVideoPlayer } from "@/components/trip-video-player";

describe("trip video evidence source", () => {
  it("switches to the driver frame for phone evidence", () => {
    render(
      <TripVideoPlayer
        tripId="T01-Sample"
        frameIndexes={[10]}
        selectedFrameIndex={10}
        evidence={[{
          detail: "Stable in-cabin phone detection",
          frameIndex: 10,
          label: "Phone use detected",
          severity: 3,
          time: "00:00.5",
          view: "driver",
        }]}
        onFrameIndexChange={() => undefined}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Phone use detected/ }));
    expect(screen.getByRole("img")).toHaveAttribute(
      "src",
      "/api/trips/T01-Sample/frames/driver/10",
    );
  });
});
