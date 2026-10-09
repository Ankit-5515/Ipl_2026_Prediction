import { NextResponse } from "next/server";
import {
  getServerDashboardAnalytics,
  tryProxyFastApi,
} from "@/lib/serverEngine";

export const dynamic = "force-dynamic";

export async function GET() {
  const proxied = await tryProxyFastApi("/api/stats/analytics");
  if (proxied) return NextResponse.json(proxied);

  return NextResponse.json(getServerDashboardAnalytics());
}
