import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import { Link } from 'react-router-dom';
import L from 'leaflet';
import { MapPin, Calendar, Database, ChevronRight } from 'lucide-react';
import { stationRoute } from '../../services/stationRoutes';
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

export function StationMap({ stations = [], center = [17.385, 78.4867], zoom = 7 }) {
  const validStations = stations.filter(
    (s) => typeof s.latitude === 'number' && typeof s.longitude === 'number'
  );

  return (
    <div className="w-full h-[550px] rounded-2xl overflow-hidden border border-slate-200 shadow-sm relative">
      <MapContainer
        center={center}
        zoom={zoom}
        scrollWheelZoom={true}
        className="w-full h-full"
      >
        <MapRecenter center={center} />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MarkerClusterGroup chunkedLoading removeOutsideVisibleBounds>
          {validStations.map((station) => (
            <Marker
              key={station.id}
              position={[station.latitude, station.longitude]}
            >
              <Popup className="aqua-map-popup">
                <div className="p-1 space-y-2 text-xs font-sans min-w-[200px]">
                  <div className="flex items-center space-x-1 text-slate-500 font-semibold text-[10px] uppercase">
                    <span>{station.state}</span>
                    {station.district && <span>• {station.district}</span>}
                  </div>

                  <h4 className="font-bold text-slate-900 text-sm leading-tight">
                    {station.station_name}
                  </h4>

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
          ))}
        </MarkerClusterGroup>
      </MapContainer>
    </div>
  );
}
