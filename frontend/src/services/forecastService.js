import { api } from './api';

let modelsCache = null;
const forecastCache = new Map();
const shapCache = new Map();

export const forecastService = {
  /**
   * Fetch available forecasting models and metadata.
   */
  getModels: () => {
    if (modelsCache) return Promise.resolve(modelsCache);
    return api.get('/api/models').then((res) => {
      modelsCache = res;
      return res;
    });
  },

  /**
   * Fetch predicted groundwater levels for a station.
   * @param {string} stationId
   * @param {Object} options
   * @param {number} options.horizonPoints - Number of horizon points (1-24)
   * @param {string} options.model - 'persistence' | 'random_forest' | 'xgboost'
   */
  getForecast: (stationId, { horizonPoints = 4, model = 'xgboost' } = {}) => {
    const key = `${stationId}::${horizonPoints}::${model}`;
    if (forecastCache.has(key)) return Promise.resolve(forecastCache.get(key));
    return api.get(`/api/stations/${encodeURIComponent(stationId)}/forecast`, {
      horizon_points: horizonPoints,
      model,
    }).then((res) => {
      forecastCache.set(key, res);
      return res;
    });
  },

  /**
   * Fetch Tree SHAP feature contribution explanation for a station forecast.
   * @param {string} stationId
   * @param {string} model - 'random_forest' | 'xgboost'
   */
  getShapExplanation: (stationId, model = 'xgboost') => {
    const key = `${stationId}::${model}`;
    if (shapCache.has(key)) return Promise.resolve(shapCache.get(key));
    return api.get(`/api/stations/${encodeURIComponent(stationId)}/explanation`, {
      model,
    }).then((res) => {
      shapCache.set(key, res);
      return res;
    });
  },
};
