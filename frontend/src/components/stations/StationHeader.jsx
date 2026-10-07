import React from 'react';
import { MapPin, Radio, Activity } from 'lucide-react';

export function StationHeader({ station, analytics, currentReading }) {
  if (!station) return null;

  const formatDate = (isoStr) => {
    if (!isoStr) return 'Unavailable';
    try {
      return new Date(isoStr).toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch (_) {
      return isoStr;
    }
  };

  const gssScore = analytics?.gss?.score;
  const gbimProfile = analytics?.gbim?.profile;
  const diePriority = analytics?.die?.priority;
  const hasReading = Number.isFinite(Number(currentReading?.groundwater_level));

  return (
    <div className="surface overflow-hidden">
      <div className="h-1 bg-gradient-to-r from-cyan-500 via-teal-400 to-blue-600" />
      <div className="p-5 md:p-7 space-y-5">
      {/* Top Tag & Status Badges */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div className="flex items-center space-x-2">
          <span className="px-2.5 py-1 text-xs font-bold bg-brand-50 text-brand-700 border border-brand-200 rounded-lg flex items-center space-x-1.5">
            <Radio className="w-3.5 h-3.5" />
            <span>{station.state || 'India'}</span>
          </span>
          {station.district && (
            <span className="px-2.5 py-1 text-xs font-semibold bg-slate-100 text-slate-700 rounded-lg">
              {station.district} District
            </span>
          )}
          {station.agency && (
            <span className="px-2 py-1 text-[11px] font-mono font-medium text-slate-500 bg-slate-50 border border-slate-200 rounded-md">
              Source: {station.agency}
            </span>
          )}
        </div>

        {/* Dynamic Analytics Badges */}
        <div className="flex items-center space-x-2 flex-wrap">
          {gbimProfile && (
            <span className={`px-2.5 py-1 text-xs font-bold rounded-lg ${
              gbimProfile === 'DECLINING' ? 'bg-rose-100 text-rose-800' :
              gbimProfile === 'RISING' ? 'bg-emerald-100 text-emerald-800' :
              gbimProfile === 'VOLATILE' ? 'bg-amber-100 text-amber-800' :
              'bg-slate-100 text-slate-700'
            }`}>
              Behavior: {gbimProfile}
            </span>
          )}

          {diePriority && (
            <span className={`px-2.5 py-1 text-xs font-bold rounded-lg ${
              diePriority === 'HIGH' ? 'bg-rose-600 text-white' :
              diePriority === 'MEDIUM' ? 'bg-amber-500 text-white' :
              'bg-emerald-600 text-white'
            }`}>
              DIE Priority: {diePriority}
            </span>
          )}
        </div>
      </div>

      {/* Main Station Name & Location Meta */}
      <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-6">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight">
            {station.station_name}
          </h1>
          <p className="text-xs md:text-sm text-slate-500 flex items-center space-x-1.5 mt-1">
            <MapPin className="w-4 h-4 text-brand-600 flex-shrink-0" />
            <span>
              {[station.village, station.tehsil, station.block, station.district, station.state].filter(Boolean).join(', ')}
            </span>
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3 rounded-xl bg-cyan-50 border border-cyan-100">
            <span className="eyebrow text-cyan-700 block">Current reading</span>
            <span className="mt-1 flex items-center gap-1 text-xl font-extrabold text-slate-950">
              {hasReading ? Number(currentReading.groundwater_level).toFixed(2) : '—'}
              <span className="text-xs font-medium text-slate-500">m bgl</span>
            </span>
            <span className="text-[10px] text-slate-500">{hasReading ? 'Observed telemetry' : 'Not available'}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
          <div>
            <span className="eyebrow block">Station ID</span>
            <span className="font-mono font-semibold text-slate-800">{station.station_id}</span>
          </div>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
          <div>
            <span className="eyebrow block">Total records</span>
            <span className="font-semibold text-slate-800">{station.observation_count?.toLocaleString() || 0}</span>
          </div>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
          <div>
            <span className="eyebrow block">Latest observation</span>
            <span className="font-semibold text-slate-800">{formatDate(station.latest_observation_timestamp)}</span>
          </div>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}
