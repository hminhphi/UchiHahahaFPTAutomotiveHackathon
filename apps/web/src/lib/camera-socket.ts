import type { CameraFrameMetadata, DecodedCameraFrame } from "./contracts";

const DEFAULT_MAX_METADATA_BYTES = 64 * 1024;
const DEFAULT_MAX_FRAME_BYTES = 8 * 1024 * 1024;

export class CameraProtocolError extends Error {
  constructor(
    message: string,
    public readonly closeCode: number,
  ) {
    super(message);
    this.name = "CameraProtocolError";
  }
}

function validMetadata(value: unknown): value is CameraFrameMetadata {
  if (typeof value !== "object" || value === null) return false;
  const data = value as Record<string, unknown>;
  return (
    data.schema_version === "1.0" &&
    Number.isInteger(data.frame_index) &&
    Number(data.frame_index) >= 0 &&
    typeof data.occurred_at === "string" &&
    !Number.isNaN(Date.parse(data.occurred_at)) &&
    typeof data.width === "number" &&
    Number.isInteger(data.width) &&
    data.width > 0 &&
    data.width <= 16_384 &&
    typeof data.height === "number" &&
    Number.isInteger(data.height) &&
    data.height > 0 &&
    data.height <= 16_384 &&
    typeof data.correlation_id === "string" &&
    data.correlation_id.length > 0 &&
    data.correlation_id.length <= 128
  );
}

export function decodeCameraFrame(
  packet: ArrayBuffer,
  maxMetadataBytes = DEFAULT_MAX_METADATA_BYTES,
  maxFrameBytes = DEFAULT_MAX_FRAME_BYTES,
): DecodedCameraFrame {
  const bytes = new Uint8Array(packet);
  if (bytes.byteLength < 4) throw new CameraProtocolError("Missing metadata length", 1007);

  const metadataLength = new DataView(packet).getUint32(0, false);
  if (metadataLength > maxMetadataBytes) {
    throw new CameraProtocolError("Metadata exceeds configured limit", 1009);
  }
  if (metadataLength === 0 || bytes.byteLength < 4 + metadataLength) {
    throw new CameraProtocolError("Invalid metadata length", 1007);
  }

  const jpeg = bytes.slice(4 + metadataLength);
  if (jpeg.byteLength > maxFrameBytes) {
    throw new CameraProtocolError("Frame exceeds configured limit", 1009);
  }

  let metadata: unknown;
  try {
    const metadataBytes = bytes.slice(4, 4 + metadataLength);
    metadata = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(metadataBytes));
  } catch {
    throw new CameraProtocolError("Invalid frame metadata", 1007);
  }
  if (!validMetadata(metadata)) {
    throw new CameraProtocolError("Invalid frame metadata", 1007);
  }
  if (
    jpeg.byteLength < 4 ||
    jpeg[0] !== 0xff ||
    jpeg[1] !== 0xd8 ||
    jpeg[jpeg.length - 2] !== 0xff ||
    jpeg[jpeg.length - 1] !== 0xd9
  ) {
    throw new CameraProtocolError("Payload is not a JPEG frame", 1003);
  }
  return { metadata, jpeg };
}

export function cameraSocketUrl(tripId: string, view: "road_left" | "road_right" | "driver") {
  const configured = process.env.NEXT_PUBLIC_WS_BASE_URL;
  const base =
    configured ??
    (typeof window === "undefined"
      ? "ws://localhost:8000"
      : `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`);
  return `${base.replace(/\/$/, "")}/ws/v1/trips/${encodeURIComponent(tripId)}/camera/${view}`;
}
