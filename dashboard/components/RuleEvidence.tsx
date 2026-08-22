"use client";

import type { RuleEvidence as RuleEvidenceData } from "@/lib/types";

/**
 * Evidencia de un escenario de ventana temporal.
 *
 * Es la diferencia práctica entre los dos motores: el agregado dice "esta
 * cuenta dispara R01", el temporal dice además *con qué operaciones*. Un ROS se
 * redacta citando esas operaciones, así que el analista tiene que poder verlas
 * sin salir del panel de escenarios.
 */

const MUTED = "#5A6478";
const DIM = "#8B93A7";
const BONE = "#EDEAE6";

const money = (n: number) =>
  "$" + n.toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// Fecha corta: el panel vive en una columna angosta de la ficha del caso.
const dt = (ts: number) =>
  new Date(ts * 1000).toLocaleString("es-AR", {
    day: "2-digit", month: "2-digit", year: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).replace(",", "");

/** Resumen de la ventana, según la familia de escenario que produjo la evidencia. */
function resumen(e: RuleEvidenceData): string[] {
  const out: string[] = [];
  if (e.contrapartes !== undefined) {
    out.push(`${e.contrapartes} contrapartes distintas`);
    if (e.monto_total !== undefined) out.push(money(e.monto_total));
    if (e.ventana_horas !== undefined) out.push(`ventana de ${e.ventana_horas} h`);
    if (e.umbral_aplicado !== undefined) out.push(`umbral ${money(e.umbral_aplicado)}`);
  }
  if (e.monto_referencia !== undefined) {
    out.push(`${money(e.monto_referencia)} → ${money(e.monto_contrapartida ?? 0)}`);
    if (e.cobertura !== undefined) out.push(`cobertura ${(e.cobertura * 100).toFixed(0)}%`);
    if (e.horas_transcurridas !== undefined) out.push(`${e.horas_transcurridas} h de diferencia`);
  }
  if (e.volumen_pico !== undefined) {
    out.push(`pico ${money(e.volumen_pico)}`);
    if (e.mediana_diaria !== undefined) out.push(`mediana diaria ${money(e.mediana_diaria)}`);
    if (e.multiplo) out.push(`${e.multiplo}× la baseline`);
    if (e.dias_activos !== undefined) out.push(`${e.dias_activos} días activos`);
  }
  return out;
}

export default function RuleEvidence({
  evidencia, cuenta,
}: {
  evidencia: RuleEvidenceData;
  /** Cuenta del caso, para leer cada operación como entrada o salida suya. */
  cuenta?: string;
}) {
  const ops = evidencia.operaciones ?? [];
  const chips = resumen(evidencia);

  return (
    <div className="mt-2 rounded-md border" style={{ borderColor: "#1E2430", backgroundColor: "#0B0E14" }}>
      <div className="px-2.5 pt-2 pb-1.5 flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="text-[10px] uppercase tracking-wide font-semibold" style={{ color: DIM }}>
          Operaciones que lo dispararon
        </span>
        {chips.map((c) => (
          <span key={c} className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                style={{ backgroundColor: "#12161F", color: MUTED }}>{c}</span>
        ))}
      </div>

      {ops.length === 0 ? (
        <p className="px-2.5 pb-2 text-[11px]" style={{ color: MUTED }}>
          Sin operaciones citadas para esta ventana.
        </p>
      ) : (
        <ul>
          {ops.map((o) => {
            const saliente = cuenta ? o.src === cuenta : true;
            const otra = saliente ? o.dst : o.src;
            const concepto = [o.glosa, o.canal].filter(Boolean).join(" · ");
            return (
              <li key={o.transaction_id} className="px-2.5 py-1.5 border-t" style={{ borderColor: "#161B24" }}>
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[11px] font-mono" style={{ color: DIM }}>{o.transaction_id}</span>
                  <span className="text-[11px] font-mono font-semibold whitespace-nowrap"
                        style={{ color: saliente ? "#F59E0B" : "#22C55E" }}>
                    {saliente ? "−" : "+"}{money(o.amount)}
                  </span>
                </div>
                <div className="text-[10px] mt-0.5 truncate" style={{ color: MUTED }} title={concepto}>
                  {dt(o.timestamp)} · {saliente ? "a" : "de"}{" "}
                  <span className="font-mono">{otra}</span>
                  {concepto ? ` · ${concepto}` : ""}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
