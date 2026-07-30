"use client";
import { useState } from "react";
import { normalizeProvincia } from "@/lib/caseAggregates";
import geoRaw from "@/public/data/geo_provincias.json";

interface ProvinciaGeo { codigo: string; nombre: string; path: string; cx: number; cy: number }
interface GeoData { viewBox: string; provincias: ProvinciaGeo[] }

const geo = geoRaw as GeoData;

interface Props { counts: Record<string, number> }

function mixColor(t: number): string {
  // #1E2430 (sin casos) -> #2E6BFF (maximo) interpolado en RGB
  const from = [30, 36, 48];
  const to   = [46, 107, 255];
  const rgb  = from.map((f, i) => Math.round(f + (to[i] - f) * t));
  return `rgb(${rgb.join(",")})`;
}

export default function GeoMapProvincias({ counts }: Props) {
  const [hover, setHover] = useState<{ nombre: string; count: number } | null>(null);

  const byNorm: Record<string, number> = {};
  for (const [nombre, n] of Object.entries(counts)) byNorm[normalizeProvincia(nombre)] = n;

  const maxCount = Math.max(1, ...Object.values(counts));
  const ranked = Object.entries(counts).sort(([, a], [, b]) => b - a).slice(0, 5);

  return (
    <div className="flex flex-col sm:flex-row items-center gap-4">
      <div className="relative flex-shrink-0" style={{ width: 200 }}>
        <svg viewBox={geo.viewBox} width="100%" role="img" aria-label="Casos por provincia">
          {geo.provincias.map(p => {
            const count = byNorm[normalizeProvincia(p.nombre)] ?? 0;
            const t = count / maxCount;
            return (
              <path
                key={p.codigo}
                d={p.path}
                fill={count > 0 ? mixColor(t) : "#12161F"}
                stroke="#07090F"
                strokeWidth={1}
                opacity={hover && hover.nombre !== p.nombre ? 0.55 : 1}
                onMouseEnter={() => setHover({ nombre: p.nombre, count })}
                onMouseLeave={() => setHover(null)}
                style={{ cursor: "pointer", transition: "opacity 0.15s ease" }}
              />
            );
          })}
        </svg>
        <div className="absolute bottom-1 left-1 pointer-events-none text-[10px] rounded px-1.5 py-0.5" style={{ backgroundColor: "rgba(7,9,15,0.85)", color: "#EDEAE6", minWidth: 120, display: hover ? "block" : "none" }}>
          {hover?.nombre} — {hover?.count} {hover?.count === 1 ? "caso" : "casos"}
        </div>
      </div>
      <div className="flex-1 w-full space-y-2">
        <p className="text-[10px] font-semibold uppercase tracking-widest mb-1" style={{ color: "#5A6478" }}>
          Top provincias
        </p>
        {ranked.map(([nombre, count]) => (
          <div key={nombre} className="flex items-center justify-between gap-2">
            <span className="text-xs truncate" style={{ color: "#5A6478" }}>{nombre}</span>
            <span className="text-xs font-mono flex-shrink-0" style={{ color: "#EDEAE6" }}>{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
