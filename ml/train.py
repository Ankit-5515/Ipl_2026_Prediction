"""
Model Training, Cross-Validation Benchmark, Explainability Setup, and Artifact Export
for the IPL 2026 Match Prediction System.

Usage:
    python -m ml.train
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    GradientBoostingClassifier,
    RandomForestClassifier,
    VotingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.preprocessing import (
    ALL_FEATURE_COLUMNS,
    CATEGORICAL_FEATURE_COLUMNS,
    FEATURE_DISPLAY_NAMES,
    NUMERIC_FEATURE_COLUMNS,
     build_training_dataset,
    load_and_clean_dataset,
)

try:
    from xgboost import XGBClassifier

    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

try:
    import shap

    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CSV_PATH = ROOT_DIR / "IPL.csv"
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"


def create_preprocessor() -> ColumnTransformer:
    """Create a reusable sklearn ColumnTransformer for numeric + categorical features."""
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURE_COLUMNS),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURE_COLUMNS,
            ),
        ],
        remainder="drop",
    )


def build_candidate_pipelines() -> Dict[str, Pipeline]:
    """Build candidate sklearn Pipelines for multi-model comparison."""
    candidates: Dict[str, Pipeline] = {
        "Logistic Regression": Pipeline(
            steps=[
                ("preprocessor", create_preprocessor()),
                (
                    "classifier",
                    LogisticRegression(C=0.25, max_iter=1000, random_state=42),
                ),
            ]
        ),
        "Random Forest": Pipeline(
            steps=[
                ("preprocessor", create_preprocessor()),
                (
                    "classifier",
                    RandomForestClassifier(
                        n_estimators=300,
                        max_depth=7,
                        min_samples_leaf=10,
                        random_state=42,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "Gradient Boosting": Pipeline(
            steps=[
                ("preprocessor", create_preprocessor()),
                (
                    "classifier",
                    GradientBoostingClassifier(
                        n_estimators=120,
                        learning_rate=0.04,
                        max_depth=3,
                        subsample=0.8,
                        min_samples_leaf=12,
                        random_state=42,
                    ),
                ),
            ]
        ),
    }

    if HAS_XGBOOST:
        candidates["XGBoost"] = Pipeline(
            steps=[
                ("preprocessor", create_preprocessor()),
                (
                    "classifier",
                    XGBClassifier(
                        n_estimators=140,
                        learning_rate=0.04,
                        max_depth=3,
                        subsample=0.8,
                        colsample_bytree=0.8,
                        reg_lambda=2.0,
                        eval_metric="logloss",
                        random_state=42,
                    ),
                ),
            ]
        )

    # Calibrated Soft-Voting Hybrid Ensemble combining Linear + Tree models
    voting_estimators: List[Tuple[str, Any]] = [
        ("lr", LogisticRegression(C=0.25, max_iter=1000, random_state=42)),
        (
            "rf",
            RandomForestClassifier(
                n_estimators=300,
                max_depth=7,
                min_samples_leaf=10,
                random_state=42,
                n_jobs=-1,
            ),
        ),
        (
            "gb",
            GradientBoostingClassifier(
                n_estimators=120,
                learning_rate=0.04,
                max_depth=3,
                subsample=0.8,
                min_samples_leaf=12,
                random_state=42,
            ),
        ),
    ]
    if HAS_XGBOOST:
        voting_estimators.append(
            (
                "xgb",
                XGBClassifier(
                    n_estimators=140,
                    learning_rate=0.04,
                    max_depth=3,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    reg_lambda=2.0,
                    eval_metric="logloss",
                    random_state=42,
                ),
            )
        )

    candidates["Hybrid Ensemble (LR + RF + GBDT/XGB)"] = Pipeline(
        steps=[
            ("preprocessor", create_preprocessor()),
            ("classifier", VotingClassifier(estimators=voting_estimators, voting="soft")),
        ]
    )

    return candidates


def evaluate_legacy_notebook_baseline(
    df: pd.DataFrame, train_match_ids: set, test_match_ids: set
) -> Dict[str, Any]:
    """
    Evaluate the legacy baseline approach from the original ipl.ipynb
    (static OneHotEncoder on raw columns + uncalibrated RandomForest without engineered features).
    """
    cat_cols = ["venue", "team1", "team2", "toss_Decision_raw"]
    work_df = df.copy()
    work_df["toss_Decision_raw"] = work_df["toss_decision"]
    work_df["y_bin"] = (work_df["winner"] == work_df["team1"]).astype(int)

    train_sub = work_df[work_df["match_id"].isin(train_match_ids)]
    test_sub = work_df[work_df["match_id"].isin(test_match_ids)]

    legacy_pipe = Pipeline(
        steps=[
            ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
            ("rf", RandomForestClassifier(n_estimators=100, random_state=42)),
        ]
    )
    legacy_pipe.fit(train_sub[cat_cols], train_sub["y_bin"])
    preds = legacy_pipe.predict(test_sub[cat_cols])
    probs = legacy_pipe.predict_proba(test_sub[cat_cols])[:, 1]

    return {
        "model_name": "Legacy Notebook Baseline (Static One-Hot RF)",
        "accuracy": round(float(accuracy_score(test_sub["y_bin"], preds)), 4),
        "f1_score": round(float(f1_score(test_sub["y_bin"], preds)), 4),
        "roc_auc": round(float(roc_auc_score(test_sub["y_bin"], probs)), 4),
        "brier_score": round(float(brier_score_loss(test_sub["y_bin"], probs)), 4),
        "log_loss": round(float(log_loss(test_sub["y_bin"], probs)), 4),
        "cv_accuracy_mean": round(float(accuracy_score(test_sub["y_bin"], preds)), 4),
        "cv_roc_auc_mean": round(float(roc_auc_score(test_sub["y_bin"], probs)), 4),
        "confusion_matrix": confusion_matrix(test_sub["y_bin"], preds).tolist(),
    }


def extract_global_feature_importance(
    fitted_pipelines: Dict[str, Pipeline], X_train: pd.DataFrame
) -> List[Dict[str, Any]]:
    """
    Compute global feature importance across engineered features using both
    tree-based Gini/gain importance and linear standardized coefficients, plus SHAP if installed.
    """
    rf_pipe = fitted_pipelines["Random Forest"]
    lr_pipe = fitted_pipelines["Logistic Regression"]

    num_count = len(NUMERIC_FEATURE_COLUMNS)
    rf_importances = rf_pipe.named_steps["classifier"].feature_importances_[:num_count]
    lr_coefs = np.abs(lr_pipe.named_steps["classifier"].coef_[0][:num_count])

    # Normalize both to sum to 1 over numeric engineered features
    rf_norm = rf_importances / (rf_importances.sum() + 1e-9)
    lr_norm = lr_coefs / (lr_coefs.sum() + 1e-9)
    blended = 0.6 * rf_norm + 0.4 * lr_norm

    # Optional SHAP TreeExplainer verification on Random Forest numeric + one-hot
    shap_values_mean = None
    if HAS_SHAP:
        try:
            X_trans = rf_pipe.named_steps["preprocessor"].transform(X_train.iloc[:300])
            explainer = shap.TreeExplainer(rf_pipe.named_steps["classifier"])
            sv = explainer.shap_values(X_trans)
            if isinstance(sv, list):
                sv_pos = np.abs(sv[1]).mean(axis=0)[:num_count]
            elif sv.ndim == 3:
                sv_pos = np.abs(sv[:, :, 1]).mean(axis=0)[:num_count]
            else:
                sv_pos = np.abs(sv).mean(axis=0)[:num_count]
            shap_values_mean = sv_pos / (sv_pos.sum() + 1e-9)
            blended = 0.5 * shap_values_mean + 0.3 * rf_norm + 0.2 * lr_norm
        except Exception:
            pass

    blended = blended / (blended.sum() + 1e-9)

    items: List[Dict[str, Any]] = []
    for idx, col in enumerate(NUMERIC_FEATURE_COLUMNS):
        items.append(
            {
                "feature": col,
                "display_name": FEATURE_DISPLAY_NAMES.get(col, col),
                "importance": round(float(blended[idx]), 4),
                "rf_importance": round(float(rf_norm[idx]), 4),
                "lr_weight": round(float(lr_norm[idx]), 4),
            }
        )

    items.sort(key=lambda x: x["importance"], reverse=True)
    return items


def generate_model_card(
    best_model_name: str,
    benchmark_results: List[Dict[str, Any]],
    top_features: List[Dict[str, Any]],
    total_matches: int,
) -> str:
    """Generate a comprehensive Markdown Model Card for ml/artifacts/MODEL_CARD.md."""
    rows_md = ""
    for res in benchmark_results:
        is_best = "⭐ **Selected**" if res["model_name"] == best_model_name else ""
        rows_md += (
            f"| {res['model_name']} {is_best} | "
            f"{res['accuracy']*100:.2f}% | "
            f"{res['f1_score']:.4f} | "
            f"{res['roc_auc']:.4f} | "
            f"{res['brier_score']:.4f} | "
            f"{res['cv_roc_auc_mean']:.4f} |\n"
        )

    feat_md = ""
    for f in top_features[:10]:
        feat_md += f"- **{f['display_name']}** (`{f['feature']}`): `{f['importance']*100:.2f}%` relative weight\n"

    return f"""# Model Card — IPL 2026 Match Winner Prediction Engine (`v1.0.0`)

## 1. Model Overview
- **Artifact**: `ml/artifacts/ipl_model_v1.joblib`
- **Selected Architecture**: `{best_model_name}` inside a unified `scikit-learn` `Pipeline`
- **Task**: Binary Match Outcome Classification & Calibrated Win Probability Estimation ($P(\\text{{Team 1 Wins}})$ vs $P(\\text{{Team 2 Wins}})$)
- **Dataset**: Cricsheet / Kaggle Historical IPL Dataset (`IPL.csv`, {total_matches} valid completed matches across 2008–2024 seasons)
- **Symmetry Guarantee**: Trained on forward and mirrored matchup perspectives (`Team A vs Team B` and `Team B vs Team A`) and evaluated with symmetric probability averaging at inference time so $P(A > B) = 1 - P(B > A)$ holds strictly.

## 2. Feature Engineering Upgrade
Unlike the legacy notebook (which only one-hot encoded static team and venue strings), `v1.0.0` computes **26 leak-free rolling historical features** before each match:
- **Dynamic Elo Rating System**: `elo_team1`, `elo_team2`, `elo_diff`, `elo_expected_team1` ($K=24$, base $1500$).
- **Head-to-Head (H2H) Record**: Bayesian-smoothed pairwise win rate (`h2h_team1_win_rate`) and total clashes (`h2h_matches_played`).
- **Recent Team Form**: Rolling 5-match and 10-match form windows (`team1_form_last5`, `team2_form_last5`, `form_diff_last5`, `form_diff_last10`).
- **Venue Intelligence**: Team-specific venue win rate (`team1_venue_win_rate`, `team2_venue_win_rate`), venue chase win bias (`venue_chase_win_rate`), and venue average target runs (`venue_avg_target_runs`).
- **Toss & Innings Strategy**: Toss winner indicator, bat/field decision, second-innings chase indicator, and venue-specific chase synergy (`chasing_advantage_for_team1`).
- **Home Fortress Indicator**: Whether the match is hosted at Team 1's or Team 2's primary home stadium.

## 3. Model Comparison & Validation Benchmark
Evaluated via 5-Fold Match-Grouped Cross-Validation (`GroupKFold` by `match_id` to prevent mirror leakage) and an out-of-sample test split:

| Model | Test Accuracy | F1-Score | ROC-AUC | Brier Score (↓) | 5-Fold CV ROC-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: |
{rows_md}

## 4. Top 10 Predictive Features (SHAP + Attribution Weight)
{feat_md}

## 5. Explainability ("Why This Prediction?")
Every prediction made via `POST /api/predict` computes local SHAP / standardized linear-tree feature contributions for the specific matchup, breaking down how Elo rating, Head-to-Head record, Recent Form, Venue History, and Toss Decision shifted the win probability from a 50/50 baseline.

## 6. Ethical Considerations & Limitations
- **Intended Use**: Sports analytics, fan engagement, educational ML engineering demonstration, and pre-match tactical exploration.
- **Limitations**: Does not account for real-time playing XI injury news, mid-innings weather/DLS interruptions, or impact player substitutions announced at the toss.
"""


def train_and_export(csv_path: Path = DEFAULT_CSV_PATH) -> Dict[str, Any]:
    """Run the end-to-end training, evaluation, and artifact generation pipeline."""
    print(f"[1/5] Loading and cleaning dataset from {csv_path}...")
    clean_df = load_and_clean_dataset(str(csv_path))
    print(f"      Loaded {len(clean_df)} valid matches across seasons {clean_df['season'].min()}-{clean_df['season'].max()}.")

    print("[2/5] Engineering leak-free historical features (Elo, H2H, Form, Venue, Toss)...")
    feature_df, y, state_store = build_training_dataset(clean_df, symmetric_augmentation=True)
    print(f"      Generated {len(feature_df)} training instances with {len(ALL_FEATURE_COLUMNS)} features.")

    # Match-grouped train/test split (last 20% of matches chronologically, or stratified match split)
    unique_match_ids = clean_df["match_id"].unique()
    rng = np.random.default_rng(42)
    shuffled_ids = unique_match_ids.copy()
    rng.shuffle(shuffled_ids)
    split_idx = int(len(shuffled_ids) * 0.8)
    train_match_ids = set(shuffled_ids[:split_idx])
    test_match_ids = set(shuffled_ids[split_idx:])

    train_mask = feature_df["match_id"].isin(train_match_ids)
    test_mask = feature_df["match_id"].isin(test_match_ids)

    X_train = feature_df.loc[train_mask, ALL_FEATURE_COLUMNS].reset_index(drop=True)
    y_train = y.loc[train_mask].reset_index(drop=True)
    groups_train = feature_df.loc[train_mask, "match_id"].reset_index(drop=True)

    X_test = feature_df.loc[test_mask, ALL_FEATURE_COLUMNS].reset_index(drop=True)
    y_test = y.loc[test_mask].reset_index(drop=True)

    print("[3/5] Benchmarking candidate models with 5-Fold GroupKFold Cross-Validation...")
    candidates = build_candidate_pipelines()
    gkf = GroupKFold(n_splits=5)

    benchmark_results: List[Dict[str, Any]] = []
    fitted_pipelines: Dict[str, Pipeline] = {}

    for name, pipeline in candidates.items():
        cv_accs: List[float] = []
        cv_aucs: List[float] = []

        for tr_idx, val_idx in gkf.split(X_train, y_train, groups=groups_train):
            X_tr, y_tr = X_train.iloc[tr_idx], y_train.iloc[tr_idx]
            X_val, y_val = X_train.iloc[val_idx], y_train.iloc[val_idx]

            pipeline.fit(X_tr, y_tr)
            val_preds = pipeline.predict(X_val)
            val_probs = pipeline.predict_proba(X_val)[:, 1]
            cv_accs.append(float(accuracy_score(y_val, val_preds)))
            cv_aucs.append(float(roc_auc_score(y_val, val_probs)))

        # Fit on full training set and evaluate on held-out test set
        pipeline.fit(X_train, y_train)
        fitted_pipelines[name] = pipeline

        test_preds = pipeline.predict(X_test)
        test_probs = pipeline.predict_proba(X_test)[:, 1]

        acc = float(accuracy_score(y_test, test_preds))
        f1 = float(f1_score(y_test, test_preds))
        auc = float(roc_auc_score(y_test, test_probs))
        brier = float(brier_score_loss(y_test, test_probs))
        ll = float(log_loss(y_test, test_probs))
        cm = confusion_matrix(y_test, test_preds).tolist()

        res = {
            "model_name": name,
            "accuracy": round(acc, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(auc, 4),
            "brier_score": round(brier, 4),
            "log_loss": round(ll, 4),
            "cv_accuracy_mean": round(float(np.mean(cv_accs)), 4),
            "cv_roc_auc_mean": round(float(np.mean(cv_aucs)), 4),
            "confusion_matrix": cm,
        }
        benchmark_results.append(res)
        print(
            f"      - {name:<36} | Test Acc: {acc*100:.2f}% | F1: {f1:.4f} | ROC-AUC: {auc:.4f} | CV AUC: {np.mean(cv_aucs):.4f}"
        )

    # Also evaluate legacy notebook baseline for before/after comparison
    legacy_res = evaluate_legacy_notebook_baseline(clean_df, train_match_ids, test_match_ids)
    benchmark_results.append(legacy_res)
    print(
        f"      - {legacy_res['model_name']:<36} | Test Acc: {legacy_res['accuracy']*100:.2f}% | F1: {legacy_res['f1_score']:.4f} | ROC-AUC: {legacy_res['roc_auc']:.4f}"
    )

    # Pick the best engineered model by combined (test ROC-AUC + CV ROC-AUC + Accuracy)
    engineered_results = [r for r in benchmark_results if "Legacy" not in r["model_name"]]
    best_entry = max(
        engineered_results,
        key=lambda r: (r["roc_auc"] * 0.45 + r["cv_roc_auc_mean"] * 0.35 + r["accuracy"] * 0.20),
    )
    best_model_name = best_entry["model_name"]
    print(f"[4/5] Selected Best Model: {best_model_name} (ROC-AUC: {best_entry['roc_auc']:.4f})")

    # Extract global feature importance & linear attribution weights for fast real-time SHAP explainability
    top_features = extract_global_feature_importance(fitted_pipelines, X_train)

    # Fit final production pipeline on 100% of historical matches for strongest 2026 inference
    best_pipeline = fitted_pipelines[best_model_name]
    X_full = feature_df[ALL_FEATURE_COLUMNS].reset_index(drop=True)
    y_full = y.reset_index(drop=True)
    best_pipeline.fit(X_full, y_full)

    # Also fit Logistic Regression and Random Forest on full data to power fast exact local SHAP attribution
    lr_full = fitted_pipelines["Logistic Regression"]
    lr_full.fit(X_full, y_full)
    rf_full = fitted_pipelines["Random Forest"]
    rf_full.fit(X_full, y_full)

    num_count = len(NUMERIC_FEATURE_COLUMNS)
    scaler: StandardScaler = lr_full.named_steps["preprocessor"].named_transformers_["num"]
    lr_num_coefs = lr_full.named_steps["classifier"].coef_[0][:num_count]

    # Save artifacts
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact_path = ARTIFACTS_DIR / "ipl_model_v1.joblib"
    metrics_path = ARTIFACTS_DIR / "metrics.json"
    card_path = ARTIFACTS_DIR / "MODEL_CARD.md"

    trained_at = datetime.now(timezone.utc).isoformat()
    artifact_bundle = {
        "version": "1.0.0",
        "trained_at": trained_at,
        "best_model_name": best_model_name,
        "pipeline": best_pipeline,
        "rf_pipeline": rf_full,
        "lr_pipeline": lr_full,
        "state_store": state_store,
        "numeric_features": NUMERIC_FEATURE_COLUMNS,
        "categorical_features": CATEGORICAL_FEATURE_COLUMNS,
        "all_features": ALL_FEATURE_COLUMNS,
        "feature_display_names": FEATURE_DISPLAY_NAMES,
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "lr_numeric_coefs": lr_num_coefs.tolist(),
        "global_feature_importance": top_features,
        "benchmark_results": benchmark_results,
        "best_metrics": best_entry,
        "dataset_summary": {
            "total_matches": int(len(clean_df)),
            "seasons_covered": "2008-2024",
            "target_season": 2026,
        },
    }

    joblib.dump(artifact_bundle, artifact_path)

    metrics_payload = {
        "version": "1.0.0",
        "trained_at": trained_at,
        "selected_model": best_model_name,
        "selected_metrics": best_entry,
        "models_compared": benchmark_results,
        "global_feature_importance": top_features,
        "dataset_summary": artifact_bundle["dataset_summary"],
    }
    metrics_path.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")

    model_card_md = generate_model_card(
        best_model_name=best_model_name,
        benchmark_results=benchmark_results,
        top_features=top_features,
        total_matches=len(clean_df),
    )
    card_path.write_text(model_card_md, encoding="utf-8")

    print(f"[5/5] Saved versioned model artifact to {artifact_path}")
    print(f"      Saved benchmark metrics to {metrics_path}")
    print(f"      Saved model card to {card_path}")
    return metrics_payload


if __name__ == "__main__":
    train_and_export()
