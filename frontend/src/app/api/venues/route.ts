import { NextResponse } from "next/server";
import { getServerVenues, tryProxyFastApi } from "@/lib/serverEngine";

export const dynamic = "force-dynamic";

export async function GET() {
  const proxied = await tryProxyFastApi("/api/venues");
  if (proxied) return NextResponse.json(proxied);

  return NextResponse.json(getServerVenues());
}
