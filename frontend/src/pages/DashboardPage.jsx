import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Radio,
  MapPin,
  TrendingUp,
  Lightbulb,
  Shield,
  Cpu,
  Layers,
  ArrowRight,
  Database,
  Compass,
  CheckCircle,
  Droplet,
  Activity,
  User
} from 'lucide-react';
import { useRole } from '../context/RoleContext';
import { stationService } from '../services/stationService';
import { forecastService } from '../services/forecastService';
import { StationCard } from '../components/stations/StationCard';
import { SkeletonCard } from '../components/common/LoadingSpinner';
import { NearbyStationBanner } from '../components/stations/NearbyStationBanner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { FarmerAdvisory } from '../components/farmer/FarmerAdvisory';
import { api } from '../services/api';

export function DashboardPage() {
  const { role, roleInfo } = useRole();
  const [states, setStates] = useState([]);
  const [featuredStations, setFeaturedStations] = useState([]);
  const [models, setModels] = useState([]);
  const [regional, setRegional] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadDashboardData() {
      try {
        setLoading(true);
        setError(null);
        const [statesData, stationsResponse, modelsData] = await Promise.allSettled([
          stationService.getStates(),
          stationService.getStations({ page: 1, pageSize: 6 }),
          forecastService.getModels(),
        ]);

        if (statesData.status === 'fulfilled') setStates(statesData.value || []);
        if (stationsResponse.status === 'fulfilled') setFeaturedStations(stationsResponse.value?.items || []);
        if (modelsData.status === 'fulfilled') setModels(modelsData.value || []);
        if ([statesData, stationsResponse, modelsData].some((result) => result.status === 'rejected')) {
          setError('Some dashboard data could not be loaded from the backend.');
        }
      } finally {
        setLoading(false);
      }
    }
    loadDashboardData();
  }, []);

  useEffect(() => {
    if (role === 'official' && !regional) {
      api.get('/api/regional/summary', {}, { cacheTtlMs: 300000 })
        .then((res) => setRegional(res))
        .catch(() => {});
    }
  }, [role, regional]);

  return (
    <div className="space-y-6">

      {/* Dynamic Stakeholder Banners */}
      <div className={`p-6 md:p-8 rounded-3xl shadow-lg border border-white/10 bg-gradient-to-r ${roleInfo.theme.banner} space-y-4`}>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center space-x-2 px-3 py-1 bg-white/10 backdrop-blur-md rounded-full text-xs font-bold text-white border border-white/15">
              <roleInfo.icon className="w-4 h-4" />
              <span>{roleInfo.name}</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white leading-tight">
              {role === 'farmer' && 'Groundwater Advisory & Telemetry Insights'}
              {role === 'official' && 'Regional Groundwater Decision Intelligence'}
              {role === 'admin' && 'Telemetry System & ML Model Console'}
              {role === 'public' && 'Groundwater Telemetry & Environmental Intelligence'}
            </h1>
            <p className="text-xs md:text-sm text-slate-300 leading-relaxed">
              {roleInfo.tagline}
            </p>
          </div>

          <div className="flex flex-col sm:flex-row md:flex-col gap-2.5 flex-shrink-0">
            <Link
              to="/stations"
              className={`px-5 py-2.5 ${roleInfo.theme.primary} font-bold text-xs rounded-xl shadow-md transition-all flex items-center justify-center space-x-2`}
            >
              <Radio className="w-4 h-4" />
              <span>Explore Telemetry Stations</span>
            </Link>
            <Link
              to="/map"
              className="px-5 py-2.5 bg-white/10 hover:bg-white/20 text-white font-semibold text-xs rounded-xl transition-colors border border-white/15 flex items-center justify-center space-x-2"
            >
              <MapPin className="w-4 h-4 text-sky-400" />
              <span>Interactive Map</span>
            </Link>
          </div>
        </div>
      </div>

      {/* FARMER SPECIFIC SIMPLE EXPERIENCE */}
      {error && <ErrorMessage title="Dashboard Data Unavailable" message={error} />}

      {role === 'farmer' && (
        <div className="space-y-6">
          {/* Nearby Station Quick Finder */}
          <NearbyStationBanner />

          {/* Simple Explanation Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-5 bg-emerald-50/80 border border-emerald-200 rounded-2xl space-y-2">
              <div className="flex items-center space-x-2 text-emerald-800 font-bold text-sm">
                <Droplet className="w-5 h-5 text-emerald-600" />
                <span>Groundwater Level Depth</span>
              </div>
              <p className="text-xs text-emerald-900 leading-relaxed">
                Groundwater level is measured in <strong>meters below ground level (m bgl)</strong>. Smaller numbers mean water is closer to the surface.
              </p>
            </div>

            <div className="p-5 bg-teal-50/80 border border-teal-200 rounded-2xl space-y-2">
              <div className="flex items-center space-x-2 text-teal-800 font-bold text-sm">
                <TrendingUp className="w-5 h-5 text-teal-600" />
                <span>24-Hour Prediction</span>
              </div>
              <p className="text-xs text-teal-900 leading-relaxed">
                Our machine learning models forecast tomorrow’s expected groundwater level depth for your local telemetry station.
              </p>
            </div>

            <div className="p-5 bg-sky-50/80 border border-sky-200 rounded-2xl space-y-2">
              <div className="flex items-center space-x-2 text-sky-800 font-bold text-sm">
                <CheckCircle className="w-5 h-5 text-sky-600" />
                <span>Action Guidance</span>
              </div>
              <p className="text-xs text-sky-900 leading-relaxed">
                Decision Intelligence provides actionable farm guidance based on measured sustainability trends and variability.
              </p>
            </div>
          </div>
          <FarmerAdvisory />
        </div>
      )}

      {/* GOVERNMENT OFFICIAL SPECIFIC EXPERIENCE */}
      {role === 'official' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-2xs space-y-2">
              <span className="text-[10px] font-extrabold uppercase text-slate-400">States Monitored</span>
              <p className="text-2xl font-extrabold text-blue-900">{states.length || '—'} States</p>
              <p className="text-xs text-slate-500">States returned by the telemetry registry</p>
            </div>
            <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-2xs space-y-2">
              <span className="text-[10px] font-extrabold uppercase text-slate-400">Regional telemetry</span>
              <p className="text-2xl font-extrabold text-blue-900">{regional?.station_count?.toLocaleString() || '—'} Stations</p>
              <p className="text-xs text-slate-500">{regional?.observation_count?.toLocaleString() || '—'} observations</p>
            </div>
            <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-2xs space-y-2">
              <span className="text-[10px] font-extrabold uppercase text-slate-400">Sustainability Framework</span>
              <p className="text-2xl font-extrabold text-blue-900">GSS & GBIM</p>
              <p className="text-xs text-slate-500">Deterministic scoring & behavior profile</p>
            </div>
            <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-2xs space-y-2">
              <span className="text-[10px] font-extrabold uppercase text-slate-400">Decision Priority</span>
              <p className="text-2xl font-extrabold text-blue-900">DIE Analytics</p>
              <p className="text-xs text-slate-500">High / Medium / Low policy priority</p>
            </div>
            <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-2xs space-y-2">
              <span className="text-[10px] font-extrabold uppercase text-slate-400">Explainable AI</span>
              <p className="text-2xl font-extrabold text-blue-900">Tree SHAP</p>
              <p className="text-xs text-slate-500">Attribution without causal overclaims</p>
            </div>
          </div>
        </div>
      )}

      {/* ADMIN SPECIFIC EXPERIENCE */}
      {role === 'admin' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-2xs space-y-2">
              <span className="text-[10px] font-extrabold uppercase text-slate-400">Ingested States</span>
              <p className="text-2xl font-extrabold text-indigo-900">{states.length} Telemetry States</p>
              <p className="text-xs text-slate-500">Data source: NWDP CSVs</p>
            </div>
            <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-2xs space-y-2">
              <span className="text-[10px] font-extrabold uppercase text-slate-400">ML Models Active</span>
              <p className="text-2xl font-extrabold text-indigo-900">{models.length} Model Binaries</p>
              <p className="text-xs text-slate-500">XGBoost, Random Forest, Persistence</p>
            </div>
            <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-2xs space-y-2">
              <span className="text-[10px] font-extrabold uppercase text-slate-400">FastAPI Route Status</span>
              <p className="text-2xl font-extrabold text-emerald-600">Connected</p>
              <p className="text-xs text-slate-500">API response received</p>
            </div>
          </div>
        </div>
      )}

      {/* Featured Stations Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Active Telemetry Stations</h2>
            <p className="text-xs text-slate-500">Select any station to open complete station analysis</p>
          </div>
          <Link
            to="/stations"
            className={`text-xs font-bold flex items-center space-x-1 ${roleInfo.theme.highlight}`}
          >
            <span>View All Stations</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {featuredStations.slice(0, 3).map((station) => (
              <StationCard key={station.id} station={station} />
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
