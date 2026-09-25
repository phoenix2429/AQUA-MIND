import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Radio,
  MapPin,
  TrendingUp,
  Lightbulb,
  Sliders,
  FileText,
  User,
  ShieldCheck,
  ChevronLeft
} from 'lucide-react';
import { useRole } from '../../context/RoleContext';

export function Sidebar({ isOpen, onCloseSidebar }) {
  const { role, roleInfo } = useRole();

  const navItems = [
    { to: '/dashboard', label: 'Dashboard Overview', icon: LayoutDashboard },
    { to: '/stations', label: 'Stations Discovery', icon: Radio },
    { to: '/map', label: 'Geospatial Map', icon: MapPin },
    { to: '/forecast', label: 'ML Forecasting', icon: TrendingUp },
    { to: '/insights', label: 'Tree SHAP Insights', icon: Lightbulb },
    { to: '/scenarios', label: 'Scenario Analysis', icon: Sliders },
    { to: '/reports', label: 'Reports & Export', icon: FileText },
    { to: '/profile', label: 'Profile & Settings', icon: User },
  ];

  if (role === 'admin') {
    navItems.push({ to: '/admin', label: 'Admin Console', icon: ShieldCheck, adminOnly: true });
  }

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-40 md:hidden"
          onClick={onCloseSidebar}
        />
      )}

      {/* Sidebar Container */}
      <aside className={`
        fixed md:sticky top-16 z-40 h-[calc(100vh-4rem)] w-64 bg-white border-r border-slate-200/80
        flex flex-col justify-between transition-transform duration-200 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        <div className="p-4 space-y-6 overflow-y-auto">

          {/* Mobile Header Close */}
          <div className="flex items-center justify-between md:hidden pb-2 border-b border-slate-100">
            <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">Navigation</span>
            <button onClick={onCloseSidebar} className="p-1 text-slate-400 hover:text-slate-600 rounded-md">
              <ChevronLeft className="w-5 h-5" />
            </button>
          </div>

          {/* Active Stakeholder View Banner */}
          <div className={`p-3.5 rounded-2xl border ${roleInfo.theme.accent}`}>
            <div className="flex items-center space-x-2">
              <roleInfo.icon className="w-4 h-4 flex-shrink-0" />
              <span className="text-xs font-extrabold uppercase tracking-wider">{roleInfo.name}</span>
            </div>
            <p className="text-[11px] opacity-80 mt-1 leading-snug">{roleInfo.tagline}</p>
          </div>

          {/* Navigation Items */}
          <nav className="space-y-1">
            <div className="px-3 pb-2 text-[10px] font-extrabold text-slate-400 uppercase tracking-wider">
              Navigation Menu
            </div>

            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onCloseSidebar}
                  className={({ isActive }) => `
                    flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all
                    ${isActive
                      ? `${roleInfo.theme.primary} shadow-xs`
                      : 'text-slate-600 hover:bg-slate-100/80 hover:text-slate-900'}
                  `}
                >
                  <Icon className="w-4 h-4 transition-colors" />
                  <span className="flex-1">{item.label}</span>
                  {item.adminOnly && (
                    <span className="px-1.5 py-0.5 text-[9px] font-bold text-amber-700 bg-amber-100 rounded">
                      ADMIN
                    </span>
                  )}
                </NavLink>
              );
            })}
          </nav>

        </div>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-slate-100 text-center bg-slate-50/50">
          <p className="text-[11px] text-slate-500 font-bold">AQUA-MIND Platform v0.1.0</p>
          <p className="text-[10px] text-slate-400">NWDP Groundwater Telemetry</p>
        </div>
      </aside>
    </>
  );
}
