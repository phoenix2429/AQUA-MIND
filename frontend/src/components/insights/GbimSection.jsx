import React from 'react';
import { Activity, Info, TrendingDown, TrendingUp, Minus, RotateCcw } from 'lucide-react';

export function GbimSection({ gbim }) {
  if (!gbim) return null;

  const profile = gbim.profile || 'UNKNOWN';

  const getProfileIcon = () => {
    switch (profile) {
      case 'DECLINING':
        return <TrendingDown className="w-5 h-5 text-rose-600" />;
      case 'RISING':
        return <TrendingUp className="w-5 h-5 text-emerald-600" />;
      case 'STABLE':
        return <Minus className="w-5 h-5 text-brand-600" />;
      default:
        return <RotateCcw className="w-5 h-5 text-amber-600" />;
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-2xs space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <Activity className="w-5 h-5 text-emerald-600" />
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">Groundwater Behavior Intelligence (GBIM)</h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Behavior profile derived from measured station telemetry indicators
          </p>
        </div>

        <div className="flex items-center space-x-2 px-3 py-1.5 bg-slate-100 rounded-xl text-xs font-bold text-slate-800 self-start sm:self-auto">
          {getProfileIcon()}
          <span>Behavior: {profile}</span>
        </div>
      </div>

      {/* Evaluation Reason */}
      <p className="text-xs text-slate-700 font-medium bg-slate-50 p-3 rounded-xl border border-slate-100">
        {gbim.reason || 'Behavior profile synthesized from telemetry time-series characteristics.'}
      </p>

      {/* Indicators Grid */}
      {gbim.components && Object.keys(gbim.components).length > 0 && (
        <div className="space-y-2 pt-1">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Measured Behavior Indicators</h4>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Object.entries(gbim.components).map(([key, val]) => (
              <div key={key} className="p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block truncate">
                  {key.replace('_', ' ')}
                </span>
                <span className="text-sm font-bold text-slate-800 block">
                  {typeof val === 'number' ? val.toFixed(3) : String(val)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
