export interface TeamInfo {
  name: string;
  short_name: string;
  primary_color: string;
  secondary_color: string;
  home_venue: string;
  titles: number[];
  title_count: number;
  active: boolean;
  matches_played: number;
  wins: number;
  win_rate: number;
  elo_rating: number;
  recent_form: number[];
}

export interface VenueInfo {
  name: string;
  matches_played: number;
  chase_win_rate: number;
  defend_win_rate: number;
  avg_target_runs: number;
  toss_field_rate: number;
  high_scoring_index: string;
}

export interface FeatureContribution {
  feature: string;
  display_name: string;
  impact: number;
  abs_impact: number;
  favored_team: string;
  value_summary: string;
}

export interface MatchupContextStats {
  team1_elo: number;
  team2_elo: number;
  team1_overall_win_rate: number;
  team2_overall_win_rate: number;
  team1_form_last5: number;
  team2_form_last5: number;
  h2h_total_matches: number;
  h2h_team1_wins: number;
  h2h_team2_wins: number;
  h2h_team1_win_rate: number;
  team1_venue_win_rate: number;
  team2_venue_win_rate: number;
  venue_chase_win_rate: number;
  venue_avg_target_runs: number;
}

export interface PredictRequest {
  team1: string;
  team2: string;
  venue: string;
  toss_winner: string;
  toss_decision: "bat" | "field";
  season: number;
}

export interface PredictResponse {
  prediction_id?: number | null;
  team1: string;
  team2: string;
  venue: string;
  toss_winner: string;
  toss_decision: string;
  season: number;
  predicted_winner: string;
  team1_win_prob: number;
  team2_win_prob: number;
  summary_text: string;
  confidence: string;
  model_name: string;
  model_version: string;
  explanations: FeatureContribution[];
  matchup_stats: MatchupContextStats;
  created_at: string;
}

export interface PredictionHistoryItem {
  id: number;
  team1: string;
  team2: string;
  venue: string;
  toss_winner: string;
  toss_decision: string;
  season: number;
  predicted_winner: string;
  team1_win_prob: number;
  team2_win_prob: number;
  confidence: string;
  model_name: string;
  model_version: string;
  explanations: FeatureContribution[];
  created_at: string;
}

export interface HeadToHeadMatch {
  match_id: number;
  season: number;
  venue: string;
  toss_winner: string;
  toss_decision: string;
  winner: string;
  result_margin: number;
  target_runs: number;
}

export interface HeadToHeadResponse {
  team1: string;
  team2: string;
  total_matches: number;
  team1_wins: number;
  team2_wins: number;
  team1_win_rate: number;
  team2_win_rate: number;
  avg_target_runs: number;
  avg_win_margin: number;
  venue_breakdown: {
    venue: string;
    matches: number;
    team1_wins: number;
    team2_wins: number;
  }[];
  season_breakdown: {
    season: number;
    matches: number;
    team1_wins: number;
    team2_wins: number;
  }[];
  recent_matches: HeadToHeadMatch[];
}

export interface ModelBenchmarkItem {
  model_name: string;
  accuracy: number;
  f1_score: number;
  roc_auc: number;
  brier_score: number;
  log_loss: number;
  cv_accuracy_mean: number;
  cv_roc_auc_mean: number;
  confusion_matrix: number[][];
}

export interface GlobalFeatureImportance {
  feature: string;
  display_name: string;
  importance: number;
  rf_importance: number;
  lr_weight: number;
}

export interface DashboardAnalytics {
  summary: {
    total_matches: number;
    seasons_count: number;
    active_teams_count: number;
    total_venues: number;
    overall_avg_target: number;
    overall_toss_field_pct: number;
  };
  team_standings: TeamInfo[];
  top_venues: VenueInfo[];
  season_trends: {
    season: number;
    matches: number;
    avg_target_runs: number;
    chase_win_rate: number;
    toss_field_rate: number;
    champion: string;
    champion_short: string;
  }[];
  model_performance: {
    version: string;
    selected_model: string;
    selected_metrics: ModelBenchmarkItem;
    models_compared: ModelBenchmarkItem[];
    global_feature_importance: GlobalFeatureImportance[];
  };
}
