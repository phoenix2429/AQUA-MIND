import React, { useState, useEffect } from 'react';
import { Lightbulb, ArrowUpRight, ArrowDownRight, Minus, AlertCircle, Info } from 'lucide-react';
import { forecastService } from '../../services/forecastService';
import { LoadingSpinner } from '../common/LoadingSpinner';

export function ShapSection({ stationId }) {
  const [model, setModel] = useState('xgboost'); // 'xgboost' | 'random_forest'
  const [shapData, setShapData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchShap() {
      if (!stationId) return;
      try {
        setLoading(true);
        setError(null);
        const data = await forecastService.getShapExplanation(stationId, model);
        setShapData(data);
      } catch (err) {
        setError(err.message || 'Model explanation is currently unavailable for this station.');
        setShapData(null);
      } finally {
        setLoading(false);
      }
    }
    fetchShap();
  }, [stationId, model]);

  const sortedContributions = shapData?.contributions
    ? [...shapData.contributions].sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
    : [];

  const maxAbsValue = sortedContributions.reduce(
    (max, c) => Math.max(max, Math.abs(c.shap_value)),
    0.0001
  );

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-2xs space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <Lightbulb className="w-5 h-5 text-amber-500" />
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">Why this forecast?</h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Model feature contribution analysis (Tree SHAP feature attributions, not causal claims)
          </p>
        </div>

        {/* Model Toggle */}
        <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-xl">
          <button
            onClick={() => setModel('xgboost')}
            className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-all ${
              model === 'xgboost' ? 'bg-white text-purple-700 shadow-2xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            XGBoost SHAP
          </button>
          <button
            onClick={() => setModel('random_forest')}
            className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-all ${
              model === 'random_forest' ? 'bg-white text-purple-700 shadow-2xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Random Forest SHAP
          </button>
        </div>
      </div>

      {/* Methodology Disclaimer Notice */}
      <div className="p-3 bg-purple-50/60 border border-purple-100 rounded-xl text-xs text-purple-900 flex items-start space-x-2">
        <Info className="w-4 h-4 text-purple-600 flex-shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <p className="font-bold">Interpretation Guidance:</p>
          <p className="text-[11px] text-purple-800">
            Positive values push the model forecast upward (predicting deeper water level). Negative values push the model forecast downward. These values explain feature influence on the statistical model's prediction, not direct environmental causation.
          </p>
        </div>
      </div>

      {/* SHAP Output */}
      {loading ? (
        <LoadingSpinner message="Calculating Tree SHAP feature attributions..." />
      ) : error ? (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 text-xs flex items-start space-x-2">
          <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">Explainability Notice:</span> {error}
          </div>
        </div>
      ) : !shapData || sortedContributions.length === 0 ? (
        <div className="py-8 text-center text-slate-400 text-xs italic bg-slate-50 rounded-xl border border-dashed border-slate-200">
          Model explanation is currently unavailable for this station.
        </div>
      ) : (
        <div className="space-y-4 pt-2">
          
          {/* Base Value & Prediction Info */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3 bg-slate-50 rounded-xl border border-slate-100 text-xs">
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Base Model Value</span>
              <span className="font-mono font-bold text-slate-800">{shapData.base_value?.toFixed(3)} m</span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Model Prediction</span>
              <span className="font-mono font-bold text-purple-900">{shapData.prediction?.toFixed(3)} m</span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Additivity Error</span>
              <span className="font-mono text-slate-600">{shapData.additivity_error?.toFixed(5)}</span>
            </div>
          </div>

          {/* Feature Contribution Bars */}
          <div className="space-y-3">
            {sortedContributions.slice(0, 8).map((contrib) => {
              const absVal = Math.abs(contrib.shap_value);
              const percentage = Math.min(100, Math.max(8, (absVal / maxAbsValue) * 100));
              const isPositive = contrib.shap_value > 0;

              return (
                <div key={contrib.feature} className="space-y-1 text-xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className={`p-1 rounded ${
                        isPositive ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'
                      }`}>
                        {isPositive ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                      </span>
                      <span className="font-bold text-slate-800">{contrib.display_name || contrib.feature}</span>
                      {contrib.value != null && (
                        <span className="text-[11px] font-mono text-slate-500">
                          (Val: {typeof contrib.value === 'number' ? contrib.value.toFixed(2) : contrib.value})
                        </span>
                      )}
                    </div>

                    <div className="flex items-center space-x-2 font-mono text-xs">
                      <span className={`font-bold ${isPositive ? 'text-rose-600' : 'text-emerald-600'}`}>
                        {isPositive ? '+' : ''}{contrib.shap_value.toFixed(4)}
                      </span>
                      <span className="text-[10px] text-slate-400 uppercase">
                        {isPositive ? 'Increases depth' : 'Decreases depth'}
                      </span>
                    </div>
                  </div>

                  {/* Horizontal Bar */}
                  <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden flex">
                    <div 
                      className={`h-full rounded-full transition-all duration-300 ${
                        isPositive ? 'bg-rose-500' : 'bg-emerald-500'
                      }`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

        </div>
      )}
    </div>
  );
}
