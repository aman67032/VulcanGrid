"use client";

import React from "react";
import { ShapFactor } from "../types";

interface ShapBarChartProps {
  factors: ShapFactor[];
}

export const ShapBarChart: React.FC<ShapBarChartProps> = ({ factors }) => {
  if (!factors || factors.length === 0) {
    return <div className="text-slate-500 text-xs py-4 font-mono">No SHAP explanations available.</div>;
  }

  // Find max absolute SHAP value for scaling bar widths
  const maxAbs = Math.max(...factors.map((f) => Math.abs(f.shap_value)), 0.01);

  return (
    <div className="space-y-2.5 font-mono text-xs">
      <div className="flex justify-between text-[11px] text-slate-400 border-b border-slate-800 pb-1">
        <span>FEATURE FACTOR</span>
        <span>SHAP IMPACT</span>
      </div>

      {factors.map((factor, idx) => {
        const val = factor.shap_value;
        const isPositive = val >= 0;
        const widthPct = Math.min((Math.abs(val) / maxAbs) * 100, 100);

        return (
          <div key={idx} className="flex flex-col space-y-1">
            <div className="flex justify-between items-center text-slate-300">
              <span className="font-semibold">{factor.feature}</span>
              <span className="text-slate-400">
                val: <strong className="text-slate-200">{factor.value}</strong> | SHAP:{" "}
                <span className={isPositive ? "text-red-400 font-bold" : "text-blue-400 font-bold"}>
                  {val > 0 ? `+${val}` : val}
                </span>
              </span>
            </div>

            {/* Horizontal Dual Direction Bar */}
            <div className="h-2.5 bg-slate-950 rounded relative overflow-hidden border border-slate-800 flex items-center">
              <div className="w-1/2 h-full border-r border-slate-700 flex justify-end">
                {!isPositive && (
                  <div
                    className="h-full bg-blue-500 rounded-l"
                    style={{ width: `${widthPct}%` }}
                  />
                )}
              </div>
              <div className="w-1/2 h-full flex justify-start">
                {isPositive && (
                  <div
                    className="h-full bg-red-500 rounded-r"
                    style={{ width: `${widthPct}%` }}
                  />
                )}
              </div>
            </div>
          </div>
        );
      })}

      <div className="flex justify-between text-[10px] text-slate-500 pt-1">
        <span className="text-blue-400">◄ Pushing Against</span>
        <span className="text-red-400">Pushing Towards ►</span>
      </div>
    </div>
  );
};
