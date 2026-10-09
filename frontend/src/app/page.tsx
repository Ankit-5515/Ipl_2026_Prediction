"use client";

import React, { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowLeftRight, Moon, Sun } from "lucide-react";
import { api, buildClientFallbackPrediction } from "@/lib/api";
import { FALLBACK_TEAMS, FALLBACK_VENUES, getTeamMeta } from "@/lib/constants";
import {
  DashboardAnalytics,
  PredictionHistoryItem,
  PredictRequest,
  PredictResponse,
  TeamInfo,
  VenueInfo,
} from "@/lib/types";
import { CustomSelect } from "@/components/TeamLogo";
import { WinProbabilityGauge } from "@/components/WinProbabilityGauge";
import { ShapInsightsSection } from "@/components/ShapInsightsSection";
import { AnalyticsDashboardSection } from "@/components/AnalyticsDashboardSection";
import { HistorySection } from "@/components/HistorySection";
import { AboutModelSection } from "@/components/AboutModelSection";

export type ActiveTab =
  | "predictor"
  | "insights"
  | "analytics"
  | "history"
  | "about";

type PredictStage = "form" | "analyzing" | "result";

interface MainAppProps {
  initialTab?: ActiveTab;
}

const NAV_TABS: { id: ActiveTab; label: string }[] = [
  { id: "predictor", label: "Predict" },
  { id: "insights", label: "Insights" },
  { id: "analytics", label: "Analytics" },
  { id: "history", label: "History" },
  { id: "about", label: "About" },
];

export function StadiumApp({ initialTab = "predictor" }: MainAppProps) {
  const reduceMotion = !!useReducedMotion();
  const [activeTab, setActiveTab] = useState<ActiveTab>(initialTab);
  const [isDark, setIsDark] = useState<boolean>(true);

  // Data state
  const [teams, setTeams] = useState<TeamInfo[]>(FALLBACK_TEAMS);
  const [venues, setVenues] = useState<VenueInfo[]>(FALLBACK_VENUES);
  const [analytics, setAnalytics] = useState<DashboardAnalytics | null>(null);
  const [history, setHistory] = useState<PredictionHistoryItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);

  // Centered Predict Card state
  const [team1, setTeam1] = useState<string>("Chennai Super Kings");
  const [team2, setTeam2] = useState<string>("Mumbai Indians");
  const [venue, setVenue] = useState<string>("Chennai");
  const [tossWinner, setTossWinner] = useState<string>("Chennai Super Kings");
  const [tossDecision, setTossDecision] = useState<"field" | "bat">("field");
  const [season] = useState<number>(2026);

  // Signature animation stage: "form" -> "analyzing" -> "result"
  const [stage, setStage] = useState<PredictStage>("form");
  const [buttonMorphing, setButtonMorphing] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [prediction, setPrediction] = useState<PredictResponse>(() =>
    buildClientFallbackPrediction({
      team1: "Chennai Super Kings",
      team2: "Mumbai Indians",
      venue: "Chennai",
      toss_winner: "Chennai Super Kings",
      toss_decision: "field",
      season: 2026,
    })
  );

  // Sync theme with system preference + localStorage without flash
  useEffect(() => {
    const root = document.documentElement;
    setIsDark(root.classList.contains("dark"));

    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const handleMediaChange = (e: MediaQueryListEvent) => {
      const stored = localStorage.getItem("ipl-theme");
      if (!stored || stored === "system") {
        root.classList.remove("light", "dark");
        root.classList.add(e.matches ? "dark" : "light");
        setIsDark(e.matches);
      }
    };
    media.addEventListener("change", handleMediaChange);
    return () => media.removeEventListener("change", handleMediaChange);
  }, []);

  const toggleTheme = () => {
    const nextDark = !isDark;
    const root = document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(nextDark ? "dark" : "light");
    localStorage.setItem("ipl-theme", nextDark ? "dark" : "light");
    setIsDark(nextDark);
  };

  // Instant validation: keep tossWinner synced with active matchup
  useEffect(() => {
    if (tossWinner !== team1 && tossWinner !== team2) {
      setTossWinner(team1);
    }
  }, [team1, team2, tossWinner]);

  const fetchHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const items = await api.getHistory(25);
      setHistory(items);
    } catch {
      // silent fallback
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  // Hydrate live backend data on mount
  useEffect(() => {
    let mounted = true;
    async function hydrate() {
      try {
        const [teamsData, venuesData, dashData] = await Promise.all([
          api.getTeams(true),
          api.getVenues(),
          api.getDashboardAnalytics(),
        ]);
        if (!mounted) return;
        if (teamsData.length) setTeams(teamsData);
        if (venuesData.length) setVenues(venuesData);
        setAnalytics(dashData);
        fetchHistory();
      } catch {
        // fallback data already loaded
      }
    }
    hydrate();
    return () => {
      mounted = false;
    };
  }, [fetchHistory]);

  const handlePredict = async () => {
    if (team1 === team2) {
      setErrorMsg("Select two different teams.");
      return;
    }
    setErrorMsg(null);
    setButtonMorphing(true);

    const req: PredictRequest = {
      team1,
      team2,
      venue,
      toss_winner: tossWinner,
      toss_decision: tossDecision,
      season,
    };

    // Step 1 -> Step 2 & 3: Morph button briefly, then transition to breathing orb
    const morphDelay = reduceMotion ? 60 : 220;
    const orbDuration = reduceMotion ? 150 : 720;

    setTimeout(() => {
      setStage("analyzing");
    }, morphDelay);

    const startTime = performance.now();
    let result: PredictResponse;
    try {
      result = await api.predictMatch(req);
      fetchHistory();
    } catch {
      result = buildClientFallbackPrediction(req);
    }

    const elapsed = performance.now() - startTime;
    const remaining = Math.max(0, morphDelay + orbDuration - elapsed);

    setTimeout(() => {
      setPrediction(result);
      setButtonMorphing(false);
      setStage("result");
    }, remaining);
  };

  const handleSwapTeams = () => {
    const prev1 = team1;
    const prev2 = team2;
    setTeam1(prev2);
    setTeam2(prev1);
    setErrorMsg(null);
  };

  const t1Meta = getTeamMeta(team1, teams);
  const t2Meta = getTeamMeta(team2, teams);

  const teamAOptions = teams.map((t) => ({
    value: t.name,
    label: t.name,
    sublabel: `${t.short_name} • Elo ${t.elo_rating.toFixed(0)}`,
    disabled: t.name === team2,
    teamName: t.name,
  }));

  const teamBOptions = teams.map((t) => ({
    value: t.name,
    label: t.name,
    sublabel: `${t.short_name} • Elo ${t.elo_rating.toFixed(0)}`,
    disabled: t.name === team1,
    teamName: t.name,
  }));

  const venueOptions = venues.map((v) => ({
    value: v.name,
    label: v.name,
    sublabel: `Avg Target ${v.avg_target_runs} • Chase ${v.chase_win_rate}%`,
  }));

  const tossOptions = [
    { value: team1, label: t1Meta.name, sublabel: t1Meta.short_name, teamName: team1 },
    { value: team2, label: t2Meta.name, sublabel: t2Meta.short_name, teamName: team2 },
  ];

  return (
    <div className="min-h-screen flex flex-col relative overflow-x-hidden">
      {/* Subtle Ambient Background Glows (Team Colors Only as Soft Accents) */}
      <div
        className="pointer-events-none fixed inset-0 overflow-hidden z-0 transition-opacity duration-700"
        style={{
          opacity: stage === "analyzing" ? 1 : 0.65,
        }}
      >
        <div
          className="absolute -top-32 left-1/4 w-[420px] h-[420px] rounded-full blur-[120px] transition-colors duration-700"
          style={{
            backgroundColor: t1Meta.primary_color,
            opacity: "var(--glow-opacity)",
          }}
        />
        <div
          className="absolute top-24 right-1/4 w-[420px] h-[420px] rounded-full blur-[120px] transition-colors duration-700"
          style={{
            backgroundColor: t2Meta.primary_color,
            opacity: "var(--glow-opacity)",
          }}
        />
      </div>

      {/* Minimal Top Navigation Bar */}
      <header className="sticky top-0 z-40 border-b border-[var(--border)] bg-[var(--surface)] backdrop-blur-2xl">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
          <button
            type="button"
            onClick={() => {
              setActiveTab("predictor");
              setStage("form");
            }}
            className="text-sm font-semibold tracking-tight text-[var(--text)] flex items-center gap-2 focus:outline-none"
          >
            <span className="w-2 h-2 rounded-full bg-[var(--accent)]" />
            <span>IPL 2026</span>
          </button>

          {/* Segmented Pill Navigation */}
          <nav
            aria-label="Primary"
            className="flex items-center gap-1 p-1 rounded-full bg-[var(--surface-subtle)] border border-[var(--border)] overflow-x-auto"
          >
            {NAV_TABS.map((tab) => {
              const active = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`relative px-3.5 py-1 rounded-full text-xs font-medium transition-colors whitespace-nowrap focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
                    active
                      ? "text-[var(--text)]"
                      : "text-[var(--muted)] hover:text-[var(--text)]"
                  }`}
                >
                  {active && (
                    <motion.span
                      layoutId="active-nav-pill"
                      transition={{ type: "spring", stiffness: 380, damping: 30 }}
                      className="absolute inset-0 rounded-full bg-[var(--surface-elevated)] shadow-sm border border-[var(--border)] -z-10"
                    />
                  )}
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* Animated Theme Toggle */}
          <motion.button
            type="button"
            aria-label="Toggle color theme"
            whileTap={{ scale: 0.92 }}
            onClick={toggleTheme}
            className="w-8 h-8 rounded-full bg-[var(--surface-subtle)] hover:bg-[var(--surface-elevated)] border border-[var(--border)] flex items-center justify-center text-[var(--text)] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            <AnimatePresence mode="wait" initial={false}>
              <motion.span
                key={isDark ? "dark" : "light"}
                initial={{ opacity: 0, rotate: -45, scale: 0.7 }}
                animate={{ opacity: 1, rotate: 0, scale: 1 }}
                exit={{ opacity: 0, rotate: 45, scale: 0.7 }}
                transition={{ duration: 0.18 }}
              >
                {isDark ? (
                  <Sun className="w-4 h-4" />
                ) : (
                  <Moon className="w-4 h-4" />
                )}
              </motion.span>
            </AnimatePresence>
          </motion.button>
        </div>
      </header>

      {/* Main Content Stage */}
      <main className="relative z-10 flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 py-10 md:py-14">
        <AnimatePresence mode="wait">
          {activeTab === "predictor" && (
            <motion.div
              key="tab-predictor"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.22 }}
            >
              {/* Minimal Heading */}
              <div className="text-center mb-8">
                <h1 className="text-3xl sm:text-4xl font-light tracking-tight text-[var(--text)]">
                  Match Predictor
                </h1>
              </div>

              <AnimatePresence mode="wait">
                {/* STAGE 1: Centered Form Card */}
                {stage === "form" && (
                  <motion.div
                    key="stage-form"
                    layoutId="predict-stage-card"
                    initial={
                      reduceMotion
                        ? { opacity: 0 }
                        : { opacity: 0, scale: 0.97, filter: "blur(6px)" }
                    }
                    animate={
                      reduceMotion
                        ? { opacity: 1 }
                        : { opacity: 1, scale: 1, filter: "blur(0px)" }
                    }
                    exit={
                      reduceMotion
                        ? { opacity: 0 }
                        : { opacity: 0, scale: 0.94, filter: "blur(12px)" }
                    }
                    transition={{ type: "spring", stiffness: 280, damping: 28 }}
                    className="glass-card p-6 sm:p-8 max-w-xl mx-auto"
                  >
                    <div className="space-y-5">
                      {/* Team A & Team B Row */}
                      <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr] items-end gap-3">
                        <CustomSelect
                          label="Team A"
                          value={team1}
                          options={teamAOptions}
                          onChange={(val) => {
                            setTeam1(val);
                            const meta = getTeamMeta(val, teams);
                            if (meta.home_venue) setVenue(meta.home_venue);
                            setErrorMsg(null);
                          }}
                          teams={teams}
                        />

                        <motion.button
                          type="button"
                          aria-label="Swap teams"
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.94 }}
                          onClick={handleSwapTeams}
                          className="h-11 w-11 mx-auto sm:mb-0.5 rounded-[14px] bg-[var(--surface-subtle)] hover:bg-[var(--surface-elevated)] border border-[var(--border)] flex items-center justify-center text-[var(--muted)] hover:text-[var(--text)] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                        >
                          <ArrowLeftRight className="w-4 h-4" />
                        </motion.button>

                        <CustomSelect
                          label="Team B"
                          value={team2}
                          options={teamBOptions}
                          onChange={(val) => {
                            setTeam2(val);
                            setErrorMsg(null);
                          }}
                          teams={teams}
                        />
                      </div>

                      {/* Venue */}
                      <CustomSelect
                        label="Venue"
                        value={venue}
                        options={venueOptions}
                        onChange={setVenue}
                        iconType="venue"
                      />

                      {/* Toss Winner + Decision */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <CustomSelect
                          label="Toss Winner"
                          value={tossWinner}
                          options={tossOptions}
                          onChange={setTossWinner}
                          teams={teams}
                        />

                        <div>
                          <span className="block text-xs font-medium text-[var(--muted)] mb-2">
                            Toss Decision
                          </span>
                          <div className="grid grid-cols-2 gap-1.5 p-1 rounded-[16px] bg-[var(--surface-subtle)] border border-[var(--border)] h-[54px]">
                            {(["field", "bat"] as const).map((dec) => {
                              const selected = tossDecision === dec;
                              return (
                                <button
                                  key={dec}
                                  type="button"
                                  onClick={() => setTossDecision(dec)}
                                  className={`rounded-[12px] text-xs font-medium capitalize transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
                                    selected
                                      ? "bg-[var(--surface-elevated)] text-[var(--text)] shadow-sm border border-[var(--border)]"
                                      : "text-[var(--muted)] hover:text-[var(--text)]"
                                  }`}
                                >
                                  {dec === "field" ? "Field" : "Bat"}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      </div>

                      {errorMsg && (
                        <p
                          role="alert"
                          className="text-xs font-medium text-rose-500 text-center"
                        >
                          {errorMsg}
                        </p>
                      )}

                      {/* Big Predict Button -> Morphs into Ring Loader on Press */}
                      <div className="pt-2 flex justify-center">
                        <motion.button
                          type="button"
                          disabled={buttonMorphing}
                          whileHover={{ y: -1 }}
                          whileTap={{ scale: 0.96 }}
                          animate={{
                            width: buttonMorphing ? 52 : "100%",
                            borderRadius: buttonMorphing ? 9999 : 18,
                          }}
                          transition={{
                            type: "spring",
                            stiffness: 360,
                            damping: 28,
                          }}
                          onClick={handlePredict}
                          className="h-[52px] bg-[var(--text)] text-[var(--bg)] font-medium text-sm flex items-center justify-center shadow-sm hover:opacity-95 transition-opacity focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] overflow-hidden"
                        >
                          {buttonMorphing ? (
                            <span className="w-5 h-5 rounded-full border-2 border-[var(--bg)] border-t-transparent animate-spin" />
                          ) : (
                            <span>Predict</span>
                          )}
                        </motion.button>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* STAGE 2 & 3: Breathing Glowing Orb with "Analyzing" Shimmer */}
                {stage === "analyzing" && (
                  <motion.div
                    key="stage-orb"
                    layoutId="predict-stage-card"
                    initial={{ opacity: 0, scale: 0.85 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 1.05 }}
                    transition={{ type: "spring", stiffness: 260, damping: 24 }}
                    className="flex flex-col items-center justify-center py-20"
                  >
                    <div className="relative flex items-center justify-center w-36 h-36">
                      {/* Outer Breathing Aura */}
                      <motion.div
                        animate={
                          reduceMotion
                            ? { opacity: 0.5 }
                            : { scale: [0.92, 1.16, 0.92], opacity: [0.35, 0.65, 0.35] }
                        }
                        transition={{
                          duration: 1.8,
                          repeat: Infinity,
                          ease: "easeInOut",
                        }}
                        className="absolute inset-0 rounded-full blur-2xl"
                        style={{
                          background: `linear-gradient(135deg, ${t1Meta.primary_color}, ${t2Meta.primary_color})`,
                        }}
                      />

                      {/* Core Frosted Orb */}
                      <motion.div
                        animate={
                          reduceMotion ? {} : { scale: [0.96, 1.04, 0.96] }
                        }
                        transition={{
                          duration: 1.4,
                          repeat: Infinity,
                          ease: "easeInOut",
                        }}
                        className="relative w-24 h-24 rounded-full glass-card flex items-center justify-center"
                      >
                        <span className="w-8 h-8 rounded-full border-2 border-[var(--text)] border-t-transparent animate-spin opacity-80" />
                      </motion.div>
                    </div>

                    <p className="mt-6 text-xs font-medium tracking-widest uppercase text-[var(--muted)] animate-shimmer-text">
                      Analyzing
                    </p>
                  </motion.div>
                )}

                {/* STAGE 4–8: Expanded Result Card */}
                {stage === "result" && (
                  <WinProbabilityGauge
                    key="stage-result"
                    prediction={prediction}
                    teams={teams}
                    onReset={() => setStage("form")}
                    onInspectInsights={() => setActiveTab("insights")}
                  />
                )}
              </AnimatePresence>
            </motion.div>
          )}

          {activeTab === "insights" && (
            <motion.div
              key="tab-insights"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.22 }}
            >
              <ShapInsightsSection prediction={prediction} teams={teams} />
            </motion.div>
          )}

          {activeTab === "analytics" && (
            <motion.div
              key="tab-analytics"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.22 }}
            >
              <AnalyticsDashboardSection
                teams={teams}
                venues={venues}
                analytics={analytics}
              />
            </motion.div>
          )}

          {activeTab === "history" && (
            <motion.div
              key="tab-history"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.22 }}
            >
              <HistorySection
                history={history}
                teams={teams}
                loading={loadingHistory}
                onRefresh={fetchHistory}
                onSelectPrediction={(pred) => {
                  setPrediction(pred);
                  setStage("result");
                  setActiveTab("predictor");
                }}
              />
            </motion.div>
          )}

          {activeTab === "about" && (
            <motion.div
              key="tab-about"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.22 }}
            >
              <AboutModelSection analytics={analytics} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}

export default function HomePage() {
  return <StadiumApp initialTab="predictor" />;
}
