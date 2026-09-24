import React from 'react';
import { Link } from 'react-router-dom';
import { MapPin, Calendar, Database, ChevronRight, Layers } from 'lucide-react';

export function StationCard({ station }) {
  const formatDate = (isoStr) => {
    if (!isoStr) return 'No timestamp available';
    try {
      const date = new Date(isoStr);
      return date.toLocaleDateString('en-IN', {
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

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 hover:border-brand-300 hover:shadow-md transition-all flex flex-col justify-between group">
      <div className="space-y-3">

        {/* Header Badges */}
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center space-x-1.5">
            <span className="px-2 py-0.5 text-[11px] font-semibold bg-brand-50 text-brand-700 border border-brand-200 rounded-md">
              {station.state || 'Unknown State'}
            </span>
            {station.district && (
              <span className="px-2 py-0.5 text-[11px] font-medium bg-slate-100 text-slate-700 rounded-md">
                {station.district}
              </span>
            )}
          </div>
          {station.agency && (
            <span className="text-[10px] font-mono font-medium text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-100">
              {station.agency}
            </span>
          )}
        </div>

        {/* Station Title */}
        <div>
          <h3 className="text-base font-bold text-slate-900 group-hover:text-brand-700 transition-colors line-clamp-1">
            {station.station_name}
          </h3>
          <p className="text-xs text-slate-500 flex items-center space-x-1 mt-0.5">
            <MapPin className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
            <span className="truncate">
              {[station.village, station.tehsil, station.block].filter(Boolean).join(', ') || 'Telemetry Station Location'}
            </span>
          </p>
        </div>

        {/* Meta Stats Grid */}
        <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100 text-xs">
          <div>
            <span className="text-slate-400 text-[10px] uppercase font-semibold tracking-wider block">Observations</span>
            <div className="flex items-center space-x-1 font-semibold text-slate-700 mt-0.5">
              <Database className="w-3.5 h-3.5 text-brand-500" />
              <span>{station.observation_count?.toLocaleString() || 0}</span>
            </div>
          </div>

          <div>
            <span className="text-slate-400 text-[10px] uppercase font-semibold tracking-wider block">Elevation</span>
            <div className="flex items-center space-x-1 font-semibold text-slate-700 mt-0.5">
              <Layers className="w-3.5 h-3.5 text-emerald-500" />
              <span>{station.elevation_msl != null ? `${station.elevation_msl} m MSL` : 'N/A'}</span>
            </div>
          </div>
        </div>

      </div>

      {/* Footer Timestamp & Action */}
      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
        <div className="text-[11px] text-slate-500 flex items-center space-x-1">
          <Calendar className="w-3.5 h-3.5 text-slate-400" />
          <span className="truncate">{formatDate(station.latest_observation_timestamp)}</span>
        </div>

        <Link
          to={`/stations/${station.station_id}`}
          className="inline-flex items-center space-x-1 text-xs font-semibold text-brand-600 hover:text-brand-800 transition-colors group-hover:translate-x-0.5 transition-transform"
        >
          <span>Analysis</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}
