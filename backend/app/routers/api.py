"""
FastAPI REST endpoints for IPL 2026 Match Prediction:
- POST /api/predict
- GET  /api/teams
- GET  /api/venues
- GET  /api/history
- GET  /api/stats/head-to-head
- GET  /api/stats/analytics
- GET  /api/health
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models import PredictionRecord
from backend.app.schemas import (
    FeatureContribution,
    HeadToHeadResponse,
    HealthResponse,
    PredictionHistoryItem,
    PredictRequest,
    PredictResponse,
    TeamInfo,
    VenueInfo,
)
from backend.app.services.analytics import analytics_service
from backend.app.services.predictor import predictor_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["IPL 2026 Prediction API"])

START_TIME = time.time()


@router.post(
    "/predict",
    response_model=PredictResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict match winner with calibrated win probabilities and SHAP explanations",
)
def predict_match_endpoint(
    payload: PredictRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> PredictResponse:
    """
    Run pre-match win probability inference, compute local SHAP feature attributions
    ('Why this prediction?'), persist the prediction to PostgreSQL/SQLite, and return the result.
    """
    try:
        prediction = predictor_service.predict_match(payload)

        # Persist prediction in database
        explanations_serialized = json.dumps(
            [exp.model_dump() for exp in prediction.explanations]
        )
        record = PredictionRecord(
            team1=prediction.team1,
            team2=prediction.team2,
            venue=prediction.venue,
            toss_winner=prediction.toss_winner,
            toss_decision=prediction.toss_decision,
            season=prediction.season,
            predicted_winner=prediction.predicted_winner,
            team1_win_prob=prediction.team1_win_prob,
            team2_win_prob=prediction.team2_win_prob,
            confidence=prediction.confidence,
            model_name=prediction.model_name,
            model_version=prediction.model_version,
            explanation_json=explanations_serialized,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        prediction.prediction_id = record.id
        prediction.created_at = record.created_at
        logger.info(
            "Prediction #%s saved: %s vs %s at %s -> %s (%s)",
            record.id,
            prediction.team1,
            prediction.team2,
            prediction.venue,
            prediction.predicted_winner,
            prediction.summary_text,
        )
        return prediction
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.exception("Prediction failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate match prediction: {exc}",
        ) from exc


@router.get(
    "/teams",
    response_model=List[TeamInfo],
    summary="List IPL franchises with Elo rating, win rate, recent form, and branding colors",
)
def get_teams_endpoint(
    active_only: bool = Query(
        default=False, description="If true, only return the 10 active IPL 2026 franchises"
    ),
) -> List[TeamInfo]:
    return analytics_service.get_teams(active_only=active_only)


@router.get(
    "/venues",
    response_model=List[VenueInfo],
    summary="List IPL venues with historical chase bias, average target runs, and toss stats",
)
def get_venues_endpoint() -> List[VenueInfo]:
    return analytics_service.get_venues()


@router.get(
    "/history",
    response_model=List[PredictionHistoryItem],
    summary="Fetch past predictions stored in the database",
)
def get_prediction_history(
    limit: int = Query(default=25, ge=1, le=100, description="Max records to return"),
    db: Session = Depends(get_db),
) -> List[PredictionHistoryItem]:
    rows = (
        db.query(PredictionRecord)
        .order_by(PredictionRecord.created_at.desc(), PredictionRecord.id.desc())
        .limit(limit)
        .all()
    )
    items: List[PredictionHistoryItem] = []
    for row in rows:
        try:
            raw_exp = json.loads(row.explanation_json or "[]")
            explanations = [FeatureContribution(**item) for item in raw_exp]
        except Exception:
            explanations = []

        items.append(
            PredictionHistoryItem(
                id=row.id,
                team1=row.team1,
                team2=row.team2,
                venue=row.venue,
                toss_winner=row.toss_winner,
                toss_decision=row.toss_decision,
                season=row.season,
                predicted_winner=row.predicted_winner,
                team1_win_prob=row.team1_win_prob,
                team2_win_prob=row.team2_win_prob,
                confidence=row.confidence,
                model_name=row.model_name,
                model_version=row.model_version,
                explanations=explanations,
                created_at=row.created_at,
            )
        )
    return items


@router.get(
    "/stats/head-to-head",
    response_model=HeadToHeadResponse,
    summary="Get head-to-head historical stats and recent clashes between two IPL teams",
)
def get_head_to_head_endpoint(
    team1: str = Query(..., description="First team name"),
    team2: str = Query(..., description="Second team name"),
) -> HeadToHeadResponse:
    try:
        return analytics_service.get_head_to_head(team1=team1, team2=team2)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get(
    "/stats/analytics",
    summary="Get full analytics dashboard data (team standings, venue stats, season trends, model metrics)",
)
def get_dashboard_analytics_endpoint() -> Dict[str, Any]:
    return analytics_service.get_dashboard_analytics()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health-check and cold-start keep-alive endpoint",
)
def health_check_endpoint(db: Session = Depends(get_db)) -> HealthResponse:
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    predictor_service.ensure_loaded()
    return HealthResponse(
        status="healthy" if (db_ok and predictor_service.loaded) else "degraded",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        uptime_seconds=round(time.time() - START_TIME, 2),
        database_connected=db_ok,
        model_loaded=predictor_service.loaded,
        model_name=predictor_service.model_name,
        total_historical_matches=len(analytics_service.df),
        timestamp=datetime.now(timezone.utc),
    )
