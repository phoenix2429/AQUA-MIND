import React, { useState, useEffect } from 'react';
import { ShieldCheck, Activity, Cpu, Database, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import { forecastService } from '../services/forecastService';
import { stationService } from '../services/stationService';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export function AdminPage() {
  const [health, setHealth] = useState(null);
  const [totalStations, setTotalStations] = useState(null);
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAdminData() {
      try {
        setLoading(true);
        const [healthRes, stationsRes, modelsRes] = await Promise.allSettled([
          api.get('/health'),
          stationService.getStations({ page: 1, pageSize: 1 }),
          forecastService.getModels(),
        ]);

        if (healthRes.status === 'fulfilled') setHealth(healthRes.value);
        if (stationsRes.status === 'fulfilled') setTotalStations(stationsRes.value?.total);
        if (modelsRes.status === 'fulfilled') setModels(modelsRes.value || []);
      } catch (err) {
        console.error('Failed to load admin metrics:', err);
      } finally {
        setLoading(false);
      }
    }
    loadAdminData();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-6 h-6 text-amber-600" />
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Administrator Control Console</h1>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          System health telemetry monitoring, database ingestion counts, and ML model registry status.
        </p>
      </div>

      {loading ? (
        <LoadingSpinner message="Querying system telemetry and API services..." />
      ) : (
        <div className="space-y-6">
          {/* Health & Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">

            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">FastAPI Service</span>
                <Activity className="w-4 h-4 text-emerald-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900">{health?.status === 'ok' ? 'HEALTHY' : 'OFFLINE'}</p>
              <p className="text-xs text-slate-500">Service: {health?.service || 'aqua-mind-api'}</p>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Total Registered Stations</span>
                <Database className="w-4 h-4 text-brand-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900">{totalStations?.toLocaleString() ?? '—'}</p>
              <p className="text-xs text-slate-500">FastAPI station registry count</p>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Active ML Models</span>
                <Cpu className="w-4 h-4 text-purple-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900">{models.length} Models</p>
              <p className="text-xs text-slate-500">Loaded in forecast engine</p>
            </div>

          </div>

          {/* Model Registry List */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-2xs space-y-4">
            <h3 className="text-sm font-bold text-slate-900">Loaded Machine Learning Models</h3>
            <div className="divide-y divide-slate-100">
              {models.map((m) => (
                <div key={m.name} className="py-3 flex items-center justify-between text-xs">
                  <div>
                    <span className="font-bold text-slate-900 uppercase">{m.name}</span>
                    <p className="text-slate-500">{m.description}</p>
                  </div>
                  <span className="font-mono font-semibold bg-slate-100 px-2 py-1 rounded text-slate-700">
                    v{m.version || '1.0'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Notice on pending admin endpoints */}
          <div className="p-4 bg-slate-100 border border-slate-200 rounded-2xl text-xs text-slate-600 flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-slate-500 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-slate-800">Admin Endpoints Notice</span>
              <p className="text-slate-500 mt-0.5">
                Advanced ingestion pipeline triggers and raw database migration management remain controlled on the backend server side. Metrics shown above are queried live from current REST endpoints.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
