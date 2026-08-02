import { describe, expect, it } from "vitest";

import { framePosition, nearestFrameIndex, nextFrameIndex } from "@/components/trip-video-player";

describe("historical video player frame selection", () => {
  const frames = [0, 2, 5, 9];

  it("maps a requested evidence frame to the first stored frame at or after it", () => {
    expect(framePosition(frames, 5)).toBe(2);
    expect(nearestFrameIndex(frames, 3)).toBe(5);
    expect(nearestFrameIndex(frames, 99)).toBe(9);
  });

  it("advances without wrapping past the end of a completed trip", () => {
    expect(nextFrameIndex(frames, 2)).toBe(5);
    expect(nextFrameIndex(frames, 9)).toBeNull();
    expect(nearestFrameIndex([], 5)).toBeNull();
  });
});
