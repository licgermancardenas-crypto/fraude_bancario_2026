"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import type { Case, CaseStatus, CasePattern } from "@/lib/types";
import PageHeader from "@/components/PageHeader";

const STATUS_LABELS: Record<CaseStatus, string> = {
  abierto:      "Abierto",
  en_revision:  "En revisión",
  escalado:     "Escalado",
  desestimado:  "Desestimado",
  sar_enviado:  "SAR enviado",
};
const STATUS_COLORS: Record<CaseStatus, { bg: string; text: string }> = {
  abierto:     { bg: "rgba(46,107,255,0.15)", text: "#7AA2FF" },
  en_revision: { bg: "rgba(245,158,11,0.15)", text: "#F59E0B" },
  escalado:    { bg: "rgba(239,68,68,0.15)",  text: "#EF4444" },
  desestimado: { bg: "rgba(90,100,120,0.15)", text: "#8A93A6" },
  sar_enviado: { bg: "rgba(34,197,94,0.15)",  text: "#22C55E" },
};
const PATTERN_LABELS: Record<CasePattern, string> = {
  anillo_lavado:           "Anillo de lavado",
  estructuracion:          "Estructuración",
  agregacion_fondos:       "Agregación de fondos",
  transacciones_inusuales: "Transacciones inusuales",
};

function getStoredStatuses(): Record<string, CaseStatus> {
  if (typeof window === "undefined") return {};
  try { return JSON.parse(localStorage.getItem("phantom_case_statuses") || "{}"); } catch { return {}; }
}

export default function CasosPage() {
  const [cases, setCases]         = useState<Case[]>([]);
  const [statuses, setStatuses]   = useState<Record<string, CaseStatus>>({});
  const [filterStatus, setFS]     = useState<CaseStatus | "all">("all");
  const [filterPattern, setFP]    = useState<CasePattern | "all">("all");
  const [sortBy, setSortBy]       = useState<"score" | "date">("score");
  const [search, setSearch]       = useState("");

  useEffect(() => {
    fetch("/data/cases.json").then(r => r.json()).then(setCases);
    setStatuses(getStoredStatuses());
  }, []);

  const effectiveStatus = (c: Case): CaseStatus =>
    statuses[c.case_id] ?? c.status;

  const filtered = cases
    .filter(c => filterStatus === "all" || effectiveStatus(c) === filterStatus)
    .filter(c => filterPattern === "all" || c.pattern === filterPattern)
    .filter(c => {
      if (!search) return true;
      const q = search.toLowerCase();
      return (
        c.case_id.toLowerCase().includes(q) ||
        c.account_id.toLowerCase().includes(q) ||
        (c.persona?.nombre_completo || "").toLowerCase().includes(q)
      );
    })
    .sort((a, b) =>
      sortBy === "score"
        ? b.gnn_score - a.gnn_score
        : new Date(b.alert_date).getTime() - new Date(a.alert_date).getTime()
    );

  const counts = {
    total:      cases.length,
    abiertos:   cases.filter(c => effectiveStatus(c) === "abierto").length,
    escalados:  cases.filter(c => effectiveStatus(c) === "escalado").length,
    resueltos:  cases.filter(c => ["desestimado","sar_enviado"].includes(effectiveStatus(c))).length,
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Cola de Alertas"
        subtitle="Gestión de casos AML generados por el motor Phantom AI"
      />

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Total alertas", value: counts.total,     color: "#EDEAE6" },
          { label: "Abiertas",      value: counts.abiertos,  color: "#7AA2FF" },
          { label: "Escaladas",     value: counts.escalados, color: "#EF4444" },
          { label: "Resueltas",     value: counts.resueltos, color: "#22C55E" },
        ].map(s => (
          <div key={s.label} className="bg-[#0E1219] rounded-xl p-3 border border-[#1E2430] text-center">
            <p className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</p>
            <p className="text-xs text-[#5A6478] mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="bg-[#0E1219] rounded-xl border border-[#1E2430] p-4 flex flex-wrap gap-3 items-center">
        <input
          type="text"
          placeholder="Buscar por caso, cuenta o nombre…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="border border-[#1E2430] rounded-lg px-3 min-h-[44px] text-sm flex-1 min-w-48 outline-none focus:ring-2 focus:ring-[#2E6BFF]"
        />
        <select
          value={filterStatus}
          onChange={e => setFS(e.target.value as any)}
          className="border border-[#1E2430] rounded-lg px-3 min-h-[44px] text-sm outline-none"
        >
          <option value="all">Todos los estados</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <select
          value={filterPattern}
          onChange={e => setFP(e.target.value as any)}
          className="border border-[#1E2430] rounded-lg px-3 min-h-[44px] text-sm outline-none"
        >
          <option value="all">Todos los patrones</option>
          {Object.entries(PATTERN_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <select
          value={sortBy}
          onChange={e => setSortBy(e.target.value as any)}
          className="border border-[#1E2430] rounded-lg px-3 min-h-[44px] text-sm outline-none"
        >
          <option value="score">Ordenar: Mayor score</option>
          <option value="date">Ordenar: Más reciente</option>
        </select>
        <span className="text-xs text-[#5A6478] ml-auto">{filtered.length} casos</span>
      </div>

      {/* Table */}
      <div className="bg-[#0E1219] rounded-xl border border-[#1E2430] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ backgroundColor: "#12161F", borderBottom: "1px solid #1E2430" }}>
                {["Caso", "Cuenta / Titular", "Patrón", "Score", "Fecha", "Estado", ""].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-[#5A6478] uppercase tracking-wider whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((c, i) => {
                const status = effectiveStatus(c);
                const sc = STATUS_COLORS[status];
                return (
                  <tr key={c.case_id}
                      style={{ borderBottom: i < filtered.length - 1 ? "1px solid #1E2430" : undefined }}
                      className="hover:bg-[#12161F] transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-[#5A6478] whitespace-nowrap">
                      {c.case_id}
                      {c.is_pep && <span className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded-full font-medium" style={{background:"rgba(245,158,11,0.15)",color:"#F59E0B"}}>PEP</span>}
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-[#EDEAE6] text-xs">{c.persona?.nombre_completo || c.account_id}</p>
                      <p className="text-[11px] text-[#5A6478]">{c.account_id}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-[#5A6478]">{PATTERN_LABELS[c.pattern]}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 rounded-full bg-[#12161F] overflow-hidden">
                          <div className="h-full rounded-full" style={{
                            width: `${c.gnn_score * 100}%`,
                            backgroundColor: c.gnn_score > 0.7 ? "#EF4444" : c.gnn_score > 0.4 ? "#F59E0B" : "#22C55E"
                          }}/>
                        </div>
                        <span className="font-mono text-xs text-[#EDEAE6]">{c.gnn_score.toFixed(3)}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-[#5A6478] whitespace-nowrap">{c.alert_date}</td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full" style={{ backgroundColor: sc.bg, color: sc.text }}>
                        {STATUS_LABELS[status]}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <Link href={`/casos/${c.case_id}`}
                            className="text-xs font-medium text-[#7AA2FF] hover:text-[#A8C4FF] whitespace-nowrap">
                        Ver caso →
                      </Link>
                    </td>
                  </tr>
                );
              })}
              {filtered.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-10 text-center text-[#5A6478] text-sm">Sin resultados</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
