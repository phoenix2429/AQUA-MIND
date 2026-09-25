import { api } from './api';

export const stationService = {
  /**
   * Fetch list of available states.
   */
  getStates: () => api.get('/api/states'),

  /**
   * Fetch list of districts for a specific state.
   */
  getDistricts: (state) => api.get(`/api/states/${encodeURIComponent(state)}/districts`),

  /**
   * List stations with state, district filters & pagination.
   */
  getStations: ({ state, district, page = 1, pageSize = 50 } = {}) =>
    api.get('/api/stations', {
      state,
      district,
      page,
      page_size: pageSize,
    }),

  /**
   * Fetch every station for the supplied states using the API's page limit.
   */
  getAllStations: async (states) => {
    const pageSize = 200;
    const stateItems = await Promise.all(
      states.map(async (state) => {
        const firstPage = await stationService.getStations({ state, page: 1, pageSize });
        const totalPages = Math.ceil(firstPage.total / pageSize);
        const remainingPages = await Promise.all(
          Array.from({ length: Math.max(0, totalPages - 1) }, (_, index) =>
            stationService.getStations({ state, page: index + 2, pageSize })
          )
        );
        return [firstPage.items, ...remainingPages.map((page) => page.items)].flat();
      })
    );
    return stateItems.flat();
  },

  /**
   * Fetch nearby stations based on geolocation coordinates.
   */
  getNearbyStations: ({ latitude, longitude, radiusKm = 50, limit = 10 }) =>
    api.get('/api/stations/nearby', {
      latitude,
      longitude,
      radius_km: radiusKm,
      limit,
    }),

  /**
   * Fetch detailed metadata for a single station by station_id.
   */
  getStation: (stationId) => api.get(`/api/stations/${encodeURIComponent(stationId)}`),

  /**
   * Fetch paginated raw observations for a station.
   */
  getObservations: (stationId, { start, end, page = 1, pageSize = 500 } = {}) =>
    api.get(`/api/stations/${encodeURIComponent(stationId)}/observations`, {
      start,
      end,
      page,
      page_size: pageSize,
    }),

  /**
   * Fetch aggregated historical time-series points for chart rendering.
   */
  getHistory: (stationId, { start, end, buckets = 500 } = {}) =>
    api.get(`/api/stations/${encodeURIComponent(stationId)}/history`, {
      start,
      end,
      buckets,
    }),
};
