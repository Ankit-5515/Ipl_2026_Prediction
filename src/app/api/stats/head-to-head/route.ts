import { NextRequest, NextResponse } from "next/server";
import { getServerHeadToHead, tryProxyFastApi } from "@/lib/serverEngine";

export async function GET(request: NextRequest) {
  const team1 =
    request.nextUrl.searchParams.get("team1") || "Chennai Super Kings";
  const team2 =
    request.nextUrl.searchParams.get("team2") || "Mumbai Indians";

  if (team1 === team2) {
    return NextResponse.json(
      { detail: "team1 and team2 must be different franchises." },
      { status: 400 }
    );
  }

  const params = new URLSearchParams({ team1, team2 });
  const proxied = await tryProxyFastApi(
    `/api/stats/head-to-head?${params.toString()}`
  );
  if (proxied) return NextResponse.json(proxied);

  return NextResponse.json(getServerHeadToHead(team1, team2));
}
