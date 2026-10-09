"""
Preprocessing, canonical normalization, season reconstruction, and leak-free
rolling feature engineering for the IPL Match Prediction pipeline.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Canonical mapping for rebranded IPL franchises
TEAM_CANONICAL_MAP: Dict[str, str] = {
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Royal Challengers Bengaluru": "Royal Challengers Bengaluru",
    "Kings XI Punjab": "Punjab Kings",
    "Punjab Kings": "Punjab Kings",
    "Delhi Daredevils": "Delhi Capitals",
    "Delhi Capitals": "Delhi Capitals",
    "Rising Pune Supergiants": "Rising Pune Supergiant",
    "Rising Pune Supergiant": "Rising Pune Supergiant",
    "Mumbai Indians": "Mumbai Indians",
    "Chennai Super Kings": "Chennai Super Kings",
    "Kolkata Knight Riders": "Kolkata Knight Riders",
    "Rajasthan Royals": "Rajasthan Royals",
    "Sunrisers Hyderabad": "Sunrisers Hyderabad",
    "Gujarat Titans": "Gujarat Titans",
    "Lucknow Super Giants": "Lucknow Super Giants",
    "Deccan Chargers": "Deccan Chargers",
    "Gujarat Lions": "Gujarat Lions",
    "Pune Warriors": "Pune Warriors",
    "Kochi Tuskers Kerala": "Kochi Tuskers Kerala",
}

# Active 10 franchises for IPL 2026
ACTIVE_IPL_TEAMS: List[str] = [
    "Chennai Super Kings",
    "Delhi Capitals",
    "Gujarat Titans",
    "Kolkata Knight Riders",
    "Lucknow Super Giants",
    "Mumbai Indians",
    "Punjab Kings",
    "Rajasthan Royals",
    "Royal Challengers Bengaluru",
    "Sunrisers Hyderabad",
]

# Rich team metadata for API & Frontend consumption
TEAM_METADATA: Dict[str, Dict[str, Any]] = {
    "Chennai Super Kings": {
        "short_name": "CSK",
        "primary_color": "#FACC15",
        "secondary_color": "#1E3A8A",
        "home_venue": "Chennai",
        "titles": [2010, 2011, 2018, 2021, 2023],
        "active": True,
    },
    "Mumbai Indians": {
        "short_name": "MI",
        "primary_color": "#3B82F6",
        "secondary_color": "#D97706",
        "home_venue": "Mumbai",
        "titles": [2013, 2015, 2017, 2019, 2020],
        "active": True,
    },
    "Royal Challengers Bengaluru": {
        "short_name": "RCB",
        "primary_color": "#EF4444",
        "secondary_color": "#1F2937",
        "home_venue": "Bengaluru",
        "titles": [],
        "active": True,
    },
    "Kolkata Knight Riders": {
        "short_name": "KKR",
        "primary_color": "#8B5CF6",
        "secondary_color": "#F59E0B",
        "home_venue": "Kolkata",
        "titles": [2012, 2014, 2024],
        "active": True,
    },
    "Sunrisers Hyderabad": {
        "short_name": "SRH",
        "primary_color": "#F97316",
        "secondary_color": "#111827",
        "home_venue": "Hyderabad",
        "titles": [2016],
        "active": True,
    },
    "Rajasthan Royals": {
        "short_name": "RR",
        "primary_color": "#EC4899",
        "secondary_color": "#1E40AF",
        "home_venue": "Jaipur",
        "titles": [2008],
        "active": True,
    },
    "Delhi Capitals": {
        "short_name": "DC",
        "primary_color": "#2563EB",
        "secondary_color": "#DC2626",
        "home_venue": "Delhi",
        "titles": [],
        "active": True,
    },
    "Punjab Kings": {
        "short_name": "PBKS",
        "primary_color": "#DC2626",
        "secondary_color": "#FBBF24",
        "home_venue": "Mohali",
        "titles": [],
        "active": True,
    },
    "Gujarat Titans": {
        "short_name": "GT",
        "primary_color": "#0EA5E9",
        "secondary_color": "#FDE047",
        "home_venue": "Ahmedabad",
        "titles": [2022],
        "active": True,
    },
    "Lucknow Super Giants": {
        "short_name": "LSG",
        "primary_color": "#06B6D4",
        "secondary_color": "#F97316",
        "home_venue": "Lucknow",
        "titles": [],
        "active": True,
    },
    "Deccan Chargers": {
        "short_name": "DCH",
        "primary_color": "#64748B",
        "secondary_color": "#94A3B8",
        "home_venue": "Hyderabad",
        "titles": [2009],
        "active": False,
    },
    "Gujarat Lions": {
        "short_name": "GL",
        "primary_color": "#FB923C",
        "secondary_color": "#FDE047",
        "home_venue": "Rajkot",
        "titles": [],
        "active": False,
    },
    "Rising Pune Supergiant": {
        "short_name": "RPS",
        "primary_color": "#A855F7",
        "secondary_color": "#EC4899",
        "home_venue": "Pune",
        "titles": [],
        "active": False,
    },
    "Pune Warriors": {
        "short_name": "PWI",
        "primary_color": "#14B8A6",
        "secondary_color": "#0F172A",
        "home_venue": "Pune",
        "titles": [],
        "active": False,
    },
    "Kochi Tuskers Kerala": {
        "short_name": "KTK",
        "primary_color": "#F59E0B",
        "secondary_color": "#7C3AED",
        "home_venue": "Kochi",
        "titles": [],
        "active": False,
    },
}

# Canonical venue city mapping
VENUE_CANONICAL_MAP: Dict[str, str] = {
    "Bangalore": "Bengaluru",
    "Bengaluru": "Bengaluru",
    "Chandigarh": "Mohali",
    "Mohali": "Mohali",
}

# Exact Cricsheet IPL match counts per season (total = 1095 rows in IPL.csv)
SEASON_MATCH_COUNTS: List[Tuple[int, int]] = [
    (2008, 58),
    (2009, 57),
    (2010, 60),
    (2011, 73),
    (2012, 74),
    (2013, 76),
    (2014, 60),
    (2015, 59),
    (2016, 60),
    (2017, 59),
    (2018, 60),
    (2019, 60),
    (2020, 60),
    (2021, 60),
    (2022, 74),
    (2023, 74),
    (2024, 71),
]

NUMERIC_FEATURE_COLUMNS: List[str] = [
    "elo_team1",
    "elo_team2",
    "elo_diff",
    "elo_expected_team1",
    "team1_overall_win_rate",
    "team2_overall_win_rate",
    "overall_win_rate_diff",
    "team1_form_last5",
    "team2_form_last5",
    "form_diff_last5",
    "team1_form_last10",
    "team2_form_last10",
    "form_diff_last10",
    "h2h_team1_win_rate",
    "h2h_matches_played",
    "team1_venue_win_rate",
    "team2_venue_win_rate",
    "venue_win_rate_diff",
    "venue_chase_win_rate",
    "venue_avg_target_runs",
    "team1_won_toss",
    "toss_decision_field",
    "team1_is_chasing",
    "chasing_advantage_for_team1",
    "team1_home_advantage",
    "team2_home_advantage",
]

CATEGORICAL_FEATURE_COLUMNS: List[str] = [
    "venue",
    "team1",
    "team2",
    "toss_decision",
]

ALL_FEATURE_COLUMNS: List[str] = NUMERIC_FEATURE_COLUMNS + CATEGORICAL_FEATURE_COLUMNS

FEATURE_DISPLAY_NAMES: Dict[str, str] = {
    "elo_team1": "Team 1 Elo Rating",
    "elo_team2": "Team 2 Elo Rating",
    "elo_diff": "Elo Strength Differential",
    "elo_expected_team1": "Elo Win Expectancy",
    "team1_overall_win_rate": "Team 1 Career Win Rate",
    "team2_overall_win_rate": "Team 2 Career Win Rate",
    "overall_win_rate_diff": "Overall Win Rate Edge",
    "team1_form_last5": "Team 1 Recent Form (Last 5)",
    "team2_form_last5": "Team 2 Recent Form (Last 5)",
    "form_diff_last5": "Recent Form Differential (Last 5)",
    "team1_form_last10": "Team 1 Momentum (Last 10)",
    "team2_form_last10": "Team 2 Momentum (Last 10)",
    "form_diff_last10": "Momentum Differential (Last 10)",
    "h2h_team1_win_rate": "Head-to-Head Dominance",
    "h2h_matches_played": "Head-to-Head Experience",
    "team1_venue_win_rate": "Team 1 Venue Win Rate",
    "team2_venue_win_rate": "Team 2 Venue Win Rate",
    "venue_win_rate_diff": "Venue Mastery Differential",
    "venue_chase_win_rate": "Venue Chasing Bias",
    "venue_avg_target_runs": "Venue Average Par Target",
    "team1_won_toss": "Toss Winner Advantage",
    "toss_decision_field": "Toss Decision (Field vs Bat)",
    "team1_is_chasing": "Second Innings Chase Factor",
    "chasing_advantage_for_team1": "Venue-Specific Toss & Chase Synergy",
    "team1_home_advantage": "Team 1 Home Fortress Factor",
    "team2_home_advantage": "Team 2 Home Fortress Factor",
}


def canonicalize_team(name: Optional[str]) -> str:
    """Return canonical IPL franchise name."""
    if not name or pd.isna(name):
        return "Unknown"
    cleaned = str(name).strip()
    return TEAM_CANONICAL_MAP.get(cleaned, cleaned)


def canonicalize_venue(venue: Optional[str], team1: Optional[str] = None) -> str:
    """Return canonical venue name, imputing missing venues from home team if needed."""
    if venue is None or pd.isna(venue) or str(venue).strip() in ("", "Unknown", "nan"):
        if team1:
            canon_t1 = canonicalize_team(team1)
            meta = TEAM_METADATA.get(canon_t1)
            if meta and meta.get("home_venue"):
                return str(meta["home_venue"])
        return "Dubai"  # Majority of missing-city Cricsheet rows are UAE neutral matches
    cleaned = str(venue).strip()
    return VENUE_CANONICAL_MAP.get(cleaned, cleaned)


def assign_seasons(df: pd.DataFrame) -> pd.Series:
    """Deterministically assign IPL season years (2008-2024) based on chronological match sequence."""
    seasons: List[int] = []
    for year, count in SEASON_MATCH_COUNTS:
        seasons.extend([year] * count)
    if len(seasons) < len(df):
        seasons.extend([2024] * (len(df) - len(seasons)))
    return pd.Series(seasons[: len(df)], index=df.index, name="season")


def load_and_clean_dataset(csv_path: str) -> pd.DataFrame:
    """Load IPL.csv, assign seasons, canonicalize teams/venues, and filter no-result rows."""
    raw_df = pd.read_csv(csv_path)
    raw_df["match_id"] = np.arange(1, len(raw_df) + 1)
    raw_df["season"] = assign_seasons(raw_df)

    # Canonicalize team names
    for col in ["team1", "team2", "toss_winner", "winner"]:
        raw_df[col] = raw_df[col].apply(canonicalize_team)

    # Canonicalize venues (imputing missing UAE/home venues cleanly)
    raw_df["venue"] = [
        canonicalize_venue(v, t1) for v, t1 in zip(raw_df["Venue"], raw_df["team1"])
    ]

    # Clean toss_decision
    raw_df["toss_decision"] = (
        raw_df["toss_decision"]
        .fillna("field")
        .astype(str)
        .str.strip()
        .str.lower()
        .replace({"bowl": "field"})
    )

    # Numeric target_runs & result_margin
    raw_df["target_runs"] = pd.to_numeric(raw_df["target_runs"], errors="coerce")
    raw_df["result_margin"] = pd.to_numeric(raw_df["result_margin"], errors="coerce").fillna(0.0)

    # Filter out matches without a valid winner (abandoned / no result: 5 rows out of 1095)
    valid_df = raw_df[raw_df["winner"] != "Unknown"].copy()
    valid_df = valid_df[
        (valid_df["winner"] == valid_df["team1"]) | (valid_df["winner"] == valid_df["team2"])
    ].copy()

    # Fill missing target_runs with venue median or global median (166.0)
    global_median_target = float(valid_df["target_runs"].median())
    valid_df["target_runs"] = valid_df["target_runs"].fillna(global_median_target)

    valid_df.reset_index(drop=True, inplace=True)
    return valid_df


@dataclass
class HistoricalStateStore:
    """
    Maintains chronological, leak-free team and venue statistics across IPL history.
    Used both during sequential training feature generation and at inference time for 2026 predictions.
    """

    elo_k: float = 24.0
    base_elo: float = 1500.0
    team_elo: Dict[str, float] = field(default_factory=dict)
    team_matches: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    team_wins: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    team_recent_results: Dict[str, List[int]] = field(default_factory=lambda: defaultdict(list))
    h2h_wins: Dict[Tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    h2h_total: Dict[frozenset, int] = field(default_factory=lambda: defaultdict(int))
    team_venue_matches: Dict[Tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    team_venue_wins: Dict[Tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    venue_matches: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    venue_chase_wins: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    venue_target_sum: Dict[str, float] = field(default_factory=lambda: defaultdict(float))

    def get_elo(self, team: str) -> float:
        return float(self.team_elo.get(team, self.base_elo))

    def get_overall_win_rate(self, team: str, prior_weight: float = 6.0) -> float:
        matches = self.team_matches.get(team, 0)
        wins = self.team_wins.get(team, 0)
        return float((wins + 0.5 * prior_weight) / (matches + prior_weight))

    def get_recent_form(self, team: str, window: int = 5) -> float:
        history = self.team_recent_results.get(team, [])
        if not history:
            return 0.5
        recent = history[-window:]
        # Smoothed recent form so 1 match doesn't jump to 0.0 or 1.0
        return float((sum(recent) + 1.0) / (len(recent) + 2.0))

    def get_h2h_stats(self, team1: str, team2: str, prior_weight: float = 4.0) -> Tuple[float, int]:
        pair_key = frozenset([team1, team2])
        total = int(self.h2h_total.get(pair_key, 0))
        t1_wins = int(self.h2h_wins.get((team1, team2), 0))
        win_rate = float((t1_wins + 0.5 * prior_weight) / (total + prior_weight))
        return win_rate, total

    def get_team_venue_win_rate(self, team: str, venue: str, prior_weight: float = 4.0) -> float:
        matches = self.team_venue_matches.get((team, venue), 0)
        wins = self.team_venue_wins.get((team, venue), 0)
        base_rate = self.get_overall_win_rate(team)
        return float((wins + base_rate * prior_weight) / (matches + prior_weight))

    def get_venue_chase_win_rate(self, venue: str, prior_weight: float = 6.0) -> float:
        matches = self.venue_matches.get(venue, 0)
        chase_wins = self.venue_chase_wins.get(venue, 0)
        # IPL historical average chase win rate is ~53.5%
        return float((chase_wins + 0.535 * prior_weight) / (matches + prior_weight))

    def get_venue_avg_target(self, venue: str, prior_weight: float = 5.0) -> float:
        matches = self.venue_matches.get(venue, 0)
        target_sum = self.venue_target_sum.get(venue, 0.0)
        return float((target_sum + 168.0 * prior_weight) / (matches + prior_weight))

    def compute_match_features(
        self,
        team1: str,
        team2: str,
        venue: str,
        toss_winner: str,
        toss_decision: str,
    ) -> Dict[str, Any]:
        """Compute leak-free pre-match features for (team1, team2, venue, toss_winner, toss_decision)."""
        t1 = canonicalize_team(team1)
        t2 = canonicalize_team(team2)
        v = canonicalize_venue(venue, t1)
        tw = canonicalize_team(toss_winner)
        td = "field" if str(toss_decision).strip().lower() in ("field", "bowl") else "bat"

        elo_t1 = self.get_elo(t1)
        elo_t2 = self.get_elo(t2)
        elo_diff = elo_t1 - elo_t2
        elo_expected_t1 = 1.0 / (1.0 + (10.0 ** (-elo_diff / 400.0)))

        t1_wr = self.get_overall_win_rate(t1)
        t2_wr = self.get_overall_win_rate(t2)

        t1_f5 = self.get_recent_form(t1, window=5)
        t2_f5 = self.get_recent_form(t2, window=5)
        t1_f10 = self.get_recent_form(t1, window=10)
        t2_f10 = self.get_recent_form(t2, window=10)

        h2h_t1_wr, h2h_cnt = self.get_h2h_stats(t1, t2)

        t1_v_wr = self.get_team_venue_win_rate(t1, v)
        t2_v_wr = self.get_team_venue_win_rate(t2, v)
        v_chase_wr = self.get_venue_chase_win_rate(v)
        v_avg_target = self.get_venue_avg_target(v)

        t1_won_toss = 1.0 if tw == t1 else 0.0
        td_field = 1.0 if td == "field" else 0.0

        # Determine if team1 is batting second (chasing)
        if (tw == t1 and td == "field") or (tw == t2 and td == "bat"):
            t1_is_chasing = 1.0
        else:
            t1_is_chasing = 0.0

        # Positive when team1 chases at a chase-friendly venue or defends at a defend-friendly venue
        chasing_advantage_t1 = (
            (v_chase_wr - 0.5) if t1_is_chasing == 1.0 else (0.5 - v_chase_wr)
        )

        t1_home = 1.0 if TEAM_METADATA.get(t1, {}).get("home_venue") == v else 0.0
        t2_home = 1.0 if TEAM_METADATA.get(t2, {}).get("home_venue") == v else 0.0

        return {
            "elo_team1": round(elo_t1, 3),
            "elo_team2": round(elo_t2, 3),
            "elo_diff": round(elo_diff, 3),
            "elo_expected_team1": round(elo_expected_t1, 5),
            "team1_overall_win_rate": round(t1_wr, 5),
            "team2_overall_win_rate": round(t2_wr, 5),
            "overall_win_rate_diff": round(t1_wr - t2_wr, 5),
            "team1_form_last5": round(t1_f5, 5),
            "team2_form_last5": round(t2_f5, 5),
            "form_diff_last5": round(t1_f5 - t2_f5, 5),
            "team1_form_last10": round(t1_f10, 5),
            "team2_form_last10": round(t2_f10, 5),
            "form_diff_last10": round(t1_f10 - t2_f10, 5),
            "h2h_team1_win_rate": round(h2h_t1_wr, 5),
            "h2h_matches_played": float(h2h_cnt),
            "team1_venue_win_rate": round(t1_v_wr, 5),
            "team2_venue_win_rate": round(t2_v_wr, 5),
            "venue_win_rate_diff": round(t1_v_wr - t2_v_wr, 5),
            "venue_chase_win_rate": round(v_chase_wr, 5),
            "venue_avg_target_runs": round(v_avg_target, 2),
            "team1_won_toss": t1_won_toss,
            "toss_decision_field": td_field,
            "team1_is_chasing": t1_is_chasing,
            "chasing_advantage_for_team1": round(chasing_advantage_t1, 5),
            "team1_home_advantage": t1_home,
            "team2_home_advantage": t2_home,
            "venue": v,
            "team1": t1,
            "team2": t2,
            "toss_decision": td,
        }

    def update_with_match(
        self,
        team1: str,
        team2: str,
        venue: str,
        toss_winner: str,
        toss_decision: str,
        winner: str,
        target_runs: float = 166.0,
    ) -> None:
        """Update historical state after observing a match outcome."""
        t1 = canonicalize_team(team1)
        t2 = canonicalize_team(team2)
        v = canonicalize_venue(venue, t1)
        tw = canonicalize_team(toss_winner)
        td = "field" if str(toss_decision).strip().lower() in ("field", "bowl") else "bat"
        w = canonicalize_team(winner)

        t1_won = 1 if w == t1 else 0
        t2_won = 1 - t1_won

        # Update Elo ratings
        elo_t1 = self.get_elo(t1)
        elo_t2 = self.get_elo(t2)
        expected_t1 = 1.0 / (1.0 + (10.0 ** (-(elo_t1 - elo_t2) / 400.0)))
        self.team_elo[t1] = elo_t1 + self.elo_k * (t1_won - expected_t1)
        self.team_elo[t2] = elo_t2 + self.elo_k * (t2_won - (1.0 - expected_t1))

        # Overall counts
        self.team_matches[t1] += 1
        self.team_matches[t2] += 1
        self.team_wins[t1] += t1_won
        self.team_wins[t2] += t2_won

        # Recent form
        self.team_recent_results[t1].append(t1_won)
        self.team_recent_results[t2].append(t2_won)

        # Head-to-head
        pair_key = frozenset([t1, t2])
        self.h2h_total[pair_key] += 1
        if t1_won:
            self.h2h_wins[(t1, t2)] += 1
        else:
            self.h2h_wins[(t2, t1)] += 1

        # Team venue records
        self.team_venue_matches[(t1, v)] += 1
        self.team_venue_matches[(t2, v)] += 1
        self.team_venue_wins[(t1, v)] += t1_won
        self.team_venue_wins[(t2, v)] += t2_won

        # Venue chase & target stats
        self.venue_matches[v] += 1
        self.venue_target_sum[v] += float(target_runs) if not pd.isna(target_runs) else 166.0
        chasing_team = t1 if ((tw == t1 and td == "field") or (tw == t2 and td == "bat")) else t2
        if w == chasing_team:
            self.venue_chase_wins[v] += 1


def build_training_dataset(
    df: pd.DataFrame, symmetric_augmentation: bool = True
) -> Tuple[pd.DataFrame, pd.Series, HistoricalStateStore]:
    """
    Build leak-free training features sequentially across all historical matches.
    When symmetric_augmentation=True, each match also yields its mirrored perspective
    (team2 vs team1) so the trained classifier is order-invariant and unbiased.
    """
    store = HistoricalStateStore()
    rows: List[Dict[str, Any]] = []
    targets: List[int] = []

    for _, row in df.iterrows():
        t1 = row["team1"]
        t2 = row["team2"]
        v = row["venue"]
        tw = row["toss_winner"]
        td = row["toss_decision"]
        w = row["winner"]
        target_runs = float(row.get("target_runs", 166.0))

        # 1. Extract pre-match features for (t1, t2) BEFORE updating store
        feat_forward = store.compute_match_features(t1, t2, v, tw, td)
        feat_forward["season"] = int(row["season"])
        feat_forward["match_id"] = int(row["match_id"])
        rows.append(feat_forward)
        targets.append(1 if w == t1 else 0)

        # 2. Optional symmetric augmentation: (t2, t1) perspective
        if symmetric_augmentation:
            feat_reverse = store.compute_match_features(t2, t1, v, tw, td)
            feat_reverse["season"] = int(row["season"])
            feat_reverse["match_id"] = int(row["match_id"])
            rows.append(feat_reverse)
            targets.append(1 if w == t2 else 0)

        # 3. Advance state store with actual outcome
        store.update_with_match(t1, t2, v, tw, td, w, target_runs=target_runs)

    feature_df = pd.DataFrame(rows)
    target_series = pd.Series(targets, name="team1_win", dtype=int)
    return feature_df, target_series, store
