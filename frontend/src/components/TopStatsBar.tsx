"use client";

import React from "react";
import { StatsData, HotspotClass } from "../types";

interface TopStatsBarProps {
  stats: StatsData | null;
  wsConnected: boolean;
  selectedClassFilter: string;
  onSelectClassFilter: (cls: string) => void;
}

export const TopStatsBar: React.FC<TopStatsBarProps> = ({
  stats,
  wsConnected,
  selectedClassFilter,
  onSelectClassFilter,
}) => {
  const classCounts = stats?.class_counts || {
    controlled_flare: 0,
    industrial_fire: 0,
    forest_fire: 0,
    false_alarm: 0,
  };

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
            {wsConnected ? "LIVE STREAM" : "RECONNECTING"}
          </span>
        </div>
        <span className="hidden md:inline-block px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-400 border border-slate-700">
          DEMO_MODE=true
        </span>
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
