import React from 'react';
import { Map, Filter, RefreshCcw } from 'lucide-react';

export function LocationSelector({ 
  states, 
  districts, 
  selectedState, 
  selectedDistrict, 
  onSelectState, 
  onSelectDistrict,
  onResetFilters,
  loadingStates,
  loadingDistricts 
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2 text-slate-900 font-bold text-sm">
          <Filter className="w-4 h-4 text-brand-600" />
          <span>Regional Discovery Filter</span>
        </div>
        {(selectedState || selectedDistrict) && (
          <button
            onClick={onResetFilters}
            className="text-xs text-brand-600 hover:text-brand-800 font-medium flex items-center space-x-1"
          >
            <RefreshCcw className="w-3 h-3" />
            <span>Reset</span>
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* State Selector */}
        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
            State
          </label>
          <select
            value={selectedState || ''}
            onChange={(e) => onSelectState(e.target.value || null)}
            disabled={loadingStates}
            className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 disabled:opacity-60"
          >
            <option value="">All States ({states.length})</option>
            {states.map((state) => (
              <option key={state} value={state}>
                {state}
              </option>
            ))}
          </select>
        </div>

        {/* District Selector */}
        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
            District
          </label>
          <select
            value={selectedDistrict || ''}
            onChange={(e) => onSelectDistrict(e.target.value || null)}
            disabled={!selectedState || loadingDistricts}
            className="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <option value="">
              {!selectedState 
                ? 'Select a state first' 
                : loadingDistricts 
                ? 'Loading districts...' 
                : `All Districts in ${selectedState} (${districts.length})`}
            </option>
            {districts.map((district) => (
              <option key={district} value={district}>
                {district}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
