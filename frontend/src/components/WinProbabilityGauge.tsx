"use client";

import React, { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { RotateCcw, Sparkles } from "lucide-react";
import { getTeamMeta } from "@/lib/constants";
import { PredictResponse, TeamInfo } from "@/lib/types";
import { TeamLogo } from "./TeamLogo";

interface WinProbabilityGaugeProps {
  prediction: PredictResponse;
  teams: TeamInfo[];
  onReset?: () => void;
  onInspectInsights?: () => void;
}

/**
 * Smooth 60fps count-up hook for win percentages.
 */
function useCountUp(target: number, durationMs = 950, reduceMotion = false): number {
  const [value, setValue] = useState(reduceMotion ? target : 0);

  useEffect(() => {
    if (reduceMotion) {
      setValue(target);
      return;
    }
    let frameId: number;
    const start = performance.now();

    const tick = (now: number) => {
      const progress = Math.min((now - start) / durationMs, 1);
      // Cubic ease-out
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Number((target * eased).toFixed(1)));
      if (progress < 1) {
        frameId = requestAnimationFrame(tick);
      }
    };

    frameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId);
  }, [target, durationMs, reduceMotion]);

  return value;
}

export function WinProbabilityGauge({
  prediction,
  teams,
  onReset,
  onInspectInsights,
}: WinProbabilityGaugeProps) {
  const reduceMotion = !!useReducedMotion();
  const t1 = getTeamMeta(prediction.team1, teams);
  const t2 = getTeamMeta(prediction.team2, teams);

  const t1IsWinner = prediction.team1_win_prob >= prediction.team2_win_prob;
  const winnerMeta = t1IsWinner ? t1 : t2;
  const winnerProb = Math.max(prediction.team1_win_prob, prediction.team2_win_prob);

  const countT1 = useCountUp(prediction.team1_win_prob, 950, reduceMotion);
  const countT2 = useCountUp(prediction.team2_win_prob, 950, reduceMotion);
  const countWinner = useCountUp(winnerProb, 950, reduceMotion);

  // Full circular ring geometry
  const size = 188;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const winnerOffset = circumference - (winnerProb / 100) * circumference;

  return (
    <motion.div
      layoutId="predict-stage-card"
      initial={
        reduceMotion
          ? { opacity: 0 }
          : { opacity: 0, scale: 0.88, filter: "blur(8px)" }
      }
      animate={
        reduceMotion
          ? { opacity: 1 }
          : { opacity: 1, scale: 1, filter: "blur(0px)" }
      }
      transition={{ type: "spring", stiffness: 260, damping: 26 }}
      className="glass-card p-8 md:p-10 relative overflow-hidden max-w-2xl mx-auto"
    >
      {/* Subtle ambient glow of the winning team */}
      <div
        className="pointer-events-none absolute -top-28 left-1/2 -translate-x-1/2 w-96 h-96 rounded-full blur-3xl transition-opacity duration-700"
        style={{
          background: `radial-gradient(circle, ${winnerMeta.primary_color}, transparent 70%)`,
          opacity: "var(--glow-opacity)",
        }}
      />

      {/* Minimal Header Pill */}
      <div className="relative z-10 flex items-center justify-between gap-2 mb-8">
        <span className="glass-pill px-3 py-1 text-xs font-medium text-[var(--muted)]">
          {prediction.venue} • {prediction.season}
        </span>
        <span className="glass-pill px-3 py-1 text-xs font-medium text-[var(--muted)]">
          {prediction.confidence}
        </span>
      </div>

      {/* Main Matchup Stage: Team A — Probability Ring — Team B */}
      <div className="relative z-10 grid grid-cols-1 sm:grid-cols-3 items-center gap-8 my-2">
        {/* Team 1 (Glides in from left; lifts if winner, dims if loser) */}
        <motion.div
          initial={reduceMotion ? { opacity: 0 } : { x: -32, opacity: 0 }}
          animate={{
            x: 0,
            y: t1IsWinner && !reduceMotion ? -4 : 0,
            scale: t1IsWinner && !reduceMotion ? 1.03 : 1,
            opacity: t1IsWinner ? 1 : 0.56,
          }}
          transition={{ type: "spring", stiffness: 240, damping: 22, delay: 0.08 }}
          className="flex flex-col items-center text-center"
        >
          <TeamLogo
            teamName={t1.name}
            teams={teams}
            size="lg"
            glow={t1IsWinner}
          />
          <p className="mt-3 text-sm font-medium text-[var(--text)]">
            {t1.short_name}
          </p>
          <p className="text-2xl font-light tracking-tight text-[var(--text)] mt-0.5 tabular-nums">
            {countT1.toFixed(1)}%
          </p>
          {t1IsWinner && (
            <span
              className="mt-1.5 text-[11px] font-medium px-2.5 py-0.5 rounded-full"
              style={{
                backgroundColor: `${t1.primary_color}18`,
                color: "var(--text)",
                border: `1px solid ${t1.primary_color}45`,
              }}
            >
              Favored
            </span>
          )}
        </motion.div>

        {/* Center Self-Drawing Probability Ring */}
        <div className="flex flex-col items-center justify-center">
          <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
            <svg width={size} height={size} className="-rotate-90">
              {/* Subtle Track */}
              <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke="var(--border)"
                strokeWidth={strokeWidth}
              />
              {/* Animated Winner Probability Arc */}
              <motion.circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke={winnerMeta.primary_color}
                strokeWidth={strokeWidth}
                strokeLinecap="round"
                strokeDasharray={circumference}
                initial={{ strokeDashoffset: reduceMotion ? winnerOffset : circumference }}
                animate={{ strokeDashoffset: winnerOffset }}
                transition={{ duration: 1.0, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
              />
            </svg>

            <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-4">
              <span className="text-[11px] uppercase tracking-widest text-[var(--muted)] font-medium">
                {winnerMeta.short_name} Win
              </span>
              <span className="text-3xl font-light tracking-tight text-[var(--text)] mt-0.5 tabular-nums">
                {countWinner.toFixed(1)}%
              </span>
            </div>
          </div>
        </div>

        {/* Team 2 (Glides in from right; lifts if winner, dims if loser) */}
        <motion.div
          initial={reduceMotion ? { opacity: 0 } : { x: 32, opacity: 0 }}
          animate={{
            x: 0,
            y: !t1IsWinner && !reduceMotion ? -4 : 0,
            scale: !t1IsWinner && !reduceMotion ? 1.03 : 1,
            opacity: !t1IsWinner ? 1 : 0.56,
          }}
          transition={{ type: "spring", stiffness: 240, damping: 22, delay: 0.08 }}
          className="flex flex-col items-center text-center"
        >
          <TeamLogo
            teamName={t2.name}
            teams={teams}
            size="lg"
            glow={!t1IsWinner}
          />
          <p className="mt-3 text-sm font-medium text-[var(--text)]">
            {t2.short_name}
          </p>
          <p className="text-2xl font-light tracking-tight text-[var(--text)] mt-0.5 tabular-nums">
            {countT2.toFixed(1)}%
          </p>
          {!t1IsWinner && (
            <span
              className="mt-1.5 text-[11px] font-medium px-2.5 py-0.5 rounded-full"
              style={{
                backgroundColor: `${t2.primary_color}18`,
                color: "var(--text)",
                border: `1px solid ${t2.primary_color}45`,
              }}
            >
              Favored
            </span>
          )}
        </motion.div>
      </div>

      {/* Staggered Insight Chips (Step 7) */}
      <motion.div
        initial="hidden"
        animate="visible"
        variants={{
          hidden: {},
          visible: {
            transition: {
              staggerChildren: reduceMotion ? 0 : 0.09,
              delayChildren: reduceMotion ? 0 : 0.28,
            },
          },
        }}
        className="relative z-10 mt-8 pt-6 border-t border-[var(--border)]"
      >
        <p className="text-xs font-medium text-[var(--muted)] text-center mb-3">
          Key Drivers
        </p>
        <div className="flex flex-wrap items-center justify-center gap-2">
          {prediction.explanations.slice(0, 4).map((exp) => {
            const favMeta = getTeamMeta(exp.favored_team, teams);
            return (
              <motion.div
                key={exp.feature}
                variants={{
                  hidden: reduceMotion ? { opacity: 0 } : { opacity: 0, y: 10 },
                  visible: { opacity: 1, y: 0 },
                }}
                transition={{ type: "spring", stiffness: 300, damping: 24 }}
                className="glass-pill px-3.5 py-1.5 text-xs flex items-center gap-2"
              >
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: favMeta.primary_color }}
                />
                <span className="text-[var(--text)] font-medium">
                  {exp.display_name}
                </span>
                <span className="text-[var(--muted)] tabular-nums">
                  {favMeta.short_name} +{exp.abs_impact.toFixed(1)}%
                </span>
              </motion.div>
            );
          })}
        </div>
      </motion.div>

      {/* Step 8: "Predict again" + "Explore Why" actions softly reappear */}
      <motion.div
        initial={{ opacity: 0, y: reduceMotion ? 0 : 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: reduceMotion ? 0 : 0.55 }}
        className="relative z-10 mt-8 flex flex-wrap items-center justify-center gap-3"
      >
        {onReset && (
          <motion.button
            type="button"
            whileHover={{ y: -1 }}
            whileTap={{ scale: 0.96 }}
            onClick={onReset}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[var(--text)] text-[var(--bg)] text-sm font-medium shadow-sm transition-opacity hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Predict again
          </motion.button>
        )}

        {onInspectInsights && (
          <motion.button
            type="button"
            whileHover={{ y: -1 }}
            whileTap={{ scale: 0.96 }}
            onClick={onInspectInsights}
            className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-full bg-[var(--surface-subtle)] hover:bg-[var(--surface-elevated)] border border-[var(--border)] text-sm font-medium text-[var(--text)] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            <Sparkles className="w-3.5 h-3.5 text-[var(--accent)]" />
            Why this prediction
          </motion.button>
        )}
      </motion.div>
    </motion.div>
  );
}
