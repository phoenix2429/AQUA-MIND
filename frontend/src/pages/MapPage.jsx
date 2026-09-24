import React, { useState, useEffect } from 'react';
import { MapPin, Navigation, Filter, Radio } from 'lucide-react';
import { stationService } from '../services/stationService';
import { StationMap } from '../components/map/StationMap';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';

export function MapPage() {
  const [states, setStates] = useState([]);
  const [selectedState, setSelectedState] = useState('');
  const [stations, setStations] = useState([]);
  const [mapCenter, setMapCenter] = useState([17.385, 78.4867]); // Hyderabad default
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadStates() {
      try {
        const data = await stationService.getStates();
        setStates(data || []);
      } catch (_) {}
    }
    loadStates();
  }, []);

  useEffect(() => {
    async function fetchMapStations() {
      try {
        setLoading(true);
        setError(null);
        const response = await stationService.getStations({
          state: selectedState || undefined,
          page: 1,
          pageSize: 200,
        });

        const items = response?.items || [];
        setStations(items);

        // Compute dynamic center if valid stations exist
        const withCoords = items.filter(s => typeof s.latitude === 'number' && typeof s.longitude === 'number');
        if (withCoords.length > 0) {
          const avgLat = withCoords.reduce((acc, s) => acc + s.latitude, 0) / withCoords.length;
          const avgLon = withCoords.reduce((acc, s) => acc + s.longitude, 0) / withCoords.length;
          setMapCenter([avgLat, avgLon]);
        }
      } catch (err) {
        setError(err.message || 'Unable to load telemetry stations for map.');
      } finally {
        setLoading(false);
      }
    }
    fetchMapStations();
  }, [selectedState]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <MapPin className="w-6 h-6 text-brand-600" />
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Interactive Geospatial Map</h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Geospatial distribution of National Water Data Portal (NWDP) telemetry stations across India.
          </p>
        </div>

        {/* State Filter */}
        <div className="flex items-center space-x-2 bg-white p-2 rounded-xl border border-slate-200 shadow-2xs">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={selectedState}
            onChange={(e) => setSelectedState(e.target.value)}
            className="text-xs bg-transparent border-none text-slate-800 font-semibold focus:outline-none"
          >
            <option value="">All Telemetry States ({states.length})</option>
            {states.map((st) => (
              <option key={st} value={st}>
                {st}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Map Display */}
      {loading ? (
        <LoadingSpinner message="Fetching telemetry station coordinates..." />
      ) : error ? (
        <ErrorMessage title="Map Loading Issue" message={error} />
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-500 px-1">
            <span>
              Displaying <strong>{stations.filter(s => s.latitude && s.longitude).length}</strong> mapped stations
            </span>
            <span>Click any marker to inspect station details</span>
          </div>

          <StationMap stations={stations} center={mapCenter} zoom={selectedState ? 8 : 6} />
        </div>
      )}
    </div>
  );
}
