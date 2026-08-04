"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import { type KycProfile, type RiesgoNivel, RIESGO_STYLE } from "@/lib/cdd";

const PANEL = "#0E1219", LINE = "#1E2430", BONE = "#EDEAE6", MUTED = "#5A6478";
const fdate = (s: string) => { try { return new Date(s + "T00:00:00").toLocaleDateString("es-AR"); } catch { return s; } };
const ORDER: Record<RiesgoNivel, number> = { Alto: 0, Medio: 1, Bajo: 2 };

export default function ClientesPage() {
  const [profiles, setProfiles] = useState<KycProfile[]>([]);
  const [search, setSearch] = useState("");
  const [filterRiesgo, setFilterRiesgo] = useState<RiesgoNivel | "all">("all");

  useEffect(() => {
    fetch("/data/kyc_profiles.json").then(r => r.json())
      .then((d: Record<string, KycProfile>) => setProfiles(Object.values(d)));
  }, []);

  const kpis = useMemo(() => ({
    total: profiles.length,
    alto: profiles.filter(p => p.cdd.riesgo_nivel === "Alto").length,
    edd: profiles.filter(p => p.cdd.edd_requerida).length,
    vencidas: profiles.filter(p => p.cdd.revision_vencida).length,
  }), [profiles]);

  const rows = useMemo(() => profiles
    .filter(p => filterRiesgo === "all" || p.cdd.riesgo_nivel === filterRiesgo)
    .filter(p => {
      if (!search.trim()) return true;
      const q = search.toLowerCase();
      return (p.persona.nombre_completo ?? "").toLowerCase().includes(q)
        || (p.persona.dni ?? "").includes(q) || p.account_id.toLowerCase().includes(q);
    })
    .sort((a, b) => ORDER[a.cdd.riesgo_nivel] - ORDER[b.cdd.riesgo_nivel] || b.cdd.riesgo_score - a.cdd.riesgo_score),
    [profiles, search, filterRiesgo]);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="KYC / Debida Diligencia del Cliente"
        title="Legajos de Clientes"
        description="Cartera bajo debida diligencia (CDD): calificación de riesgo, estado de revisión periódica y disparadores de EDD. Cubre los clientes de mayor riesgo y una muestra de la cartera."
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Legajos", value: kpis.total, color: BONE },
          { label: "Alto riesgo", value: kpis.alto, color: "#EF4444" },
          { label: "Con EDD requerida", value: kpis.edd, color: "#F59E0B" },
          { label: "Revisión vencida", value: kpis.vencidas, color: "#EF4444" },
        ].map(s => (
          <div key={s.label} className="rounded-xl p-3 text-center" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
            <p className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</p>
            <p className="text-xs mt-0.5" style={{ color: MUTED }}>{s.label}</p>
          </div>
        ))}
      </div>

      <div className="rounded-xl p-4 flex flex-wrap gap-3 items-center" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar por nombre, DNI o cuenta…"
          className="flex-1 min-w-[200px] rounded-lg border border-[#1E2430] bg-[#12161F] px-3 min-h-[44px] text-sm outline-none" style={{ color: BONE }} />
        <select value={filterRiesgo} onChange={e => setFilterRiesgo(e.target.value as any)}
          className="rounded-lg border border-[#1E2430] bg-[#12161F] px-3 min-h-[44px] text-sm outline-none" style={{ color: BONE }}>
          <option value="all">Todos los riesgos</option>
          <option value="Alto">Alto</option><option value="Medio">Medio</option><option value="Bajo">Bajo</option>
        </select>
        <span className="text-xs ml-auto" style={{ color: MUTED }}>{rows.length} legajos</span>
      </div>

      <div className="rounded-xl overflow-hidden" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: "#12161F", borderBottom: `1px solid ${LINE}` }}>
                {["Cliente", "Ocupación", "Riesgo CDD", "EDD", "Próxima revisión", "Screening / PEP", ""].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider" style={{ color: MUTED }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((p, i) => {
                const rs = RIESGO_STYLE[p.cdd.riesgo_nivel];
                const scr = p.screening.hit_directo ? "🔴 Lista" : p.screening.exposicion_indirecta.length ? "⚠ Indirecta" : "—";
                return (
                  <tr key={p.account_id} style={{ borderBottom: i < rows.length - 1 ? `1px solid ${LINE}` : undefined }} className="hover:bg-[#12161F]">
                    <td className="px-4 py-3">
                      <p className="text-xs font-medium" style={{ color: BONE }}>{p.persona.nombre_completo || p.account_id}</p>
                      <p className="text-[10px] font-mono" style={{ color: MUTED }}>{p.account_id} · DNI {p.persona.dni}</p>
                    </td>
                    <td className="px-4 py-3 text-xs" style={{ color: MUTED }}>{p.persona.ocupacion}</td>
                    <td className="px-4 py-3">
                      <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ background: rs.bg, color: rs.text }}>{p.cdd.riesgo_nivel}</span>
                    </td>
                    <td className="px-4 py-3 text-xs">{p.cdd.edd_requerida ? <span style={{ color: "#F59E0B" }}>Sí</span> : <span style={{ color: MUTED }}>No</span>}</td>
                    <td className="px-4 py-3 text-xs whitespace-nowrap" style={{ color: p.cdd.revision_vencida ? "#EF4444" : MUTED }}>
                      {fdate(p.cdd.proxima_revision)} {p.cdd.revision_vencida && "⚠"}
                    </td>
                    <td className="px-4 py-3 text-[11px]" style={{ color: p.screening.hit_directo ? "#EF4444" : MUTED }}>
                      {scr}{p.pep ? " · PEP" : ""}
                    </td>
                    <td className="px-4 py-3">
                      <Link href={`/app/clientes/${p.account_id}`} className="text-xs font-medium whitespace-nowrap" style={{ color: "#7AA2FF" }}>Ver legajo →</Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
