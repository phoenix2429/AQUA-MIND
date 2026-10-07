import React, { useState, useEffect } from 'react';
import { TrendingUp, Cpu, Radio, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { forecastService } from '../services/forecastService';
import { stationService } from '../services/stationService';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { stationRoute } from '../services/stationRoutes';

export function ForecastPage() {
  const [models, setModels] = useState([]);
  const [stations, setStations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        const [modelsRes, stationsRes] = await Promise.allSettled([
          forecastService.getModels(),
          stationService.getStations({ page: 1, pageSize: 6 }),
        ]);

        if (modelsRes.status === 'fulfilled') setModels(modelsRes.value || []);
        if (stationsRes.status === 'fulfilled') setStations(stationsRes.value?.items || []);
        if (modelsRes.status === 'rejected' || stationsRes.status === 'rejected') {
          setError('Unable to load forecasting data from the backend.');
        }
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center space-x-2">
          <TrendingUp className="w-6 h-6 text-brand-600" />
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Machine Learning Forecasting Center</h1>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          24-hour horizon groundwater level prediction models (XGBoost, Random Forest, Persistence baseline).
        </p>
      </div>

      {error && <ErrorMessage title="Forecast Data Unavailable" message={error} />}

      {/* Deployed Models Card Grid */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-2xs space-y-4">
        <div className="flex items-center space-x-2 text-slate-900 font-bold text-sm">
          <Cpu className="w-4 h-4 text-brand-600" />
          <span>Deployed Forecasting Models</span>
        </div>

        {loading ? (
          <LoadingSpinner message="Querying active model registry..." />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {models.map((model) => {
              const metrics = model.evaluation || model.test_metrics;
              const displayName = model.display_name || model.name || model.model_name;
              return (
                <div key={model.model_name || model.name} className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900 uppercase">{displayName}</span>
                    <span className="text-[10px] font-mono bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-600">
                      v{model.version || '1.0'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {model.description || `${displayName} for 24-hour horizon groundwater level forecasting`}
                  </p>
                  {metrics && (
                    <div className="pt-2 border-t border-slate-200/60 grid grid-cols-3 gap-1 text-[11px] font-mono">
                      <div>
                        <span className="text-[9px] uppercase text-slate-400 block">MAE</span>
                        <span className="font-bold text-slate-700">{metrics.mae?.toFixed(3) ?? 'N/A'}</span>
                      </div>
                      <div>
                        <span className="text-[9px] uppercase text-slate-400 block">RMSE</span>
                        <span className="font-bold text-slate-700">{metrics.rmse?.toFixed(3) ?? 'N/A'}</span>
                      </div>
                      <div>
                        <span className="text-[9px] uppercase text-slate-400 block">R²</span>
                        <span className="font-bold text-slate-700">{metrics.r2?.toFixed(3) ?? 'N/A'}</span>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Select Station for Forecast */}
      <div className="space-y-3">
        <h2 className="text-base font-bold text-slate-900">Select Station to Forecast</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {stations.map((st) => (
            <Link
              key={st.id}
              to={stationRoute(st.station_id)}
              className="p-4 bg-white border border-slate-200 rounded-xl hover:border-brand-400 hover:shadow-md transition-all flex items-center justify-between group"
            >
              <div>
                <span className="text-[10px] uppercase font-bold text-brand-700 bg-brand-50 px-1.5 py-0.5 rounded border border-brand-200">
                  {st.state}
                </span>
                <h4 className="text-sm font-bold text-slate-900 mt-1 group-hover:text-brand-700">
                  {st.station_name}
                </h4>
                <p className="text-xs text-slate-500">{st.district} District</p>
              </div>
              <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-brand-600 transition-colors" />
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
