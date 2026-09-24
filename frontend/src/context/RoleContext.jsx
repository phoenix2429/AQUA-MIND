import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, Droplet, Shield, Activity } from 'lucide-react';

const RoleContext = createContext();

export const STAKEHOLDER_ROLES = {
  public: {
    id: 'public',
    name: 'Public User',
    tagline: 'Accessible Groundwater Telemetry & Discovery',
    icon: User,
    theme: {
      primary: 'bg-sky-600 hover:bg-sky-700 text-white',
      accent: 'text-sky-600 bg-sky-50 border-sky-200',
      badge: 'bg-sky-100 text-sky-800 border-sky-300',
      banner: 'from-slate-900 via-sky-950 to-slate-950 text-white',
      cardBorder: 'hover:border-sky-300',
      highlight: 'text-sky-700',
      ring: 'focus:ring-sky-500/20 focus:border-sky-500',
    },
  },
  farmer: {
    id: 'farmer',
    name: 'Farmer View',
    tagline: 'Simple Groundwater Depth, 24h Predictions & Farm Actions',
    icon: Droplet,
    theme: {
      primary: 'bg-emerald-600 hover:bg-emerald-700 text-white',
      accent: 'text-emerald-700 bg-emerald-50 border-emerald-200',
      badge: 'bg-emerald-100 text-emerald-800 border-emerald-300',
      banner: 'from-emerald-950 via-teal-900 to-slate-950 text-white',
      cardBorder: 'hover:border-emerald-300',
      highlight: 'text-emerald-700',
      ring: 'focus:ring-emerald-500/20 focus:border-emerald-500',
    },
  },
  official: {
    id: 'official',
    name: 'Government Official',
    tagline: 'Regional Analytics, GSS Distribution & DIE Policy Recommendations',
    icon: Shield,
    theme: {
      primary: 'bg-blue-700 hover:bg-blue-800 text-white',
      accent: 'text-blue-700 bg-blue-50 border-blue-200',
      badge: 'bg-blue-100 text-blue-900 border-blue-300',
      banner: 'from-blue-950 via-slate-900 to-slate-950 text-white',
      cardBorder: 'hover:border-blue-300',
      highlight: 'text-blue-800',
      ring: 'focus:ring-blue-500/20 focus:border-blue-500',
    },
  },
  admin: {
    id: 'admin',
    name: 'Administrator Console',
    tagline: 'Telemetry Ingestion Health, Model Registry & System Status',
    icon: Activity,
    theme: {
      primary: 'bg-indigo-600 hover:bg-indigo-700 text-white',
      accent: 'text-indigo-700 bg-indigo-50 border-indigo-200',
      badge: 'bg-indigo-100 text-indigo-900 border-indigo-300',
      banner: 'from-indigo-950 via-slate-900 to-slate-950 text-white',
      cardBorder: 'hover:border-indigo-300',
      highlight: 'text-indigo-800',
      ring: 'focus:ring-indigo-500/20 focus:border-indigo-500',
    },
  },
};

export function RoleProvider({ children }) {
  const [role, setRole] = useState(() => {
    return localStorage.getItem('aqua_mind_role') || 'public';
  });

  const changeRole = (newRole) => {
    if (STAKEHOLDER_ROLES[newRole]) {
      setRole(newRole);
      localStorage.setItem('aqua_mind_role', newRole);
    }
  };

  const currentRoleInfo = STAKEHOLDER_ROLES[role] || STAKEHOLDER_ROLES.public;

  return (
    <RoleContext.Provider value={{ role, changeRole, roleInfo: currentRoleInfo }}>
      {children}
    </RoleContext.Provider>
  );
}

export function useRole() {
  const context = useContext(RoleContext);
  if (!context) {
    throw new Error('useRole must be used within a RoleProvider');
  }
  return context;
}
