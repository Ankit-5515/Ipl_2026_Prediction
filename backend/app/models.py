"""SQLAlchemy ORM models for storing match predictions."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class PredictionRecord(Base):
    """Persisted record of every match prediction requested by users."""

    __tablename__ = "prediction_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    team1: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    team2: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    venue: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    toss_winner: Mapped[str] = mapped_column(String(100), nullable=False)
    toss_decision: Mapped[str] = mapped_column(String(20), nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False, default=2026)

    predicted_winner: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    team1_win_prob: Mapped[float] = mapped_column(Float, nullable=False)
    team2_win_prob: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    explanation_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
