import React, { useEffect, useState } from 'react';
import { AlertTriangle, Droplet, Sprout, Zap } from 'lucide-react';
import { stationService } from '../../services/stationService';
import { forecastService } from '../../services/forecastService';
import { analyticsService } from '../../services/analyticsService';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ErrorMessage } from '../common/ErrorMessage';

export function FarmerAdvisory() {
  const [station, setStation] = useState(null);
  const [forecast, setForecast] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const list = await stationService.getStations({ page: 1, pageSize: 1 });
        const selected = list?.items?.[0];
        if (!selected) throw new Error('No telemetry station is available.');
        const [detail, prediction, insight, series] = await Promise.all([
          stationService.getStation(selected.station_id),
          forecastService.getForecast(selected.station_id, { horizonPoints: 4, model: 'xgboost' }),
          analyticsService.getStationAnalytics(selected.station_id),
          stationService.getHistory(selected.station_id, { buckets: 30 }),
        ]);
        setStation(detail);
        setForecast(prediction || []);
        setAnalytics(insight);
        setHistory(series || []);
      } catch (err) {
        setError(err.message || 'Farmer advisory data is unavailable.');
      }
    }
    load();
  }, []);

  if (error) return <ErrorMessage title="Farmer Advisory Unavailable" message={error} />;
  if (!station) return <LoadingSpinner message="Loading current groundwater and farm advisory..." />;

  const current = history.at(-1)?.groundwater_level;
  const previous = history.at(-2)?.groundwater_level;
  const declining = Number.isFinite(current) && Number.isFinite(previous) && current > previous;
  const stressed = analytics?.gss?.score != null && analytics.gss.score < 40;
  const alert = declining || stressed;
  const crop = stressed || declining
    ? 'Prefer drought-tolerant crops and avoid water-intensive expansion.'
    : 'Common seasonal crops may be considered subject to local agronomy guidance.';
  const irrigation = alert
    ? 'Conserve groundwater: use drip irrigation, irrigate during cooler hours, and verify soil moisture first.'
    : 'Use measured soil moisture and local guidance; avoid unnecessary irrigation.';

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Farmer Advisory</h2>
          <p className="text-xs text-slate-500">Advisory for {station.station_name} ({station.state})</p>
        </div>
        <span className={`px-2 py-1 rounded-lg text-xs font-bold ${alert ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'}`}>
          {alert ? 'Attention' : 'Routine monitoring'}
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-white border rounded-2xl"><Droplet className="w-5 h-5 text-sky-600" /><p className="text-[10px] uppercase text-slate-400 mt-2">Latest measured level</p><strong className="text-2xl">{Number.isFinite(current) ? `${current.toFixed(2)} m` : 'Unavailable'}</strong></div>
        <div className="p-4 bg-white border rounded-2xl"><Zap className="w-5 h-5 text-emerald-600" /><p className="text-[10px] uppercase text-slate-400 mt-2">Next 24h prediction</p><strong className="text-2xl">{forecast[3]?.predicted_value != null ? `${forecast[3].predicted_value.toFixed(2)} m` : 'Unavailable'}</strong></div>
        <div className={`p-4 border rounded-2xl ${alert ? 'bg-amber-50 border-amber-200' : 'bg-emerald-50 border-emerald-200'}`}><AlertTriangle className="w-5 h-5" /><p className="text-[10px] uppercase mt-2">Alert</p><strong>{alert ? 'Review conservation actions' : 'No immediate trend alert'}</strong></div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-white border rounded-2xl"><Sprout className="w-5 h-5 text-green-600" /><h3 className="font-bold mt-2">Crop recommendation</h3><p className="text-xs text-slate-600 mt-1">{crop}</p></div>
        <div className="p-4 bg-white border rounded-2xl"><Droplet className="w-5 h-5 text-blue-600" /><h3 className="font-bold mt-2">Irrigation recommendation</h3><p className="text-xs text-slate-600 mt-1">{irrigation}</p></div>
        <div className="p-4 bg-white border rounded-2xl"><Zap className="w-5 h-5 text-amber-600" /><h3 className="font-bold mt-2">Farm actions</h3><p className="text-xs text-slate-600 mt-1">Monitor the station trend, review the prediction, and consult local agricultural officers before changing crop or irrigation plans.</p></div>
      </div>
      <p className="text-[11px] text-slate-500">Advisory only: recommendations use this station's measured telemetry, forecast, and analytical indicators; they are not agronomic guarantees.</p>
    </section>
  );
}
