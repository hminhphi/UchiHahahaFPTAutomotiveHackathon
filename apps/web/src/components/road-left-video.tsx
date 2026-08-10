"use client";

import Video from "next-video";
import { useEffect, useRef } from "react";

import { RoadAnalysisOverlay } from "@/components/road-analysis-overlay";
import { frameAtTime, timeAtFrame, type RoadFrameAnalysis, type RoadVideoDescriptor } from "@/lib/operations";

interface RoadLeftVideoProps {
  descriptor: RoadVideoDescriptor;
  selectedFrameIndex: number | null;
  onFrameIndexChange: (frameIndex: number) => void;
  analysis?: RoadFrameAnalysis | null;
}

export function RoadLeftVideo({ descriptor, selectedFrameIndex, onFrameIndexChange, analysis = null }: RoadLeftVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (selectedFrameIndex === null || !videoRef.current) return;
    const timeS = timeAtFrame(descriptor.frameMap, selectedFrameIndex);
    if (timeS !== null && Math.abs(videoRef.current.currentTime - timeS) > 0.025) {
      videoRef.current.currentTime = timeS;
    }
  }, [descriptor.frameMap, selectedFrameIndex]);

  return (
    <section className="road-left-player" aria-label="Historical road-left video">
      <div className="road-video-stage">
        <Video
        ref={videoRef}
        src={{
          status: "ready",
          originalFilePath: descriptor.assetUrl,
          provider: "external",
          sources: [{ src: descriptor.assetUrl, type: "video/mp4" }],
          createdAt: 0,
          updatedAt: 0,
        }}
        transform={(asset) => asset}
        controls
        playsInline
        preload="metadata"
        onLoadedMetadata={(event) => {
          const frameIndex = frameAtTime(descriptor.frameMap, event.currentTarget.currentTime);
          if (frameIndex !== null) onFrameIndexChange(frameIndex);
        }}
        onTimeUpdate={(event) => {
          const frameIndex = frameAtTime(descriptor.frameMap, event.currentTarget.currentTime);
          if (frameIndex !== null) onFrameIndexChange(frameIndex);
        }}
        style={{ width: "100%", aspectRatio: "16 / 9", background: "#071124" }}
        />
        <RoadAnalysisOverlay tripId={descriptor.tripId} frameIndex={selectedFrameIndex} analysis={analysis} />
      </div>
    </section>
  );
}