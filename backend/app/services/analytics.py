"""
Historical Analytics, Team/Venue Metadata, Head-to-Head, and Season Trend Service
with built-in TTL memory caching.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from backend.app.config import settings
from backend.app.schemas import (
    HeadToHeadMatch,
    HeadToHeadResponse,
    TeamInfo,
    VenueInfo,
)
from backend.app.services.predictor import predictor_service
from ml.preprocessing import (
    TEAM_METADATA,
    canonicalize_team,
    load_and_clean_dataset,
)


class AnalyticsService:
    """Provides cached analytical aggregations over the IPL historical dataset."""

    def __init__(self) -> None:
        self._df: Optional[pd.DataFrame] = None
        self._cache: Dict[str, Tuple[float, Any]] = {}

    @property
    def df(self) -> pd.DataFrame:
        if self._df is None:
            self._df = load_and_clean_dataset(settings.DATASET_PATH)
        return self._df

    def _get_cached(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry is None:
            return None
        expires_at, val = entry
        if time.time() > expires_at:
            del self._cache[key]
            return None
        return val

    def _set_cached(self, key: str, value: Any) -> Any:
        self._cache[key] = (time.time() + settings.CACHE_TTL_SECONDS, value)
        return value

    def get_teams(self, active_only: bool = False) -> List[TeamInfo]:
        cache_key = f"teams:{active_only}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        store = predictor_service.state_store
        teams_list: List[TeamInfo] = []

        for team_name, meta in TEAM_METADATA.items():
            if active_only and not meta.get("active", False):
                continue

            matches = int(store.team_matches.get(team_name, 0))
            wins = int(store.team_wins.get(team_name, 0))
            win_rate = round((wins / matches) * 100.0, 2) if matches > 0 else 50.0
            elo = round(store.get_elo(team_name), 1)
            recent = list(store.team_recent_results.get(team_name, []))[-5:]
            titles = list(meta.get("titles", []))

            teams_list.append(
                TeamInfo(
                    name=team_name,
                    short_name=str(meta["short_name"]),
                    primary_color=str(meta["primary_color"]),
                    secondary_color=str(meta["secondary_color"]),
                    home_venue=str(meta["home_venue"]),
                    titles=titles,
                    title_count=len(titles),
                    active=bool(meta.get("active", True)),
                    matches_played=matches,
                    wins=wins,
                    win_rate=win_rate,
                    elo_rating=elo,
                    recent_form=recent,
                )
            )

        # Sort active franchises first, then by Elo rating descending
        teams_list.sort(key=lambda t: (t.active, t.elo_rating), reverse=True)
        return self._set_cached(cache_key, teams_list)

    def get_venues(self) -> List[VenueInfo]:
        cache_key = "venues:all"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        df = self.df
        venues: List[VenueInfo] = []

        for venue_name, group in df.groupby("venue"):
            total = len(group)
            if total < 3:
                continue

            # Determine chasing wins
            chasing_team = [
                t1 if ((tw == t1 and td == "field") or (tw == t2 and td == "bat")) else t2
                for t1, t2, tw, td in zip(
                    group["team1"],
                    group["team2"],
                    group["toss_winner"],
                    group["toss_decision"],
                )
            ]
            chase_wins = sum(w == ct for w, ct in zip(group["winner"], chasing_team))
            chase_wr = round((chase_wins / total) * 100.0, 1)
            defend_wr = round(100.0 - chase_wr, 1)
            avg_target = round(float(group["target_runs"].mean()), 1)
            field_rate = round(
                float((group["toss_decision"] == "field").mean()) * 100.0, 1
            )

            if avg_target >= 173.0:
                scoring_idx = "Batting Paradise (High Scoring)"
            elif avg_target >= 162.0:
                scoring_idx = "Balanced Sporting Deck"
            else:
                scoring_idx = "Bowler Friendly / Tactical"

            venues.append(
                VenueInfo(
                    name=str(venue_name),
                    matches_played=int(total),
                    chase_win_rate=chase_wr,
                    defend_win_rate=defend_wr,
                    avg_target_runs=avg_target,
                    toss_field_rate=field_rate,
                    high_scoring_index=scoring_idx,
                )
            )

        venues.sort(key=lambda v: v.matches_played, reverse=True)
        return self._set_cached(cache_key, venues)

    def get_head_to_head(self, team1: str, team2: str) -> HeadToHeadResponse:
        t1 = canonicalize_team(team1)
        t2 = canonicalize_team(team2)
        if t1 == t2:
            raise ValueError("team1 and team2 must be different franchises.")

        cache_key = f"h2h:{t1}:{t2}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        df = self.df
        mask = ((df["team1"] == t1) & (df["team2"] == t2)) | (
            (df["team1"] == t2) & (df["team2"] == t1)
        )
        sub = df[mask].copy()

        total = len(sub)
        t1_wins = int((sub["winner"] == t1).sum())
        t2_wins = int((sub["winner"] == t2).sum())
        t1_wr = round((t1_wins / total) * 100.0, 1) if total > 0 else 50.0
        t2_wr = round((t2_wins / total) * 100.0, 1) if total > 0 else 50.0
        avg_target = round(float(sub["target_runs"].mean()), 1) if total > 0 else 168.0
        avg_margin = round(float(sub["result_margin"].mean()), 1) if total > 0 else 15.0

        # Venue breakdown
        venue_breakdown: List[Dict[str, Any]] = []
        if total > 0:
            for v_name, v_grp in sub.groupby("venue"):
                venue_breakdown.append(
                    {
                        "venue": str(v_name),
                        "matches": int(len(v_grp)),
                        "team1_wins": int((v_grp["winner"] == t1).sum()),
                        "team2_wins": int((v_grp["winner"] == t2).sum()),
                    }
                )
            venue_breakdown.sort(key=lambda x: x["matches"], reverse=True)

        # Season breakdown
        season_breakdown: List[Dict[str, Any]] = []
        if total > 0:
            for s_yr, s_grp in sub.groupby("season"):
                season_breakdown.append(
                    {
                        "season": int(s_yr),
                        "matches": int(len(s_grp)),
                        "team1_wins": int((s_grp["winner"] == t1).sum()),
                        "team2_wins": int((s_grp["winner"] == t2).sum()),
                    }
                )
            season_breakdown.sort(key=lambda x: x["season"])

        # Recent 8 matches
        recent_rows = sub.tail(8).iloc[::-1]
        recent_matches = [
            HeadToHeadMatch(
                match_id=int(r["match_id"]),
                season=int(r["season"]),
                venue=str(r["venue"]),
                toss_winner=str(r["toss_winner"]),
                toss_decision=str(r["toss_decision"]),
                winner=str(r["winner"]),
                result_margin=float(r["result_margin"]),
                target_runs=float(r["target_runs"]),
            )
            for _, r in recent_rows.iterrows()
        ]

        res = HeadToHeadResponse(
            team1=t1,
            team2=t2,
            total_matches=total,
            team1_wins=t1_wins,
            team2_wins=t2_wins,
            team1_win_rate=t1_wr,
            team2_win_rate=t2_wr,
            avg_target_runs=avg_target,
            avg_win_margin=avg_margin,
            venue_breakdown=venue_breakdown[:8],
            season_breakdown=season_breakdown,
            recent_matches=recent_matches,
        )
        return self._set_cached(cache_key, res)

    def get_dashboard_analytics(self) -> Dict[str, Any]:
        """Return comprehensive analytics for the Frontend Dashboard & About pages."""
        cache_key = "dashboard:overview"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        df = self.df
        teams = self.get_teams(active_only=True)
        venues = self.get_venues()[:12]

        # Season trends (2008 - 2024)
        season_trends: List[Dict[str, Any]] = []
        for s_yr, grp in df.groupby("season"):
            total = len(grp)
            chasing_team = [
                t1 if ((tw == t1 and td == "field") or (tw == t2 and td == "bat")) else t2
                for t1, t2, tw, td in zip(
                    grp["team1"], grp["team2"], grp["toss_winner"], grp["toss_decision"]
                )
            ]
            chase_wr = round(
                (sum(w == ct for w, ct in zip(grp["winner"], chasing_team)) / total) * 100.0,
                1,
            )
            toss_field_pct = round(
                float((grp["toss_decision"] == "field").mean()) * 100.0, 1
            )
            final_winner = str(grp.iloc[-1]["winner"])
            season_trends.append(
                {
                    "season": int(s_yr),
                    "matches": int(total),
                    "avg_target_runs": round(float(grp["target_runs"].mean()), 1),
                    "chase_win_rate": chase_wr,
                    "toss_field_rate": toss_field_pct,
                    "champion": final_winner,
                    "champion_short": TEAM_METADATA.get(final_winner, {}).get(
                        "short_name", final_winner
                    ),
                }
            )

        # Load metrics.json if available
        metrics_data: Dict[str, Any] = {}
        metrics_path = Path(settings.METRICS_PATH)
        if metrics_path.exists():
            try:
                metrics_data = json.loads(metrics_path.read_text(encoding="utf-8"))
            except Exception:
                metrics_data = {}
        if not metrics_data:
            predictor_service.ensure_loaded()
            art = predictor_service.artifact
            metrics_data = {
                "version": art.get("version", "1.0.0"),
                "selected_model": art.get("best_model_name", "Hybrid Ensemble"),
                "selected_metrics": art.get("best_metrics", {}),
                "models_compared": art.get("benchmark_results", []),
                "global_feature_importance": art.get("global_feature_importance", []),
                "dataset_summary": art.get("dataset_summary", {}),
            }

        payload = {
            "summary": {
                "total_matches": int(len(df)),
                "seasons_count": int(df["season"].nunique()),
                "active_teams_count": len(teams),
                "total_venues": int(df["venue"].nunique()),
                "overall_avg_target": round(float(df["target_runs"].mean()), 1),
                "overall_toss_field_pct": round(
                    float((df["toss_decision"] == "field").mean()) * 100.0, 1
                ),
            },
            "team_standings": [t.model_dump() for t in teams],
            "top_venues": [v.model_dump() for v in venues],
            "season_trends": season_trends,
            "model_performance": metrics_data,
        }
        return self._set_cached(cache_key, payload)


analytics_service = AnalyticsService()
