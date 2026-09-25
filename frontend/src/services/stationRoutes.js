export function stationRoute(stationId) {
  return `/stations/${encodeURIComponent(stationId)}`;
}
