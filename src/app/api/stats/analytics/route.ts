import { NextResponse } from "next/server";
import { getAnalyticsDashboard, tryProxyFastApi } from "@/lib/serverEngine";

export const dynamic = "force-dynamic";

export async function GET() {
  const proxied = await tryProxyFastApi("/api/stats/analytics");
  if (proxied && proxied.ok) {
    return NextResponse.json(await proxied.json());
  }
  return NextResponse.json(getAnalyticsDashboard());
}
