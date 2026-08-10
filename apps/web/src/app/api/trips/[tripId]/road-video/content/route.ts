import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE_URL = process.env.FLEETIQ_API_BASE_URL ?? "http://localhost:8000";

export async function GET(request: Request, { params }: { params: Promise<{ tripId: string }> }) {
  const { tripId } = await params;
  const headers = new Headers();
  const range = request.headers.get("range");
  if (range) headers.set("Range", range);
  const upstream = await fetch(
    `${API_BASE_URL}/api/v1/trips/${encodeURIComponent(tripId)}/road-video/content`,
    { cache: "no-store", headers },
  );
  if (!upstream.ok || !upstream.body) {
    return NextResponse.json({ error: "Road video unavailable" }, { status: upstream.status });
  }
  const responseHeaders = new Headers();
  for (const name of ["Accept-Ranges", "Content-Length", "Content-Range", "Content-Type"]) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }
  responseHeaders.set("Cache-Control", "private, max-age=300");
  return new NextResponse(upstream.body, { status: upstream.status, headers: responseHeaders });
}