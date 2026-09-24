import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

export function ErrorMessage({ title = 'Unable to Load Data', message, onRetry }) {
  return (
    <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-900 text-sm flex items-start space-x-3">
      <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
      <div className="flex-1 space-y-1">
        <h4 className="font-semibold text-rose-950">{title}</h4>
        <p className="text-xs text-rose-800 leading-relaxed">{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-2 inline-flex items-center space-x-1.5 px-3 py-1 bg-white border border-rose-300 text-rose-800 hover:bg-rose-100 rounded-lg text-xs font-semibold shadow-2xs transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry Request</span>
          </button>
        )}
      </div>
    </div>
  );
}
