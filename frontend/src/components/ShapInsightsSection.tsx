"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { getTeamMeta } from "@/lib/constants";
import { PredictResponse, TeamInfo } from "@/lib/types";
import { TeamLogo } from "./TeamLogo";

interface ShapInsightsSectionProps {
  prediction: PredictResponse;
  teams: TeamInfo[];
}

export function ShapInsightsSection({
  prediction,
  teams,
}: ShapInsightsSectionProps) {
  const t1 = getTeamMeta(prediction.team1, teams);
  const t2 = getTeamMeta(prediction.team2, teams);

  const chartData = prediction.explanations.map((exp) => ({
    name: exp.display_name,
    impact: exp.impact,
    favored_team: exp.favored_team,
    summary: exp.value_summary,
    fill: exp.impact >= 0 ? t1.primary_color : t2.primary_color,
  }));

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Main Attribution Chart Card */}
      <div className="glass-card p-6 md:p-8">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
              Feature Attribution
            </p>
            <h2 className="text-2xl font-light tracking-tight text-[var(--text)] mt-1">
              {prediction.summary_text}
            </h2>
          </div>

          <div className="flex items-center gap-4 text-xs font-medium text-[var(--text)]">
            <div className="flex items-center gap-2 glass-pill px-3 py-1.5">
              <TeamLogo teamName={t1.name} teams={teams} size="xs" />
              <span>{t1.short_name} (+%)</span>
            </div>
            <div className="flex items-center gap-2 glass-pill px-3 py-1.5">
              <TeamLogo teamName={t2.name} teams={teams} size="xs" />
              <span>{t2.short_name} (-%)</span>
            </div>
          </div>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
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
                tickFormatter={(val) => `${val > 0 ? "+" : ""}${val}%`}
              />
              <YAxis
                type="category"
                dataKey="name"
                stroke="var(--muted)"
                tick={{ fill: "var(--text)", fontSize: 12 }}
                width={195}
              />
              <Tooltip
                cursor={{ fill: "var(--surface-subtle)" }}
                contentStyle={{
                  backgroundColor: "var(--tooltip-bg)",
                  borderColor: "var(--border)",
                  borderRadius: "16px",
                  color: "var(--text)",
                  boxShadow: "var(--shadow-card)",
                }}
                itemStyle={{ color: "var(--text)" }}
                labelStyle={{ color: "var(--text)", fontWeight: 600 }}
                formatter={(value: number, _name: string, props: any) => [
                  `${value > 0 ? "+" : ""}${value}% (${props.payload.favored_team})`,
                  props.payload.summary,
                ]}
              />
              <ReferenceLine x={0} stroke="var(--border)" strokeWidth={1.5} />
              <Bar dataKey="impact" radius={[6, 6, 6, 6]} fillOpacity={0.82}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Concise Factor Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {prediction.explanations.map((item, idx) => {
          const isT1 = item.impact >= 0;
          const teamMeta = isT1 ? t1 : t2;
          return (
            <motion.div
              key={item.feature}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              whileHover={{ y: -2 }}
              className="glass-card p-5 flex flex-col justify-between"
            >
              <div className="flex items-start justify-between gap-3">
                <span className="text-xs font-medium text-[var(--muted)]">
                  {item.display_name}
                </span>
                <span
                  className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium shrink-0"
                  style={{
                    backgroundColor: `${teamMeta.primary_color}18`,
                    color: "var(--text)",
                    border: `1px solid ${teamMeta.primary_color}45`,
                  }}
                >
                  {isT1 ? (
                    <ArrowUpRight className="w-3 h-3" />
                  ) : (
                    <ArrowDownRight className="w-3 h-3" />
                  )}
                  {teamMeta.short_name} +{item.abs_impact.toFixed(1)}%
                </span>
              </div>

              <p className="text-sm font-medium text-[var(--text)] mt-3">
                {item.value_summary}
              </p>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
