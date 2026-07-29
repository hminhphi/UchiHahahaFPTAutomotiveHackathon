"use client";

import { useEffect, useState } from "react";

import { cameraSocketUrl, CameraProtocolError, decodeCameraFrame } from "@/lib/camera-socket";

export function TripLiveView({ tripId }: { tripId: string }) {
  const [frameUrl, setFrameUrl] = useState<string | null>(null);
  const [status, setStatus] = useState("Connecting");
  const [frameIndex, setFrameIndex] = useState<number | null>(null);

  useEffect(() => {
    const socket = new WebSocket(cameraSocketUrl(tripId, "road_left"));
    socket.binaryType = "arraybuffer";
    socket.onopen = () => setStatus("Live stream");
    socket.onclose = () => setStatus("Replay unavailable");
    socket.onerror = () => setStatus("Stream degraded");
    socket.onmessage = (message) => {
      if (!(message.data instanceof ArrayBuffer)) return;
      try {
        const frame = decodeCameraFrame(message.data);
        const jpeg = new Uint8Array(frame.jpeg).buffer;
        const nextUrl = URL.createObjectURL(new Blob([jpeg], { type: "image/jpeg" }));
        setFrameIndex(frame.metadata.frame_index);
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
    <section className="live-view">
      {frameUrl ? (
        // A blob URL is required for binary WebSocket frames; next/image cannot optimize it.
        // eslint-disable-next-line @next/next/no-img-element
        <img alt={`Road camera frame ${frameIndex ?? ""}`} src={frameUrl} />
      ) : (
        <div className="camera-placeholder">
          <div className="road-grid" />
          <strong>Road camera</strong>
          <span>Waiting for binary JPEG frames</span>
        </div>
      )}
      <div className="live-badge">
        <span className="pulse" />
        {status}
        {frameIndex === null ? null : <b>Frame {frameIndex}</b>}
      </div>
    </section>
  );
}
