# Model Card — IPL 2026 Match Winner Prediction Engine (`v1.0.0`)

## 1. Model Overview
- **Artifact**: `ml/artifacts/ipl_model_v1.joblib`
- **Selected Architecture**: `Logistic Regression` inside a unified `scikit-learn` `Pipeline`
- **Task**: Binary Match Outcome Classification & Calibrated Win Probability Estimation ($P(\text{Team 1 Wins})$ vs $P(\text{Team 2 Wins})$)
- **Dataset**: Cricsheet / Kaggle Historical IPL Dataset (`IPL.csv`, 1090 valid completed matches across 2008–2024 seasons)
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
| Logistic Regression ⭐ **Selected** | 54.13% | 0.5413 | 0.5758 | 0.2465 | 0.5411 |
| Random Forest  | 56.88% | 0.5766 | 0.5667 | 0.2473 | 0.5087 |
| Gradient Boosting  | 52.98% | 0.5221 | 0.5415 | 0.2502 | 0.5089 |
| XGBoost  | 53.44% | 0.5418 | 0.5713 | 0.2460 | 0.5051 |
| Hybrid Ensemble (LR + RF + GBDT/XGB)  | 57.57% | 0.5708 | 0.5725 | 0.2462 | 0.5217 |
| Legacy Notebook Baseline (Static One-Hot RF)  | 50.92% | 0.5158 | 0.5275 | 0.3041 | 0.5275 |


## 4. Top 10 Predictive Features (SHAP + Attribution Weight)
- **Second Innings Chase Factor** (`team1_is_chasing`): `10.63%` relative weight
- **Overall Win Rate Edge** (`overall_win_rate_diff`): `6.59%` relative weight
- **Elo Win Expectancy** (`elo_expected_team1`): `5.81%` relative weight
- **Venue Mastery Differential** (`venue_win_rate_diff`): `5.48%` relative weight
- **Team 1 Venue Win Rate** (`team1_venue_win_rate`): `4.89%` relative weight
- **Venue-Specific Toss & Chase Synergy** (`chasing_advantage_for_team1`): `4.85%` relative weight
- **Elo Strength Differential** (`elo_diff`): `4.79%` relative weight
- **Momentum Differential (Last 10)** (`form_diff_last10`): `4.70%` relative weight
- **Team 2 Venue Win Rate** (`team2_venue_win_rate`): `4.67%` relative weight
- **Team 1 Home Fortress Factor** (`team1_home_advantage`): `4.59%` relative weight


## 5. Explainability ("Why This Prediction?")
Every prediction made via `POST /api/predict` computes local SHAP / standardized linear-tree feature contributions for the specific matchup, breaking down how Elo rating, Head-to-Head record, Recent Form, Venue History, and Toss Decision shifted the win probability from a 50/50 baseline.

## 6. Ethical Considerations & Limitations
- **Intended Use**: Sports analytics, fan engagement, educational ML engineering demonstration, and pre-match tactical exploration.
- **Limitations**: Does not account for real-time playing XI injury news, mid-innings weather/DLS interruptions, or impact player substitutions announced at the toss.
