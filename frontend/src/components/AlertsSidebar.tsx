"use client";

import React from "react";
import { AlertItem, HotspotClass } from "../types";

interface AlertsSidebarProps {
  alerts: AlertItem[];
  selectedAlertId: string | null;
  onSelectAlert: (id: string) => void;
}

export const AlertsSidebar: React.FC<AlertsSidebarProps> = ({
  alerts,
  selectedAlertId,
  onSelectAlert,
}) => {
  const getClassBorder = (cls: HotspotClass) => {
    switch (cls) {
      case "controlled_flare":
        return "border-l-4 border-l-emerald-500 hover:bg-emerald-950/30";
      case "industrial_fire":
        return "border-l-4 border-l-red-500 hover:bg-red-950/30";
      case "forest_fire":
        return "border-l-4 border-l-orange-500 hover:bg-orange-950/30";
      case "false_alarm":
        return "border-l-4 border-l-slate-400 hover:bg-slate-800/50";
      default:
        return "border-l-4 border-l-slate-500 hover:bg-slate-800/50";
    }
  };

  const getClassBadge = (cls: HotspotClass) => {
    switch (cls) {
      case "controlled_flare":
        return <span className="text-emerald-400 font-bold">FLARE</span>;
      case "industrial_fire":
        return <span className="text-red-400 font-bold">IND FIRE</span>;
      case "forest_fire":
        return <span className="text-orange-400 font-bold">WILDFIRE</span>;
      case "false_alarm":
        return <span className="text-slate-400 font-bold">GLARE</span>;
    }
  };

  return (
    <aside className="w-80 bg-slate-900 border-l border-slate-800 flex flex-col z-20 shrink-0 select-none">
      {/* Header */}
      <div className="p-3.5 border-b border-slate-800 flex items-center justify-between font-mono text-xs">
        <span className="font-bold text-slate-200 uppercase tracking-wider">Active Alerts Stream</span>
        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
          {alerts.length} ITEMS
        </span>
      </div>

      {/* Alert Cards List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2 font-mono text-xs">
        {alerts.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            Waiting for live satellite stream...
          </div>
        ) : (
          alerts.map((item) => {
            const isSelected = item.id === selectedAlertId;
            const timeStr = new Date(item.acq_datetime).toLocaleTimeString();

            return (
              <div
                key={item.id}
                onClick={() => onSelectAlert(item.id)}
                className={`p-3 rounded bg-slate-950 border cursor-pointer transition-all ${
                  getClassBorder(item.predicted_class)
                } ${
                  isSelected
                    ? "border-slate-400 shadow-lg ring-1 ring-slate-400"
                    : "border-slate-800"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  {getClassBadge(item.predicted_class)}
                  <span className="text-[11px] text-slate-400">{timeStr}</span>
                </div>

                <div className="flex items-center justify-between text-slate-300 text-[11px]">
                  <span>FRP: <strong className="text-slate-100">{item.frp} MW</strong></span>
                  <span>CONF: <strong className="text-emerald-400">{(item.overall_confidence * 100).toFixed(0)}%</strong></span>
                </div>

                <div className="flex items-center justify-between text-slate-400 text-[10px] pt-1 mt-1 border-t border-slate-900">
                  <span>H3: {item.h3_index.slice(0, 8)}...</span>
                  <span>{item.latitude.toFixed(3)}°, {item.longitude.toFixed(3)}°</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
};
