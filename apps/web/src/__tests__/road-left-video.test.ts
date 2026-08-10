import { render } from "@testing-library/react";
import { createElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { RoadLeftVideo } from "@/components/road-left-video";
import { frameAtTime, timeAtFrame } from "@/lib/operations";

const videoMock = vi.hoisted(() => ({ props: null as Record<string, unknown> | null }));

vi.mock("next-video", () => ({
  default: (props: Record<string, unknown>) => {
    videoMock.props = props;
    return createElement("video", { "aria-label": "Road video" });
  },
}));

describe("road-left frame map", () => {
  const frameMap = [
    { frameIndex: 0, timeS: 0 },
    { frameIndex: 8, timeS: 0.4 },
    { frameIndex: 15, timeS: 0.8 },
  ];

  it("maps player time to the closest stored frame", () => {
    expect(frameAtTime(frameMap, 0.39)).toBe(8);
    expect(frameAtTime(frameMap, 0.72)).toBe(15);
  });

  it("maps an evidence frame back to its packaged video time", () => {
    expect(timeAtFrame(frameMap, 9)).toBe(0.4);
    expect(timeAtFrame([], 9)).toBeNull();
  });

  it("passes a ready asset to next-video so remote MP4 URLs are not polled as JSON", () => {
    render(createElement(RoadLeftVideo, {
      descriptor: {
          tripId: "T01-Sample",
          assetUrl: "/api/trips/T01-Sample/road-video/content",
          fps: 20,
          durationS: 30,
          frameMap,
      },
        selectedFrameIndex: 0,
      onFrameIndexChange: () => undefined,
    }));

    expect(videoMock.props?.src).toMatchObject({
      status: "ready",
      sources: [{ src: "/api/trips/T01-Sample/road-video/content", type: "video/mp4" }],
    });
  });
});