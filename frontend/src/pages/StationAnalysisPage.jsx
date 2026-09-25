import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  BarChart2,
  TrendingUp,
  Lightbulb,
  Shield,
  Activity,
  FileText,
  Clock,
  Radio,
  Layers
} from 'lucide-react';
import { useRole } from '../context/RoleContext';
import { stationService } from '../services/stationService';
import { analyticsService } from '../services/analyticsService';
import { StationHeader } from '../components/stations/StationHeader';
import { HistoryChart } from '../components/charts/HistoryChart';
import { ForecastSection } from '../components/forecast/ForecastSection';
import { ShapSection } from '../components/insights/ShapSection';
import { GssSection } from '../components/insights/GssSection';
import { GbimSection } from '../components/insights/GbimSection';
import { DieSection } from '../components/recommendations/DieSection';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';

export function StationAnalysisPage() {
  const { stationId } = useParams();
  const { roleInfo } = useRole();

  const [station, setStation] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Tab Navigation State
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'history' | 'forecast' | 'shap' | 'gss_gbim' | 'die'

  useEffect(() => {
    async function loadStationData() {
      if (!stationId) return;
      try {
        setLoading(true);
        setError(null);

        const [stationRes, analyticsRes] = await Promise.allSettled([
          stationService.getStation(stationId),
          analyticsService.getStationAnalytics(stationId),
        ]);

        if (stationRes.status === 'fulfilled') {
          setStation(stationRes.value);
        } else {
          throw new Error(`Station '${stationId}' was not found or backend API is unreachable.`);
        }

        if (analyticsRes.status === 'fulfilled') {
          setAnalytics(analyticsRes.value);
        }
      } catch (err) {
        setError(err.message || 'Failed to load station analysis.');
      } finally {
        setLoading(false);
      }
    }
    loadStationData();
  }, [stationId]);

  if (loading) {
    return <LoadingSpinner message={`Loading telemetry analysis for ${stationId}...`} />;
  }

  if (error || !station) {
    return (
      <div className="space-y-4">
        <Link
          to="/stations"
          className="inline-flex items-center space-x-1.5 text-xs font-bold text-slate-600 hover:text-brand-700"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Stations</span>
        </Link>
        <ErrorMessage title="Station Analysis Error" message={error} />
      </div>
    );
  }

  const tabs = [
    { id: 'overview', label: 'Overview & Summary', icon: BarChart2 },
    { id: 'history', label: 'Groundwater History', icon: Clock },
    { id: 'forecast', label: '24h ML Forecast', icon: TrendingUp },
    { id: 'shap', label: 'Tree SHAP Insights', icon: Lightbulb },
    { id: 'gss_gbim', label: 'GSS & Behavior', icon: Shield },
    { id: 'die', label: 'Decision Intelligence', icon: Activity },
  ];

  return (
    <div className="space-y-6">

      {/* Top Back Nav Button */}
      <div className="flex items-center justify-between">
        <Link
          to="/stations"
          className="inline-flex items-center space-x-1.5 text-xs font-bold text-slate-600 hover:text-brand-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Stations Discovery</span>
        </Link>

        <span className="text-xs text-slate-400 font-mono">
          Station Analysis • {station.station_id}
        </span>
      </div>

      {/* 1. Station Header Banner */}
      <StationHeader station={station} analytics={analytics} />

      {/* 2. Analytical Tabbed Navigation Bar */}
      <div className="bg-white p-1.5 rounded-2xl border border-slate-200 shadow-2xs flex items-center space-x-1 overflow-x-auto no-scrollbar">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all flex-shrink-0
                ${isActive
                  ? `${roleInfo.theme.primary} shadow-2xs`
                  : 'text-slate-600 hover:bg-slate-100/70 hover:text-slate-900'}
              `}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* 3. Tab Content Panels */}
      <div className="space-y-6">

        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-6 animate-in fade-in duration-200">
            {/* Key Metric Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-2xs space-y-1">
                <span className="text-[10px] uppercase font-extrabold text-slate-400 block">Total Observations</span>
                <span className="text-2xl font-extrabold text-slate-900">{station.observation_count?.toLocaleString() || 0}</span>
                <span className="text-[10px] text-slate-500 block">Telemetry records</span>
              </div>

              <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-2xs space-y-1">
                <span className="text-[10px] uppercase font-extrabold text-slate-400 block">GSS Metric</span>
                <span className="text-2xl font-extrabold text-teal-700">
                  {analytics?.gss?.score != null ? Math.round(analytics.gss.score) : 'N/A'}
                </span>
                <span className="text-[10px] text-slate-500 block">/ 100 Analytical Score</span>
              </div>

              <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-2xs space-y-1">
                <span className="text-[10px] uppercase font-extrabold text-slate-400 block">Groundwater Behavior</span>
                <span className="text-base font-extrabold text-slate-900 truncate block mt-1">
                  {analytics?.gbim?.profile || 'UNKNOWN'}
                </span>
                <span className="text-[10px] text-slate-500 block">Measured profile</span>
              </div>

              <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-2xs space-y-1">
                <span className="text-[10px] uppercase font-extrabold text-slate-400 block">DIE Priority</span>
                <span className="text-base font-extrabold text-brand-700 truncate block mt-1">
                  {analytics?.die?.priority ? `${analytics.die.priority} Priority` : 'Evaluated'}
                </span>
                <span className="text-[10px] text-slate-500 block">Decision priority</span>
              </div>
            </div>

            {/* Quick Chart Preview */}
            <HistoryChart stationId={station.station_id} />

            {/* DIE Recommendation Overview */}
            <DieSection die={analytics?.die} />
          </div>
        )}

        {/* HISTORY TAB */}
        {activeTab === 'history' && (
          <div className="animate-in fade-in duration-200">
            <HistoryChart stationId={station.station_id} />
          </div>
        )}

        {/* FORECAST TAB */}
        {activeTab === 'forecast' && (
          <div className="animate-in fade-in duration-200">
            <ForecastSection stationId={station.station_id} />
          </div>
        )}

        {/* SHAP TAB */}
        {activeTab === 'shap' && (
          <div className="animate-in fade-in duration-200">
            <ShapSection stationId={station.station_id} />
          </div>
        )}

        {/* GSS & GBIM TAB */}
        {activeTab === 'gss_gbim' && (
          <div className="space-y-6 animate-in fade-in duration-200">
            <GssSection gss={analytics?.gss} />
            <GbimSection gbim={analytics?.gbim} />
          </div>
        )}

        {/* DIE TAB */}
        {activeTab === 'die' && (
          <div className="animate-in fade-in duration-200">
            <DieSection die={analytics?.die} />
          </div>
        )}

      </div>

    </div>
  );
}
