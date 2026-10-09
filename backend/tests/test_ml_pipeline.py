"""Unit tests for ML preprocessing, leak-free feature engineering, and model inference."""

from __future__ import annotations

from pathlib import Path

from backend.app.schemas import PredictRequest
from backend.app.services.predictor import predictor_service
from ml.preprocessing import (
    ALL_FEATURE_COLUMNS,
    HistoricalStateStore,
    build_training_dataset,
    canonicalize_team,
    canonicalize_venue,
    load_and_clean_dataset,
)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CSV_PATH = ROOT_DIR / "IPL.csv"


def test_canonical_entity_normalization() -> None:
    """Verify historical franchise and venue rebrands map to canonical names."""
    assert canonicalize_team("Royal Challengers Bangalore") == "Royal Challengers Bengaluru"
    assert canonicalize_team("Kings XI Punjab") == "Punjab Kings"
    assert canonicalize_team("Delhi Daredevils") == "Delhi Capitals"
    assert canonicalize_team("Rising Pune Supergiants") == "Rising Pune Supergiant"
    assert canonicalize_venue("Bangalore") == "Bengaluru"
    assert canonicalize_venue("Chandigarh") == "Mohali"


def test_dataset_cleaning_and_seasons() -> None:
    """Verify dataset loads 1,090 valid completed matches across seasons 2008-2024."""
    df = load_and_clean_dataset(str(CSV_PATH))
    assert len(df) == 1090
    assert df["season"].min() == 2008
    assert df["season"].max() == 2024
    assert df["venue"].isna().sum() == 0
    assert df["winner"].isna().sum() == 0


def test_leak_free_feature_generation() -> None:
    """Verify sequential feature store generates all expected numeric and categorical features."""
    df = load_and_clean_dataset(str(CSV_PATH)).iloc[:50]
    X_df, y, store = build_training_dataset(df, symmetric_augmentation=True)
    assert len(X_df) == 100
    assert len(y) == 100
    for col in ALL_FEATURE_COLUMNS:
        assert col in X_df.columns
    assert store.get_elo("Chennai Super Kings") != 1500.0


def test_prediction_order_symmetry() -> None:
    """
    Verify P(CSK beats MI) == 100 - P(MI beats CSK) when team1 and team2 are swapped
    under identical venue and toss conditions.
    """
    req_forward = PredictRequest(
        team1="Chennai Super Kings",
        team2="Mumbai Indians",
        venue="Chennai",
        toss_winner="Chennai Super Kings",
        toss_decision="field",
        season=2026,
    )
    req_reverse = PredictRequest(
        team1="Mumbai Indians",
        team2="Chennai Super Kings",
        venue="Chennai",
        toss_winner="Chennai Super Kings",
        toss_decision="field",
        season=2026,
    )

    res_fwd = predictor_service.predict_match(req_forward)
    res_rev = predictor_service.predict_match(req_reverse)

    assert abs(res_fwd.team1_win_prob - res_rev.team2_win_prob) <= 0.2
    assert abs((res_fwd.team1_win_prob + res_fwd.team2_win_prob) - 100.0) <= 0.1
    assert res_fwd.predicted_winner == res_rev.predicted_winner
    assert len(res_fwd.explanations) >= 5
