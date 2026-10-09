import { NextResponse } from "next/server";
import { getHealth, tryProxyFastApi } from "@/lib/serverEngine";

export const dynamic = "force-dynamic";

export async function GET() {
  const proxied = await tryProxyFastApi("/api/health");
  if (proxied && proxied.ok) {
    return NextResponse.json(await proxied.json());
  }
  return NextResponse.json(getHealth());
}
