import React, { useState } from 'react';
import { Navigation, MapPin, AlertCircle, Loader2, Compass } from 'lucide-react';
import { stationService } from '../../services/stationService';
import { StationCard } from './StationCard';

export function NearbyStationBanner() {
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [nearbyResult, setNearbyResult] = useState(null);

  const handleUseLocation = () => {
    if (!navigator.geolocation) {
      setErrorMsg('Geolocation is not supported by your browser.');
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    setNearbyResult(null);

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const latitude = position.coords.latitude;
          const longitude = position.coords.longitude;
          const response = await stationService.getNearbyStations({
            latitude,
            longitude,
            radiusKm: 100,
            limit: 6,
          });
          setNearbyResult(response);
        } catch (err) {
          setErrorMsg(err.message || 'Failed to fetch nearby stations from backend.');
        } finally {
          setLoading(false);
        }
      },
      (geoErr) => {
        setLoading(false);
        if (geoErr.code === geoErr.PERMISSION_DENIED) {
          setErrorMsg('Location access was denied. You can select a station manually.');
        } else if (geoErr.code === geoErr.POSITION_UNAVAILABLE) {
          setErrorMsg('Location information is unavailable. Please select a station manually.');
        } else {
          setErrorMsg('Location request timed out. Please try selecting a station manually.');
        }
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  return (
    <div className="bg-gradient-to-r from-slate-900 to-brand-950 border border-brand-800/40 rounded-2xl p-5 text-white space-y-4 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-2 text-brand-300 font-semibold text-xs uppercase tracking-wider">
            <Compass className="w-4 h-4 text-aqua-400" />
            <span>Geospatial Telemetry Discovery</span>
          </div>
          <h2 className="text-lg font-bold text-white">Find Telemetry Stations Near You</h2>
          <p className="text-xs text-slate-300">
            Use your device location to discover nearest groundwater monitoring stations via Haversine backend distance matching.
          </p>
        </div>

        <button
          onClick={handleUseLocation}
          disabled={loading}
          className="inline-flex items-center justify-center space-x-2 px-4 py-2 bg-gradient-to-r from-aqua-500 to-brand-500 hover:from-aqua-600 hover:to-brand-600 text-white text-xs font-bold rounded-xl shadow-md shadow-brand-500/20 transition-all flex-shrink-0 disabled:opacity-50"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Locating...</span>
            </>
          ) : (
            <>
              <Navigation className="w-4 h-4" />
              <span>Use My Location</span>
            </>
          )}
        </button>
      </div>

      {/* Geolocation Permission / Error Message */}
      {errorMsg && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-200 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Nearby Results Display */}
      {nearbyResult && nearbyResult.items && nearbyResult.items.length > 0 && (
        <div className="space-y-3 pt-3 border-t border-white/10">
          <div className="flex items-center justify-between text-xs text-slate-300">
            <span>
              Found <strong>{nearbyResult.items.length}</strong> stations within {nearbyResult.radius_km} km of your position ({nearbyResult.latitude.toFixed(4)}°, {nearbyResult.longitude.toFixed(4)}°)
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 text-slate-900">
            {nearbyResult.items.map((station) => (
              <div key={station.id} className="relative">
                <div className="absolute top-3 right-3 z-10 bg-slate-900/90 text-aqua-300 text-[10px] font-bold font-mono px-2 py-0.5 rounded-full border border-aqua-500/30">
                  {station.distance_km} km away
                </div>
                <StationCard station={station} />
              </div>
            ))}
          </div>
        </div>
      )}

      {nearbyResult && nearbyResult.items && nearbyResult.items.length === 0 && (
        <p className="text-xs text-slate-400 italic">No telemetry stations found within {nearbyResult.radius_km} km radius.</p>
      )}
    </div>
  );
}
