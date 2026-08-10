import { render, screen } from "@testing-library/react";
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
});