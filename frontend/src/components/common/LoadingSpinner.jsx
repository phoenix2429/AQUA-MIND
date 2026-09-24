import React from 'react';

export function LoadingSpinner({ message = 'Loading AQUA-MIND data...' }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 space-y-3">
      <div className="relative flex items-center justify-center">
        <div className="w-10 h-10 border-3 border-brand-200 border-t-brand-600 rounded-full animate-spin" />
        <div className="absolute w-4 h-4 bg-brand-500/20 rounded-full animate-ping" />
      </div>
      <p className="text-xs font-medium text-slate-500 animate-pulse">{message}</p>
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs animate-pulse space-y-3">
      <div className="h-4 bg-slate-200 rounded w-1/3" />
      <div className="h-6 bg-slate-200 rounded w-2/3" />
      <div className="h-4 bg-slate-100 rounded w-1/2" />
    </div>
  );
}
