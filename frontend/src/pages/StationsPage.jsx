import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Radio, Search, ChevronLeft, ChevronRight, Filter } from 'lucide-react';
import { stationService } from '../services/stationService';
import { StationCard } from '../components/stations/StationCard';
import { LocationSelector } from '../components/stations/LocationSelector';
import { NearbyStationBanner } from '../components/stations/NearbyStationBanner';
import { LoadingSpinner, SkeletonCard } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';

export function StationsPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const [states, setStates] = useState([]);
  const [districts, setDistricts] = useState([]);

  const [selectedState, setSelectedState] = useState(searchParams.get('state') || null);
  const [selectedDistrict, setSelectedDistrict] = useState(searchParams.get('district') || null);
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');

  const [page, setPage] = useState(parseInt(searchParams.get('page') || '1', 10));
  const pageSize = 24;

  const [loadingStates, setLoadingStates] = useState(true);
  const [loadingDistricts, setLoadingDistricts] = useState(false);
  const [loadingStations, setLoadingStations] = useState(true);

  const [stationsData, setStationsData] = useState({ items: [], total: 0, page: 1, page_size: pageSize });
  const [error, setError] = useState(null);

  // Load States on mount
  useEffect(() => {
    async function loadStates() {
      try {
        setLoadingStates(true);
        const data = await stationService.getStates();
        setStates(data || []);
      } catch (err) {
        console.error('Failed to load states:', err);
      } finally {
        setLoadingStates(false);
      }
    }
    loadStates();
  }, []);

  // Load Districts when State changes
  useEffect(() => {
    if (!selectedState) {
      setDistricts([]);
      setSelectedDistrict(null);
      return;
    }

    async function loadDistricts() {
      try {
        setLoadingDistricts(true);
        const data = await stationService.getDistricts(selectedState);
        setDistricts(data || []);
      } catch (err) {
        console.error('Failed to load districts:', err);
      } finally {
        setLoadingDistricts(false);
      }
    }
    loadDistricts();
  }, [selectedState]);

  // Load Stations whenever State, District, or Page changes
  useEffect(() => {
    async function fetchStations() {
      try {
        setLoadingStations(true);
        setError(null);
        const response = await stationService.getStations({
          state: selectedState,
          district: selectedDistrict,
          page,
          pageSize,
        });
        setStationsData(response);
      } catch (err) {
        setError(err.message || 'Unable to connect to telemetry API service.');
      } finally {
        setLoadingStations(false);
      }
    }
    fetchStations();
  }, [selectedState, selectedDistrict, page]);

  // Handle URL sync
  const updateStateFilter = (newState) => {
    setSelectedState(newState);
    setSelectedDistrict(null);
    setPage(1);
  };

  const updateDistrictFilter = (newDistrict) => {
    setSelectedDistrict(newDistrict);
    setPage(1);
  };

  const handleResetFilters = () => {
    setSelectedState(null);
    setSelectedDistrict(null);
    setSearchQuery('');
    setPage(1);
  };

  // Filter items by client-side text search if query typed
  const filteredItems = (stationsData.items || []).filter((station) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      station.station_name?.toLowerCase().includes(q) ||
      station.state?.toLowerCase().includes(q) ||
      station.district?.toLowerCase().includes(q) ||
      station.village?.toLowerCase().includes(q) ||
      station.station_id?.toLowerCase().includes(q)
    );
  });

  const totalPages = Math.ceil(stationsData.total / pageSize) || 1;

  return (
    <div className="space-y-6">

      {/* Title & Overview Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Radio className="w-6 h-6 text-brand-600" />
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Telemetry Stations Discovery</h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Browse, filter, and inspect groundwater telemetry monitoring stations across India.
          </p>
        </div>

        {/* Search Bar */}
        <div className="relative w-full md:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search stations by name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 shadow-2xs"
          />
        </div>
      </div>

      {/* Geolocation Nearby Station Banner */}
      <NearbyStationBanner />

      {/* State & District Cascade Selector */}
      <LocationSelector
        states={states}
        districts={districts}
        selectedState={selectedState}
        selectedDistrict={selectedDistrict}
        onSelectState={updateStateFilter}
        onSelectDistrict={updateDistrictFilter}
        onResetFilters={handleResetFilters}
        loadingStates={loadingStates}
        loadingDistricts={loadingDistricts}
      />

      {/* Main Content Area */}
      {error ? (
        <ErrorMessage
          title="Telemetry API Connection Issue"
          message={error}
          onRetry={() => setPage(page)}
        />
      ) : loadingStations ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="text-center py-16 bg-white border border-slate-200 rounded-2xl p-6">
          <Radio className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-800">No Stations Found</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
            No telemetry stations match the selected filters or search query. Try choosing a different state or clearing your search.
          </p>
          <button
            onClick={handleResetFilters}
            className="mt-4 px-4 py-2 bg-brand-50 text-brand-700 hover:bg-brand-100 font-semibold text-xs rounded-xl transition-colors"
          >
            Clear All Filters
          </button>
        </div>
      ) : (
        <div className="space-y-4">

          {/* Header Count */}
          <div className="flex items-center justify-between text-xs text-slate-500 px-1">
            <span>
              Showing <strong>{filteredItems.length}</strong> of <strong>{stationsData.total?.toLocaleString() || 0}</strong> registered stations
            </span>
            <span>
              Page {page} of {totalPages}
            </span>
          </div>

          {/* Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredItems.map((station) => (
              <StationCard key={station.id} station={station} />
            ))}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t border-slate-200">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="inline-flex items-center space-x-1 px-3.5 py-2 bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 rounded-xl text-xs font-semibold shadow-2xs disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" />
                <span>Previous</span>
              </button>

              <span className="text-xs font-medium text-slate-600">
                Page {page} of {totalPages}
              </span>

              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="inline-flex items-center space-x-1 px-3.5 py-2 bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 rounded-xl text-xs font-semibold shadow-2xs disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <span>Next</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}

        </div>
      )}

    </div>
  );
}
