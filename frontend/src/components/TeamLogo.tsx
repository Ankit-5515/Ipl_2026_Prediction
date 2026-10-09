"use client";

import React, { useEffect, useId, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Check, ChevronDown, MapPin } from "lucide-react";
import { getTeamMeta } from "@/lib/constants";
import { TeamInfo } from "@/lib/types";

interface TeamLogoProps {
  teamName: string;
  teams?: TeamInfo[];
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  glow?: boolean;
}

const SIZE_CLASSES = {
  xs: "w-6 h-6 text-[10px] rounded-lg",
  sm: "w-8 h-8 text-xs rounded-[10px]",
  md: "w-11 h-11 text-xs rounded-[14px]",
  lg: "w-14 h-14 text-sm rounded-[18px]",
  xl: "w-18 h-18 text-base rounded-[22px]",
};

/**
 * Apple-style Frosted Team Emblem.
 * Uses team color strictly as a soft radial inner glow and delicate ring accent,
 * never as a harsh flat block fill.
 */
export function TeamLogo({
  teamName,
  teams,
  size = "md",
  glow = false,
}: TeamLogoProps) {
  const meta = getTeamMeta(teamName, teams);

  return (
    <div
      className={`${SIZE_CLASSES[size]} relative inline-flex items-center justify-center font-semibold tracking-tight select-none shrink-0 bg-[var(--surface-elevated)] text-[var(--text)] transition-transform duration-200`}
      style={{
        border: `1px solid ${meta.primary_color}40`,
        boxShadow: glow
          ? `0 8px 28px -4px ${meta.primary_color}45, 0 0 0 1px ${meta.primary_color}25 inset`
          : `0 2px 8px -2px rgba(0,0,0,0.08), 0 0 0 1px ${meta.primary_color}18 inset`,
      }}
      aria-label={meta.name}
    >
      {/* Soft radial team-color aura inside glass squircle */}
      <span
        className="pointer-events-none absolute inset-0 rounded-[inherit] opacity-25"
        style={{
          background: `radial-gradient(circle at 30% 25%, ${meta.primary_color}, transparent 75%)`,
        }}
      />
      {/* Subtle accent dot */}
      <span
        className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: meta.primary_color }}
      />
      <span className="relative z-10 font-bold tracking-tight">
        {meta.short_name}
      </span>
    </div>
  );
}

export interface SelectOption {
  value: string;
  label: string;
  sublabel?: string;
  disabled?: boolean;
  teamName?: string;
}

interface CustomSelectProps {
  label: string;
  value: string;
  options: SelectOption[];
  onChange: (value: string) => void;
  teams?: TeamInfo[];
  iconType?: "team" | "venue";
}

/**
 * Accessible custom select dropdown with team logos, spring physics, and WCAG AA contrast.
 */
export function CustomSelect({
  label,
  value,
  options,
  onChange,
  teams,
  iconType = "team",
}: CustomSelectProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const reduceMotion = useReducedMotion();
  const id = useId();

  const selected = options.find((o) => o.value === value) || options[0];

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div ref={containerRef} className="relative">
      <label
        id={`${id}-label`}
        className="block text-xs font-medium text-[var(--muted)] mb-2"
      >
        {label}
      </label>

      <button
        type="button"
        aria-labelledby={`${id}-label`}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
        className="w-full flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-[16px] bg-[var(--surface-subtle)] hover:bg-[var(--surface-elevated)] border border-[var(--border)] text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
      >
        <div className="flex items-center gap-3 min-w-0">
          {iconType === "team" ? (
            <TeamLogo
              teamName={selected?.teamName || selected?.value || ""}
              teams={teams}
              size="sm"
            />
          ) : (
            <div className="w-8 h-8 rounded-[10px] bg-[var(--surface-elevated)] border border-[var(--border)] flex items-center justify-center text-[var(--muted)] shrink-0">
              <MapPin className="w-4 h-4" />
            </div>
          )}
          <div className="truncate">
            <p className="text-sm font-medium text-[var(--text)] truncate">
              {selected?.label}
            </p>
            {selected?.sublabel && (
              <p className="text-[11px] text-[var(--muted)] truncate">
                {selected.sublabel}
              </p>
            )}
          </div>
        </div>

        <ChevronDown
          className={`w-4 h-4 text-[var(--muted)] shrink-0 transition-transform duration-200 ${
            open ? "rotate-180 text-[var(--text)]" : ""
          }`}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.ul
            role="listbox"
            aria-labelledby={`${id}-label`}
            initial={
              reduceMotion ? { opacity: 0 } : { opacity: 0, y: -6, scale: 0.98 }
            }
            animate={
              reduceMotion ? { opacity: 1 } : { opacity: 1, y: 0, scale: 1 }
            }
            exit={
              reduceMotion ? { opacity: 0 } : { opacity: 0, y: -4, scale: 0.98 }
            }
            transition={{ type: "spring", stiffness: 420, damping: 30 }}
            className="absolute z-50 mt-2 w-full max-h-64 overflow-y-auto rounded-[20px] bg-[var(--surface-elevated)] backdrop-blur-2xl border border-[var(--border)] shadow-floating p-1.5 focus:outline-none"
          >
            {options.map((opt) => {
              const isSelected = opt.value === value;
              return (
                <li key={opt.value} role="option" aria-selected={isSelected}>
                  <button
                    type="button"
                    disabled={opt.disabled}
                    onClick={() => {
                      if (!opt.disabled) {
                        onChange(opt.value);
                        setOpen(false);
                      }
                    }}
                    className={`w-full flex items-center justify-between gap-2.5 px-3 py-2 rounded-[12px] text-left transition-colors ${
                      opt.disabled
                        ? "opacity-40 cursor-not-allowed"
                        : isSelected
                        ? "bg-[var(--accent-soft)] text-[var(--text)]"
                        : "hover:bg-[var(--surface-subtle)] text-[var(--text)]"
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      {iconType === "team" && (
                        <TeamLogo
                          teamName={opt.teamName || opt.value}
                          teams={teams}
                          size="xs"
                        />
                      )}
                      <div className="truncate">
                        <span className="text-sm font-medium block truncate">
                          {opt.label}
                        </span>
                        {opt.sublabel && (
                          <span className="text-[11px] text-[var(--muted)] block truncate">
                            {opt.sublabel}
                          </span>
                        )}
                      </div>
                    </div>

                    {isSelected && (
                      <Check className="w-4 h-4 text-[var(--accent)] shrink-0" />
                    )}
                  </button>
                </li>
              );
            })}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}
