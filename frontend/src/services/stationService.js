import { api } from './api';

let statesCache;
let statesRequest;
const allStationsCache = new Map();
const allStationsRequests = new Map();

const districtsCache = new Map();
const stationDetailCache = new Map();
const historyCache = new Map();

export const stationService = {
  /**
   * Fetch list of available states.
   */
  getStates: () => {
    if (statesCache) return Promise.resolve(statesCache);
    if (!statesRequest) {
      statesRequest = api.get('/api/states').then((states) => {
        statesCache = states || [];
        return statesCache;
      }).finally(() => {
        statesRequest = undefined;
      });
    }
    return statesRequest;
  },

  /**
   * Fetch list of districts for a specific state.
   */
  getDistricts: (state) => {
    if (!state) return Promise.resolve([]);
    if (districtsCache.has(state)) return Promise.resolve(districtsCache.get(state));
    return api.get(`/api/states/${encodeURIComponent(state)}/districts`).then((districts) => {
      districtsCache.set(state, districts || []);
      return districts || [];
    });
  },

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
    const cacheKey = [...states].sort().join('\u001f');
    if (allStationsCache.has(cacheKey)) {
      return allStationsCache.get(cacheKey);
    }
    if (allStationsRequests.has(cacheKey)) {
      return allStationsRequests.get(cacheKey);
    }

    const request = (async () => {
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
      const items = stateItems.flat();
      allStationsCache.set(cacheKey, items);
      return items;
    })().finally(() => {
      allStationsRequests.delete(cacheKey);
    });
    allStationsRequests.set(cacheKey, request);
    return request;
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
  getStation: (stationId) => {
    if (!stationId) return Promise.reject(new Error('stationId is required'));
    if (stationDetailCache.has(stationId)) return Promise.resolve(stationDetailCache.get(stationId));
    return api.get(`/api/stations/${encodeURIComponent(stationId)}`).then((st) => {
      stationDetailCache.set(stationId, st);
      return st;
    });
  },

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
  getHistory: (stationId, { start, end, buckets = 500 } = {}) => {
    const key = `${stationId}::${start || ''}::${end || ''}::${buckets}`;
    if (historyCache.has(key)) return Promise.resolve(historyCache.get(key));
    return api.get(`/api/stations/${encodeURIComponent(stationId)}/history`, {
      start,
      end,
      buckets,
    }).then((res) => {
      historyCache.set(key, res);
      return res;
    });
  },
};
