import React from 'react';
import { Wind, Activity, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function Header({ isConnected = true, healthInfo = null }) {
  return (
    <header className="navbar bg-base-100 border-b border-base-300 px-4 lg:px-8 shadow-sm">
      <div className="navbar-start gap-3">
        <div className="p-2 bg-primary/10 text-primary rounded-lg">
          <Wind className="w-6 h-6 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold tracking-tight text-base-content">WindLens</span>
            <span className="badge badge-sm badge-outline font-mono">v0.2.0</span>
          </div>
          <p className="text-xs text-base-content/70 hidden sm:block">
            GB Wind Generation Forecast Selection & Accuracy Engine
          </p>
        </div>
      </div>

      <div className="navbar-center hidden md:flex">
        <div className="text-xs text-center px-4 py-1.5 rounded-full bg-base-200 border border-base-300 text-base-content/80">
          Source: <span className="font-semibold text-base-content">Elexon BMRS</span> (FUELHH Actuals & WINDFOR Forecasts)
        </div>
      </div>

      <div className="navbar-end gap-3">
        {isConnected ? (
          <div className="flex items-center gap-1.5 text-xs text-success bg-success/10 px-2.5 py-1 rounded-full border border-success/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span className="font-medium">API Connected</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-xs text-error bg-error/10 px-2.5 py-1 rounded-full border border-error/20">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span className="font-medium">Backend Offline</span>
          </div>
        )}
      </div>
    </header>
  );
}

