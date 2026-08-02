"use client";

import { useEffect, useRef, useState } from "react";

import type { TripEvidence } from "@/lib/trip-evidence";

const PLAYBACK_FPS = 10;

export function framePosition(frameIndexes: readonly number[], frameIndex: number): number {
  const exact = frameIndexes.indexOf(frameIndex);
  if (exact >= 0) return exact;
  const following = frameIndexes.findIndex((candidate) => candidate >= frameIndex);
  return following >= 0 ? following : Math.max(0, frameIndexes.length - 1);
}

export function nearestFrameIndex(frameIndexes: readonly number[], requestedFrame: number): number | null {
  if (!frameIndexes.length) return null;
  return frameIndexes[framePosition(frameIndexes, requestedFrame)];
}

export function nextFrameIndex(frameIndexes: readonly number[], currentFrame: number): number | null {
  const position = framePosition(frameIndexes, currentFrame);
  return position < frameIndexes.length - 1 ? frameIndexes[position + 1] : null;
}

interface TripVideoPlayerProps {
  tripId: string;
  frameIndexes: number[];
  selectedFrameIndex: number | null;
  evidence: TripEvidence[];
  onFrameIndexChange: (frameIndex: number) => void;
}

export function TripVideoPlayer({
  tripId,
  frameIndexes,
  selectedFrameIndex,
  evidence,
  onFrameIndexChange,
}: TripVideoPlayerProps) {
  const playerRef = useRef<HTMLElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [frameStatus, setFrameStatus] = useState<"loading" | "ready" | "error">("loading");
  const currentFrame = nearestFrameIndex(frameIndexes, selectedFrameIndex ?? frameIndexes[0] ?? 0);
  const currentPosition = currentFrame === null ? 0 : framePosition(frameIndexes, currentFrame);
  const imageUrl = currentFrame === null
    ? null
    : `/api/trips/${encodeURIComponent(tripId)}/frames/road_left/${currentFrame}`;

  useEffect(() => {
    const onFullscreenChange = () => setIsFullscreen(document.fullscreenElement === playerRef.current);
    document.addEventListener("fullscreenchange", onFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", onFullscreenChange);
  }, []);

  useEffect(() => {
    if (!isPlaying || currentFrame === null) return;
    const next = nextFrameIndex(frameIndexes, currentFrame);
    if (next === null) {
      setIsPlaying(false);
      return;
    }
    const timer = window.setTimeout(() => onFrameIndexChange(next), 1000 / PLAYBACK_FPS);
    return () => window.clearTimeout(timer);
  }, [currentFrame, frameIndexes, isPlaying, onFrameIndexChange]);

  useEffect(() => setFrameStatus("loading"), [imageUrl]);

  function chooseFrame(frameIndex: number) {
    const nearest = nearestFrameIndex(frameIndexes, frameIndex);
    if (nearest !== null) onFrameIndexChange(nearest);
  }

  function togglePlayback() {
    if (currentPosition === frameIndexes.length - 1 && frameIndexes.length) {
      chooseFrame(frameIndexes[0]);
      setIsPlaying(true);
      return;
    }
    setIsPlaying((playing) => !playing);
  }

  async function toggleFullscreen() {
    if (!playerRef.current) return;
    if (document.fullscreenElement === playerRef.current) {
      await document.exitFullscreen();
      return;
    }
    await playerRef.current.requestFullscreen();
  }

  return (
    <section className="trip-video-player" ref={playerRef} aria-label="Historical road-facing video player">
      <div className="live-view">
        {imageUrl ? (
          // Exact historical frames are intentionally served from the same-origin Next proxy.
          // eslint-disable-next-line @next/next/no-img-element
          <img alt={`Road-facing camera frame ${currentFrame}`} src={imageUrl} onLoad={() => setFrameStatus("ready")} onError={() => setFrameStatus("error")} />
        ) : (
          <div className="camera-placeholder"><div className="road-grid" /><strong>No historical frames</strong><span>This trip has no road-facing camera evidence.</span></div>
        )}
        <div className="live-badge"><span className="pulse" /> Historical evidence <b>{currentFrame === null ? "No frame" : `Frame ${currentFrame}`}</b></div>
        <div className="video-diagnostics"><span>CAM 01 / LEFT ROAD</span><span>{frameStatus === "ready" ? "Frame verified" : frameStatus === "error" ? "Frame unavailable" : "Loading evidence"}</span></div>
      </div>

      <div className="player-controls" aria-label="Replay controls">
        <button type="button" className="player-primary" onClick={togglePlayback} disabled={currentFrame === null}>
          {isPlaying ? "Pause" : currentPosition === frameIndexes.length - 1 ? "Replay" : "Play"}
        </button>
        <button type="button" className="player-step" onClick={() => chooseFrame(frameIndexes[Math.max(0, currentPosition - 1)])} disabled={currentPosition === 0}>Previous frame</button>
        <input
          aria-label="Select historical frame"
          type="range"
          min="0"
          max={Math.max(0, frameIndexes.length - 1)}
          value={currentPosition}
          disabled={!frameIndexes.length}
          onChange={(event) => chooseFrame(frameIndexes[Number(event.target.value)])}
        />
        <button type="button" className="player-step" onClick={() => chooseFrame(frameIndexes[Math.min(frameIndexes.length - 1, currentPosition + 1)])} disabled={currentPosition >= frameIndexes.length - 1}>Next frame</button>
        <output aria-live="polite">{currentFrame === null ? "--" : `${currentFrame} / ${frameIndexes.at(-1)}`}</output>
        <button type="button" className="player-fullscreen" onClick={() => void toggleFullscreen()} disabled={currentFrame === null}>{isFullscreen ? "Exit full screen" : "Full screen"}</button>
      </div>

      {evidence.length ? (
        <nav className="event-trace" aria-label="Risk event trace">
          <span>Trace risk event</span>
          {evidence.map((event) => (
            <button key={`${event.label}-${event.frameIndex}`} type="button" className={`event-trace-button severity-${event.severity}`} onClick={() => { setIsPlaying(false); chooseFrame(event.frameIndex); }}>
              <b>F{event.frameIndex}</b>{event.label}
            </button>
          ))}
        </nav>
      ) : null}
    </section>
  );
}
