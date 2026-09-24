import React, { useState } from 'react';
import { User, Shield, CheckCircle } from 'lucide-react';
import { useOutletContext } from 'react-router-dom';

export function ProfilePage() {
  const { activeRole } = useOutletContext() || { activeRole: 'public' };

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center space-x-2">
          <User className="w-6 h-6 text-brand-600" />
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">User Profile & View Settings</h1>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Configure application interface view mode and analytical preferences.
        </p>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-2xs space-y-4">
        <h3 className="text-sm font-bold text-slate-900">Current Presentation Role</h3>
        <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-1 text-xs font-bold bg-brand-600 text-white rounded-md uppercase">
              {activeRole}
            </span>
            <span className="text-xs text-slate-500">Selected via Navbar switcher</span>
          </div>
          <p className="text-xs text-slate-600">
            Frontend role switching customizes visual presentation and layout focus for your specific workflow.
          </p>
        </div>
      </div>
    </div>
  );
}
