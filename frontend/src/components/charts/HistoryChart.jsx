import React, { useState, useEffect } from 'react';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid 
} from 'recharts';
import { Calendar, RefreshCw, AlertCircle, LineChart as ChartIcon } from 'lucide-react';
import { stationService } from '../../services/stationService';
import { LoadingSpinner } from '../common/LoadingSpinner';

export function HistoryChart({ stationId }) {
  const [historyData, setHistoryData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timeRange, setTimeRange] = useState('30d'); // '7d' | '30d' | '6m' | '1y' | 'all'

  useEffect(() => {
    async function fetchHistory() {
      if (!stationId) return;
      try {
        setLoading(true);
        setError(null);

        // Compute start date based on timeRange
        let startIso = null;
        const now = new Date();
        if (timeRange === '7d') {
          now.setDate(now.getDate() - 7);
          startIso = now.toISOString();
        } else if (timeRange === '30d') {
          now.setDate(now.getDate() - 30);
          startIso = now.toISOString();
        } else if (timeRange === '6m') {
          now.setMonth(now.getMonth() - 6);
          startIso = now.toISOString();
        } else if (timeRange === '1y') {
          now.setFullYear(now.getFullYear() - 1);
          startIso = now.toISOString();
        }

        const data = await stationService.getHistory(stationId, {
          start: startIso,
          buckets: 300,
        });

        // Format data points for Recharts
        const formatted = (data || []).map((pt) => ({
          timestamp: pt.timestamp,
          formattedDate: new Date(pt.timestamp).toLocaleDateString('en-IN', {
            day: 'numeric',
            month: 'short',
            year: timeRange === '7d' || timeRange === '30d' ? undefined : '2-digit',
            hour: timeRange === '7d' ? '2-digit' : undefined,
          }),
          fullDate: new Date(pt.timestamp).toLocaleString('en-IN'),
          level: Number(pt.groundwater_level?.toFixed(2)),
          count: pt.observation_count,
        }));

        setHistoryData(formatted);
      } catch (err) {
        setError(err.message || 'Unable to load historical observation data.');
      } finally {
        setLoading(false);
      }
    }

    fetchHistory();
  }, [stationId, timeRange]);

  const ranges = [
    { id: '7d', label: '7 Days' },
    { id: '30d', label: '30 Days' },
    { id: '6m', label: '6 Months' },
    { id: '1y', label: '1 Year' },
    { id: 'all', label: 'All History' },
  ];

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-2xs space-y-4">
      {/* Section Header & Range Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <ChartIcon className="w-5 h-5 text-brand-600" />
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">Groundwater Telemetry History</h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Measured observations (depth to water level in meters below ground level / m bgl)
          </p>
        </div>

        {/* Time Range Selector */}
        <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-xl">
          {ranges.map((r) => (
            <button
              key={r.id}
              onClick={() => setTimeRange(r.id)}
              className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-all ${
                timeRange === r.id 
                  ? 'bg-white text-brand-700 shadow-2xs' 
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart Container */}
      {loading ? (
        <LoadingSpinner message="Aggregating telemetry observation time-series..." />
      ) : error ? (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-rose-500 flex-shrink-0" />
          <span>{error}</span>
        </div>
      ) : historyData.length === 0 ? (
        <div className="py-12 text-center text-slate-400 text-xs italic bg-slate-50 rounded-xl border border-dashed border-slate-200">
          No groundwater observations available for the selected period.
        </div>
      ) : (
        <div className="h-72 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={historyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis 
                dataKey="formattedDate" 
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickLine={false}
                axisLine={{ stroke: '#cbd5e1' }}
              />
              <YAxis 
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickLine={false}
                axisLine={false}
                domain={['auto', 'auto']}
                unit=" m"
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="bg-slate-900 text-white p-3 rounded-xl shadow-xl text-xs space-y-1 border border-slate-700">
                        <p className="text-[11px] text-slate-400">{data.fullDate}</p>
                        <p className="font-bold text-brand-300 text-sm">
                          {data.level} m <span className="text-[10px] text-slate-300 font-normal">below ground level</span>
                        </p>
                        {data.count > 1 && (
                          <p className="text-[10px] text-slate-400">Aggregated from {data.count} telemetry points</p>
                        )}
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Line 
                type="monotone" 
                dataKey="level" 
                stroke="#0284c7" 
                strokeWidth={2.5}
                dot={historyData.length < 30 ? { r: 3, fill: '#0284c7' } : false}
                activeDot={{ r: 5, fill: '#0369a1', stroke: '#ffffff', strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
