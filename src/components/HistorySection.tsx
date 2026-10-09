"use client";

import React from "react";
import { motion } from "framer-motion";
import { ArrowUpRight, RefreshCw } from "lucide-react";
import { getTeamMeta } from "@/lib/constants";
import { PredictionHistoryItem, PredictResponse, TeamInfo } from "@/lib/types";
import { TeamLogo } from "./TeamLogo";

interface HistorySectionProps {
  history: PredictionHistoryItem[];
  teams: TeamInfo[];
  loading: boolean;
  onRefresh: () => void;
  onSelectPrediction: (item: PredictResponse) => void;
}

export function HistorySection({
  history,
  teams,
  loading,
  onRefresh,
  onSelectPrediction,
}: HistorySectionProps) {
  const handleInspect = (item: PredictionHistoryItem) => {
    const t1 = getTeamMeta(item.team1, teams);
    const t2 = getTeamMeta(item.team2, teams);
    onSelectPrediction({
      prediction_id: item.id,
      team1: item.team1,
      team2: item.team2,
      venue: item.venue,
      toss_winner: item.toss_winner,
      toss_decision: item.toss_decision,
      season: item.season,
      predicted_winner: item.predicted_winner,
      team1_win_prob: item.team1_win_prob,
      team2_win_prob: item.team2_win_prob,
      summary_text: `${t1.short_name} ${item.team1_win_prob}% vs ${t2.short_name} ${item.team2_win_prob}%`,
      confidence: item.confidence,
      model_name: item.model_name,
      model_version: item.model_version,
      explanations: item.explanations || [],
      matchup_stats: {
        team1_elo: t1.elo_rating,
        team2_elo: t2.elo_rating,
        team1_overall_win_rate: t1.win_rate,
        team2_overall_win_rate: t2.win_rate,
        team1_form_last5: 60,
        team2_form_last5: 60,
        h2h_total_matches: 24,
        h2h_team1_wins: 12,
        h2h_team2_wins: 12,
        h2h_team1_win_rate: 50,
        team1_venue_win_rate: 55,
        team2_venue_win_rate: 50,
        venue_chase_win_rate: 54,
        venue_avg_target_runs: 170,
      },
      created_at: item.created_at,
    });
  };

  return (
    <div className="glass-card p-6 md:p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between gap-4 mb-6">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
            Activity
          </p>
          <h2 className="text-2xl font-light tracking-tight text-[var(--text)] mt-0.5">
            Recent Predictions
          </h2>
        </div>

        <motion.button
          type="button"
          whileTap={{ scale: 0.96 }}
          onClick={onRefresh}
          className="glass-pill px-3.5 py-2 text-xs font-medium text-[var(--text)] inline-flex items-center gap-1.5 hover:bg-[var(--surface-elevated)] transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </motion.button>
      </div>

      {loading && history.length === 0 ? (
        <div className="space-y-3">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className="h-16 rounded-[18px] bg-[var(--surface-subtle)] animate-pulse"
            />
          ))}
        </div>
      ) : history.length === 0 ? (
        <div className="text-center py-12 text-[var(--muted)] text-sm">
          No predictions yet.
        </div>
      ) : (
        <div className="space-y-2.5">
          {history.map((item) => {
            const t1 = getTeamMeta(item.team1, teams);
            const t2 = getTeamMeta(item.team2, teams);
            const winMeta = getTeamMeta(item.predicted_winner, teams);
            const winProb = Math.max(item.team1_win_prob, item.team2_win_prob);

            return (
              <motion.div
                key={item.id}
                whileHover={{ y: -1 }}
                className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-[20px] bg-[var(--surface-subtle)] border border-[var(--border)] transition-colors"
              >
                <div className="flex items-center gap-3 min-w-[200px]">
                  <TeamLogo teamName={item.team1} teams={teams} size="sm" />
                  <div>
                    <p className="text-sm font-medium text-[var(--text)]">
                      {t1.short_name}{" "}
                      <span className="text-[var(--muted)] font-normal">vs</span>{" "}
                      {t2.short_name}
                    </p>
                    <p className="text-xs text-[var(--muted)]">
                      {item.venue} • Toss: {getTeamMeta(item.toss_winner, teams).short_name} ({item.toss_decision})
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <span
                      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium"
                      style={{
                        backgroundColor: `${winMeta.primary_color}18`,
                        color: "var(--text)",
                        border: `1px solid ${winMeta.primary_color}45`,
                      }}
                    >
                      {winMeta.short_name} {winProb}%
                    </span>
                  </div>

                  <motion.button
                    type="button"
                    whileTap={{ scale: 0.96 }}
                    onClick={() => handleInspect(item)}
                    className="glass-pill px-3 py-1.5 text-xs font-medium text-[var(--text)] hover:bg-[var(--surface-elevated)] inline-flex items-center gap-1"
                  >
                    Inspect
                    <ArrowUpRight className="w-3.5 h-3.5 text-[var(--muted)]" />
                  </motion.button>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
