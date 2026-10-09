"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";
import { getTeamMeta } from "@/lib/constants";
import {
  DashboardAnalytics,
  HeadToHeadResponse,
  TeamInfo,
  VenueInfo,
} from "@/lib/types";
import { CustomSelect, TeamLogo } from "./TeamLogo";

interface AnalyticsDashboardSectionProps {
  teams: TeamInfo[];
  venues: VenueInfo[];
  analytics: DashboardAnalytics | null;
}

export function AnalyticsDashboardSection({
  teams,
  venues,
  analytics,
}: AnalyticsDashboardSectionProps) {
  const [h2hTeam1, setH2hTeam1] = useState<string>("Chennai Super Kings");
  const [h2hTeam2, setH2hTeam2] = useState<string>("Mumbai Indians");
  const [h2hData, setH2hData] = useState<HeadToHeadResponse | null>(null);
  const [loadingH2h, setLoadingH2h] = useState<boolean>(false);

  useEffect(() => {
    if (!h2hTeam1 || !h2hTeam2 || h2hTeam1 === h2hTeam2) return;
    let active = true;
    setLoadingH2h(true);
    api
      .getHeadToHead(h2hTeam1, h2hTeam2)
      .then((res) => {
        if (active) setH2hData(res);
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoadingH2h(false);
      });
    return () => {
      active = false;
    };
  }, [h2hTeam1, h2hTeam2]);

  const standings = analytics?.team_standings || teams;
  const venueStats = (analytics?.top_venues || venues).slice(0, 8);
  const seasonTrends = analytics?.season_trends || [
    { season: 2008, avg_target_runs: 160.2, chase_win_rate: 58.6, champion_short: "RR" },
    { season: 2012, avg_target_runs: 161.4, chase_win_rate: 55.4, champion_short: "KKR" },
    { season: 2016, avg_target_runs: 166.9, chase_win_rate: 66.7, champion_short: "SRH" },
    { season: 2020, avg_target_runs: 170.5, chase_win_rate: 45.0, champion_short: "MI" },
    { season: 2022, avg_target_runs: 172.8, chase_win_rate: 50.0, champion_short: "GT" },
    { season: 2024, avg_target_runs: 190.7, chase_win_rate: 49.3, champion_short: "KKR" },
  ];

  const t1Meta = getTeamMeta(h2hTeam1, teams);
  const t2Meta = getTeamMeta(h2hTeam2, teams);

  const teamOptions1 = teams.map((t) => ({
    value: t.name,
    label: t.name,
    sublabel: `Elo ${t.elo_rating.toFixed(0)}`,
    disabled: t.name === h2hTeam2,
    teamName: t.name,
  }));

  const teamOptions2 = teams.map((t) => ({
    value: t.name,
    label: t.name,
    sublabel: `Elo ${t.elo_rating.toFixed(0)}`,
    disabled: t.name === h2hTeam1,
    teamName: t.name,
  }));

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* 4 Minimal KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          {
            label: "Matches",
            value: analytics?.summary.total_matches ?? 1090,
            sub: "2008 – 2024",
          },
          {
            label: "Seasons",
            value: analytics?.summary.seasons_count ?? 17,
            sub: "Complete History",
          },
          {
            label: "Avg Target",
            value: `${analytics?.summary.overall_avg_target ?? 165.7}`,
            sub: "First Innings Runs",
          },
          {
            label: "Field First",
            value: `${analytics?.summary.overall_toss_field_pct ?? 64.4}%`,
            sub: "Toss Preference",
          },
        ].map((kpi) => (
          <motion.div
            key={kpi.label}
            whileHover={{ y: -2 }}
            className="glass-card p-5"
          >
            <p className="text-xs font-medium text-[var(--muted)]">{kpi.label}</p>
            <p className="text-3xl font-light tracking-tight text-[var(--text)] mt-1 tabular-nums">
              {kpi.value}
            </p>
            <p className="text-[11px] text-[var(--muted)] mt-1">{kpi.sub}</p>
          </motion.div>
        ))}
      </div>

      {/* Team Standings & Elo */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 glass-card p-6">
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
            Franchises
          </p>
          <h3 className="text-xl font-light tracking-tight text-[var(--text)] mt-0.5 mb-4">
            Career Win Rate
          </h3>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={standings}
                margin={{ top: 8, right: 12, left: -12, bottom: 8 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--chart-grid)"
                  vertical={false}
                />
                <XAxis
                  dataKey="short_name"
                  stroke="var(--muted)"
                  tick={{ fill: "var(--text)", fontSize: 11 }}
                />
                <YAxis
                  stroke="var(--muted)"
                  tick={{ fill: "var(--muted)", fontSize: 11 }}
                  domain={[35, 70]}
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
                  formatter={(value: number, _name: string, props: any) => [
                    `${value}% • Elo ${props.payload.elo_rating}`,
                    props.payload.name,
                  ]}
                />
                <Bar dataKey="win_rate" radius={[8, 8, 0, 0]} fillOpacity={0.8}>
                  {standings.map((entry, idx) => (
                    <Cell key={idx} fill={entry.primary_color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="lg:col-span-5 glass-card p-6">
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
            Power Index
          </p>
          <h3 className="text-xl font-light tracking-tight text-[var(--text)] mt-0.5 mb-4">
            Elo & Recent Form
          </h3>
          <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
            {standings.map((team) => (
              <div
                key={team.name}
                className="flex items-center justify-between p-2.5 rounded-[16px] bg-[var(--surface-subtle)] border border-[var(--border)]"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <TeamLogo teamName={team.name} teams={teams} size="sm" />
                  <div className="truncate">
                    <p className="text-sm font-medium text-[var(--text)] truncate">
                      {team.short_name}
                    </p>
                    <p className="text-[11px] text-[var(--muted)] tabular-nums">
                      Elo {team.elo_rating.toFixed(0)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {team.recent_form.map((res, i) => (
                    <span
                      key={i}
                      className={`w-5 h-5 rounded-full text-[10px] font-semibold flex items-center justify-center ${
                        res === 1
                          ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300 border border-emerald-500/30"
                          : "bg-[var(--surface-elevated)] text-[var(--muted)] border border-[var(--border)]"
                      }`}
                    >
                      {res === 1 ? "W" : "L"}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Head-to-Head Explorer */}
      <div className="glass-card p-6 md:p-8">
        <div className="grid grid-cols-1 md:grid-cols-3 items-end gap-4 mb-6">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
              Rivalry
            </p>
            <h3 className="text-xl font-light tracking-tight text-[var(--text)] mt-0.5">
              Head-to-Head
            </h3>
          </div>
          <CustomSelect
            label="Team A"
            value={h2hTeam1}
            options={teamOptions1}
            onChange={setH2hTeam1}
            teams={teams}
          />
          <CustomSelect
            label="Team B"
            value={h2hTeam2}
            options={teamOptions2}
            onChange={setH2hTeam2}
            teams={teams}
          />
        </div>

        {loadingH2h ? (
          <div className="h-32 rounded-[20px] bg-[var(--surface-subtle)] animate-pulse" />
        ) : h2hData ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
            <div className="p-5 rounded-[20px] bg-[var(--surface-subtle)] border border-[var(--border)] flex items-center justify-between">
              <div className="flex items-center gap-3">
                <TeamLogo teamName={h2hData.team1} teams={teams} size="md" />
                <div>
                  <p className="text-xs text-[var(--muted)]">{t1Meta.short_name}</p>
                  <p className="text-2xl font-light text-[var(--text)] tabular-nums">
                    {h2hData.team1_wins} wins
                  </p>
                </div>
              </div>
              <span className="text-xs font-medium text-[var(--muted)] tabular-nums">
                {h2hData.team1_win_rate}%
              </span>
            </div>

            <div className="p-5 rounded-[20px] bg-[var(--surface-subtle)] border border-[var(--border)] text-center">
              <p className="text-xs text-[var(--muted)]">Total Encounters</p>
              <p className="text-2xl font-light text-[var(--text)] mt-0.5 tabular-nums">
                {h2hData.total_matches}
              </p>
              <p className="text-[11px] text-[var(--muted)] mt-0.5 tabular-nums">
                Avg Target {h2hData.avg_target_runs}
              </p>
            </div>

            <div className="p-5 rounded-[20px] bg-[var(--surface-subtle)] border border-[var(--border)] flex items-center justify-between">
              <span className="text-xs font-medium text-[var(--muted)] tabular-nums">
                {h2hData.team2_win_rate}%
              </span>
              <div className="flex items-center gap-3 text-right">
                <div>
                  <p className="text-xs text-[var(--muted)]">{t2Meta.short_name}</p>
                  <p className="text-2xl font-light text-[var(--text)] tabular-nums">
                    {h2hData.team2_wins} wins
                  </p>
                </div>
                <TeamLogo teamName={h2hData.team2} teams={teams} size="md" />
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {/* Venue Chase Bias + Season Target Trend */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card p-6">
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
            Venues
          </p>
          <h3 className="text-xl font-light tracking-tight text-[var(--text)] mt-0.5 mb-4">
            Chase Win Rate (%)
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={venueStats}
                margin={{ top: 8, right: 12, left: -12, bottom: 8 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--chart-grid)"
                  vertical={false}
                />
                <XAxis
                  dataKey="name"
                  stroke="var(--muted)"
                  tick={{ fill: "var(--text)", fontSize: 11 }}
                />
                <YAxis
                  stroke="var(--muted)"
                  tick={{ fill: "var(--muted)", fontSize: 11 }}
                  domain={[0, 100]}
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
                  dataKey="chase_win_rate"
                  name="Chase Win %"
                  fill="var(--accent)"
                  fillOpacity={0.8}
                  radius={[8, 8, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-card p-6">
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
            Trends
          </p>
          <h3 className="text-xl font-light tracking-tight text-[var(--text)] mt-0.5 mb-4">
            Par Target by Season
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={seasonTrends}
                margin={{ top: 8, right: 12, left: -12, bottom: 8 }}
              >
                <defs>
                  <linearGradient id="appleAreaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="var(--accent)" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--chart-grid)"
                  vertical={false}
                />
                <XAxis
                  dataKey="season"
                  stroke="var(--muted)"
                  tick={{ fill: "var(--text)", fontSize: 11 }}
                />
                <YAxis
                  stroke="var(--muted)"
                  tick={{ fill: "var(--muted)", fontSize: 11 }}
                  domain={[145, 200]}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--tooltip-bg)",
                    borderColor: "var(--border)",
                    borderRadius: "16px",
                    color: "var(--text)",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="avg_target_runs"
                  name="Avg Target"
                  stroke="var(--accent)"
                  strokeWidth={2}
                  fill="url(#appleAreaGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
