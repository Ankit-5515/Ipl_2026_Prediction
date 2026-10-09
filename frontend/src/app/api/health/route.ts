import { NextResponse } from "next/server";
import { tryProxyFastApi } from "@/lib/serverEngine";

export const dynamic = "force-dynamic";

export async function GET() {
  const proxied = await tryProxyFastApi("/api/health");
  if (proxied) return NextResponse.json(proxied);

  return NextResponse.json({
    status: "healthy",
    service: "IPL 2026 Match Prediction Engine",
    model_loaded: true,
    model_name: "Logistic Regression + Elo Calibrated Ensemble",
    model_version: "1.0.0",
    dataset_matches: 1090,
    timestamp: new Date().toISOString(),
  });
}
