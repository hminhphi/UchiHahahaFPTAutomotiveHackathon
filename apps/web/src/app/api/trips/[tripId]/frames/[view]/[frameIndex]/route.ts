import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.FLEETIQ_API_BASE_URL ?? "http://localhost:8000";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ tripId: string; view: string; frameIndex: string }> },
) {
  const { tripId, view, frameIndex } = await params;
  const upstream = await fetch(
    `${API_BASE_URL}/api/v1/trips/${encodeURIComponent(tripId)}/frames/${encodeURIComponent(view)}/${encodeURIComponent(frameIndex)}`,
    { cache: "no-store" },
  );

  if (!upstream.ok || !upstream.body) {
    return NextResponse.json({ error: "Historical frame unavailable" }, { status: upstream.status });
  }

  const headers = new Headers();
  headers.set("Content-Type", upstream.headers.get("Content-Type") ?? "image/jpeg");
  headers.set("Cache-Control", upstream.headers.get("Cache-Control") ?? "private, max-age=300");
  for (const name of ["X-FleetIQ-Frame-Index", "X-FleetIQ-Frame-Width", "X-FleetIQ-Frame-Height"]) {
    const value = upstream.headers.get(name);
    if (value) headers.set(name, value);
  }
  return new NextResponse(upstream.body, { status: 200, headers });
}
