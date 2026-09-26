import { api } from './api';

const analyticsCache = new Map();
const gssCache = new Map();
const gbimCache = new Map();
const dieCache = new Map();

export const analyticsService = {
  /**
   * Fetch complete station analytics (GSS + GBIM + DIE).
   */
  getStationAnalytics: (stationId) => {
    if (!stationId) return Promise.reject(new Error('stationId is required'));
    if (analyticsCache.has(stationId)) return Promise.resolve(analyticsCache.get(stationId));
    return api.get(`/api/stations/${encodeURIComponent(stationId)}/analytics`).then((res) => {
      analyticsCache.set(stationId, res);
      return res;
    });
  },

  /**
   * Fetch Groundwater Sustainability Score (GSS) response.
   */
  getGSS: (stationId) => {
    if (!stationId) return Promise.reject(new Error('stationId is required'));
    if (gssCache.has(stationId)) return Promise.resolve(gssCache.get(stationId));
    return api.get(`/api/stations/${encodeURIComponent(stationId)}/gss`).then((res) => {
      gssCache.set(stationId, res);
      return res;
    });
  },

  /**
   * Fetch Groundwater Behavior Intelligence (GBIM) response.
   */
  getGBIM: (stationId) => {
    if (!stationId) return Promise.reject(new Error('stationId is required'));
    if (gbimCache.has(stationId)) return Promise.resolve(gbimCache.get(stationId));
    return api.get(`/api/stations/${encodeURIComponent(stationId)}/gbim`).then((res) => {
      gbimCache.set(stationId, res);
      return res;
    });
  },

  /**
   * Fetch Decision Intelligence Engine (DIE) recommendations.
   */
  getDIE: (stationId) => {
    if (!stationId) return Promise.reject(new Error('stationId is required'));
    if (dieCache.has(stationId)) return Promise.resolve(dieCache.get(stationId));
    return api.get(`/api/stations/${encodeURIComponent(stationId)}/die`).then((res) => {
      dieCache.set(stationId, res);
      return res;
    });
  },
};
