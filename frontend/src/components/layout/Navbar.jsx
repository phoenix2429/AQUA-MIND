import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Droplet, Search, ChevronDown, Menu, MapPin, LoaderCircle } from 'lucide-react';
import { useRole, STAKEHOLDER_ROLES } from '../../context/RoleContext';
import { api } from '../../services/api';
import { stationService } from '../../services/stationService';
import { stationRoute } from '../../services/stationRoutes';

export function Navbar({ onToggleSidebar }) {
  const { role, changeRole, roleInfo } = useRole();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchStations, setSearchStations] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [backendStatus, setBackendStatus] = useState('checking');
  const [isRoleDropdownOpen, setIsRoleDropdownOpen] = useState(false);
  const searchRequest = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    let isMounted = true;
    async function checkHealth() {
      try {
        await api.get('/health');
        if (isMounted) setBackendStatus('ok');
      } catch (_) {
        if (isMounted) setBackendStatus('offline');
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    const query = searchQuery.trim().toLowerCase();
    if (query.length < 2) {
      setSearchStations([]);
      setSearchLoading(false);
      return undefined;
    }

    let active = true;
    setSearchOpen(true);
    setSearchLoading(true);

    async function loadSearchIndex() {
      try {
        if (!searchRequest.current) {
          searchRequest.current = stationService.getStates()
            .then((states) => stationService.getAllStations(states))
            .finally(() => {
              searchRequest.current = null;
            });
        }
        const stations = await searchRequest.current;
        if (!active) return;
        const matches = stations
          .filter((station) => [
            station.station_name,
            station.station_id,
            station.state,
            station.district,
            station.village,
          ].some((value) => value?.toLowerCase().includes(query)))
          .slice(0, 8);
        setSearchStations(matches);
      } catch (_) {
        if (active) setSearchStations([]);
      } finally {
        if (active) setSearchLoading(false);
      }
    }

    loadSearchIndex();
    return () => {
      active = false;
    };
  }, [searchQuery]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      setSearchOpen(false);
      navigate(`/stations?search=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const searchMessage = useMemo(() => {
    if (searchQuery.trim().length < 2) return 'Type at least 2 characters to search stations';
    if (searchLoading) return 'Searching telemetry stations…';
    if (!searchStations.length) return 'No matching stations found';
    return null;
  }, [searchLoading, searchQuery, searchStations.length]);

  const RoleIcon = roleInfo.icon;

  return (
    <header className="sticky top-0 z-30 bg-[#071a2b] text-white border-b border-white/10 shadow-lg">
      <div className="flex items-center justify-between h-[4.5rem] px-4 md:px-7">

        {/* Left: Mobile Drawer Button & Branding */}
        <div className="flex items-center space-x-3">
          <button
            onClick={onToggleSidebar}
            className="p-2 text-slate-500 rounded-lg hover:bg-slate-100 focus:outline-none md:hidden"
            aria-label="Toggle Navigation"
          >
            <Menu className="w-5 h-5" />
          </button>

          <Link to="/" className="flex items-center space-x-2.5 group">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-cyan-500 to-teal-400 text-slate-950 shadow-md shadow-cyan-500/20 group-hover:scale-105 transition-transform duration-200">
              <Droplet className="w-5 h-5 fill-current" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-lg tracking-tight text-white">AQUA-MIND</span>
                <span className="px-2 py-0.5 text-[10px] font-bold tracking-wider text-cyan-200 bg-white/10 rounded-md border border-white/15 uppercase">
                  Telemetry Intelligence
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-medium hidden sm:block leading-none mt-0.5">
                Explainable Groundwater Decision Intelligence
              </p>
            </div>
          </Link>
        </div>

        {/* Center: Search Box */}
        <form onSubmit={handleSearchSubmit} className="hidden md:flex items-center flex-1 max-w-sm mx-6" role="search">
          <div className="relative w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search telemetry station or district..."
              value={searchQuery}
              onFocus={() => setSearchOpen(true)}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setSearchOpen(true);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Escape') {
                  setSearchOpen(false);
                  e.currentTarget.blur();
                }
              }}
              aria-label="Search telemetry stations"
              aria-expanded={searchOpen}
              aria-controls="navbar-search-suggestions"
              className={`w-full pl-9 pr-4 py-2 text-xs bg-white/10 border border-white/15 rounded-xl font-medium text-white focus:outline-none focus:ring-2 transition-all placeholder:text-slate-400 ${roleInfo.theme.ring}`}
            />
            {searchOpen && (
              <div
                id="navbar-search-suggestions"
                className="absolute left-0 right-0 top-full z-50 mt-2 overflow-hidden rounded-2xl border border-slate-200 bg-white p-1.5 text-left shadow-2xl"
              >
                {searchLoading && (
                  <div className="flex items-center gap-2 px-3 py-3 text-xs text-slate-500">
                    <LoaderCircle className="h-4 w-4 animate-spin text-cyan-600" />
                    <span>Searching telemetry stations…</span>
                  </div>
                )}
                {!searchLoading && searchStations.map((station) => (
                  <Link
                    key={station.id ?? station.station_id}
                    to={stationRoute(station.station_id)}
                    onClick={() => setSearchOpen(false)}
                    className="flex items-start gap-2 rounded-xl px-3 py-2.5 hover:bg-slate-50"
                  >
                    <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-cyan-600" />
                    <span className="min-w-0">
                      <span className="block truncate text-xs font-bold text-slate-900">{station.station_name}</span>
                      <span className="block truncate text-[10px] text-slate-500">
                        {[station.district, station.state].filter(Boolean).join(' · ')}
                      </span>
                    </span>
                  </Link>
                ))}
                {!searchLoading && searchMessage && (
                  <div className="px-3 py-3 text-xs text-slate-500">{searchMessage}</div>
                )}
              </div>
            )}
          </div>
        </form>

        {/* Right: API Health & Stakeholder Role Selector */}
        <div className="flex items-center space-x-3">

          {/* Health Pill */}
          <div
            className={`hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold border ${
              backendStatus === 'ok'
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : backendStatus === 'offline'
                ? 'bg-rose-50 text-rose-700 border-rose-200'
                : 'bg-amber-50 text-amber-700 border-amber-200'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${
              backendStatus === 'ok' ? 'bg-emerald-500 animate-pulse' : backendStatus === 'offline' ? 'bg-rose-500' : 'bg-amber-500'
            }`} />
            <span>{backendStatus === 'ok' ? 'FastAPI Online' : backendStatus === 'offline' ? 'API Offline' : 'Connecting...'}</span>
          </div>

          {/* Stakeholder Switcher */}
          <div className="relative">
            <button
              onClick={() => setIsRoleDropdownOpen(!isRoleDropdownOpen)}
              className={`flex items-center space-x-2 px-3 py-2 rounded-xl border text-xs font-bold transition-all shadow-2xs ${roleInfo.theme.badge}`}
            >
              <RoleIcon className="w-4 h-4" />
              <span className="hidden sm:inline">{roleInfo.name}</span>
              <ChevronDown className="w-3.5 h-3.5 opacity-70" />
            </button>

            {isRoleDropdownOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setIsRoleDropdownOpen(false)} />
                <div className="absolute right-0 mt-2 w-64 bg-white rounded-2xl shadow-xl border border-slate-100 py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                  <div className="px-4 py-2 border-b border-slate-100">
                    <p className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">Select Stakeholder View</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">Tailors color theme & layout focus</p>
                  </div>

                  {Object.values(STAKEHOLDER_ROLES).map((r) => {
                    const IconComp = r.icon;
                    const isSelected = role === r.id;
                    return (
                      <button
                        key={r.id}
                        onClick={() => {
                          changeRole(r.id);
                          setIsRoleDropdownOpen(false);
                        }}
                        className={`w-full flex items-start space-x-3 px-4 py-2.5 text-left hover:bg-slate-50 transition-colors ${
                          isSelected ? 'bg-slate-50 border-l-4 border-brand-600' : ''
                        }`}
                      >
                        <div className={`p-1.5 rounded-lg mt-0.5 ${r.theme.badge}`}>
                          <IconComp className="w-4 h-4" />
                        </div>
                        <div className="flex-1">
                          <p className={`text-xs font-bold ${isSelected ? 'text-slate-900' : 'text-slate-700'}`}>
                            {r.name}
                          </p>
                          <p className="text-[10px] text-slate-400 line-clamp-1">{r.tagline}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </>
            )}
          </div>

        </div>

      </div>
    </header>
  );
}
