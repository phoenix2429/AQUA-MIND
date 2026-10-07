import React, { useState } from 'react';
import { Sliders, AlertCircle, Info, Play } from 'lucide-react';

export function ScenariosPage() {
  const [syntheticExtractionDelta, setSyntheticExtractionDelta] = useState(0);
  const [syntheticRainfallDelta, setSyntheticRainfallDelta] = useState(0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center space-x-2">
          <Sliders className="w-6 h-6 text-brand-600" />
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Scenario & What-If Analysis</h1>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Explore synthetic response behavior under hypothetical stress inputs.
        </p>
      </div>

      {/* Explicit Backend Status Notice */}
      <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl text-amber-950 text-xs flex items-start space-x-3">
        <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h4 className="font-bold">Feature Status — Backend Scenario Endpoint Pending</h4>
          <p className="text-amber-900 leading-relaxed">
            Scientifically validated backend scenario endpoints are currently under development. The controls below operate purely in <strong>Demonstration Scenario — Synthetic Input</strong> mode for UI design validation; values must not be used as observed groundwater measurements.
          </p>
        </div>
      </div>

      {/* Synthetic Interactive Controls */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-2xs space-y-6">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Demonstration Scenario — Synthetic Input
          </span>
          <span className="px-2 py-0.5 text-[10px] font-semibold bg-amber-100 text-amber-800 rounded">
            SYNTHETIC DEMO ONLY
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Slider 1 */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs font-semibold text-slate-700">
              <span>Hypothetical Extraction Variation</span>
              <span className="font-mono text-brand-700">{syntheticExtractionDelta > 0 ? `+${syntheticExtractionDelta}` : syntheticExtractionDelta}%</span>
            </div>
            <input
              type="range"
              min="-50"
              max="50"
              value={syntheticExtractionDelta}
              onChange={(e) => setSyntheticExtractionDelta(Number(e.target.value))}
              className="w-full accent-brand-600 cursor-pointer"
            />
            <p className="text-[10px] text-slate-400">Simulates hypothetical stress change on groundwater extraction</p>
          </div>

          {/* Slider 2 */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs font-semibold text-slate-700">
              <span>Hypothetical Recharge / Rainfall Delta</span>
              <span className="font-mono text-brand-700">{syntheticRainfallDelta > 0 ? `+${syntheticRainfallDelta}` : syntheticRainfallDelta}%</span>
            </div>
            <input
              type="range"
              min="-50"
              max="50"
              value={syntheticRainfallDelta}
              onChange={(e) => setSyntheticRainfallDelta(Number(e.target.value))}
              className="w-full accent-brand-600 cursor-pointer"
            />
            <p className="text-[10px] text-slate-400">Simulates hypothetical precipitation/recharge variation</p>
          </div>
        </div>

        {/* Demo Output Card */}
        <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs">
          <div className="flex items-center justify-between font-bold text-slate-800">
            <span>Synthetic Scenario Summary Output</span>
            <span className="text-slate-400 font-normal text-[11px]">Unvalidated Demonstration</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-center pt-2">
            <div className="bg-white p-2 rounded-lg border border-slate-200">
              <span className="text-[9px] uppercase font-semibold text-slate-400 block">Reference input</span>
              <span className="font-mono font-bold text-slate-800">0% delta</span>
            </div>
            <div className="bg-white p-2 rounded-lg border border-slate-200">
              <span className="text-[9px] uppercase font-semibold text-slate-400 block">Synthetic response index</span>
              <span className="font-mono font-bold text-brand-700">
                {(syntheticExtractionDelta * 0.05 - syntheticRainfallDelta * 0.04).toFixed(2)} units
              </span>
            </div>
            <div className="bg-white p-2 rounded-lg border border-slate-200">
              <span className="text-[9px] uppercase font-semibold text-slate-400 block">Synthetic difference</span>
              <span className="font-mono font-bold text-amber-700">
                {((syntheticExtractionDelta * 0.05) - (syntheticRainfallDelta * 0.04)).toFixed(2)} units
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
