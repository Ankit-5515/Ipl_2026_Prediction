"use client";

import React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { DashboardAnalytics, ModelBenchmarkItem } from "@/lib/types";

interface AboutModelSectionProps {
  analytics: DashboardAnalytics | null;
}

const FALLBACK_BENCHMARKS: ModelBenchmarkItem[] = [
  {
    model_name: "Hybrid Ensemble (LR + RF + GBDT/XGB)",
    accuracy: 0.5757,
    f1_score: 0.5708,
    roc_auc: 0.5725,
    brier_score: 0.2449,
    log_loss: 0.681,
    cv_accuracy_mean: 0.556,
    cv_roc_auc_mean: 0.5217,
    confusion_matrix: [
      [124, 94],
      [91, 127],
    ],
  },
  {
    model_name: "Logistic Regression",
    accuracy: 0.5413,
    f1_score: 0.5413,
    roc_auc: 0.5758,
    brier_score: 0.2441,
    log_loss: 0.679,
    cv_accuracy_mean: 0.542,
    cv_roc_auc_mean: 0.5411,
    confusion_matrix: [
      [118, 100],
      [100, 118],
    ],
  },
  {
    model_name: "Random Forest",
    accuracy: 0.5688,
    f1_score: 0.5766,
    roc_auc: 0.5667,
    brier_score: 0.2447,
    log_loss: 0.682,
    cv_accuracy_mean: 0.548,
    cv_roc_auc_mean: 0.5087,
    confusion_matrix: [
      [120, 98],
      [90, 128],
    ],
  },
  {
    model_name: "XGBoost",
    accuracy: 0.5344,
    f1_score: 0.5418,
    roc_auc: 0.5713,
    brier_score: 0.246,
    log_loss: 0.685,
    cv_accuracy_mean: 0.535,
    cv_roc_auc_mean: 0.5051,
    confusion_matrix: [
      [115, 103],
      [100, 118],
    ],
  },
];

export function AboutModelSection({ analytics }: AboutModelSectionProps) {
  const models =
    analytics?.model_performance?.models_compared?.length
      ? analytics.model_performance.models_compared
      : FALLBACK_BENCHMARKS;
  const selectedModel =
    analytics?.model_performance?.selected_model || "Logistic Regression";

  const topFeatures = (
    analytics?.model_performance?.global_feature_importance || [
      { display_name: "Second Innings Chase Factor", importance: 0.106 },
      { display_name: "Overall Win Rate Edge", importance: 0.066 },
      { display_name: "Elo Win Expectancy", importance: 0.058 },
      { display_name: "Venue Mastery Differential", importance: 0.055 },
      { display_name: "Team 1 Venue Win Rate", importance: 0.049 },
      { display_name: "Venue-Specific Toss & Chase Synergy", importance: 0.048 },
    ]
  )
    .slice(0, 6)
    .map((f) => ({
      name: f.display_name,
      weight: Number((f.importance * 100).toFixed(1)),
    }));

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Minimal Specs Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Architecture", value: "Calibrated Pipeline" },
          { label: "Features", value: "26 Rolling Signals" },
          { label: "Validation", value: "5-Fold GroupKFold" },
          { label: "Explainability", value: "SHAP Attribution" },
        ].map((spec) => (
          <div key={spec.label} className="glass-card p-5">
            <p className="text-xs font-medium text-[var(--muted)]">{spec.label}</p>
            <p className="text-base font-medium text-[var(--text)] mt-1">
              {spec.value}
            </p>
          </div>
        ))}
      </div>

      {/* Model Benchmark Table */}
      <div className="glass-card p-6 md:p-8">
        <p className="text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
          Evaluation
        </p>
        <h2 className="text-2xl font-light tracking-tight text-[var(--text)] mt-0.5 mb-6">
          Model Benchmark
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-xs font-medium text-[var(--muted)]">
                <th className="py-3 pr-4">Model</th>
                <th className="py-3 pr-4">Accuracy</th>
                <th className="py-3 pr-4">F1</th>
                <th className="py-3 pr-4">ROC-AUC</th>
                <th className="py-3">Brier</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {models.map((m) => {
                const isBest = m.model_name === selectedModel;
                return (
                  <tr key={m.model_name} className="text-[var(--text)]">
                    <td className="py-3.5 pr-4 font-medium flex items-center gap-2">
                      <span>{m.model_name}</span>
                      {isBest && (
                        <span className="glass-pill px-2.5 py-0.5 text-[10px] font-medium text-[var(--accent)]">
                          Active
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 pr-4 tabular-nums">
                      {(m.accuracy * 100).toFixed(1)}%
                    </td>
                    <td className="py-3.5 pr-4 tabular-nums">
                      {m.f1_score.toFixed(3)}
                    </td>
                    <td className="py-3.5 pr-4 tabular-nums font-medium">
                      {m.roc_auc.toFixed(3)}
                    </td>
                    <td className="py-3.5 tabular-nums text-[var(--muted)]">
                      {m.brier_score.toFixed(3)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Global Feature Weights */}
      <div className="glass-card p-6 md:p-8">
        <p className="text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
          Global Signals
        </p>
        <h3 className="text-xl font-light tracking-tight text-[var(--text)] mt-0.5 mb-4">
          Feature Weights
        </h3>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={topFeatures}
              layout="vertical"
              margin={{ top: 4, right: 24, left: 16, bottom: 4 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="var(--chart-grid)"
                horizontal={false}
              />
              <XAxis
                type="number"
                stroke="var(--muted)"
                tick={{ fill: "var(--muted)", fontSize: 11 }}
                tickFormatter={(v) => `${v}%`}
              />
              <YAxis
                type="category"
                dataKey="name"
                stroke="var(--muted)"
                tick={{ fill: "var(--text)", fontSize: 12 }}
                width={210}
              />
              <Tooltip
                cursor={{ fill: "var(--surface-subtle)" }}
                contentStyle={{
                  backgroundColor: "var(--tooltip-bg)",
                  borderColor: "var(--border)",
                  borderRadius: "16px",
                  color: "var(--text)",
                }}
              />
              <Bar
                dataKey="weight"
                fill="var(--accent)"
                fillOpacity={0.8}
                radius={[0, 6, 6, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
