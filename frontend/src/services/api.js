/**
 * Centralized API client for AQUA-MIND FastAPI Backend.
 * Consumes real FastAPI endpoints and handles errors, network failures, and parsing.
 */

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '';
// When accessed from another machine or via a tunnel (HTTPS), always use relative URL ('')
// so requests proxy through Vite and avoid Mixed Content or teammate localhost connection errors.
const isRemoteOrTunnel = typeof window !== 'undefined' && 
  window.location.hostname !== 'localhost' && 
  window.location.hostname !== '127.0.0.1';
const BASE_URL = isRemoteOrTunnel ? '' : rawBaseUrl;

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

// In-flight request deduplication map: cacheKey -> Promise
const inFlightRequests = new Map();

// In-memory TTL cache: cacheKey -> { data: any, expiresAt: number }
const memoryCache = new Map();

export async function request(endpoint, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const url = `${BASE_URL}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
  const isGet = method === 'GET';
  const cacheKey = isGet ? url : null;
  const ttl = options.cacheTtlMs ?? 0;

  // 1. Check TTL cache if enabled
  if (isGet && ttl > 0 && memoryCache.has(cacheKey)) {
    const entry = memoryCache.get(cacheKey);
    if (Date.now() < entry.expiresAt) {
      return entry.data;
    }
    memoryCache.delete(cacheKey);
  }

  // 2. In-flight request de-duplication
  if (isGet && inFlightRequests.has(cacheKey)) {
    return inFlightRequests.get(cacheKey);
  }

  const reqPromise = (async () => {
    const headers = {
      'Accept': 'application/json',
      ...options.headers,
    };

    try {
      const response = await fetch(url, { ...options, headers });

      if (!response.ok) {
        let errorData = null;
        try {
          errorData = await response.json();
        } catch (_) {
          errorData = await response.text();
        }

        const detailMsg = typeof errorData === 'object' && errorData?.detail
          ? (typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail))
          : `API request failed with status ${response.status}`;

        throw new ApiError(detailMsg, response.status, errorData);
      }

      const data = await response.json();

      if (isGet && ttl > 0) {
        memoryCache.set(cacheKey, { data, expiresAt: Date.now() + ttl });
      }

      return data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      // Network or parse error
      throw new ApiError(
        error.message === 'Failed to fetch'
          ? 'Unable to connect to the AQUA-MIND backend service. Please check if the backend is running.'
          : error.message,
        0,
        null
      );
    }
  })().finally(() => {
    if (isGet) {
      inFlightRequests.delete(cacheKey);
    }
  });

  if (isGet) {
    inFlightRequests.set(cacheKey, reqPromise);
  }

  return reqPromise;
}

export const api = {
  get: (endpoint, params = {}, options = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        query.append(key, val);
      }
    });
    const queryString = query.toString();
    const fullEndpoint = queryString ? `${endpoint}?${queryString}` : endpoint;
    return request(fullEndpoint, { method: 'GET', ...options });
  },
  clearCache: () => {
    memoryCache.clear();
    inFlightRequests.clear();
  },
};
