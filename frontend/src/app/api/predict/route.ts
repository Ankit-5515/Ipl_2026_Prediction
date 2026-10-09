import { NextRequest, NextResponse } from "next/server";
import {
  computeServerPrediction,
  tryProxyFastApi,
} from "@/lib/serverEngine";
import { PredictRequest } from "@/lib/types";

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as PredictRequest;
    if (!body.team1 || !body.team2 || body.team1 === body.team2) {
      return NextResponse.json(
        { detail: "team1 and team2 must be two different teams." },
        { status: 422 }
      );
    }

    const proxied = await tryProxyFastApi("/api/predict", {
      method: "POST",
      body: JSON.stringify(body),
    });
    if (proxied) return NextResponse.json(proxied);

    const pred = computeServerPrediction(body);
    return NextResponse.json(pred);
  } catch (err: any) {
    return NextResponse.json(
      { detail: err?.message || "Invalid prediction request." },
      { status: 400 }
    );
  }
}
