import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.FLEETIQ_API_BASE_URL ?? "http://localhost:8000";

export async function GET(_request: NextRequest, context: { params: Promise<{ tripId: string; frameIndex: string }> }) {
  const { tripId, frameIndex } = await context.params;
  if (!/^\d+$/.test(frameIndex)) return new NextResponse(null, { status: 404 });
  const upstream = await fetch(
    `${API_BASE_URL}/api/v1/trips/${encodeURIComponent(tripId)}/analysis/road/masks/${frameIndex}`,
    { cache: "no-store" },
  );
  return new NextResponse(await upstream.arrayBuffer(), {
    status: upstream.status,
    headers: { "content-type": upstream.headers.get("content-type") ?? "image/png" },
  });
}