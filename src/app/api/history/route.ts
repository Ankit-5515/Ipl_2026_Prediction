import { NextRequest, NextResponse } from "next/server";
import { getServerHistory, tryProxyFastApi } from "@/lib/serverEngine";

export async function GET(request: NextRequest) {
  const limit = Number(request.nextUrl.searchParams.get("limit") || "25");
  const proxied = await tryProxyFastApi(`/api/history?limit=${limit}`);
  if (proxied) return NextResponse.json(proxied);

  return NextResponse.json(getServerHistory(limit));
}
