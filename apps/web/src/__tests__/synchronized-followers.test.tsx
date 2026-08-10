import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SynchronizedFollowers } from "@/components/synchronized-followers";

describe("synchronized followers", () => {
  it("renders all evidence views without playback controls", () => {
    render(<SynchronizedFollowers tripId="T01-Sample" frameIndex={12} />);

    expect(screen.getByText("Road-right stereo")).toBeVisible();
    expect(screen.getByText("Driver monitoring")).toBeVisible();
    expect(screen.getByText("Depth map")).toBeVisible();
    expect(screen.queryByRole("button", { name: /play/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("slider")).not.toBeInTheDocument();
  });

  it("keeps DMS state visible when the matching driver image is unavailable", () => {
    render(
      <SynchronizedFollowers
        tripId="T01-Sample"
        frameIndex={1220}
        dmsAnalysis={{
          frame_index: 1220,
          producer: "mediapipe_dms",
          driver_state: {
            state: "distracted",
            subtype: null,
            confidence: 0.85,
            face_detected: true,
            ear: null,
            mar: null,
            perclos: null,
            head_pitch_deg: null,
            head_yaw_deg: null,
            face_bounding_box: null,
            face_hull: [],
            left_eye_contour: [],
            right_eye_contour: [],
            mouth_contour: [],
            head_axis: [],
            model_version: "test-model",
          },
        }}
      />,
    );

    fireEvent.error(screen.getByAltText("Driver monitoring at frame 1220"));

    expect(screen.getByText("DMS: distracted")).toBeVisible();
    expect(screen.getByText(/Driver image is unavailable at frame 1220/i)).toBeVisible();
  });
});
