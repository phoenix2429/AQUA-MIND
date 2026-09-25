import { api } from './api';

export const analyticsService = {
  /**
   * Fetch complete station analytics (GSS + GBIM + DIE).
   */
  getStationAnalytics: (stationId) =>
    api.get(`/api/stations/${encodeURIComponent(stationId)}/analytics`),

  /**
   * Fetch Groundwater Sustainability Score (GSS) response.
   */
  getGSS: (stationId) =>
    api.get(`/api/stations/${encodeURIComponent(stationId)}/gss`),

  /**
   * Fetch Groundwater Behavior Intelligence (GBIM) response.
   */
  getGBIM: (stationId) =>
    api.get(`/api/stations/${encodeURIComponent(stationId)}/gbim`),

  /**
   * Fetch Decision Intelligence Engine (DIE) recommendations.
   */
  getDIE: (stationId) =>
    api.get(`/api/stations/${encodeURIComponent(stationId)}/die`),
};
