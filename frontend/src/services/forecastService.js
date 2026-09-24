import { api } from './api';

export const forecastService = {
  /**
   * Fetch available forecasting models and metadata.
   */
  getModels: () => api.get('/api/models'),

  /**
   * Fetch predicted groundwater levels for a station.
   * @param {string} stationId
   * @param {Object} options
   * @param {number} options.horizonPoints - Number of horizon points (1-24)
   * @param {string} options.model - 'persistence' | 'random_forest' | 'xgboost'
   */
  getForecast: (stationId, { horizonPoints = 4, model = 'xgboost' } = {}) =>
    api.get(`/api/stations/${encodeURIComponent(stationId)}/forecast`, {
      horizon_points: horizonPoints,
      model,
    }),

  /**
   * Fetch Tree SHAP feature contribution explanation for a station forecast.
   * @param {string} stationId
   * @param {string} model - 'random_forest' | 'xgboost'
   */
  getShapExplanation: (stationId, model = 'xgboost') =>
    api.get(`/api/stations/${encodeURIComponent(stationId)}/explanation`, {
      model,
    }),
};
