import React, { useState, useEffect } from 'react';
import { TrendingUp, Cpu, Calendar, AlertCircle, Info } from 'lucide-react';
import { forecastService } from '../../services/forecastService';
import { LoadingSpinner } from '../common/LoadingSpinner';

export function ForecastSection({ stationId }) {
  const [model, setModel] = useState('xgboost'); // 'xgboost' | 'random_forest' | 'persistence'
  const [horizon, setHorizon] = useState(4); // 4 | 8 | 12 | 24
  const [forecastPoints, setForecastPoints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchForecast() {
      if (!stationId) return;
      try {
        setLoading(true);
        setError(null);
        const data = await forecastService.getForecast(stationId, {
          model,
          horizonPoints: horizon,
        });
        setForecastPoints(data || []);
      } catch (err) {
        setError(err.message || 'Forecast is currently unavailable for this station.');
        setForecastPoints([]);
      } finally {
        setLoading(false);
      }
    }
    fetchForecast();
  }, [stationId, model, horizon]);

  const formatDate = (isoStr) => {
    if (!isoStr) return '—';
    try {
      return new Date(isoStr).toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch (_) {
      return isoStr;
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-2xs space-y-4">
      {/* Header & Model Selector Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <TrendingUp className="w-5 h-5 text-blue-600" />
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">Machine Learning 24-Hour Forecast</h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Predictions generated from historical telemetry state (depth to water level in meters below ground level / m bgl)
          </p>
        </div>

        {/* Model & Horizon Toggles */}
        <div className="flex items-center space-x-2 flex-wrap">
          {/* Horizon Selector */}
          <select
            value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value))}
            className="px-2.5 py-1 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-700 font-semibold focus:outline-none"
          >
            <option value={4}>4 Points (Horizon)</option>
            <option value={8}>8 Points</option>
            <option value={12}>12 Points</option>
            <option value={24}>24 Points (24h)</option>
          </select>

          {/* Model Selector */}
          <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-xl">
            <button
              onClick={() => setModel('xgboost')}
              className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-all ${
                model === 'xgboost' ? 'bg-white text-blue-700 shadow-2xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              XGBoost
            </button>
            <button
              onClick={() => setModel('random_forest')}
              className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-all ${
                model === 'random_forest' ? 'bg-white text-brand-700 shadow-2xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Random Forest
            </button>
            <button
              onClick={() => setModel('persistence')}
              className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-all ${
                model === 'persistence' ? 'bg-white text-slate-800 shadow-2xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Persistence Baseline
            </button>
          </div>
        </div>
      </div>

      {/* Model Info Banner */}
      <div className="p-3 bg-blue-50/60 border border-blue-100 rounded-xl text-xs text-blue-900 flex items-start space-x-2.5">
        <Info className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <p className="font-bold">
            Model: <span className="uppercase text-blue-700">{model.replace('_', ' ')}</span>
            {forecastPoints[0]?.model_version && ` (v${forecastPoints[0].model_version})`}
          </p>
          <p className="text-[11px] text-blue-800">
            Forecast transition point: <strong className="text-slate-800">Latest Available Observation</strong>. Forecast values are predicted model outputs and must be distinguished from observed telemetry data.
          </p>
        </div>
      </div>

      {/* Forecast Output */}
      {loading ? (
        <LoadingSpinner message={`Running ${model.toUpperCase()} forecast inferencing...`} />
      ) : error ? (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 text-xs flex items-start space-x-2">
          <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">Forecast Notice:</span> {error}
          </div>
        </div>
      ) : forecastPoints.length === 0 ? (
        <div className="py-8 text-center text-slate-400 text-xs italic bg-slate-50 rounded-xl border border-dashed border-slate-200">
          Forecast unavailable because this station does not have sufficient recent historical observations.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
          {forecastPoints.map((pt, index) => (
            <div 
              key={index}
              className="p-4 bg-gradient-to-b from-white to-blue-50/30 border border-blue-100 rounded-xl shadow-2xs space-y-2 hover:border-blue-300 transition-colors"
            >
              <div className="flex items-center justify-between text-[11px] text-slate-500 font-medium">
                <span className="flex items-center space-x-1">
                  <Calendar className="w-3 h-3 text-blue-500" />
                  <span>{formatDate(pt.forecast_time)}</span>
                </span>
                <span className="px-1.5 py-0.5 bg-blue-100 text-blue-800 rounded font-semibold text-[10px]">
                  +{index + 1} Step
                </span>
              </div>

              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Predicted Water Level</span>
                <span className="text-xl font-extrabold text-blue-900">
                  {pt.predicted_value?.toFixed(2)} <span className="text-xs font-medium text-slate-500">m bgl</span>
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
