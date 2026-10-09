"""Pydantic v2 request and response schemas with strict validation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from ml.preprocessing import canonicalize_team, canonicalize_venue


class PredictRequest(BaseModel):
    """Input payload for POST /api/predict."""

    team1: str = Field(..., min_length=2, description="First team name (e.g., Chennai Super Kings)")
    team2: str = Field(..., min_length=2, description="Second team name (e.g., Mumbai Indians)")
    venue: str = Field(..., min_length=2, description="Match venue/city (e.g., Chennai)")
    toss_winner: str = Field(..., min_length=2, description="Team that won the toss")
    toss_decision: Literal["bat", "field", "bowl"] = Field(
        default="field", description="Toss decision: 'bat' or 'field'"
    )
    season: int = Field(default=2026, ge=2008, le=2030, description="Target IPL season")

    @model_validator(mode="after")
    def validate_match_constraints(self) -> "PredictRequest":
        t1 = canonicalize_team(self.team1)
        t2 = canonicalize_team(self.team2)
        tw = canonicalize_team(self.toss_winner)
        v = canonicalize_venue(self.venue, t1)

        if t1 == t2:
            raise ValueError("team1 and team2 must be two different teams.")
        if tw not in (t1, t2):
            raise ValueError("toss_winner must be either team1 or team2.")

        self.team1 = t1
        self.team2 = t2
        self.toss_winner = tw
        self.venue = v
        if self.toss_decision == "bowl":
            self.toss_decision = "field"
        return self


class FeatureContribution(BaseModel):
    """Individual SHAP / feature attribution explaining 'Why this prediction?'."""

    feature: str
    display_name: str
    impact: float = Field(..., description="Signed probability impact in percentage points")
    abs_impact: float = Field(..., description="Absolute impact magnitude")
    favored_team: str = Field(..., description="Which team this factor favors")
    value_summary: str = Field(..., description="Human-readable comparison of feature values")


class MatchupContextStats(BaseModel):
    """Pre-match statistical context returned alongside the prediction."""

    team1_elo: float
    team2_elo: float
    team1_overall_win_rate: float
    team2_overall_win_rate: float
    team1_form_last5: float
    team2_form_last5: float
    h2h_total_matches: int
    h2h_team1_wins: int
    h2h_team2_wins: int
    h2h_team1_win_rate: float
    team1_venue_win_rate: float
    team2_venue_win_rate: float
    venue_chase_win_rate: float
    venue_avg_target_runs: float


class PredictResponse(BaseModel):
    """Response payload for POST /api/predict."""

    prediction_id: Optional[int] = None
    team1: str
    team2: str
    venue: str
    toss_winner: str
    toss_decision: str
    season: int
    predicted_winner: str
    team1_win_prob: float = Field(..., description="Percentage probability (0-100) for team1")
    team2_win_prob: float = Field(..., description="Percentage probability (0-100) for team2")
    summary_text: str = Field(..., description="Formatted e.g. 'CSK 63.4% vs MI 36.6%'")
    confidence: str = Field(..., description="High / Moderate / Nail-Biter")
    model_name: str
    model_version: str
    explanations: List[FeatureContribution]
    matchup_stats: MatchupContextStats
    created_at: datetime


class TeamInfo(BaseModel):
    """Team metadata and historical performance summary."""

    name: str
    short_name: str
    primary_color: str
    secondary_color: str
    home_venue: str
    titles: List[int]
    title_count: int
    active: bool
    matches_played: int
    wins: int
    win_rate: float
    elo_rating: float
    recent_form: List[int]


class VenueInfo(BaseModel):
    """Venue metadata and historical pitch statistics."""

    name: str
    matches_played: int
    chase_win_rate: float
    defend_win_rate: float
    avg_target_runs: float
    toss_field_rate: float
    high_scoring_index: str


class PredictionHistoryItem(BaseModel):
    """Single item in GET /api/history."""

    id: int
    team1: str
    team2: str
    venue: str
    toss_winner: str
    toss_decision: str
    season: int
    predicted_winner: str
    team1_win_prob: float
    team2_win_prob: float
    confidence: str
    model_name: str
    model_version: str
    explanations: List[FeatureContribution] = []
    created_at: datetime


class HeadToHeadMatch(BaseModel):
    """Historical encounter summary between two franchises."""

    match_id: int
    season: int
    venue: str
    toss_winner: str
    toss_decision: str
    winner: str
    result_margin: float
    target_runs: float


class HeadToHeadResponse(BaseModel):
    """Response for GET /api/stats/head-to-head."""

    team1: str
    team2: str
    total_matches: int
    team1_wins: int
    team2_wins: int
    team1_win_rate: float
    team2_win_rate: float
    avg_target_runs: float
    avg_win_margin: float
    venue_breakdown: List[Dict[str, Any]]
    season_breakdown: List[Dict[str, Any]]
    recent_matches: List[HeadToHeadMatch]


class HealthResponse(BaseModel):
    """Response for GET /api/health."""

    status: str
    version: str
    environment: str
    uptime_seconds: float
    database_connected: bool
    model_loaded: bool
    model_name: str
    total_historical_matches: int
    timestamp: datetime
