"use client";

import { Flame, RefreshCw, Search, Bell } from "lucide-react";

interface TopBarProps {
  incidentCount: number;
  dataOrigin: "REAL_FIRMS" | "SIMULATED_DEMO";
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export function TopBar({
  incidentCount,
  dataOrigin,
  searchQuery,
  onSearchChange,
  onRefresh,
  isRefreshing,
}: TopBarProps) {
  return (
    <header className="h-11 bg-[#081216] border-b border-[#1c333c] flex items-center justify-between px-3 z-30 shrink-0">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-red-500/20 border border-red-500/60 flex items-center justify-center">
            <Flame className="w-3.5 h-3.5 text-red-400" />
          </div>
          <span className="font-semibold text-sm tracking-tight text-slate-100">
            FlarePoint
          </span>
        </div>

        <div className="relative flex items-center">
          <Bell className="w-4 h-4 text-slate-400" />
          {incidentCount > 0 && (
            <span className="ml-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-red-600 text-white leading-none">
              {incidentCount}
            </span>
          )}
        </div>

        <span
          className={`px-2 py-0.5 rounded text-[10px] font-semibold tracking-wide border ${
            dataOrigin === "SIMULATED_DEMO"
              ? "bg-amber-500/15 text-amber-300 border-amber-500/40"
              : "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
          }`}
        >
          {dataOrigin === "SIMULATED_DEMO" ? "SIMULATED DEMO" : "LIVE FIRMS"}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <div className="relative w-64">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Place, coordinates, or incident ID"
            className="w-full h-7 pl-8 pr-2.5 bg-[#0c181d] border border-[#1c333c] rounded text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-teal-400"
          />
        </div>
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Run ingestion & clustering"
          className="h-7 px-2.5 rounded bg-[#112128] hover:bg-[#162b34] border border-[#1c333c] text-xs text-slate-200 flex items-center gap-1.5 disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-teal-400" : ""}`} />
          <span>Sync</span>
        </button>
      </div>
    </header>
  );
}
