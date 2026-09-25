import React, { useState, useEffect } from 'react';
import { FileText, Download, Printer, Radio, CheckCircle } from 'lucide-react';
import { stationService } from '../services/stationService';

export function ReportsPage() {
  const [stations, setStations] = useState([]);
  const [selectedStationId, setSelectedStationId] = useState('');
  const [exported, setExported] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const res = await stationService.getStations({ page: 1, pageSize: 20 });
        setStations(res?.items || []);
        if (res?.items?.[0]) setSelectedStationId(res.items[0].station_id);
      } catch (_) {}
    }
    load();
  }, []);

  const handleExportCsv = async () => {
    if (!selectedStationId) return;
    try {
      const data = await stationService.getObservations(selectedStationId, { pageSize: 500 });
      const items = data?.items || [];

      const csvRows = [
        ['timestamp', 'groundwater_level', 'unit', 'source'],
        ...items.map(i => [i.timestamp, i.groundwater_level, i.unit, i.source])
      ];

      const csvString = csvRows.map(e => e.join(',')).join('\n');
      const blob = new Blob([csvString], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.setAttribute('href', url);
      a.setAttribute('download', `aqua_mind_station_${selectedStationId}_observations.csv`);
      a.click();
      setExported(true);
      setTimeout(() => setExported(false), 3000);
    } catch (err) {
      alert('Failed to export CSV: ' + err.message);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center space-x-2">
          <FileText className="w-6 h-6 text-brand-600" />
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Reports & Telemetry Data Export</h1>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Generate analytical summary reports and export station observation telemetry CSVs.
        </p>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-2xs space-y-4">
        <h3 className="text-sm font-bold text-slate-900">Export Station Telemetry Observations (CSV)</h3>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <select
            value={selectedStationId}
            onChange={(e) => setSelectedStationId(e.target.value)}
            className="px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-800 font-medium focus:outline-none flex-1"
          >
            {stations.map((s) => (
              <option key={s.id} value={s.station_id}>
                {s.station_name} ({s.district}, {s.state}) — ID: {s.station_id}
              </option>
            ))}
          </select>

          <button
            onClick={handleExportCsv}
            className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl shadow-xs transition-all flex items-center justify-center space-x-2"
          >
            <Download className="w-4 h-4" />
            <span>Download Observations CSV</span>
          </button>
        </div>

        {exported && (
          <div className="p-3 bg-emerald-50 text-emerald-800 text-xs font-semibold rounded-xl flex items-center space-x-2">
            <CheckCircle className="w-4 h-4 text-emerald-600" />
            <span>Telemetry CSV export completed successfully!</span>
          </div>
        )}
      </div>
    </div>
  );
}
