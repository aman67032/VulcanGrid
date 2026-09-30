"use client";

import React, { useEffect, useState } from "react";
import { AlertItem, HotspotClass } from "../types";
import { ShapBarChart } from "./ShapBarChart";

interface AlertDetailPanelProps {
  alertId: string | null;
  onClose: () => void;
  showPlume: boolean;
  onTogglePlume: () => void;
}

export const AlertDetailPanel: React.FC<AlertDetailPanelProps> = ({
  alertId,
  onClose,
  showPlume,
  onTogglePlume,
}) => {
  const [detail, setDetail] = useState<AlertItem | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (!alertId) {
      setDetail(null);
      return;
    }
    setLoading(true);
    fetch(`/api/alerts/${alertId}`)
      .then((res) => res.json())
      .then((data) => {
        setDetail(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed fetching alert detail:", err);
        setLoading(false);
      });
  }, [alertId]);

  if (!alertId) return null;

  const getClassBadge = (cls: HotspotClass) => {
    switch (cls) {
      case "controlled_flare":
        return { label: "CONTROLLED FLARE", color: "bg-emerald-950 text-emerald-300 border-emerald-600" };
      case "industrial_fire":
        return { label: "INDUSTRIAL ACCIDENT / FIRE", color: "bg-red-950 text-red-300 border-red-600" };
      case "forest_fire":
        return { label: "FOREST / WILDFIRE", color: "bg-orange-950 text-orange-300 border-orange-600" };
      case "false_alarm":
        return { label: "FALSE ALARM (SOLAR GLARE)", color: "bg-slate-800 text-slate-300 border-slate-600" };
      default:
        return { label: cls, color: "bg-slate-800 text-slate-300 border-slate-600" };
    }
  };

  return (
    <div className="absolute bottom-4 left-4 right-80 max-w-4xl bg-slate-900/95 backdrop-blur border border-slate-800 rounded-lg p-4 shadow-2xl z-30 font-sans text-xs text-slate-100 flex flex-col md:flex-row gap-5">
      {/* Close Button */}
      <button
        onClick={onClose}
        className="absolute top-3 right-3 text-slate-400 hover:text-white font-mono text-sm px-2 py-0.5 rounded bg-slate-800 border border-slate-700"
      >
        ✕ CLOSE
      </button>

      {loading || !detail ? (
        <div className="p-8 text-center font-mono text-slate-400 w-full">Loading alert intelligence telemetry...</div>
      ) : (
        <>
          {/* Left Column: Image Patch & Quick Telemetry */}
          <div className="flex flex-col space-y-3 shrink-0 w-full md:w-56">
            <div className="flex items-center space-x-2">
              <span className={`px-2 py-1 rounded text-[11px] font-mono font-bold border uppercase ${getClassBadge(detail.predicted_class).color}`}>
                {getClassBadge(detail.predicted_class).label}
              </span>
            </div>

            {/* Multispectral Patch Tile */}
            <div className="flex flex-col space-y-1">
              <span className="text-[11px] font-mono text-slate-400 uppercase">Multispectral Composite Patch (SWIR/NIR/Red)</span>
              <div className="w-full h-36 bg-slate-950 border border-slate-800 rounded overflow-hidden flex items-center justify-center relative">
                {detail.patch_image_base64 ? (
                  <img
                    src={detail.patch_image_base64}
                    alt="False color patch"
                    className="w-full h-full object-cover rounded"
                  />
                ) : (
                  <span className="text-slate-600 font-mono">NO PATCH DATA</span>
                )}
                <span className="absolute bottom-1 right-1 text-[9px] font-mono bg-slate-950/80 text-slate-400 px-1.5 py-0.5 rounded border border-slate-800">
                  32x32px False-Colour
                </span>
              </div>
            </div>

            {/* Plume Dispersion Toggle for Industrial Fire */}
            {detail.predicted_class === "industrial_fire" && (
              <button
                onClick={onTogglePlume}
                className={`w-full py-1.5 px-3 rounded font-mono text-xs border transition-colors flex items-center justify-center space-x-2 ${
                  showPlume
                    ? "bg-red-900 text-white border-red-500 font-bold"
                    : "bg-slate-800 text-slate-300 border-slate-700 hover:border-red-600"
                }`}
              >
                <span>{showPlume ? "HIDE PLUME MODEL" : "SHOW GAUSSIAN PLUME"}</span>
              </button>
            )}
          </div>

          {/* Middle Column: Model Tier Metrics & Feature Vector */}
          <div className="flex flex-col space-y-3 flex-1 border-t md:border-t-0 md:border-l border-slate-800 pt-3 md:pt-0 md:pl-5">
            <div className="flex items-center justify-between font-mono text-xs border-b border-slate-800 pb-2">
              <div>
                <span className="text-slate-400">HOTSPOT ID: </span>
                <span className="text-slate-200 font-bold">{detail.firms_id || detail.id.slice(0, 8)}</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 rounded bg-blue-950 border border-blue-700 text-blue-300 font-bold">
                  TIER {detail.tier_used} {detail.tier_used === 1 ? "(Fast LightGBM)" : "(CNN Patch Validation)"}
                </span>
                <span className="text-slate-400">
                  CONF: <strong className="text-emerald-400">{(detail.overall_confidence * 100).toFixed(1)}%</strong>
                </span>
                <span className="text-slate-400">LATENCY: <strong className="text-blue-400">{detail.latency_ms}ms</strong></span>
              </div>
            </div>

            {/* Feature Telemetry Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 font-mono text-[11px] bg-slate-950 p-2.5 rounded border border-slate-800">
              <div>
                <span className="text-slate-500">FRP:</span> <span className="text-slate-200 font-bold">{detail.frp} MW</span>
              </div>
              <div>
                <span className="text-slate-500">BRIGHTNESS:</span> <span className="text-slate-200 font-bold">{detail.brightness} K</span>
              </div>
              <div>
                <span className="text-slate-500">IND DIST:</span> <span className="text-slate-200 font-bold">{detail.feature_vector?.dist_to_industrial_km ?? "N/A"} km</span>
              </div>
              <div>
                <span className="text-slate-500">FACILITY INSIDE:</span> <span className="text-slate-200 font-bold">{detail.feature_vector?.inside_facility ? "YES" : "NO"}</span>
              </div>
              <div>
                <span className="text-slate-500">SOLAR DIST:</span> <span className="text-slate-200 font-bold">{detail.feature_vector?.dist_to_solar_km ?? "N/A"} km</span>
              </div>
              <div>
                <span className="text-slate-500">PERSIST (7D):</span> <span className="text-slate-200 font-bold">{detail.feature_vector?.persistence_7d ?? 0} count</span>
              </div>
            </div>

            {/* SHAP Explanation Chart */}
            <div className="flex flex-col space-y-1">
              <span className="text-[11px] font-mono text-slate-400 uppercase">SHAP Model Explanation (Top 5 Decision Factors)</span>
              {detail.shap_explanation ? (
                <ShapBarChart factors={detail.shap_explanation} />
              ) : (
                <span className="text-slate-500 font-mono">No SHAP data available.</span>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
