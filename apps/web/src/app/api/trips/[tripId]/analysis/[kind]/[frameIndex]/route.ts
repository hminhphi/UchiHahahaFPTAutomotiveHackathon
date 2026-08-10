import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.FLEETIQ_API_BASE_URL ?? "http://localhost:8000";

export async function GET(_request: NextRequest, context: { params: Promise<{ tripId: string; kind: string; frameIndex: string }> }) {
  const { tripId, kind, frameIndex } = await context.params;
  if (!/^(road|dms|fusion)$/.test(kind) || !/^\d+$/.test(frameIndex)) {
    return NextResponse.json({ detail: "Frame analysis not found" }, { status: 404 });
  }
  const upstream = await fetch(
    `${API_BASE_URL}/api/v1/trips/${encodeURIComponent(tripId)}/analysis/${kind}/frames/${frameIndex}`,
    { cache: "no-store" },
  );
  return new NextResponse(await upstream.arrayBuffer(), {
    status: upstream.status,
    headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
  });
}