"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import PatternDonut from "@/components/PatternDonut";
import AlertsAreaChart from "@/components/AlertsAreaChart";
import SyntheticDisclaimer from "@/components/SyntheticDisclaimer";
import type { Case, CaseStatus } from "@/lib/types";
import { computeTriage } from "@/lib/triage";
import { daysUntil, RESOLVED_STATUSES } from "@/lib/dates";
import { casesByPattern, casesByMonth } from "@/lib/caseAggregates";
import { getStoredStatuses } from "@/lib/caseStatus";
import gov from "@/public/data/model_governance.json";
import bi from "@/public/data/business_impact.json";

const PANEL = "#12161F", CARD = "#0E1219", LINE = "#1E2430", BONE = "#EDEAE6", MUTED = "#5A6478";
const moneyM = (n: number) => "$ " + (n / 1e6).toLocaleString("es-AR", { maximumFractionDigits: 1 }) + " M";

export default function DireccionPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [statuses, setStatuses] = useState<Record<string, CaseStatus>>({});

  useEffect(() => {
    fetch("/data/cases.json").then(r => r.json()).then(setCases);
    setStatuses(getStoredStatuses());
  }, []);

  const imp = gov.impacto_programa;
  const conc = bi.key_thresholds.recall_90_pct; // top-N por score → % de monto rastreado
  const lastMonit = gov.monitoreo_mensual[gov.monitoreo_mensual.length - 1];

  const eff = (c: Case) => statuses[c.case_id] ?? c.status;
  const openCases = cases.filter(c => !RESOLVED_STATUSES.includes(eff(c)));
  const criticos = cases.filter(c => computeTriage(c).score >= 80).length;
  const overdue = openCases.filter(c => daysUntil(c.vencimiento_ros) < 0).length;
  const slaComp = openCases.length ? Math.round((1 - overdue / openCases.length) * 100) : 100;
  const screeningExp = cases.filter(c => c.screening.hit_directo || c.screening.exposicion_indirecta.length > 0).length;
  const peps = cases.filter(c => c.is_pep).length;
  const escalados = cases.filter(c => eff(c) === "escalado" || eff(c) === "sar_enviado").length;
  const patternData = cases.length ? casesByPattern(cases) : [];
  const monthData = cases.length ? casesByMonth(cases) : [];

  const hero = [
    { label: "Fondos ilícitos identificados", value: moneyM(imp.monto_ilicito_rastreado), color: "#7AA2FF", sub: "rastreados en la red sintética" },
    { label: "Tasa de detección", value: `${Math.round(imp.tasa_deteccion * 100)}%`, color: "#22C55E", sub: "del fraude etiquetado (a validar con datos reales)" },
    { label: "Perpetradores de origen", value: imp.perpetradores_origen.toLocaleString("es-AR"), color: "#F59E0B", sub: "cuentas inyectoras rastreadas" },
    { label: "Casos críticos abiertos", value: String(criticos), color: "#EF4444", sub: "prioridad ≥ 80/100" },
    { label: "Cumplimiento SLA ROS", value: `${slaComp}%`, color: slaComp >= 90 ? "#22C55E" : slaComp >= 75 ? "#F59E0B" : "#EF4444", sub: `${overdue} reporte(s) vencido(s)` },
  ];

  const impacto = [
    { k: "Tipologías de lavado cubiertas", v: String(imp.tipologias_cubiertas) },
    { k: "Cuentas mula detectadas", v: imp.mulas_detectadas.toLocaleString("es-AR") },
    { k: "Portfolio monitoreado", v: imp.portfolio.toLocaleString("es-AR") + " cuentas" },
    { k: "Cuentas marcadas como fraude", v: imp.cuentas_fraude.toLocaleString("es-AR") },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Reporte a Dirección"
        title="Panel Ejecutivo — Programa de Prevención de Lavado"
        description="Vista consolidada para el Comité de Dirección: impacto del programa, postura de riesgo y cumplimiento regulatorio. Datos del período sobre el portfolio de BRS."
      />

      <SyntheticDisclaimer />

      {/* Hero KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {hero.map(h => (
          <div key={h.label} className="rounded-xl p-4" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
            <div className="text-2xl font-bold leading-tight" style={{ color: h.color }}>{h.value}</div>
            <div className="text-xs font-semibold mt-1" style={{ color: BONE }}>{h.label}</div>
            <div className="text-[10px] mt-0.5" style={{ color: MUTED }}>{h.sub}</div>
          </div>
        ))}
      </div>

      {/* Eficiencia / concentración (mensaje para dirección) */}
      <div className="rounded-xl p-5" style={{ background: "linear-gradient(90deg, rgba(46,107,255,0.10), transparent)", border: `1px solid ${LINE}` }}>
        <div className="flex items-start gap-3">
          <span className="text-2xl">🎯</span>
          <p className="text-sm leading-relaxed" style={{ color: BONE }}>
            Con inteligencia de grafos, revisar apenas el <b style={{ color: "#7AA2FF" }}>{conc.accounts_pct}%</b> de las cuentas de mayor riesgo
            permite rastrear el <b style={{ color: "#7AA2FF" }}>{Math.round(conc.amount_recall * 100)}%</b> del monto ilícito del portafolio —
            concentrando el esfuerzo del equipo de cumplimiento donde realmente hay riesgo, en lugar de revisar alertas al azar.
          </p>
        </div>
      </div>

      {/* Impacto del programa */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {impacto.map(x => (
          <div key={x.k} className="rounded-xl p-4 text-center" style={{ background: CARD, border: `1px solid ${LINE}` }}>
            <div className="text-xl font-bold" style={{ color: BONE }}>{x.v}</div>
            <div className="text-[11px] mt-1" style={{ color: MUTED }}>{x.k}</div>
          </div>
        ))}
      </div>

      {/* Postura de riesgo + cumplimiento */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl p-5" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
          <h3 className="text-sm font-bold mb-3" style={{ color: BONE }}>Exposición por tipología de lavado</h3>
          {patternData.length > 0 ? <PatternDonut data={patternData} /> : <p className="text-xs" style={{ color: MUTED }}>Cargando…</p>}
          <div className="mt-3 flex gap-4 text-xs">
            <span style={{ color: MUTED }}>Exposición a sanciones: <b style={{ color: "#EF4444" }}>{screeningExp}</b> casos</span>
            <span style={{ color: MUTED }}>Personas Expuestas (PEP): <b style={{ color: "#F59E0B" }}>{peps}</b></span>
          </div>
        </div>

        <div className="rounded-xl p-5" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
          <h3 className="text-sm font-bold mb-3" style={{ color: BONE }}>Salud del programa</h3>
          <div className="space-y-3">
            <HealthRow label="Casos en cola de investigación" value={String(cases.length)} color={BONE} />
            <HealthRow label="Elevados a ROS (UIF)" value={String(escalados)} color="#EF4444" />
            <HealthRow label="Cumplimiento de plazos ROS" value={`${slaComp}%`} color={slaComp >= 90 ? "#22C55E" : "#F59E0B"}
              flag={overdue > 0 ? `${overdue} vencido(s) — riesgo regulatorio` : undefined} />
            <div className="pt-2" style={{ borderTop: `1px solid ${LINE}` }}>
              <div className="flex items-center justify-between">
                <span className="text-xs" style={{ color: MUTED }}>Estado del modelo</span>
                <span className="rounded-full px-2 py-0.5 text-[11px] font-bold" style={{ background: "rgba(34,197,94,0.15)", color: "#22C55E", border: "1px solid rgba(34,197,94,0.4)" }}>
                  {gov.model_card.estado}
                </span>
              </div>
              <div className="flex items-center justify-between mt-2">
                <span className="text-xs" style={{ color: MUTED }}>PR-AUC (último monitoreo · {lastMonit.mes})</span>
                <span className="text-xs font-bold" style={{ color: "#7AA2FF" }}>{lastMonit.pr_auc.toFixed(3)}</span>
              </div>
              <Link href="/app/gobernanza" className="mt-2 inline-block text-[11px]" style={{ color: "#7AA2FF" }}>Ver gobernanza del modelo →</Link>
            </div>
          </div>
        </div>
      </div>

      {/* Tendencia */}
      {monthData.length > 0 && (
        <div className="rounded-xl p-5" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
          <h3 className="text-sm font-bold mb-3" style={{ color: BONE }}>Alertas generadas por mes</h3>
          <AlertsAreaChart data={monthData} />
        </div>
      )}

      <p className="text-[10px]" style={{ color: MUTED }}>
        Datos sobre grafo transaccional sintético (portfolio BRS simulado). Los montos representan flujos rastreados en la red de lavado, no pérdidas contables.
      </p>
    </div>
  );
}

function HealthRow({ label, value, color, flag }: { label: string; value: string; color: string; flag?: string }) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <span className="text-xs" style={{ color: MUTED }}>{label}</span>
        {flag && <span className="ml-2 text-[10px]" style={{ color: "#EF4444" }}>⚠ {flag}</span>}
      </div>
      <span className="text-sm font-bold" style={{ color }}>{value}</span>
    </div>
  );
}
