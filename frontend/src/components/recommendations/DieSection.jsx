import React from 'react';
import { Lightbulb, AlertOctagon, AlertTriangle, CheckCircle, Info } from 'lucide-react';

export function DieSection({ die }) {
  if (!die) return null;

  const priority = die.priority || 'LOW';
  
  const priorityStyles = {
    HIGH: {
      bg: 'bg-rose-50 border-rose-200 text-rose-950',
      badge: 'bg-rose-600 text-white',
      icon: <AlertOctagon className="w-5 h-5 text-rose-600" />,
    },
    MEDIUM: {
      bg: 'bg-amber-50 border-amber-200 text-amber-950',
      badge: 'bg-amber-500 text-white',
      icon: <AlertTriangle className="w-5 h-5 text-amber-600" />,
    },
    LOW: {
      bg: 'bg-emerald-50 border-emerald-200 text-emerald-950',
      badge: 'bg-emerald-600 text-white',
      icon: <CheckCircle className="w-5 h-5 text-emerald-600" />,
    },
  };

  const style = priorityStyles[priority] || priorityStyles.LOW;

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-2xs space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <Lightbulb className="w-5 h-5 text-amber-500" />
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">Decision Intelligence Recommendations</h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            AQUA-MIND analytical recommendations based on GSS and GBIM telemetry evaluation
          </p>
        </div>

        <span className={`px-3 py-1 text-xs font-bold rounded-lg ${style.badge} self-start sm:self-auto`}>
          Priority: {priority}
        </span>
      </div>

      {/* Distinction Disclaimer */}
      <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 flex items-start space-x-2">
        <Info className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
        <p className="text-[11px] text-slate-600">
          <strong>Analytical Guidance:</strong> Recommendations are generated purely by analytical algorithms for decision-support. They do not constitute official government mandates, orders, or guaranteed actions.
        </p>
      </div>

      {/* Main Recommendation Card */}
      <div className={`p-5 rounded-2xl border ${style.bg} space-y-3`}>
        <div className="flex items-start space-x-3">
          <div className="mt-0.5 flex-shrink-0">{style.icon}</div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-900">
              {die.recommendation || 'Maintain standard telemetry monitoring.'}
            </h3>
            {die.action && (
              <p className="text-xs font-semibold text-slate-800">
                Suggested Action: <span className="font-normal">{die.action}</span>
              </p>
            )}
            <p className="text-xs text-slate-700 leading-relaxed mt-1">
              {die.reason || 'Evaluation based on recent telemetry trend, recovery rate, and variability.'}
            </p>
          </div>
        </div>

        {/* Supporting Indicators */}
        {die.source_indicators && Object.keys(die.source_indicators).length > 0 && (
          <div className="pt-3 border-t border-current/10 flex flex-wrap gap-2 text-[11px]">
            <span className="font-bold text-slate-700">Supporting Indicators:</span>
            {Object.entries(die.source_indicators).map(([k, v]) => (
              <span key={k} className="px-2 py-0.5 bg-white/70 rounded border border-current/15 font-mono text-slate-800">
                {k}: {typeof v === 'number' ? v.toFixed(2) : String(v)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
