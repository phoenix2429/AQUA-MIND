import React, { useState } from 'react';
import { User, Info } from 'lucide-react';
import { useRole } from '../context/RoleContext';

export function ProfilePage() {
  const { role, roleInfo } = useRole();
  const RoleIcon = roleInfo.icon;

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center space-x-2">
          <User className="w-6 h-6 text-brand-600" />
          <h1 className="page-title">Profile & workspace settings</h1>
        </div>
        <p className="page-subtitle">
          Configure the presentation lens used across this AQUA-MIND workspace.
        </p>
      </div>

      <div className="surface p-6 space-y-5">
        <div className="flex items-center gap-3">
          <div className={`p-3 rounded-xl ${roleInfo.theme.accent}`}><RoleIcon className="w-5 h-5" /></div>
          <div>
            <p className="eyebrow">Current presentation role</p>
            <h2 className="text-lg font-extrabold text-slate-950">{roleInfo.name}</h2>
          </div>
        </div>
        <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-1 text-xs font-bold bg-brand-600 text-white rounded-md uppercase">
              {role}
            </span>
            <span className="text-xs text-slate-500">Selected via Navbar switcher</span>
          </div>
          <p className="text-xs text-slate-600">
            {roleInfo.tagline}. Role switching changes the interface focus only; it is not authentication or access control.
          </p>
        </div>
        <div className="flex items-start gap-2 rounded-xl border border-cyan-100 bg-cyan-50 p-3 text-xs text-cyan-900">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-cyan-700" />
          <span>Use the workspace navigation to move between measured telemetry, model forecasts, explainability, and descriptive analytics.</span>
        </div>
      </div>
    </div>
  );
}
