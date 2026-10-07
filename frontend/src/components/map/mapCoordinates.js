// Verified display correction for a source coordinate that places the
// Battiprolu station offshore. The backend/database value is unchanged.
const DISPLAY_COORDINATE_OVERRIDES = {
  'Andhra Pradesh::33/11 KV substation': {
    latitude: 16.1026,
    longitude: 80.7807,
  },
};

export function getMapCoordinates(station) {
  const override = DISPLAY_COORDINATE_OVERRIDES[station.station_id];
  return override || {
    latitude: station.latitude,
    longitude: station.longitude,
  };
}

export function getMapStation(station) {
  const coordinates = getMapCoordinates(station);
  return { ...station, ...coordinates };
}
