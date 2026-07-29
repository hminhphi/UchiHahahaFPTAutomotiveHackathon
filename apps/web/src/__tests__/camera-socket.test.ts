import { describe, expect, it } from "vitest";

import { CameraProtocolError, decodeCameraFrame } from "@/lib/camera-socket";

const metadata = {
  schema_version: "1.0" as const,
  frame_index: 7,
  occurred_at: "2026-07-29T12:00:00Z",
  width: 640,
  height: 360,
  correlation_id: "corr-7",
};

function packet(meta = metadata, jpeg = new Uint8Array([0xff, 0xd8, 1, 0xff, 0xd9])) {
  const encoded = new TextEncoder().encode(JSON.stringify(meta));
  const output = new Uint8Array(4 + encoded.length + jpeg.length);
  new DataView(output.buffer).setUint32(0, encoded.length, false);
  output.set(encoded, 4);
  output.set(jpeg, 4 + encoded.length);
  return output.buffer;
}

describe("camera frame protocol", () => {
  it("decodes the FastAPI u32be metadata and JPEG packet", () => {
    const frame = decodeCameraFrame(packet());

    expect(frame.metadata.frame_index).toBe(7);
    expect(frame.metadata.width).toBe(640);
    expect([...frame.jpeg]).toEqual([0xff, 0xd8, 1, 0xff, 0xd9]);
  });

  it("rejects oversized metadata with close code 1009", () => {
    const bytes = new Uint8Array(4);
    new DataView(bytes.buffer).setUint32(0, 70_000, false);

    expect(() => decodeCameraFrame(bytes.buffer)).toThrow(
      expect.objectContaining<Partial<CameraProtocolError>>({ closeCode: 1009 }),
    );
  });

  it("rejects non-JPEG payloads", () => {
    expect(() => decodeCameraFrame(packet(metadata, new Uint8Array([1, 2, 3, 4])))).toThrow(
      expect.objectContaining<Partial<CameraProtocolError>>({ closeCode: 1003 }),
    );
  });
});
