"use client";

import { useEffect, useRef, useState } from "react";

import { cameraSocketUrl, CameraProtocolError, decodeCameraFrame } from "@/lib/camera-socket";
import type { DecodedCameraFrame } from "@/lib/contracts";

export function TripLiveView({ tripId, onFrame }: { tripId: string; onFrame?: (frame: DecodedCameraFrame) => void }) {
  const [frameUrl, setFrameUrl] = useState<string | null>(null);
  const [status, setStatus] = useState("Opening replay");
  const [frameIndex, setFrameIndex] = useState<number | null>(null);
  const [framesReceived, setFramesReceived] = useState(0);
  const onFrameRef = useRef(onFrame);
  onFrameRef.current = onFrame;

  useEffect(() => {
    const socket = new WebSocket(cameraSocketUrl(tripId, "road_left"));
    socket.binaryType = "arraybuffer";
    socket.onopen = () => setStatus("Historical replay");
    socket.onclose = () => setStatus("Replay disconnected");
    socket.onerror = () => setStatus("Stream degraded");
    socket.onmessage = (message) => {
      if (!(message.data instanceof ArrayBuffer)) return;
      try {
        const frame = decodeCameraFrame(message.data);
        const jpeg = new Uint8Array(frame.jpeg).buffer;
        const nextUrl = URL.createObjectURL(new Blob([jpeg], { type: "image/jpeg" }));
        setFrameIndex(frame.metadata.frame_index);
        setFramesReceived((count) => count + 1);
        onFrameRef.current?.(frame);
        setFrameUrl((previous) => {
          if (previous) URL.revokeObjectURL(previous);
          return nextUrl;
        });
      } catch (error) {
        setStatus("Invalid camera packet");
        if (error instanceof CameraProtocolError) socket.close(error.closeCode);
      }
    };
    return () => {
      socket.close();
      setFrameUrl((current) => {
        if (current) URL.revokeObjectURL(current);
        return null;
      });
    };
  }, [tripId]);

  return (
    <section className="live-view" aria-label="Historical road-facing camera replay">
      {frameUrl ? (
        // A blob URL is required for binary WebSocket frames; next/image cannot optimize it.
        // eslint-disable-next-line @next/next/no-img-element
        <img alt={`Road camera frame ${frameIndex ?? ""}`} src={frameUrl} />
      ) : (
        <div className="camera-placeholder">
          <div className="road-grid" />
          <strong>Road-facing camera</strong>
          <span>Connecting to historical replay</span>
        </div>
      )}
      <div className="live-badge">
        <span className="pulse" />
        {status}
        {frameIndex === null ? null : <b>Frame {frameIndex}</b>}
      </div>
      <div className="video-diagnostics">
        <span>CAM 01 / LEFT ROAD</span>
        <span>{framesReceived} frames received</span>
      </div>
    </section>
  );
}
