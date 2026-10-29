import React, { useState, useEffect } from 'react';
import { Wind, Sun, Moon, CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function Header({ isConnected = true, healthInfo = null }) {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('windlens_theme') || 'windlens-dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('windlens_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'windlens-dark' ? 'windlens-light' : 'windlens-dark'));
  };

  return (
    <header className="navbar bg-base-100 border-b border-base-300 px-4 lg:px-8 shadow-sm sticky top-0 z-40 backdrop-blur-md bg-base-100/90">
      <div className="navbar-start gap-3">
        <div className="p-2 bg-primary/15 text-primary rounded-lg border border-primary/20 shadow-xs">
          <Wind className="w-5 h-5 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold tracking-tight text-base-content font-sans">
              WindLens
            </span>
            <span className="badge badge-sm badge-outline font-mono text-[11px] py-0.5">
              v0.2.0
            </span>
          </div>
          <p className="text-xs text-base-content/60 hidden sm:block">
            GB Wind Generation Forecast Selection & Accuracy Engine
          </p>
        </div>
      </div>

      <div className="navbar-center hidden md:flex">
        <div className="flex items-center gap-2 text-xs px-3.5 py-1.5 rounded-full bg-base-200 border border-base-300 text-base-content/75 shadow-xs">
          <ShieldCheck className="w-3.5 h-3.5 text-primary" />
          <span>Elexon BMRS Insights API</span>
          <span className="text-base-content/40">•</span>
          <span className="font-mono text-[11px] text-base-content/90">FUELHH & WINDFOR</span>
        </div>
      </div>

      <div className="navbar-end gap-2.5">
        {/* Live Backend Connection Indicator */}
        {isConnected ? (
          <div
            className="flex items-center gap-1.5 text-xs text-success bg-success/10 px-2.5 py-1 rounded-full border border-success/20"
            title="FastAPI serverless backend connected and responsive"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span className="font-medium hidden sm:inline">API Connected</span>
          </div>
        ) : (
          <div
            className="flex items-center gap-1.5 text-xs text-error bg-error/10 px-2.5 py-1 rounded-full border border-error/20"
            title="Cannot reach FastAPI backend"
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            <span className="font-medium hidden sm:inline">Backend Offline</span>
          </div>
        )}

        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          aria-label="Toggle visual theme"
          className="btn btn-sm btn-ghost btn-circle text-base-content hover:bg-base-200 border border-base-300"
          title={`Switch to ${theme === 'windlens-dark' ? 'Light' : 'Dark'} theme`}
        >
          {theme === 'windlens-dark' ? (
            <Sun className="w-4 h-4 text-warning" />
          ) : (
            <Moon className="w-4 h-4 text-primary" />
          )}
        </button>
      </div>
    </header>
  );
}
