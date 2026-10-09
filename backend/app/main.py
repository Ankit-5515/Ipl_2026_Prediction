"""
FastAPI Application Entrypoint for IPL 2026 Match Prediction Engine.
Configures CORS, Rate Limiting, Structured Logging, Database Lifespan, and OpenAPI Docs (/docs).
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable, Dict, List

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import settings
from backend.app.database import SessionLocal, init_db
from backend.app.models import PredictionRecord
from backend.app.routers.api import router as api_router
from backend.app.schemas import PredictRequest
from backend.app.services.predictor import predictor_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("ipl2026.api")


def seed_initial_predictions_if_empty() -> None:
    """Seed 3 marquee IPL 2026 predictions into the database on first startup so History is immediately rich."""
    db = SessionLocal()
    try:
        count = db.query(PredictionRecord).count()
        if count > 0:
            return

        marquee_fixtures = [
            PredictRequest(
                team1="Chennai Super Kings",
                team2="Mumbai Indians",
                venue="Chennai",
                toss_winner="Chennai Super Kings",
                toss_decision="field",
                season=2026,
            ),
            PredictRequest(
                team1="Royal Challengers Bengaluru",
                team2="Kolkata Knight Riders",
                venue="Bengaluru",
                toss_winner="Royal Challengers Bengaluru",
                toss_decision="field",
                season=2026,
            ),
            PredictRequest(
                team1="Gujarat Titans",
                team2="Rajasthan Royals",
                venue="Ahmedabad",
                toss_winner="Rajasthan Royals",
                toss_decision="field",
                season=2026,
            ),
        ]
        for fix in marquee_fixtures:
            pred = predictor_service.predict_match(fix)
            rec = PredictionRecord(
                team1=pred.team1,
                team2=pred.team2,
                venue=pred.venue,
                toss_winner=pred.toss_winner,
                toss_decision=pred.toss_decision,
                season=pred.season,
                predicted_winner=pred.predicted_winner,
                team1_win_prob=pred.team1_win_prob,
                team2_win_prob=pred.team2_win_prob,
                confidence=pred.confidence,
                model_name=pred.model_name,
                model_version=pred.model_version,
                explanation_json=json.dumps([e.model_dump() for e in pred.explanations]),
            )
            db.add(rec)
        db.commit()
        logger.info("Seeded %d initial marquee IPL 2026 predictions.", len(marquee_fixtures))
    except Exception as exc:
        logger.warning("Could not seed initial predictions: %s", exc)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize database tables and warm up ML model artifact on startup."""
    logger.info("Starting %s v%s...", settings.APP_NAME, settings.APP_VERSION)
    init_db()
    predictor_service.ensure_loaded()
    seed_initial_predictions_if_empty()
    yield
    logger.info("Shutting down %s.", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production-grade IPL 2026 Match Prediction & Sports Analytics API powered by "
        "calibrated ensemble machine learning, dynamic Elo ratings, and SHAP explainability."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lightweight Sliding-Window Rate Limiter Middleware (protects POST /api/predict)
_rate_buckets: Dict[str, List[float]] = defaultdict(list)
MAX_REQUESTS_PER_MINUTE = 120


@app.middleware("http")
async def rate_limit_and_timing_middleware(
    request: Request, call_next: Callable
) -> Response:
    start = time.perf_counter()
    client_ip = request.client.host if request.client else "local"

    if request.url.path == "/api/predict" and request.method == "POST":
        now = time.time()
        window_start = now - 60.0
        bucket = [ts for ts in _rate_buckets[client_ip] if ts > window_start]
        if len(bucket) >= MAX_REQUESTS_PER_MINUTE:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Please try again in a minute."},
            )
        bucket.append(now)
        _rate_buckets[client_ip] = bucket

    response: Response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
    return response


app.include_router(api_router)


@app.get("/", tags=["Root"])
def root() -> Dict[str, str]:
    """Root status endpoint pointing to Swagger UI and Health Check."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/api/health",
    }
