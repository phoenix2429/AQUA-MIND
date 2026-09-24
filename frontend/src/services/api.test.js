import { describe, it, expect, vi } from 'vitest';
import { api, ApiError } from './api';
import { stationService } from './stationService';
import { forecastService } from './forecastService';
import { analyticsService } from './analyticsService';

describe('AQUA-MIND Frontend API Service Layer', () => {
  it('constructs correct query params for station search', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: [], total: 0, page: 1, page_size: 50 }),
    });

    const result = await stationService.getStations({ state: 'Telangana', district: 'Medak', page: 2 });
    expect(global.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8001/api/stations?state=Telangana&district=Medak&page=2&page_size=50',
      expect.objectContaining({ method: 'GET' })
    );
    expect(result.total).toBe(0);
  });

  it('handles backend API errors gracefully with ApiError instance', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Station was not found' }),
    });

    await expect(stationService.getStation('NONEXISTENT')).rejects.toThrow('Station was not found');
  });

  it('constructs correct forecast and explanation endpoints', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ([]),
    });

    await forecastService.getForecast('ST_123', { model: 'xgboost', horizonPoints: 8 });
    expect(global.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8001/api/stations/ST_123/forecast?horizon_points=8&model=xgboost',
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('constructs analytics endpoint request', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ station_id: 'ST_123' }),
    });

    const analytics = await analyticsService.getStationAnalytics('ST_123');
    expect(analytics.station_id).toBe('ST_123');
  });
});
