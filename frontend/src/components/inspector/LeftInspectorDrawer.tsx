"use client";

import { useState } from "react";
import { Flame, Info, ChevronDown, ChevronUp, MapPin, Wind, Thermometer, Droplets } from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  AreaChart,
  Area,
  XAxis,
  YAxis,
} from "recharts";
import { Incident, Observation, ProgressionAnalysis, Snapshot, TerrainContext } from "@/types/flarepoint";

interface LeftInspectorDrawerProps {
  incidents: Incident[];
  selectedIncident: Incident | null;
  onSelectIncident: (inc: Incident) => void;
  observations: Observation[];
  timeline: Snapshot[];
  terrain: TerrainContext | null;
  progression: ProgressionAnalysis | null;
  highlightLatest: boolean;
  onToggleHighlightLatest: () => void;
}

const LAND_COVER_COLORS: Record<string, string> = {
  Forest: "#2e7d32",
  Shrubland: "#d97706",
  Grassland: "#eab308",
  Cropland: "#c084fc",
  "Built-up": "#dc2626",
  Bare: "#94a3b8",
};

type TabId = "land_cover" | "frp" | "timeline" | "weather" | "hotspots" | "terrain" | "progression";

export function LeftInspectorDrawer({
  incidents,
  selectedIncident,
  onSelectIncident,
  observations,
  timeline,
  terrain,
  progression,
  highlightLatest,
  onToggleHighlightLatest,
}: LeftInspectorDrawerProps) {
  const [activeTab, setActiveTab] = useState<TabId>("land_cover");
  const [showPriorityRules, setShowPriorityRules] = useState(false);

  if (!selectedIncident) {
    return (
      <aside className="w-[340px] bg-[#0c181d] border-r border-[#1c333c] p-4 text-xs text-slate-400 shrink-0">
        No incidents available. Click Sync to ingest observations.
      </aside>
    );
  }

  const firstDt = new Date(selectedIncident.first_seen_at);
  const lastDt = new Date(selectedIncident.last_seen_at);
  const lifetimeHours = Math.max(1, Math.round((lastDt.getTime() - firstDt.getTime()) / 3600000));
  const lifetimeLabel =
    lifetimeHours >= 24 ? `${Math.round(lifetimeHours / 24)} days` : `${lifetimeHours} hours`;

  const landCoverData = Object.entries(selectedIncident.land_cover_summary || {}).map(
    ([name, value]) => ({ name, value })
  );

  const tierColor =
    selectedIncident.priority_tier === "CRITICAL"
      ? "bg-red-500/80 text-white"
      : selectedIncident.priority_tier === "HIGH"
      ? "bg-amber-500/80 text-slate-950"
      : "bg-teal-500/70 text-slate-950";

  return (
    <aside className="w-[340px] bg-[#0c181d] border-r border-[#1c333c] flex flex-col text-xs text-slate-200 shrink-0 z-20 overflow-y-auto">
      {/* Incident Switcher */}
      <div className="px-3 py-2 border-b border-[#1c333c] bg-[#081216] flex items-center gap-2">
        <select
          value={selectedIncident.id}
          onChange={(e) => {
            const found = incidents.find((i) => i.id === e.target.value);
            if (found) onSelectIncident(found);
          }}
          className="w-full bg-[#112128] border border-[#1c333c] rounded px-2 py-1 text-xs text-slate-100 focus:outline-none focus:border-teal-400"
        >
          {incidents.map((inc) => (
            <option key={inc.id} value={inc.id}>
              {inc.persistent_key} — {inc.hotspot_count} hotspots ({inc.priority_tier})
            </option>
          ))}
        </select>
      </div>

      {/* Header */}
      <div className="px-3 py-2.5 border-b border-[#1c333c] flex items-center justify-between">
        <div className="flex items-center gap-2 font-semibold text-sm text-slate-100">
          <Flame className="w-4 h-4 text-amber-400" />
          <span>Cluster with {selectedIncident.hotspot_count} Hotspots</span>
        </div>
        <span className="text-[10px] font-mono text-slate-400">{selectedIncident.persistent_key}</span>
      </div>

      {/* Metadata Table */}
      <div className="px-3 py-2.5 space-y-1.5 border-b border-[#1c333c] text-[11px]">
        <div className="flex justify-between">
          <span className="text-slate-400">First Hotspot</span>
          <span className="font-mono text-slate-200">{firstDt.toISOString().slice(0, 16).replace("T", " ")} UTC</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Last Hotspot</span>
          <span className="font-mono text-slate-200">{lastDt.toISOString().slice(0, 16).replace("T", " ")} UTC</span>
        </div>
        <label className="flex items-center gap-2 pl-24 py-0.5 text-slate-300 cursor-pointer">
          <input
            type="checkbox"
            checked={highlightLatest}
            onChange={onToggleHighlightLatest}
            className="accent-teal-400 rounded"
          />
          <span>Highlight latest detections</span>
        </label>
        <div className="flex justify-between">
          <span className="text-slate-400">Lifetime</span>
          <span>{lifetimeLabel}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-slate-400">Location</span>
          <span className="font-mono flex items-center gap-1">
            {selectedIncident.centroid_lat.toFixed(5)}°, {selectedIncident.centroid_lon.toFixed(5)}°
            <MapPin className="w-3 h-3 text-teal-400" />
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Max FRP</span>
          <span className="font-semibold text-amber-300">{selectedIncident.max_frp.toFixed(1)} MW</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Total Burnt Area</span>
          <span className="italic text-slate-500">not yet received</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Affected Area (upper-bound)</span>
          <span>{selectedIncident.affected_area_km2.toFixed(2)} km² or less</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Cluster Confidence</span>
          <span>{selectedIncident.cluster_confidence.toFixed(2)}</span>
        </div>

        {/* Rule-Based Priority Score */}
        <div className="pt-1">
          <div className="flex justify-between items-center mb-1">
            <span className="text-slate-400 flex items-center gap-1">
              Priority Score <Info className="w-3 h-3 text-slate-500" />
            </span>
            <button
              onClick={() => setShowPriorityRules(!showPriorityRules)}
              className={`px-2 py-0.5 rounded text-[11px] font-semibold flex items-center gap-1 ${tierColor}`}
            >
              <span>
                {selectedIncident.priority_tier} ({selectedIncident.priority_score})
              </span>
              {showPriorityRules ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          </div>
          {showPriorityRules && (
            <div className="bg-[#081216] border border-[#1c333c] rounded p-2 space-y-1 text-[10px]">
              {selectedIncident.priority_explanation.rules.map((r, idx) => (
                <div key={idx} className="flex justify-between text-slate-300">
                  <span>{r.rule} ({r.value})</span>
                  <span className="text-teal-400 font-mono">+{r.points}</span>
                </div>
              ))}
              <p className="text-slate-500 pt-1 border-t border-[#1c333c]">
                {selectedIncident.priority_explanation.disclaimer}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* 2-Column Action/Tab Grid */}
      <div className="p-2.5 grid grid-cols-2 gap-1.5 border-b border-[#1c333c]">
        {[
          { id: "timeline" as const, label: "Timeline" },
          { id: "weather" as const, label: "Weather" },
          { id: "hotspots" as const, label: "Hotspots" },
          { id: "frp" as const, label: "Fire Radiative Power" },
          { id: "terrain" as const, label: "Terrain Morphology" },
          { id: "progression" as const, label: "Centroid Progression" },
          { id: "land_cover" as const, label: "Land Cover Distribution", span: true },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-2.5 py-1.5 rounded border text-left text-[11px] transition-colors ${
              tab.span ? "col-span-2" : ""
            } ${
              activeTab === tab.id
                ? "bg-[#162b34] border-teal-400 text-teal-300 font-medium"
                : "bg-[#112128] border-[#1c333c] text-slate-300 hover:bg-[#162b34]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Active Tab Content */}
      <div className="p-3 flex-1">
        {activeTab === "land_cover" && (
          <div>
            <div className="text-xs font-semibold text-slate-200 mb-2">Land Cover Distribution</div>
            <div className="flex items-center gap-2">
              <div className="space-y-1 text-[10px] w-28 shrink-0">
                {landCoverData.map((entry) => (
                  <div key={entry.name} className="flex items-center gap-1.5">
                    <span
                      className="w-3 h-2 rounded-sm shrink-0"
                      style={{ backgroundColor: LAND_COVER_COLORS[entry.name] || "#64748b" }}
                    />
                    <span className="truncate text-slate-300">{entry.name}</span>
                  </div>
                ))}
              </div>
              <div className="h-36 flex-1">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={landCoverData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={28}
                      outerRadius={52}
                      stroke="none"
                    >
                      {landCoverData.map((entry) => (
                        <Cell
                          key={entry.name}
                          fill={LAND_COVER_COLORS[entry.name] || "#64748b"}
                        />
                      ))}
                    </Pie>
                    <RechartsTooltip
                      contentStyle={{ backgroundColor: "#081216", borderColor: "#1c333c", fontSize: "11px" }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {(activeTab === "frp" || activeTab === "timeline") && (
          <div>
            <div className="text-xs font-semibold text-slate-200 mb-2">
              {activeTab === "frp" ? "Max FRP Evolution (MW)" : "Hotspot Count Evolution"}
            </div>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={timeline.map((s) => ({
                    time: new Date(s.window_start).toISOString().slice(5, 16).replace("T", " "),
                    max_frp: s.max_frp,
                    hotspots: s.hotspot_count,
                  }))}
                >
                  <XAxis dataKey="time" tick={{ fontSize: 9, fill: "#94a3b8" }} />
                  <YAxis tick={{ fontSize: 9, fill: "#94a3b8" }} width={28} />
                  <RechartsTooltip
                    contentStyle={{ backgroundColor: "#081216", borderColor: "#1c333c", fontSize: "11px" }}
                  />
                  <Area
                    type="monotone"
                    dataKey={activeTab === "frp" ? "max_frp" : "hotspots"}
                    stroke="#2dd4bf"
                    fill="#2dd4bf"
                    fillOpacity={0.2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {activeTab === "weather" && (
          <div className="space-y-2 text-[11px]">
            <div className="text-xs font-semibold text-slate-200">Surface Weather Context</div>
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-[#112128] border border-[#1c333c] rounded p-2">
                <Thermometer className="w-3.5 h-3.5 text-amber-400 mb-1" />
                <div className="text-slate-400 text-[10px]">Temp</div>
                <div className="font-semibold">
                  {selectedIncident.weather_context.temperature_c ?? "N/A"} °C
                </div>
              </div>
              <div className="bg-[#112128] border border-[#1c333c] rounded p-2">
                <Droplets className="w-3.5 h-3.5 text-sky-400 mb-1" />
                <div className="text-slate-400 text-[10px]">Humidity</div>
                <div className="font-semibold">
                  {selectedIncident.weather_context.relative_humidity_pct ?? "N/A"} %
                </div>
              </div>
              <div className="bg-[#112128] border border-[#1c333c] rounded p-2">
                <Wind className="w-3.5 h-3.5 text-teal-400 mb-1" />
                <div className="text-slate-400 text-[10px]">Wind</div>
                <div className="font-semibold">
                  {selectedIncident.weather_context.wind_speed_kmh ?? "N/A"} km/h
                </div>
              </div>
            </div>
            <div className="text-[10px] text-slate-500">
              Source: {selectedIncident.weather_context.source}
            </div>
          </div>
        )}

        {activeTab === "hotspots" && (
          <div className="space-y-1.5">
            <div className="text-xs font-semibold text-slate-200">
              Latest Detections ({observations.length})
            </div>
            <div className="max-h-40 overflow-y-auto space-y-1 pr-1">
              {observations.slice(0, 20).map((o) => (
                <div
                  key={o.id}
                  className="flex justify-between items-center bg-[#112128] px-2 py-1 rounded text-[10px] font-mono"
                >
                  <span>{new Date(o.acq_timestamp).toISOString().slice(5, 16).replace("T", " ")}</span>
                  <span className="text-amber-300">{(o.frp ?? 0).toFixed(1)} MW</span>
                  <span className="text-slate-400">{o.satellite}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "terrain" && (
          <div className="space-y-2 text-[10px]">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-200">Terrain Context</span>
              {terrain && (
                <span className="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/40 font-mono">
                  {terrain.metadata.source_type}
                </span>
              )}
            </div>
            {terrain?.center_point ? (
              <>
                <div className="grid grid-cols-3 gap-1.5 bg-[#112128] p-2 rounded border border-[#1c333c]">
                  <div><span className="text-slate-400">Elev:</span> {terrain.center_point.elevation_m} m</div>
                  <div><span className="text-slate-400">Slope:</span> {terrain.center_point.slope_deg ?? "N/A"}°</div>
                  <div><span className="text-slate-400">TRI:</span> {terrain.center_point.tri_m ?? "N/A"} m</div>
                </div>
                <div className="space-y-1">
                  {terrain.multiscale.map((s) => (
                    <div key={s.scale_m} className="flex justify-between bg-[#081216] px-2 py-1 rounded font-mono">
                      <span>{s.scale_m}m</span>
                      <span>Elev {s.elev_mean_m}m</span>
                      <span>Slope {s.slope_mean_deg ?? "-"}°</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="text-slate-400">Terrain unavailable.</div>
            )}
          </div>
        )}

        {activeTab === "progression" && (
          <div className="space-y-2 text-[10px]">
            <div className="text-xs font-semibold text-slate-200">Observed Centroid Displacement</div>
            <div className="max-h-32 overflow-y-auto space-y-1 pr-1">
              {progression?.transitions.map((t, i) => (
                <div key={i} className="bg-[#112128] px-2 py-1 rounded flex justify-between font-mono">
                  <span>{t.displacement_km} km</span>
                  <span className="text-teal-300">{t.classification}</span>
                  <span>{t.elevation_delta_m ?? 0} m</span>
                </div>
              ))}
            </div>
            {progression && <p className="text-slate-500 leading-tight">{progression.disclaimer}</p>}
          </div>
        )}
      </div>
    </aside>
  );
}
