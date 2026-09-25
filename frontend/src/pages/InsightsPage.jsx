import React, { useState, useEffect } from 'react';
import { Lightbulb, Info, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { stationService } from '../services/stationService';
import { stationRoute } from '../services/stationRoutes';

export function InsightsPage() {
  const [stations, setStations] = useState([]);

  useEffect(() => {
    async function load() {
      try {
        const res = await stationService.getStations({ page: 1, pageSize: 6 });
        setStations(res?.items || []);
      } catch (_) {}
    }
    load();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center space-x-2">
          <Lightbulb className="w-6 h-6 text-amber-500" />
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Tree SHAP Explainability & Feature Insights</h1>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Quantitative feature attribution explaining machine learning model predictions.
        </p>
      </div>

      <div className="p-4 bg-purple-50 border border-purple-200 rounded-2xl text-purple-900 text-xs flex items-start space-x-3">
        <Info className="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h4 className="font-bold">What is Tree SHAP in AQUA-MIND?</h4>
          <p className="text-purple-800 leading-relaxed">
            Tree SHAP (SHapley Additive exPlanations) computes exact game-theoretic Shapley values for tree ensemble models (XGBoost and Random Forest). It quantifies how each telemetry feature (lags, rolling averages, trend slopes, calendar metrics) pushes the predicted groundwater depth relative to the model baseline.
          </p>
        </div>
      </div>

      <div className="space-y-3">
        <h2 className="text-base font-bold text-slate-900">Select Station to Inspect SHAP Explanations</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {stations.map((st) => (
            <Link
              key={st.id}
              to={stationRoute(st.station_id)}
              className="p-4 bg-white border border-slate-200 rounded-xl hover:border-purple-300 hover:shadow-md transition-all flex items-center justify-between group"
            >
              <div>
                <span className="text-[10px] uppercase font-bold text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded border border-purple-200">
                  {st.state}
                </span>
                <h4 className="text-sm font-bold text-slate-900 mt-1 group-hover:text-purple-700">
                  {st.station_name}
                </h4>
                <p className="text-xs text-slate-500">{st.district} District</p>
              </div>
              <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-purple-600 transition-colors" />
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
