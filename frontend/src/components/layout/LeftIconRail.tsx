"use client";

import { Globe, BarChart3, BellRing, ShieldCheck } from "lucide-react";

interface LeftIconRailProps {
  activeSection: "map" | "analytics" | "alerts" | "audit";
  onSelectSection: (s: "map" | "analytics" | "alerts" | "audit") => void;
}

export function LeftIconRail({ activeSection, onSelectSection }: LeftIconRailProps) {
  const items = [
    { id: "map" as const, icon: Globe, label: "Geospatial Monitor" },
    { id: "analytics" as const, icon: BarChart3, label: "Analytics" },
    { id: "alerts" as const, icon: BellRing, label: "Priority Queue" },
    { id: "audit" as const, icon: ShieldCheck, label: "Provenance & Audit" },
  ];

  return (
    <aside className="w-11 bg-[#081216] border-r border-[#1c333c] flex flex-col items-center py-2.5 gap-2 shrink-0 z-20">
      {items.map((item) => {
        const Icon = item.icon;
        const active = activeSection === item.id;
        return (
          <button
            key={item.id}
            onClick={() => onSelectSection(item.id)}
            title={item.label}
            className={`w-8 h-8 rounded flex items-center justify-center transition-colors ${
              active
                ? "bg-[#162b34] text-teal-400 border border-teal-500/40"
                : "text-slate-400 hover:text-slate-200 hover:bg-[#0c181d]"
            }`}
          >
            <Icon className="w-4 h-4" />
          </button>
        );
      })}
    </aside>
  );
}
