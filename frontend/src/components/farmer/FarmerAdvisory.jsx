import React, { useEffect, useState, useRef, useCallback } from 'react';
import { AlertTriangle, Droplet, Sprout, Zap, MapPin, CheckCircle, RefreshCw, Info } from 'lucide-react';
import { stationService } from '../../services/stationService';
import { forecastService } from '../../services/forecastService';
import { analyticsService } from '../../services/analyticsService';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ErrorMessage } from '../common/ErrorMessage';

// Module-level in-memory cache keyed by stationId for instantaneous switching (Station A -> B -> A)
const advisoryCache = new Map();

export function FarmerAdvisory() {
  // Selector states
  const [states, setStates] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [stations, setStations] = useState([]);

  const [selectedState, setSelectedState] = useState('');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [selectedStationId, setSelectedStationId] = useState('');

  // Station data states
  const [station, setStation] = useState(null);
  const [forecast, setForecast] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [history, setHistory] = useState([]);

  // Independent loading states for resilient parallel UX
  const [loadingSelectors, setLoadingSelectors] = useState(true);
  const [loadingStation, setLoadingStation] = useState(false);
  const [loadingForecast, setLoadingForecast] = useState(false);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Independent error states
  const [globalError, setGlobalError] = useState(null);
  const [forecastError, setForecastError] = useState(null);
  const [analyticsError, setAnalyticsError] = useState(null);
  const [historyError, setHistoryError] = useState(null);

  // 1. Initial Load: Load States and first available station
  useEffect(() => {
    let mounted = true;

    async function initSelectors() {
      try {
        setLoadingSelectors(true);
        setGlobalError(null);

        const statesList = await stationService.getStates();
        if (!mounted) return;
        setStates(statesList || []);

        if (statesList && statesList.length > 0) {
          const firstState = statesList[0];
          setSelectedState(firstState);

          const [distList, stnResponse] = await Promise.all([
            stationService.getDistricts(firstState).catch(() => []),
            stationService.getStations({ state: firstState, page: 1, pageSize: 50 }),
          ]);
          if (!mounted) return;

          setDistricts(distList || []);
          const items = stnResponse?.items || [];
          setStations(items);

          if (items.length > 0) {
            setSelectedStationId(items[0].station_id);
            if (items[0].district) {
              setSelectedDistrict(items[0].district);
            }
          }
        }
      } catch (err) {
        if (mounted) {
          setGlobalError(err.message || 'Unable to load telemetry stations.');
        }
      } finally {
        if (mounted) {
          setLoadingSelectors(false);
        }
      }
    }

    initSelectors();

    return () => {
      mounted = false;
    };
  }, []);

  // 2. When State Changes: update districts and stations
  const handleStateChange = async (e) => {
    const newState = e.target.value;
    setSelectedState(newState);
    setSelectedDistrict('');
    try {
      const [distList, stnResponse] = await Promise.all([
        stationService.getDistricts(newState).catch(() => []),
        stationService.getStations({ state: newState, page: 1, pageSize: 50 }),
      ]);
      setDistricts(distList || []);
      const items = stnResponse?.items || [];
      setStations(items);
      if (items.length > 0) {
        setSelectedStationId(items[0].station_id);
      } else {
        setSelectedStationId('');
        setStation(null);
      }
    } catch (err) {
      console.error('Failed to change state:', err);
    }
  };

  // 3. When District Changes: filter stations
  const handleDistrictChange = async (e) => {
    const newDistrict = e.target.value;
    setSelectedDistrict(newDistrict);
    try {
      const stnResponse = await stationService.getStations({
        state: selectedState,
        district: newDistrict || undefined,
        page: 1,
        pageSize: 50,
      });
      const items = stnResponse?.items || [];
      setStations(items);
      if (items.length > 0) {
        setSelectedStationId(items[0].station_id);
      }
    } catch (err) {
      console.error('Failed to change district:', err);
    }
  };

  // 4. When Station Changes: Load Station Data with In-Memory Caching & Parallel Requests
  const loadStationData = useCallback(async (stationId) => {
    if (!stationId) return;

    // Check in-memory advisory cache first for instantaneous switching
    if (advisoryCache.has(stationId)) {
      const cached = advisoryCache.get(stationId);
      setStation(cached.station);
      setForecast(cached.forecast);
      setAnalytics(cached.analytics);
      setHistory(cached.history);
      setForecastError(cached.forecastError || null);
      setAnalyticsError(cached.analyticsError || null);
      setHistoryError(cached.historyError || null);
      setLoadingStation(false);
      setLoadingForecast(false);
      setLoadingAnalytics(false);
      setLoadingHistory(false);
      return;
    }

    // Reset errors and set loading states
    setGlobalError(null);
    setForecastError(null);
    setAnalyticsError(null);
    setHistoryError(null);

    setLoadingStation(true);
    setLoadingForecast(true);
    setLoadingAnalytics(true);
    setLoadingHistory(true);

    const cacheEntry = {
      station: null,
      forecast: [],
      analytics: null,
      history: [],
      forecastError: null,
      analyticsError: null,
      historyError: null,
    };

    // Parallel independent request 1: Station Details
    const stationPromise = stationService.getStation(stationId)
      .then((data) => {
        setStation(data);
        cacheEntry.station = data;
      })
      .catch((err) => {
        console.error('Station fetch error:', err);
      })
      .finally(() => {
        setLoadingStation(false);
      });

    // Parallel independent request 2: ML Forecast
    const forecastPromise = forecastService.getForecast(stationId, { horizonPoints: 4, model: 'xgboost' })
      .then((data) => {
        const list = data || [];
        setForecast(list);
        cacheEntry.forecast = list;
      })
      .catch((err) => {
        const msg = err.message || 'Forecast unavailable';
        setForecastError(msg);
        cacheEntry.forecastError = msg;
      })
      .finally(() => {
        setLoadingForecast(false);
      });

    // Parallel independent request 3: Analytics & Station-Specific DIE Recommendation
    const analyticsPromise = analyticsService.getStationAnalytics(stationId)
      .then((data) => {
        setAnalytics(data);
        cacheEntry.analytics = data;
      })
      .catch((err) => {
        const msg = err.message || 'Recommendation unavailable';
        setAnalyticsError(msg);
        cacheEntry.analyticsError = msg;
      })
      .finally(() => {
        setLoadingAnalytics(false);
      });

    // Parallel independent request 4: History Observations
    const historyPromise = stationService.getHistory(stationId, { buckets: 30 })
      .then((data) => {
        const list = data || [];
        setHistory(list);
        cacheEntry.history = list;
      })
      .catch((err) => {
        const msg = err.message || 'History unavailable';
        setHistoryError(msg);
        cacheEntry.historyError = msg;
      })
      .finally(() => {
        setLoadingHistory(false);
      });

    // Cache results once all settle
    Promise.allSettled([stationPromise, forecastPromise, analyticsPromise, historyPromise])
      .then(() => {
        advisoryCache.set(stationId, cacheEntry);
      });
  }, []);

  useEffect(() => {
    if (selectedStationId) {
      loadStationData(selectedStationId);
    }
  }, [selectedStationId, loadStationData]);

  if (globalError) {
    return <ErrorMessage title="Farmer Advisory Unavailable" message={globalError} />;
  }

  // Derived Telemetry Values
  const current = history.length > 0 ? history.at(-1)?.groundwater_level : null;
  const previous = history.length > 1 ? history.at(-2)?.groundwater_level : null;
  const declining = Number.isFinite(current) && Number.isFinite(previous) && current > previous;
  const gssScore = analytics?.gss?.score;
  const stressed = gssScore != null && gssScore < 40;
  const diePriority = analytics?.die?.priority || (declining || stressed ? 'HIGH' : 'LOW');
  const alert = diePriority === 'HIGH' || declining || stressed;

  // Real Station-Level Crop & Irrigation Guidance from DIE backend
  const stationCropRec = analytics?.die?.crop_recommendation;
  const stationIrrigRec = analytics?.die?.irrigation_recommendation;
  const stationCondition = analytics?.die?.groundwater_condition;
  const stationReason = analytics?.die?.reason;
  const stationAction = analytics?.die?.action;

  // Fallback crop guidance if analytics are still computing or unavailable
  const fallbackCrop = stressed || declining
    ? 'Aquifer indicators signal stress. Strictly prioritize drought-resilient crops (millets, pulses, oilseeds); avoid heavy pre-monsoon pumping.'
    : 'Moderate to stable groundwater levels observed. Common seasonal crops (cereals, vegetables) supported under normal water efficiency.';
  const fallbackIrrig = alert
    ? 'Conserve groundwater: utilize micro/drip irrigation, avoid midday watering, and inspect soil moisture before pumping.'
    : 'Apply standard crop-stage irrigation matching measured soil moisture; avoid unmetered flood irrigation.';

  const displayCrop = stationCropRec || fallbackCrop;
  const displayIrrig = stationIrrigRec || fallbackIrrig;
  const displayAction = stationAction || 'Monitor local station telemetry, review tomorrow’s prediction, and consult local agricultural extension officers before modifying crop plans.';

  return (
    <section className="space-y-5">
      {/* 1. Header with Station Selection Controls */}
      <div className="bg-white border border-slate-200 rounded-3xl p-5 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <div className="flex items-center space-x-2">
              <Sprout className="w-5 h-5 text-emerald-600" />
              <h2 className="text-lg font-bold text-slate-900 tracking-tight">Farmer Telemetry Advisory</h2>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Select your local state, district, and telemetry station to inspect real-time groundwater indicators and agronomic guidance.
            </p>
          </div>

          {station && (
            <div className="flex items-center space-x-2 self-start md:self-auto">
              <span className={`px-2.5 py-1 rounded-xl text-xs font-bold flex items-center space-x-1.5 ${alert ? 'bg-amber-100 text-amber-900 border border-amber-200' : 'bg-emerald-100 text-emerald-900 border border-emerald-200'}`}>
                {alert ? <AlertTriangle className="w-3.5 h-3.5 text-amber-700" /> : <CheckCircle className="w-3.5 h-3.5 text-emerald-700" />}
                <span>{alert ? 'Attention Advised' : 'Routine Monitoring'}</span>
              </span>
            </div>
          )}
        </div>

        {/* State, District, and Station Selectors */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-3 border-t border-slate-100">
          {/* State Selector */}
          <div className="space-y-1">
            <label className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">State</label>
            <select
              value={selectedState}
              onChange={handleStateChange}
              disabled={loadingSelectors || states.length === 0}
              className="w-full text-xs font-semibold bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
            >
              {states.map((st) => (
                <option key={st} value={st}>{st}</option>
              ))}
            </select>
          </div>

          {/* District Selector */}
          <div className="space-y-1">
            <label className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">District</label>
            <select
              value={selectedDistrict}
              onChange={handleDistrictChange}
              disabled={loadingSelectors || districts.length === 0}
              className="w-full text-xs font-semibold bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
            >
              <option value="">All Districts ({districts.length})</option>
              {districts.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          {/* Station Selector */}
          <div className="space-y-1">
            <label className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Telemetry Station</label>
            <select
              value={selectedStationId}
              onChange={(e) => setSelectedStationId(e.target.value)}
              disabled={loadingSelectors || stations.length === 0}
              className="w-full text-xs font-semibold bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
            >
              {stations.map((stn) => (
                <option key={stn.station_id} value={stn.station_id}>
                  {stn.station_name || stn.station_id}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Selected Station Banner Info */}
        {station && (
          <div className="flex flex-wrap items-center justify-between text-xs text-slate-600 bg-slate-50/70 p-3 rounded-2xl border border-slate-100 gap-2">
            <div className="flex items-center space-x-2">
              <MapPin className="w-4 h-4 text-brand-600 flex-shrink-0" />
              <span className="font-semibold text-slate-900">{station.station_name}</span>
              <span className="text-slate-400">•</span>
              <span>{station.district ? `${station.district}, ` : ''}{station.state}</span>
            </div>
            <div className="text-[11px] text-slate-500 font-mono">
              Station ID: {station.station_id} | Ingested Obs: {station.observation_count?.toLocaleString()}
            </div>
          </div>
        )}
      </div>

      {/* 2. Top Metric Cards (Independent Loading UX) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Latest Measured Level */}
        <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-extrabold text-slate-400 tracking-wider">Latest Measured Level</span>
            <Droplet className="w-5 h-5 text-sky-600" />
          </div>
          {loadingHistory ? (
            <div className="h-8 bg-slate-100 animate-pulse rounded-lg w-28 mt-2" />
          ) : historyError ? (
            <p className="text-xs text-rose-500">{historyError}</p>
          ) : (
            <div>
              <strong className="text-2xl font-extrabold text-slate-900">
                {Number.isFinite(current) ? `${current.toFixed(2)} m` : 'Unavailable'}
              </strong>
              <p className="text-[11px] text-slate-500 mt-1">meters below ground level (m bgl)</p>
            </div>
          )}
        </div>

        {/* Next 24h Prediction */}
        <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-extrabold text-slate-400 tracking-wider">Next 24h ML Prediction</span>
            <Zap className="w-5 h-5 text-emerald-600" />
          </div>
          {loadingForecast ? (
            <div className="h-8 bg-slate-100 animate-pulse rounded-lg w-28 mt-2" />
          ) : forecastError ? (
            <p className="text-xs text-rose-500">{forecastError}</p>
          ) : (
            <div>
              <strong className="text-2xl font-extrabold text-slate-900">
                {forecast[3]?.predicted_value != null
                  ? `${forecast[3].predicted_value.toFixed(2)} m`
                  : forecast[0]?.predicted_value != null
                    ? `${forecast[0].predicted_value.toFixed(2)} m`
                    : 'Unavailable'}
              </strong>
              <p className="text-[11px] text-slate-500 mt-1">Predicted depth to water (XGBoost)</p>
            </div>
          )}
        </div>

        {/* Alert / Sustainability Condition */}
        <div className={`p-5 rounded-2xl border shadow-xs space-y-2 ${alert ? 'bg-amber-50/90 border-amber-200 text-amber-950' : 'bg-emerald-50/90 border-emerald-200 text-emerald-950'}`}>
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-extrabold tracking-wider opacity-75">Aquifer Telemetry Status</span>
            <AlertTriangle className={`w-5 h-5 ${alert ? 'text-amber-600' : 'text-emerald-600'}`} />
          </div>
          {loadingAnalytics ? (
            <div className="h-8 bg-black/5 animate-pulse rounded-lg w-32 mt-2" />
          ) : (
            <div>
              <strong className="text-base font-extrabold block">
                {alert ? 'Conservation Attention Recommended' : 'Routine Monitoring Level'}
              </strong>
              <p className="text-[11px] opacity-80 mt-1 leading-snug">
                {stationCondition || (alert ? 'Water table decline or elevated variability observed.' : 'Aquifer trends remain within normal seasonal parameters.')}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* 3. Station-Specific Actionable Recommendations */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Real Station Crop Recommendation */}
        <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-2 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center space-x-2 text-green-700">
              <Sprout className="w-5 h-5 flex-shrink-0" />
              <h3 className="font-bold text-sm text-slate-900">Crop Recommendation</h3>
            </div>
            {loadingAnalytics ? (
              <div className="space-y-2 pt-2">
                <div className="h-4 bg-slate-100 animate-pulse rounded w-full" />
                <div className="h-4 bg-slate-100 animate-pulse rounded w-3/4" />
              </div>
            ) : (
              <p className="text-xs text-slate-700 leading-relaxed pt-1">
                {displayCrop}
              </p>
            )}
          </div>
          {stationReason && !loadingAnalytics && (
            <p className="text-[10px] text-slate-500 pt-2 border-t border-slate-100 font-sans">
              Basis: {stationReason}
            </p>
          )}
        </div>

        {/* Real Station Irrigation Recommendation */}
        <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-2 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center space-x-2 text-blue-700">
              <Droplet className="w-5 h-5 flex-shrink-0" />
              <h3 className="font-bold text-sm text-slate-900">Irrigation Guidance</h3>
            </div>
            {loadingAnalytics ? (
              <div className="space-y-2 pt-2">
                <div className="h-4 bg-slate-100 animate-pulse rounded w-full" />
                <div className="h-4 bg-slate-100 animate-pulse rounded w-3/4" />
              </div>
            ) : (
              <p className="text-xs text-slate-700 leading-relaxed pt-1">
                {displayIrrig}
              </p>
            )}
          </div>
          <p className="text-[10px] text-slate-500 pt-2 border-t border-slate-100">
            Water conservation protocol based on measured volatility & slope.
          </p>
        </div>

        {/* Farm Actions */}
        <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-2 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center space-x-2 text-amber-700">
              <Zap className="w-5 h-5 flex-shrink-0" />
              <h3 className="font-bold text-sm text-slate-900">Recommended Farm Actions</h3>
            </div>
            {loadingAnalytics ? (
              <div className="space-y-2 pt-2">
                <div className="h-4 bg-slate-100 animate-pulse rounded w-full" />
                <div className="h-4 bg-slate-100 animate-pulse rounded w-3/4" />
              </div>
            ) : (
              <p className="text-xs text-slate-700 leading-relaxed pt-1">
                {displayAction}
              </p>
            )}
          </div>
          <p className="text-[10px] text-slate-500 pt-2 border-t border-slate-100">
            Always verify local rainfall and consult block extension officers.
          </p>
        </div>
      </div>

      {/* 4. Honest Advisory Footnote & Distinction */}
      <div className="p-3.5 bg-slate-50 border border-slate-200/80 rounded-2xl text-slate-600 flex items-start space-x-2.5">
        <Info className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
        <p className="text-[11px] leading-relaxed">
          <strong>Advisory Notice:</strong> Crop recommendations and irrigation advice are deterministic decision-support suggestions derived from station-level telemetry, trend analysis, and sustainability scores (GSS & GBIM). They are not complete farm agronomy models or agronomic guarantees. Farm managers should review local soil types, crop rotations, and district agricultural advisories before altering planting decisions.
        </p>
      </div>
    </section>
  );
}
