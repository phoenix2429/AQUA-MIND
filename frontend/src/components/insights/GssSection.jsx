import React from 'react';
import { Shield, Info, AlertTriangle, CheckCircle2, HelpCircle } from 'lucide-react';

export function GssSection({ gss }) {
  if (!gss) return null;

  const score = gss.score != null ? Math.round(gss.score) : null;
  const profile = gss.profile || 'UNKNOWN';

  const profileColors = {
    STABLE: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    WATCH: 'bg-amber-50 text-amber-800 border-amber-200',
    VARIABLE: 'bg-orange-50 text-orange-800 border-orange-200',
    INSUFFICIENT_DATA: 'bg-slate-50 text-slate-700 border-slate-200',
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-2xs space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <Shield className="w-5 h-5 text-teal-600" />
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">Groundwater Sustainability Score (GSS)</h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            AQUA-MIND analytical score (0–100) derived from measured station indicators
          </p>
        </div>

        <span className="px-2.5 py-1 text-[11px] font-semibold bg-slate-100 text-slate-600 rounded-lg border border-slate-200 self-start sm:self-auto">
          AQUA-MIND Analytical Score
        </span>
      </div>

      {/* Official Disclaimer */}
      <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 flex items-start space-x-2">
        <Info className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
        <p className="text-[11px] text-slate-600">
          <strong>Notice:</strong> This metric is an internal analytical score computed by the AQUA-MIND framework. It is not an official government index or regulatory classification.
        </p>
      </div>

      {/* Main Score & Component Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
        
        {/* Score Card */}
        <div className={`p-5 rounded-2xl border flex flex-col justify-between ${profileColors[profile] || profileColors.INSUFFICIENT_DATA}`}>
          <div className="space-y-1">
            <span className="text-[10px] uppercase font-bold tracking-wider opacity-75">Sustainability Metric</span>
            <div className="flex items-baseline space-x-2">
              <span className="text-4xl font-extrabold">{score != null ? score : 'N/A'}</span>
              <span className="text-sm font-semibold opacity-75">/ 100</span>
            </div>
          </div>

          <div className="pt-3 border-t border-current/15 mt-3 flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wide">Profile: {profile}</span>
            {gss.sufficient ? (
              <CheckCircle2 className="w-4 h-4" />
            ) : (
              <HelpCircle className="w-4 h-4" />
            )}
          </div>
        </div>

        {/* Reason & Sufficiency */}
        <div className="md:col-span-2 p-5 bg-slate-50 rounded-2xl border border-slate-200 space-y-3 flex flex-col justify-between">
          <div className="space-y-1.5">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">Analytical Evaluation</h4>
            <p className="text-sm text-slate-800 font-medium leading-relaxed">
              {gss.reason || 'Sufficient historical observations evaluated.'}
            </p>
          </div>

          {/* Component Breakdown from backend */}
          {gss.components && Object.keys(gss.components).length > 0 && (
            <div className="pt-3 border-t border-slate-200/80 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              {Object.entries(gss.components).map(([key, value]) => (
                <div key={key} className="bg-white p-2 rounded-lg border border-slate-100">
                  <span className="text-[10px] uppercase font-semibold text-slate-400 block truncate">
                    {key.replace('_', ' ')}
                  </span>
                  <span className="font-bold text-slate-800">
                    {typeof value === 'number' ? value.toFixed(2) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
