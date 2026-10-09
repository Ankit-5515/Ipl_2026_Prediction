import { NextResponse } from "next/server";
import { getVenues, tryProxyFastApi } from "@/lib/serverEngine";

export const dynamic = "force-dynamic";

export async function GET() {
  const proxied = await tryProxyFastApi("/api/venues");
  if (proxied && proxied.ok) {
    return NextResponse.json(await proxied.json());
  }
  return NextResponse.json(getVenues());
}
