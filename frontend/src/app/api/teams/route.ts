import { NextRequest, NextResponse } from "next/server";
import { getServerTeams, tryProxyFastApi } from "@/lib/serverEngine";

export async function GET(request: NextRequest) {
  const activeOnly =
    request.nextUrl.searchParams.get("active_only") !== "false";
  const proxied = await tryProxyFastApi(
    `/api/teams?active_only=${activeOnly}`
  );
  if (proxied) return NextResponse.json(proxied);

  return NextResponse.json(getServerTeams(activeOnly));
}
