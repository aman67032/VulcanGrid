"use client";

import React from "react";
import { StatsData, HotspotClass } from "../types";

interface TopStatsBarProps {
  stats: StatsData | null;
  wsConnected: boolean;
  selectedClassFilter: string;
  onSelectClassFilter: (cls: string) => void;
  onSync?: () => void;
  isSyncing?: boolean;
}

export const TopStatsBar: React.FC<TopStatsBarProps> = ({
  stats,
  wsConnected,
  selectedClassFilter,
  onSelectClassFilter,
  onSync,
  isSyncing = false,
}) => {
  const classCounts = stats?.class_counts || {
    controlled_flare: 0,
    industrial_fire: 0,
    forest_fire: 0,
    false_alarm: 0,
  };

  const isDemoMode = stats?.demo_mode !== false;

  return (
    <header className="h-16 bg-slate-900 border-b border-slate-800 px-4 flex items-center justify-between text-xs sm:text-sm select-none z-20 shrink-0">
      {/* Brand & Live Indicator */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-red-600 rounded-sm animate-pulse" />
          <span className="font-bold text-base tracking-wider text-slate-100 uppercase">
            VulcanGrid
          </span>
        </div>
        <span className="text-slate-500 font-mono">|</span>
        <div className="flex items-center space-x-2 px-2.5 py-1 rounded bg-slate-950 border border-slate-800 font-mono">
          <span
            className={`w-2 h-2 rounded-full ${
              wsConnected ? "bg-emerald-500 animate-ping" : "bg-amber-500"
            }`}
          />
          <span className={wsConnected ? "text-emerald-400 font-semibold" : "text-amber-400"}>
            {wsConnected ? "LIVE STREAM" : "CONNECTING"}
          </span>
        </div>

        {/* Dynamic Mode Badge */}
        {isDemoMode ? (
          <span className="hidden md:inline-flex items-center space-x-1.5 px-2 py-0.5 rounded text-[11px] font-mono bg-amber-950/60 text-amber-300 border border-amber-800/80">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
            <span>DEMO STREAM</span>
          </span>
        ) : (
          <span className="hidden md:inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded text-[11px] font-mono bg-emerald-950/80 text-emerald-300 border border-emerald-700/80 shadow-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>NASA VIIRS LIVE</span>
          </span>
        )}

        {/* Sync Satellite Trigger */}
        {onSync && (
          <button
            onClick={onSync}
            disabled={isSyncing}
            title={isDemoMode ? "Generate fresh synthetic satellite batch" : "Fetch latest real-time observations from NASA VIIRS"}
            className="flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 active:scale-95 border border-slate-700 text-slate-200 text-xs font-mono transition-all disabled:opacity-50 cursor-pointer"
          >
            <svg
              className={`w-3.5 h-3.5 ${isSyncing ? "animate-spin text-blue-400" : "text-slate-400"}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            <span>{isSyncing ? "Syncing..." : "Sync FIRMS"}</span>
          </button>
        )}
      </div>

      {/* Metrics Row */}
      <div className="hidden lg:flex items-center space-x-6">
        <div className="flex flex-col text-right">
          <span className="text-slate-400 text-[11px] uppercase tracking-wider">Total Evaluated</span>
          <span className="font-mono text-sm font-semibold text-slate-100">
            {stats?.total_hotspots_evaluated ?? 0}
          </span>
        </div>

        <div className="flex flex-col text-right">
          <span className="text-slate-400 text-[11px] uppercase tracking-wider">H3 Load Reduced</span>
          <span className="font-mono text-sm font-semibold text-emerald-400">
            {stats?.pct_cells_skipped ?? 0}% skipped
          </span>
        </div>

        <div className="flex flex-col text-right">
          <span className="text-slate-400 text-[11px] uppercase tracking-wider">Avg Latency</span>
          <span className="font-mono text-sm font-semibold text-blue-400">
            {stats?.avg_latency_ms ?? 0} ms
          </span>
        </div>
      </div>

      {/* Class Counts & Filter Tabs */}
      <div className="flex items-center space-x-1.5 font-mono">
        <button
          onClick={() => onSelectClassFilter("ALL")}
          className={`px-2.5 py-1 rounded border text-xs transition-colors ${
            selectedClassFilter === "ALL"
              ? "bg-slate-700 text-white border-slate-500"
              : "bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700"
          }`}
        >
          ALL ({stats?.total_alerts ?? 0})
        </button>

        <button
          onClick={() => onSelectClassFilter("controlled_flare")}
          className={`px-2.5 py-1 rounded border text-xs transition-colors flex items-center space-x-1.5 ${
            selectedClassFilter === "controlled_flare"
              ? "bg-emerald-950/80 text-emerald-300 border-emerald-500"
              : "bg-slate-950 text-slate-400 border-slate-800 hover:border-emerald-800"
          }`}
        >
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span>FLARE ({classCounts.controlled_flare})</span>
        </button>

        <button
          onClick={() => onSelectClassFilter("industrial_fire")}
          className={`px-2.5 py-1 rounded border text-xs transition-colors flex items-center space-x-1.5 ${
            selectedClassFilter === "industrial_fire"
              ? "bg-red-950/80 text-red-300 border-red-500"
              : "bg-slate-950 text-slate-400 border-slate-800 hover:border-red-800"
          }`}
        >
          <span className="w-2 h-2 rounded-full bg-red-500" />
          <span>IND FIRE ({classCounts.industrial_fire})</span>
        </button>

        <button
          onClick={() => onSelectClassFilter("forest_fire")}
          className={`px-2.5 py-1 rounded border text-xs transition-colors flex items-center space-x-1.5 ${
            selectedClassFilter === "forest_fire"
              ? "bg-orange-950/80 text-orange-300 border-orange-500"
              : "bg-slate-950 text-slate-400 border-slate-800 hover:border-orange-800"
          }`}
        >
          <span className="w-2 h-2 rounded-full bg-orange-500" />
          <span>WILDFIRE ({classCounts.forest_fire})</span>
        </button>

        <button
          onClick={() => onSelectClassFilter("false_alarm")}
          className={`px-2.5 py-1 rounded border text-xs transition-colors flex items-center space-x-1.5 ${
            selectedClassFilter === "false_alarm"
              ? "bg-slate-800 text-slate-200 border-slate-500"
              : "bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700"
          }`}
        >
          <span className="w-2 h-2 rounded-full bg-slate-400" />
          <span>GLARE ({classCounts.false_alarm})</span>
        </button>
      </div>
    </header>
  );
};
