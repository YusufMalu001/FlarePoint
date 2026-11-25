"use client";

import { Layers, ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";

export type BaseMapId = "dark" | "satellite" | "bright" | "topographic";

interface LayersPanelProps {
  baseMap: BaseMapId;
  onBaseMapChange: (b: BaseMapId) => void;
  showFootprints: boolean;
  onToggleFootprints: () => void;
  showHotspots: boolean;
  onToggleHotspots: () => void;
  footprintOpacity: number;
  onOpacityChange: (v: number) => void;
  activeIncidentCount: number;
}

export function LayersPanel({
  baseMap,
  onBaseMapChange,
  showFootprints,
  onToggleFootprints,
  showHotspots,
  onToggleHotspots,
  footprintOpacity,
  onOpacityChange,
  activeIncidentCount,
}: LayersPanelProps) {
  const [openBase, setOpenBase] = useState(true);
  const [openFires, setOpenFires] = useState(true);
  const [openOverlays, setOpenOverlays] = useState(true);

  const baseMaps: { id: BaseMapId; label: string }[] = [
    { id: "satellite", label: "Satellite Imagery" },
    { id: "bright", label: "Bright" },
    { id: "dark", label: "Dark" },
    { id: "topographic", label: "Topographic" },
  ];

  return (
    <aside className="w-64 bg-[#0c181d] border-l border-[#1c333c] flex flex-col text-xs text-slate-200 shrink-0 z-20 overflow-y-auto">
      <div className="h-10 px-3 border-b border-[#1c333c] flex items-center justify-between">
        <div className="flex items-center gap-2 font-semibold text-slate-100">
          <Layers className="w-3.5 h-3.5 text-teal-400" />
          <span>Layers</span>
        </div>
      </div>

      {/* Base Maps */}
      <div className="border-b border-[#1c333c]">
        <button
          onClick={() => setOpenBase(!openBase)}
          className="w-full px-3 py-2 flex items-center justify-between text-slate-300 hover:bg-[#112128]"
        >
          <span className="font-medium">Base Map</span>
          {openBase ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </button>
        {openBase && (
          <div className="px-3 pb-2.5 space-y-1.5">
            {baseMaps.map((bm) => (
              <label key={bm.id} className="flex items-center gap-2 cursor-pointer text-slate-300 hover:text-white">
                <input
                  type="radio"
                  name="basemap"
                  checked={baseMap === bm.id}
                  onChange={() => onBaseMapChange(bm.id)}
                  className="accent-teal-400"
                />
                <span>{bm.label}</span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Fires */}
      <div className="border-b border-[#1c333c]">
        <button
          onClick={() => setOpenFires(!openFires)}
          className="w-full px-3 py-2 flex items-center justify-between text-slate-300 hover:bg-[#112128]"
        >
          <span className="font-medium">Fires ({activeIncidentCount} active)</span>
          {openFires ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </button>
        {openFires && (
          <div className="px-3 pb-2.5 space-y-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showHotspots}
                onChange={onToggleHotspots}
                className="accent-teal-400 rounded"
              />
              <span>Satellite Hotspots (VIIRS/MODIS)</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showFootprints}
                onChange={onToggleFootprints}
                className="accent-teal-400 rounded"
              />
              <span>Cluster Footprints (Upper-Bound)</span>
            </label>
          </div>
        )}
      </div>

      {/* Overlays & Opacity */}
      <div className="border-b border-[#1c333c]">
        <button
          onClick={() => setOpenOverlays(!openOverlays)}
          className="w-full px-3 py-2 flex items-center justify-between text-slate-300 hover:bg-[#112128]"
        >
          <span className="font-medium">Overlays & Opacity</span>
          {openOverlays ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </button>
        {openOverlays && (
          <div className="px-3 pb-3 space-y-2">
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span>Footprint Opacity</span>
              <span>{Math.round(footprintOpacity * 100)}%</span>
            </div>
            <input
              type="range"
              min={0.1}
              max={0.9}
              step={0.05}
              value={footprintOpacity}
              onChange={(e) => onOpacityChange(parseFloat(e.target.value))}
              className="w-full accent-teal-400"
            />
            <div className="pt-1 space-y-1 text-[11px] text-slate-400">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block" />
                <span>High FRP (&ge; 50 MW)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400 inline-block" />
                <span>Moderate FRP (15–50 MW)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-sky-400 inline-block" />
                <span>Low FRP (&lt; 15 MW)</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
