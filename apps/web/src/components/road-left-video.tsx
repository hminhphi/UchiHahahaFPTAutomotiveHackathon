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
  const selectedFrameAvailable = selectedFrameIndex === null || descriptor.frameMap.some(
    (entry) => entry.frameIndex === selectedFrameIndex,
  );
  const firstFrame = descriptor.frameMap[0]?.frameIndex;
  const lastFrame = descriptor.frameMap.at(-1)?.frameIndex;

  useEffect(() => {
    if (selectedFrameIndex === null || !selectedFrameAvailable || !videoRef.current) return;
    const timeS = timeAtFrame(descriptor.frameMap, selectedFrameIndex);
    if (timeS !== null && Math.abs(videoRef.current.currentTime - timeS) > 0.025) {
      videoRef.current.currentTime = timeS;
    }
  }, [descriptor.frameMap, selectedFrameIndex, selectedFrameAvailable]);

  return (
    <section className="road-left-player" aria-label="Historical road-left video">
      <div className="road-video-stage">
        {selectedFrameAvailable ? (
          <>
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
            <RoadAnalysisOverlay frameIndex={selectedFrameIndex} analysis={analysis} />
          </>
        ) : (
          <div className="camera-placeholder road-video-unavailable">
            <strong>Road video unavailable at frame {selectedFrameIndex}</strong>
            <span>Packaged road video covers frames {firstFrame}–{lastFrame}; DMS and telemetry remain frame-linked.</span>
          </div>
        )}
      </div>
    </section>
  );
}
