import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.FLEETIQ_API_BASE_URL ?? "http://localhost:8000";
const MINIO_PUBLIC_URL = process.env.FLEETIQ_MINIO_PUBLIC_URL ?? "http://localhost:9000";

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ tripId: string; frameIndex: string }> },
) {
  const { tripId, frameIndex } = await context.params;
  const stripped = frameIndex.endsWith(".png") ? frameIndex.slice(0, -4) : frameIndex;
  const padded = stripped.padStart(6, "0");
  const pngFilename = `${padded}.png`;

  try {
    const upstream = await fetch(
      `${API_BASE_URL}/api/v1/trips/${encodeURIComponent(tripId)}/derived/depth/${pngFilename}`,
      { cache: "no-store" },
    );
    if (upstream.ok && upstream.body) {
      return new NextResponse(upstream.body, {
        status: 200,
        headers: {
          "content-type": upstream.headers.get("content-type") ?? "image/png",
          "cache-control": "private, max-age=300",
        },
      });
    }
  } catch {
    // Fall through to MinIO fallback
  }

  const fallbackUrl = `${MINIO_PUBLIC_URL}/fleetiq-demo/trips/${encodeURIComponent(tripId)}/media/depth/${pngFilename}`;
  try {
    const fallback = await fetch(fallbackUrl, { cache: "no-store" });
    if (fallback.ok && fallback.body) {
      return new NextResponse(fallback.body, {
        status: 200,
        headers: {
          "content-type": fallback.headers.get("content-type") ?? "image/png",
          "cache-control": "private, max-age=300",
        },
      });
    }
  } catch {
    // Ignore
  }

  return NextResponse.json({ detail: "Depth frame unavailable" }, { status: 404 });
}
