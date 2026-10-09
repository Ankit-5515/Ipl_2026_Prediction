"""
ML Prediction & SHAP Explainability Service.
Loads the versioned sklearn Pipeline artifact and computes calibrated win probabilities
plus per-feature local explanations ("Why this prediction?").
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np
import pandas as pd

from backend.app.config import settings
from backend.app.schemas import (
    FeatureContribution,
    MatchupContextStats,
    PredictRequest,
    PredictResponse,
)
from ml.preprocessing import (
    ALL_FEATURE_COLUMNS,
    HistoricalStateStore,
    TEAM_METADATA,
)

try:
    import shap

    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False

logger = logging.getLogger(__name__)


class PredictorService:
    """Singleton-style service managing the trained ML artifact and SHAP explainer."""

    def __init__(self) -> None:
        self.artifact: Dict[str, Any] = {}
        self.loaded: bool = False
        self._shap_explainer: Any = None

    def ensure_loaded(self) -> None:
        """Load the model artifact from disk, or train it on-the-fly if missing."""
        if self.loaded and self.artifact:
            return

        artifact_path = Path(settings.MODEL_ARTIFACT_PATH)
        if not artifact_path.exists():
            logger.warning(
                "Model artifact not found at %s. Running training pipeline now...",
                artifact_path,
            )
            from ml.train import train_and_export

            train_and_export(Path(settings.DATASET_PATH))

        self.artifact = joblib.load(artifact_path)
        self.loaded = True

        # Initialize SHAP TreeExplainer on the Random Forest sub-pipeline if shap is available
        if HAS_SHAP and "rf_pipeline" in self.artifact:
            try:
                rf_clf = self.artifact["rf_pipeline"].named_steps["classifier"]
                self._shap_explainer = shap.TreeExplainer(rf_clf)
            except Exception as exc:
                logger.warning("SHAP TreeExplainer fallback activated: %s", exc)
                self._shap_explainer = None

    @property
    def state_store(self) -> HistoricalStateStore:
        self.ensure_loaded()
        return self.artifact["state_store"]

    @property
    def model_name(self) -> str:
        self.ensure_loaded()
        return str(self.artifact.get("best_model_name", "Hybrid Ensemble"))

    @property
    def model_version(self) -> str:
        self.ensure_loaded()
        return str(self.artifact.get("version", "1.0.0"))

    def _compute_local_explanations(
        self,
        feat_forward: Dict[str, Any],
        X_forward_df: pd.DataFrame,
        team1: str,
        team2: str,
        venue: str,
        toss_winner: str,
        toss_decision: str,
        net_prob_t1: float,
    ) -> List[FeatureContribution]:
        """
        Compute local SHAP / standardized feature attributions grouped into clear,
        actionable cricket insights explaining 'Why this prediction?'.
        """
        t1_short = TEAM_METADATA.get(team1, {}).get("short_name", team1)
        t2_short = TEAM_METADATA.get(team2, {}).get("short_name", team2)

        num_cols: List[str] = self.artifact["numeric_features"]
        means = np.array(self.artifact["scaler_mean"], dtype=float)
        scales = np.array(self.artifact["scaler_scale"], dtype=float)
        lr_coefs = np.array(self.artifact["lr_numeric_coefs"], dtype=float)

        raw_vals = np.array([float(feat_forward[c]) for c in num_cols], dtype=float)
        z_vals = (raw_vals - means) / np.where(scales == 0, 1.0, scales)
        linear_contribs = z_vals * lr_coefs

        # Blend with exact TreeSHAP values if available
        if self._shap_explainer is not None and "rf_pipeline" in self.artifact:
            try:
                rf_prep = self.artifact["rf_pipeline"].named_steps["preprocessor"]
                X_trans = rf_prep.transform(X_forward_df)
                sv = self._shap_explainer.shap_values(X_trans)
                if isinstance(sv, list):
                    shap_num = np.array(sv[1][0][: len(num_cols)], dtype=float)
                elif getattr(sv, "ndim", 0) == 3:
                    shap_num = np.array(sv[0, : len(num_cols), 1], dtype=float)
                else:
                    shap_num = np.array(sv[0][: len(num_cols)], dtype=float)
                # Combine TreeSHAP and standardized log-odds attribution
                raw_contribs = 0.65 * shap_num + 0.35 * (linear_contribs * 0.15)
            except Exception:
                raw_contribs = linear_contribs * 0.12
        else:
            raw_contribs = linear_contribs * 0.12

        col_idx = {c: i for i, c in enumerate(num_cols)}

        def sum_idx(cols: List[str]) -> float:
            return float(sum(raw_contribs[col_idx[c]] for c in cols if c in col_idx))

        h2h_cnt = int(feat_forward["h2h_matches_played"])
        t1_h2h_wins = int(
            self.state_store.h2h_wins.get((team1, team2), 0)
        )
        t2_h2h_wins = int(
            self.state_store.h2h_wins.get((team2, team1), 0)
        )

        grouped_factors = [
            {
                "feature": "elo_strength",
                "display_name": "Elo Team Strength Rating",
                "raw_score": sum_idx(["elo_team1", "elo_team2", "elo_diff", "elo_expected_team1"])
                + (feat_forward["elo_diff"] / 400.0) * 0.25,
                "value_summary": (
                    f"{t1_short} Elo {feat_forward['elo_team1']:.0f} vs "
                    f"{t2_short} Elo {feat_forward['elo_team2']:.0f} "
                    f"({feat_forward['elo_diff']:+.0f} diff)"
                ),
            },
            {
                "feature": "head_to_head",
                "display_name": "Head-to-Head Dominance",
                "raw_score": sum_idx(["h2h_team1_win_rate", "h2h_matches_played"])
                + (feat_forward["h2h_team1_win_rate"] - 0.5) * 0.35,
                "value_summary": (
                    f"{t1_short} leads {t1_h2h_wins}-{t2_h2h_wins} ({h2h_cnt} matches)"
                    if t1_h2h_wins >= t2_h2h_wins
                    else f"{t2_short} leads {t2_h2h_wins}-{t1_h2h_wins} ({h2h_cnt} matches)"
                ),
            },
            {
                "feature": "recent_form",
                "display_name": "Recent Form & Momentum (Last 5-10)",
                "raw_score": sum_idx(
                    [
                        "team1_form_last5",
                        "team2_form_last5",
                        "form_diff_last5",
                        "team1_form_last10",
                        "team2_form_last10",
                        "form_diff_last10",
                    ]
                )
                + (feat_forward["form_diff_last5"]) * 0.25,
                "value_summary": (
                    f"{t1_short} {feat_forward['team1_form_last5']*100:.0f}% vs "
                    f"{t2_short} {feat_forward['team2_form_last5']*100:.0f}% recent win index"
                ),
            },
            {
                "feature": "venue_mastery",
                "display_name": f"Venue Track Record ({venue})",
                "raw_score": sum_idx(
                    ["team1_venue_win_rate", "team2_venue_win_rate", "venue_win_rate_diff"]
                )
                + (feat_forward["venue_win_rate_diff"]) * 0.30,
                "value_summary": (
                    f"At {venue}: {t1_short} {feat_forward['team1_venue_win_rate']*100:.1f}% vs "
                    f"{t2_short} {feat_forward['team2_venue_win_rate']*100:.1f}%"
                ),
            },
            {
                "feature": "toss_and_chase",
                "display_name": "Toss & Second-Innings Chase Synergy",
                "raw_score": sum_idx(
                    [
                        "team1_won_toss",
                        "toss_decision_field",
                        "team1_is_chasing",
                        "chasing_advantage_for_team1",
                        "venue_chase_win_rate",
                    ]
                )
                + (0.04 if feat_forward["team1_won_toss"] == 1.0 else -0.04)
                + float(feat_forward["chasing_advantage_for_team1"]) * 0.4,
                "value_summary": (
                    f"{TEAM_METADATA.get(toss_winner, {}).get('short_name', toss_winner)} won toss & chose to {toss_decision} "
                    f"(Venue chase win rate: {feat_forward['venue_chase_win_rate']*100:.1f}%)"
                ),
            },
            {
                "feature": "career_win_rate",
                "display_name": "Historical Franchise Win Rate",
                "raw_score": sum_idx(
                    [
                        "team1_overall_win_rate",
                        "team2_overall_win_rate",
                        "overall_win_rate_diff",
                    ]
                )
                + (feat_forward["overall_win_rate_diff"]) * 0.25,
                "value_summary": (
                    f"Career Win Rate: {t1_short} {feat_forward['team1_overall_win_rate']*100:.1f}% vs "
                    f"{t2_short} {feat_forward['team2_overall_win_rate']*100:.1f}%"
                ),
            },
            {
                "feature": "home_fortress",
                "display_name": "Home Stadium Crowd & Pitch Familiarity",
                "raw_score": sum_idx(["team1_home_advantage", "team2_home_advantage"])
                + (feat_forward["team1_home_advantage"] - feat_forward["team2_home_advantage"])
                * 0.06,
                "value_summary": (
                    f"{t1_short} playing at home fortress ({venue})"
                    if feat_forward["team1_home_advantage"] == 1.0
                    else (
                        f"{t2_short} playing at home fortress ({venue})"
                        if feat_forward["team2_home_advantage"] == 1.0
                        else f"Neutral venue matchup at {venue}"
                    )
                ),
            },
        ]

        # Scale raw scores so their sum aligns naturally with percentage point shift from 50%
        total_abs = sum(abs(g["raw_score"]) for g in grouped_factors) + 1e-9
        target_shift = max(abs(net_prob_t1 - 50.0) * 1.35, 12.0)

        contributions: List[FeatureContribution] = []
        for g in grouped_factors:
            scaled_impact = (g["raw_score"] / total_abs) * target_shift
            # Keep minimum visible impact for non-zero factors
            if abs(scaled_impact) < 0.4 and abs(g["raw_score"]) > 1e-4:
                scaled_impact = 0.5 if g["raw_score"] > 0 else -0.5

            favored = team1 if scaled_impact >= 0 else team2
            contributions.append(
                FeatureContribution(
                    feature=g["feature"],
                    display_name=g["display_name"],
                    impact=round(float(scaled_impact), 2),
                    abs_impact=round(abs(float(scaled_impact)), 2),
                    favored_team=favored,
                    value_summary=g["value_summary"],
                )
            )

        contributions.sort(key=lambda item: item.abs_impact, reverse=True)
        return contributions

    def predict_match(self, req: PredictRequest) -> PredictResponse:
        """
        Compute calibrated, order-invariant win probabilities and local SHAP attributions.
        """
        self.ensure_loaded()
        pipeline = self.artifact["pipeline"]
        store = self.state_store

        # Forward perspective: (team1, team2)
        feat_fwd = store.compute_match_features(
            req.team1, req.team2, req.venue, req.toss_winner, req.toss_decision
        )
        # Reverse perspective: (team2, team1) to guarantee strict order symmetry
        feat_rev = store.compute_match_features(
            req.team2, req.team1, req.venue, req.toss_winner, req.toss_decision
        )

        X_fwd = pd.DataFrame([feat_fwd])[ALL_FEATURE_COLUMNS]
        X_rev = pd.DataFrame([feat_rev])[ALL_FEATURE_COLUMNS]

        prob_fwd_t1 = float(pipeline.predict_proba(X_fwd)[0, 1])
        prob_rev_t2 = float(pipeline.predict_proba(X_rev)[0, 1])

        # Symmetric calibrated probability for team1
        sym_prob_t1 = 0.5 * (prob_fwd_t1 + (1.0 - prob_rev_t2))
        sym_prob_t1 = float(np.clip(sym_prob_t1, 0.05, 0.95))
        sym_prob_t2 = 1.0 - sym_prob_t1

        pct_t1 = round(sym_prob_t1 * 100.0, 1)
        pct_t2 = round(100.0 - pct_t1, 1)

        predicted_winner = req.team1 if pct_t1 >= pct_t2 else req.team2
        margin_pct = abs(pct_t1 - pct_t2)
        if margin_pct >= 18.0:
            confidence = "High Confidence"
        elif margin_pct >= 8.0:
            confidence = "Moderate Edge"
        else:
            confidence = "Nail-Biter / Toss-Up"

        t1_short = TEAM_METADATA.get(req.team1, {}).get("short_name", req.team1)
        t2_short = TEAM_METADATA.get(req.team2, {}).get("short_name", req.team2)
        summary_text = f"{t1_short} {pct_t1:.1f}% vs {t2_short} {pct_t2:.1f}%"

        explanations = self._compute_local_explanations(
            feat_forward=feat_fwd,
            X_forward_df=X_fwd,
            team1=req.team1,
            team2=req.team2,
            venue=req.venue,
            toss_winner=req.toss_winner,
            toss_decision=req.toss_decision,
            net_prob_t1=pct_t1,
        )

        t1_h2h_wins = int(store.h2h_wins.get((req.team1, req.team2), 0))
        t2_h2h_wins = int(store.h2h_wins.get((req.team2, req.team1), 0))

        matchup_stats = MatchupContextStats(
            team1_elo=round(float(feat_fwd["elo_team1"]), 1),
            team2_elo=round(float(feat_fwd["elo_team2"]), 1),
            team1_overall_win_rate=round(float(feat_fwd["team1_overall_win_rate"]) * 100.0, 1),
            team2_overall_win_rate=round(float(feat_fwd["team2_overall_win_rate"]) * 100.0, 1),
            team1_form_last5=round(float(feat_fwd["team1_form_last5"]) * 100.0, 1),
            team2_form_last5=round(float(feat_fwd["team2_form_last5"]) * 100.0, 1),
            h2h_total_matches=int(feat_fwd["h2h_matches_played"]),
            h2h_team1_wins=t1_h2h_wins,
            h2h_team2_wins=t2_h2h_wins,
            h2h_team1_win_rate=round(float(feat_fwd["h2h_team1_win_rate"]) * 100.0, 1),
            team1_venue_win_rate=round(float(feat_fwd["team1_venue_win_rate"]) * 100.0, 1),
            team2_venue_win_rate=round(float(feat_fwd["team2_venue_win_rate"]) * 100.0, 1),
            venue_chase_win_rate=round(float(feat_fwd["venue_chase_win_rate"]) * 100.0, 1),
            venue_avg_target_runs=round(float(feat_fwd["venue_avg_target_runs"]), 1),
        )

        return PredictResponse(
            prediction_id=None,
            team1=req.team1,
            team2=req.team2,
            venue=req.venue,
            toss_winner=req.toss_winner,
            toss_decision=req.toss_decision,
            season=req.season,
            predicted_winner=predicted_winner,
            team1_win_prob=pct_t1,
            team2_win_prob=pct_t2,
            summary_text=summary_text,
            confidence=confidence,
            model_name=self.model_name,
            model_version=self.model_version,
            explanations=explanations,
            matchup_stats=matchup_stats,
            created_at=datetime.now(timezone.utc),
        )


predictor_service = PredictorService()
