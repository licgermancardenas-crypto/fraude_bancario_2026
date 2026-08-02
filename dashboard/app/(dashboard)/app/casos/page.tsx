"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import type { Case, CaseStatus, CasePattern } from "@/lib/types";
import { RESOLVED_STATUSES, daysUntil, rosUrgency } from "@/lib/dates";
import { kycTier, KYC_TIER_STYLE } from "@/lib/kyc";
import { SCREENING_STATUS_STYLE, screeningSummary } from "@/lib/screening";
import { getStoredStatuses } from "@/lib/caseStatus";
import { PATTERN_LABELS } from "@/lib/patterns";
import { computeTriage } from "@/lib/triage";
import PageHeader from "@/components/PageHeader";

const STATUS_LABELS: Record<CaseStatus, string> = {
  abierto:      "Abierto",
  en_revision:  "En revisión",
  escalado:     "Escalado",
  desestimado:  "Desestimado",
  sar_enviado:  "ROS enviado",
};
const STATUS_COLORS: Record<CaseStatus, { bg: string; text: string }> = {
  abierto:     { bg: "rgba(46,107,255,0.15)", text: "#7AA2FF" },
  en_revision: { bg: "rgba(245,158,11,0.15)", text: "#F59E0B" },
  escalado:    { bg: "rgba(239,68,68,0.15)",  text: "#EF4444" },
  desestimado: { bg: "rgba(90,100,120,0.15)", text: "#8A93A6" },
  sar_enviado: { bg: "rgba(34,197,94,0.15)",  text: "#22C55E" },
};

function RosBadge({ c, status }: { c: Case; status: CaseStatus }) {
  if (RESOLVED_STATUSES.includes(status)) {
    return <span className="text-xs" style={{ color: "#5A6478" }}>— caso cerrado</span>;
  }
  const { bg, text, label } = rosUrgency(daysUntil(c.vencimiento_ros));
  return (
    <span className="text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap" style={{ backgroundColor: bg, color: text }}>
      {label}
    </span>
  );
}

function ScreeningBadge({ c }: { c: Case }) {
  const summary = screeningSummary(c.screening);
  if (summary.kind === "none") {
    return <span className="text-xs" style={{ color: "#5A6478" }}>Sin coincidencias</span>;
  }
  if (summary.kind === "indirect") {
    return (
      <span className="text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap" style={{ backgroundColor: "rgba(124,58,237,0.15)", color: "#A78BFA" }}>
        Exposición indirecta
      </span>
    );
  }
  const s = SCREENING_STATUS_STYLE[summary.status];
  return (
    <span className="text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap" style={{ backgroundColor: s.bg, color: s.text }}>
      {summary.lista} · {s.label}
    </span>
  );
}

export default function CasosPage() {
  const [cases, setCases]         = useState<Case[]>([]);
  const [statuses, setStatuses]   = useState<Record<string, CaseStatus>>({});
  const [filterStatus, setFS]     = useState<CaseStatus | "all">("all");
  const [filterPattern, setFP]    = useState<CasePattern | "all">("all");
  const [filterAnalista, setFA]   = useState<string>("all");
  const [sortBy, setSortBy]       = useState<"score" | "date" | "vencimiento">("score");
  const [search, setSearch]       = useState("");

  useEffect(() => {
    fetch("/data/cases.json").then(r => r.json()).then(setCases);
    setStatuses(getStoredStatuses());
  }, []);

  const effectiveStatus = (c: Case): CaseStatus =>
    statuses[c.case_id] ?? c.status;

  const analistas = Array.from(new Set(cases.map(c => c.analista_asignado))).sort();

  const filtered = cases
    .filter(c => filterStatus === "all" || effectiveStatus(c) === filterStatus)
    .filter(c => filterPattern === "all" || c.pattern === filterPattern)
    .filter(c => filterAnalista === "all" || c.analista_asignado === filterAnalista)
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
      sortBy === "score"       ? computeTriage(b).score - computeTriage(a).score :
      sortBy === "vencimiento" ? new Date(a.vencimiento_ros).getTime() - new Date(b.vencimiento_ros).getTime() :
                                 new Date(b.alert_date).getTime() - new Date(a.alert_date).getTime()
    );

  const counts = {
    total:      cases.length,
    abiertos:   cases.filter(c => effectiveStatus(c) === "abierto").length,
    escalados:  cases.filter(c => effectiveStatus(c) === "escalado").length,
    resueltos:  cases.filter(c => ["desestimado","sar_enviado"].includes(effectiveStatus(c))).length,
    screeningPendiente: cases.filter(c => c.screening.hit_directo?.estado === "pendiente").length,
  };

  // Aging / SLA de reportes ROS (solo casos abiertos, no resueltos)
  const openCases = cases.filter(c => !RESOLVED_STATUSES.includes(effectiveStatus(c)));
  const sla = { vencidos: 0, criticos: 0, porVencer: 0, ok: 0 };
  openCases.forEach(c => {
    const d = daysUntil(c.vencimiento_ros);
    if (d < 0) sla.vencidos++;
    else if (d <= 15) sla.criticos++;
    else if (d <= 45) sla.porVencer++;
    else sla.ok++;
  });
  const slaBands = [
    { key: "vencidos",  label: "Vencidos",        value: sla.vencidos,  color: "#EF4444" },
    { key: "criticos",  label: "≤ 15 días",       value: sla.criticos,  color: "#F59E0B" },
    { key: "porVencer", label: "16–45 días",      value: sla.porVencer, color: "#7AA2FF" },
    { key: "ok",        label: "> 45 días",       value: sla.ok,        color: "#22C55E" },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Cola de Alertas"
        subtitle="Gestión de casos ALD generados por el motor Phantom AI"
      />

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {[
          { label: "Total alertas", value: counts.total,     color: "#EDEAE6" },
          { label: "Abiertas",      value: counts.abiertos,  color: "#7AA2FF" },
          { label: "Escaladas",     value: counts.escalados, color: "#EF4444" },
          { label: "Resueltas",     value: counts.resueltos, color: "#22C55E" },
          { label: "Screening pendiente", value: counts.screeningPendiente, color: "#F59E0B" },
        ].map(s => (
          <div key={s.label} className="bg-[#0E1219] rounded-xl p-3 border border-[#1E2430] text-center">
            <p className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</p>
            <p className="text-xs text-[#5A6478] mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Aging / SLA de reportes ROS */}
      <div className="bg-[#0E1219] rounded-xl border border-[#1E2430] p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-bold text-[#EDEAE6]">Vencimiento de reportes ROS <span className="text-[11px] font-normal text-[#5A6478]">— plazo UIF (Ley 25.246)</span></h3>
          <span className="text-xs text-[#5A6478]">{openCases.length} casos abiertos</span>
        </div>
        <div className="flex h-3 w-full overflow-hidden rounded-full bg-[#07090F]">
          {slaBands.filter(b => b.value > 0).map(b => (
            <div key={b.key} title={`${b.label}: ${b.value}`}
              style={{ width: `${(b.value / Math.max(1, openCases.length)) * 100}%`, background: b.color }} />
          ))}
        </div>
        <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2">
          {slaBands.map(b => (
            <div key={b.key} className="flex items-center gap-2">
              <span style={{ width: 9, height: 9, borderRadius: "50%", background: b.color }} />
              <span className="text-lg font-bold" style={{ color: b.color }}>{b.value}</span>
              <span className="text-[11px] text-[#5A6478]">{b.label}</span>
            </div>
          ))}
        </div>
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
          value={filterAnalista}
          onChange={e => setFA(e.target.value)}
          className="border border-[#1E2430] rounded-lg px-3 min-h-[44px] text-sm outline-none"
        >
          <option value="all">Todos los analistas</option>
          {analistas.map(a => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
        <select
          value={sortBy}
          onChange={e => setSortBy(e.target.value as any)}
          className="border border-[#1E2430] rounded-lg px-3 min-h-[44px] text-sm outline-none"
        >
          <option value="score">Ordenar: Mayor prioridad</option>
          <option value="date">Ordenar: Más reciente</option>
          <option value="vencimiento">Ordenar: Vencimiento ROS</option>
        </select>
        <span className="text-xs text-[#5A6478] ml-auto">{filtered.length} casos</span>
      </div>

      {/* Table */}
      <div className="bg-[#0E1219] rounded-xl border border-[#1E2430] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ backgroundColor: "#12161F", borderBottom: "1px solid #1E2430" }}>
                {["Caso", "Prioridad", "Cuenta / Titular", "Patrón", "Rating KYC", "Score GNN", "Analista", "Vencimiento ROS", "Screening", "Estado", ""].map(h => (
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
                      {(() => {
                        const t = computeTriage(c);
                        return (
                          <span className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-bold whitespace-nowrap"
                            style={{ background: `${t.color}22`, color: t.color, border: `1px solid ${t.color}55` }}
                            title={`${t.level} — ${t.score}/100`}>
                            {t.score}
                            <span className="text-[9px] font-semibold uppercase tracking-wide opacity-80">{t.level}</span>
                          </span>
                        );
                      })()}
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-[#EDEAE6] text-xs">{c.persona?.nombre_completo || c.account_id}</p>
                      <p className="text-[11px] text-[#5A6478]">{c.account_id}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-[#5A6478]">{PATTERN_LABELS[c.pattern]}</span>
                    </td>
                    <td className="px-4 py-3">
                      {(() => {
                        const tier = kycTier(c.risk_score);
                        const s = KYC_TIER_STYLE[tier];
                        return (
                          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full whitespace-nowrap" style={{ backgroundColor: s.bg, color: s.text }}>
                            {tier}
                          </span>
                        );
                      })()}
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
                    <td className="px-4 py-3 text-xs text-[#EDEAE6] whitespace-nowrap">{c.analista_asignado}</td>
                    <td className="px-4 py-3">
                      <RosBadge c={c} status={status} />
                    </td>
                    <td className="px-4 py-3">
                      <ScreeningBadge c={c} />
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full" style={{ backgroundColor: sc.bg, color: sc.text }}>
                        {STATUS_LABELS[status]}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <Link href={`/app/casos/${c.case_id}`}
                            className="text-xs font-medium text-[#7AA2FF] hover:text-[#A8C4FF] whitespace-nowrap">
                        Ver caso →
                      </Link>
                    </td>
                  </tr>
                );
              })}
              {filtered.length === 0 && (
                <tr><td colSpan={10} className="px-4 py-10 text-center text-[#5A6478] text-sm">Sin resultados</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
