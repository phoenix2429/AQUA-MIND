import React, { memo, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import { Link } from 'react-router-dom';
import L from 'leaflet';
import { MapPin, Calendar, Database, ChevronRight, LocateFixed, LoaderCircle } from 'lucide-react';
import { stationRoute } from '../../services/stationRoutes';
import { getMapStation } from './mapCoordinates';
import 'leaflet/dist/leaflet.css';
import 'react-leaflet-cluster/lib/assets/MarkerCluster.css';
import 'react-leaflet-cluster/lib/assets/MarkerCluster.Default.css';

// Fix default Leaflet marker icon paths in Vite
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

function MapRecenter({ center }) {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.flyTo(center, map.getZoom(), { duration: 1.5 });
    }
  }, [center, map]);
  return null;
}

function CurrentLocationControl({ location, onLocate, locating }) {
  const map = useMap();

  const handleLocate = () => {
    onLocate((position) => {
      const nextLocation = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
      };
      map.flyTo([nextLocation.latitude, nextLocation.longitude], 10, { duration: 1 });
      return nextLocation;
    });
  };

  return (
    <>
      <div className="leaflet-top leaflet-right" style={{ marginTop: 10, marginRight: 10 }}>
        <button
          type="button"
          onClick={handleLocate}
          disabled={locating}
          title="Center map on my current location"
          aria-label="Center map on my current location"
          className="leaflet-control rounded-lg border border-slate-200 bg-white p-2 text-slate-700 shadow-md hover:bg-slate-50 disabled:cursor-wait disabled:opacity-60"
        >
          {locating ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <LocateFixed className="h-4 w-4" />}
        </button>
      </div>
      {location && (
        <>
          <Circle
            center={[location.latitude, location.longitude]}
            radius={Math.max(location.accuracy || 0, 25)}
            pathOptions={{ color: '#0284c7', fillColor: '#38bdf8', fillOpacity: 0.14 }}
          />
          <Marker position={[location.latitude, location.longitude]}>
            <Popup>
              <strong>Your current location</strong>
              <br />
              Accuracy: approximately {Math.round(location.accuracy || 0)} m
            </Popup>
          </Marker>
        </>
      )}
    </>
  );
}

const StationMarker = memo(function StationMarker({ station }) {
  return (
    <Marker position={[station.latitude, station.longitude]}>
      <Popup className="aqua-map-popup">
        <div className="p-1 space-y-2 text-xs font-sans min-w-[200px]">
          <div className="flex items-center space-x-1 text-slate-500 font-semibold text-[10px] uppercase">
            <span>{station.state}</span>
            {station.district && <span>• {station.district}</span>}
          </div>
          <h4 className="font-bold text-slate-900 text-sm leading-tight">{station.station_name}</h4>
          <div className="space-y-1 text-slate-600 text-[11px]">
            <div className="flex items-center space-x-1">
              <Database className="w-3 h-3 text-brand-500" />
              <span>{station.observation_count?.toLocaleString()} observations</span>
            </div>
            {station.latest_observation_timestamp && (
              <div className="flex items-center space-x-1">
                <Calendar className="w-3 h-3 text-slate-400" />
                <span>{new Date(station.latest_observation_timestamp).toLocaleDateString('en-IN')}</span>
              </div>
            )}
          </div>
          <div className="pt-2 border-t border-slate-100 flex justify-end">
            <Link
              to={stationRoute(station.station_id)}
              className="inline-flex items-center space-x-1 text-xs font-bold text-brand-600 hover:text-brand-800"
            >
              <span>View Analysis</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </Popup>
    </Marker>
  );
});

export const StationMap = memo(function StationMap({
  stations = [],
  center = [17.385, 78.4867],
  zoom = 7,
  location,
  onLocate,
  locating = false,
}) {
  const validStations = useMemo(() => stations.map(getMapStation).filter(
    (s) => typeof s.latitude === 'number' && typeof s.longitude === 'number'
  ), [stations]);

  return (
    <div className="w-full h-[550px] rounded-2xl overflow-hidden border border-slate-200 shadow-sm relative">
      <MapContainer
        center={center}
        zoom={zoom}
        scrollWheelZoom={true}
        className="w-full h-full"
      >
        <MapRecenter center={center} />
        <CurrentLocationControl location={location} onLocate={onLocate} locating={locating} />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MarkerClusterGroup chunkedLoading removeOutsideVisibleBounds>
          {validStations.map((station) => (
            <StationMarker key={station.id ?? station.station_id} station={station} />
          ))}
        </MarkerClusterGroup>
      </MapContainer>
    </div>
  );
});
