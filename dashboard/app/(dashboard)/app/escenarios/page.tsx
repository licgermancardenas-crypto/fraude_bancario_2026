"use client";

import { useEffect, useMemo, useState } from "react";
import PageHeader from "@/components/PageHeader";
import SessionSwitcher from "@/components/SessionSwitcher";
import SyntheticDisclaimer from "@/components/SyntheticDisclaimer";
import CalibrationChart from "@/components/CalibrationChart";
import { getSession, setSessionRole, can, type Session, type Role } from "@/lib/session";
import { appendAudit } from "@/lib/auditLog";
import {
  type ScenariosData, type Scenario, type CalibrationProposal,
  SEVERITY_STYLE, MOTIVOS_CALIBRACION, calibrationImpact, currentPoint,
  getProposals, saveProposal, decideProposal, canApprove, pendingFor,
} from "@/lib/scenarios";

const PANEL = "#0E1219", LINE = "#1E2430", BONE = "#EDEAE6", MUTED = "#5A6478";
const BLUE = "#7AA2FF", GREEN = "#22C55E", AMBER = "#F59E0B", RED = "#EF4444";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const num = (v: number) => v.toLocaleString("es-AR");
const signed = (v: number) => (v > 0 ? `+${num(v)}` : num(v));
const signedPct = (v: number) => `${v > 0 ? "+" : ""}${(v * 100).toFixed(1)} pp`;

const SEG_LABEL: Record<string, string> = {
  personal: "Personal", business: "Empresa", merchant: "Comercio",
};

function thresholdText(valor: number | Record<string, number>): string {
  if (typeof valor === "number") return num(valor);
  return ["personal", "business", "merchant"]
    .filter(s => s in valor)
    .map(s => `${SEG_LABEL[s]} ${num(valor[s])}`)
    .join(" · ");
}

export default function EscenariosPage() {
  const [data, setData] = useState<ScenariosData | null>(null);
  const [session, setSession] = useState<Session>({ role: "analista", nombre: "" });
  const [selId, setSelId] = useState<string>("R01");
  const [factorIdx, setFactorIdx] = useState<number | null>(null);
  const [proposals, setProposals] = useState<CalibrationProposal[]>([]);
  const [motivo, setMotivo] = useState(MOTIVOS_CALIBRACION[0]);
  const [comentario, setComentario] = useState("");

  useEffect(() => {
    fetch("/data/scenarios.json").then(r => r.json()).then(setData);
    setSession(getSession());
    setProposals(getProposals());
  }, []);

  const changeRole = (role: Role) => { setSessionRole(role); setSession(getSession()); };

  const sel: Scenario | undefined = useMemo(
    () => data?.escenarios.find(e => e.id === selId), [data, selId],
  );
  const cal = sel?.calibracion ?? null;

  // Índice del factor vigente (1×) — punto de partida del simulador.
  const baseIdx = useMemo(
    () => (cal ? Math.max(0, cal.puntos.findIndex(p => p.factor === 1)) : 0), [cal],
  );
  const idx = factorIdx ?? baseIdx;
  useEffect(() => setFactorIdx(null), [selId]);

  if (!data) return <div className="flex items-center justify-center h-64 text-[#5A6478]">Cargando escenarios…</div>;

  const factor = cal ? cal.puntos[idx].factor : 1;
  const impacto = cal ? calibrationImpact(cal, factor) : null;
  const pendiente = sel ? pendingFor(proposals, sel.id) : undefined;
  const puedeProponer = can(session.role, "escenario.calibrar");

  const proponer = () => {
    if (!sel || !cal || !impacto || factor === 1 || !puedeProponer || pendiente) return;
    const p: CalibrationProposal = {
      id: `PROP-${Date.now()}`,
      scenario_id: sel.id,
      scenario_nombre: sel.nombre,
      parametro: cal.label,
      factor,
      valor_actual: cal.valor_actual,
      valor_propuesto: impacto.hasta.valor,
      justificacion: motivo,
      proponente: session.nombre,
      rol: session.role,
      fecha: new Date().toISOString(),
      estado: "pendiente",
      impacto: {
        dAlertas: impacto.dAlertas, dPrecision: impacto.dPrecision,
        dRecall: impacto.dRecall, perdidaCobertura: impacto.perdidaCobertura,
      },
    };
    setProposals(saveProposal(p));
    appendAudit({
      actor: session.nombre, role: session.role, action: "escenario.calibracion_propuesta",
      target: sel.id, detail: `${cal.label}: ${cal.valor_actual} → ${impacto.hasta.valor} (${factor}×) · ${motivo}`,
    });
    setFactorIdx(null);
  };

  const decidir = (p: CalibrationProposal, estado: "aprobada" | "rechazada") => {
    setProposals(decideProposal(p.id, estado, session.nombre, comentario));
    appendAudit({
      actor: session.nombre, role: session.role, action: `escenario.calibracion_${estado}`,
      target: p.scenario_id, detail: `${p.parametro}: ${p.valor_actual} → ${p.valor_propuesto}${comentario ? ` · ${comentario}` : ""}`,
    });
    setComentario("");
  };

  const comp = data.complementariedad;
  const pendientes = proposals.filter(p => p.estado === "pendiente");

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <PageHeader eyebrow="Motor de reglas" title="Gestión de escenarios"
          description="Catálogo de escenarios ALD con su norma de respaldo, sus umbrales vigentes y su rendimiento medido. Cada escenario puede recalibrarse: el simulador backtestea el umbral sobre toda la cartera antes de proponer el cambio, que requiere aprobación de un segundo par de ojos." />
        <SessionSwitcher role={session.role} nombre={session.nombre} onChange={changeRole} />
      </div>

      <SyntheticDisclaimer compact />

      {/* ── rendimiento del motor ─────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {[
          { label: "Escenarios activos", value: `${data.resumen.activos} / ${data.resumen.escenarios}`, color: BONE },
          { label: "Cuentas marcadas", value: num(data.resumen.disparos), color: BLUE },
          { label: "Precisión del motor", value: pct(data.resumen.precision), color: GREEN },
          { label: "Recall sobre el fraude", value: pct(data.resumen.recall), color: AMBER },
          { label: "Lift sobre la tasa base", value: `${data.resumen.lift}×`, color: BONE },
        ].map(k => (
          <div key={k.label} className="rounded-xl p-4" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
            <div className="text-2xl font-bold" style={{ color: k.color }}>{k.value}</div>
            <div className="text-[11px] mt-1" style={{ color: MUTED }}>{k.label}</div>
          </div>
        ))}
      </div>

      {/* ── los dos motores de reglas ─────────────────────────────────────── */}
      {data.resumen.por_motor && data.resumen.cruce_motores && (() => {
        const pm = data.resumen.por_motor!;
        const cx = data.resumen.cruce_motores!;
        return (
          <div className="rounded-xl p-5" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
            <h2 className="text-sm font-bold mb-1" style={{ color: BONE }}>Dos motores, dos formas de mirar</h2>
            <p className="text-xs mb-4" style={{ color: MUTED }}>
              Los escenarios <b style={{ color: BONE }}>agregados</b> evalúan totales y promedios de la cuenta
              sobre todo el período. Los <b style={{ color: BONE }}>temporales</b> evalúan la secuencia de
              operaciones dentro de una ventana móvil — la diferencia entre &ldquo;diez transferencias a diez
              destinatarios&rdquo; en un año, que es normal, y las mismas diez en cuarenta y ocho horas, que es pitufeo.
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr style={{ color: MUTED }}>
                    <th className="text-left font-medium px-3 py-2">Motor</th>
                    <th className="text-right font-medium px-3 py-2">Escenarios</th>
                    <th className="text-right font-medium px-3 py-2">Cuentas marcadas</th>
                    <th className="text-right font-medium px-3 py-2">Precisión</th>
                    <th className="text-right font-medium px-3 py-2">Recall</th>
                    <th className="text-right font-medium px-3 py-2">Lift</th>
                  </tr>
                </thead>
                <tbody>
                  {([
                    ["agregado", "Agregado (features de cuenta)"],
                    ["temporal", "Temporal (ventana sobre el stream)"],
                  ] as const).map(([k, label]) => {
                    const m = pm[k];
                    if (!m) return null;
                    const destaca = k === "temporal";
                    return (
                      <tr key={k} className="border-t" style={{ borderColor: LINE }}>
                        <td className="px-3 py-2" style={{ color: destaca ? BONE : "rgba(237,234,230,0.75)" }}>
                          {label}
                        </td>
                        <td className="px-3 py-2 text-right font-mono" style={{ color: MUTED }}>{m.escenarios}</td>
                        <td className="px-3 py-2 text-right font-mono" style={{ color: BLUE }}>{num(m.disparos)}</td>
                        <td className="px-3 py-2 text-right font-mono font-bold" style={{ color: destaca ? GREEN : MUTED }}>{pct(m.precision)}</td>
                        <td className="px-3 py-2 text-right font-mono" style={{ color: AMBER }}>{pct(m.recall)}</td>
                        <td className="px-3 py-2 text-right font-mono" style={{ color: MUTED }}>{m.lift}×</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="grid grid-cols-3 gap-3 mt-4">
              {[
                { label: "Fraude que sólo ve el motor agregado", value: cx.solo_agregado, color: MUTED },
                { label: "Fraude que sólo ve el motor temporal", value: cx.solo_temporal, color: GREEN },
                { label: "Visto por los dos motores", value: cx.ambos, color: BLUE },
              ].map(k => (
                <div key={k.label} className="rounded-lg p-3" style={{ background: "#07090F", border: `1px solid ${LINE}` }}>
                  <div className="text-xl font-bold" style={{ color: k.color }}>{num(k.value)}</div>
                  <div className="text-[11px] mt-1" style={{ color: MUTED }}>{k.label}</div>
                </div>
              ))}
            </div>

            <div className="rounded-lg p-3 mt-3 text-[11px] leading-relaxed" style={{ background: "rgba(34,197,94,0.07)", border: "1px solid rgba(34,197,94,0.25)", color: "rgba(237,234,230,0.82)" }}>
              <b style={{ color: GREEN }}>Qué cambió al agregar la ventana:</b> el motor temporal marca
              menos de la mitad de cuentas que el agregado y aun así detecta más fraude
              ({pct(pm.temporal.recall)} contra {pct(pm.agregado.recall)}), con una precisión de
              {" "}{pct(pm.temporal.precision)} frente a {pct(pm.agregado.precision)}. Son
              {" "}{num(cx.solo_temporal)} casos que ningún escenario agregado alcanza: dependen de
              <i> cuándo</i> ocurrieron las operaciones, y un promedio anual no conserva esa información.
              Además citan las operaciones que los dispararon, que es lo que se transcribe en el ROS.
            </div>
          </div>
        );
      })()}

      {/* ── complementariedad reglas ↔ modelo ─────────────────────────────── */}
      {comp?.fraude_total ? (
        <div className="rounded-xl p-5" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
          <h2 className="text-sm font-bold mb-1" style={{ color: BONE }}>¿Para qué mantener reglas si hay un modelo?</h2>
          <p className="text-xs mb-4" style={{ color: MUTED }}>
            Reparto de los {num(comp.fraude_total)} casos de fraude entre las dos capas de detección,
            tomando el corte del GNN en {comp.corte_gnn}.
          </p>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
            {[
              { label: "Detectados por ambas capas", value: comp.ambos, color: GREEN },
              { label: "Sólo por el modelo", value: comp.solo_gnn, color: BLUE },
              { label: "Sólo por las reglas", value: comp.solo_reglas, color: AMBER },
              { label: "Por ninguna de las dos", value: comp.ninguno, color: RED },
            ].map(k => (
              <div key={k.label} className="rounded-lg p-3" style={{ background: "#07090F", border: `1px solid ${LINE}` }}>
                <div className="text-xl font-bold" style={{ color: k.color }}>{num(k.value)}</div>
                <div className="text-[11px] mt-1" style={{ color: MUTED }}>{k.label}</div>
              </div>
            ))}
          </div>
          <div className="rounded-lg p-3 text-[11px] leading-relaxed" style={{ background: "rgba(46,107,255,0.07)", border: "1px solid rgba(46,107,255,0.25)", color: "rgba(237,234,230,0.82)" }}>
            <b style={{ color: BLUE }}>Lectura honesta:</b> las reglas no aportan cobertura adicional —
            el modelo ya detecta todo lo que ellas detectan, y {num(comp.solo_gnn)} casos más que ninguna
            regla alcanza. Su valor no es la cobertura sino la <b>defendibilidad</b>: un escenario
            determinista con cita normativa se le explica a un inspector de la UIF, se audita y se
            versiona. El modelo aporta cobertura; las reglas, trazabilidad regulatoria.
          </div>
          {comp.nota && (
            <p className="text-[10px] mt-2 leading-relaxed" style={{ color: MUTED }}>{comp.nota}</p>
          )}
        </div>
      ) : null}

      {/* ── propuestas pendientes de aprobación ───────────────────────────── */}
      {pendientes.length > 0 && (
        <div className="rounded-xl p-5" style={{ background: "#07090F", border: "1px solid rgba(245,158,11,0.35)" }}>
          <h2 className="text-sm font-bold mb-3" style={{ color: AMBER }}>
            Cambios de umbral pendientes de aprobación ({pendientes.length})
          </h2>
          <div className="space-y-3">
            {pendientes.map(p => {
              const habilitado = canApprove(p, session.nombre, can(session.role, "escenario.aprobar"));
              return (
                <div key={p.id} className="rounded-lg p-3" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
                  <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 mb-2">
                    <span className="text-xs font-mono" style={{ color: BLUE }}>{p.scenario_id}</span>
                    <span className="text-sm font-medium" style={{ color: BONE }}>{p.scenario_nombre}</span>
                    <span className="text-[11px]" style={{ color: MUTED }}>
                      {p.parametro}: <b style={{ color: BONE }}>{p.valor_actual}</b> → <b style={{ color: AMBER }}>{p.valor_propuesto}</b> ({p.factor}×)
                    </span>
                  </div>
                  <div className="text-[11px] mb-2" style={{ color: MUTED }}>
                    Propuesto por {p.proponente} · {new Date(p.fecha).toLocaleString("es-AR")} · {p.justificacion}
                  </div>
                  <div className="flex flex-wrap gap-x-5 gap-y-1 text-[11px] mb-3">
                    <span style={{ color: MUTED }}>Alertas <b style={{ color: BONE }}>{signed(p.impacto.dAlertas)}</b></span>
                    <span style={{ color: MUTED }}>Precisión <b style={{ color: p.impacto.dPrecision >= 0 ? GREEN : RED }}>{signedPct(p.impacto.dPrecision)}</b></span>
                    <span style={{ color: MUTED }}>Recall <b style={{ color: p.impacto.dRecall >= 0 ? GREEN : RED }}>{signedPct(p.impacto.dRecall)}</b></span>
                    <span style={{ color: MUTED }}>Fraude que se dejaría de detectar <b style={{ color: p.impacto.perdidaCobertura > 0 ? RED : GREEN }}>{signed(p.impacto.perdidaCobertura)}</b></span>
                  </div>
                  {habilitado ? (
                    <div className="flex flex-wrap gap-2 items-center">
                      <input value={comentario} onChange={e => setComentario(e.target.value)}
                        placeholder="Comentario de la decisión (opcional)"
                        className="flex-1 min-w-[200px] rounded-lg border border-[#1E2430] bg-[#12161F] px-3 min-h-[36px] text-xs outline-none" style={{ color: BONE }} />
                      <button onClick={() => decidir(p, "aprobada")} className="rounded-lg px-3 min-h-[36px] text-xs font-medium"
                        style={{ background: "rgba(34,197,94,0.12)", color: GREEN, border: "1px solid rgba(34,197,94,0.35)" }}>Aprobar cambio</button>
                      <button onClick={() => decidir(p, "rechazada")} className="rounded-lg px-3 min-h-[36px] text-xs font-medium"
                        style={{ background: "rgba(239,68,68,0.10)", color: RED, border: "1px solid rgba(239,68,68,0.30)" }}>Rechazar</button>
                    </div>
                  ) : (
                    <p className="text-[11px]" style={{ color: MUTED }}>
                      {p.proponente === session.nombre
                        ? "No podés aprobar tu propia propuesta — control de cuatro ojos."
                        : "Requiere aprobación del Oficial de Cumplimiento."}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── catálogo ──────────────────────────────────────────────────────── */}
      <div className="rounded-xl overflow-hidden" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
        <div className="px-5 py-3" style={{ borderBottom: `1px solid ${LINE}` }}>
          <h2 className="text-sm font-bold" style={{ color: BONE }}>Catálogo de escenarios</h2>
          <p className="text-[11px] mt-0.5" style={{ color: MUTED }}>
            Rendimiento medido sobre {num(data.poblacion.cuentas)} cuentas · tasa base de fraude {pct(data.poblacion.tasa_base)}
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr style={{ color: MUTED, borderBottom: `1px solid ${LINE}` }}>
                <th className="text-left font-medium px-4 py-2">Escenario</th>
                <th className="text-left font-medium px-3 py-2">Severidad</th>
                <th className="text-right font-medium px-3 py-2">Alertas</th>
                <th className="text-right font-medium px-3 py-2">Precisión</th>
                <th className="text-right font-medium px-3 py-2">Recall</th>
                <th className="text-right font-medium px-3 py-2">Lift</th>
                <th className="text-right font-medium px-4 py-2">Aporte exclusivo</th>
              </tr>
            </thead>
            <tbody>
              {data.escenarios.map(e => {
                const activo = e.id === selId;
                const sev = SEVERITY_STYLE[e.severidad];
                return (
                  <tr key={e.id} onClick={() => setSelId(e.id)}
                    className="cursor-pointer transition-colors"
                    style={{ borderBottom: `1px solid ${LINE}`, background: activo ? "rgba(46,107,255,0.08)" : "transparent" }}>
                    <td className="px-4 py-2.5">
                      <div className="flex items-baseline gap-2">
                        <span className="font-mono" style={{ color: BLUE }}>{e.id}</span>
                        <span style={{ color: BONE }}>{e.nombre}</span>
                        {e.motor === "temporal" && (
                          <span className="text-[10px] rounded px-1.5 py-0.5" style={{ background: "rgba(34,197,94,0.12)", color: GREEN }}
                            title="Evaluado sobre la secuencia de operaciones en una ventana móvil">ventana</span>
                        )}
                        {pendingFor(proposals, e.id) && (
                          <span className="text-[10px] rounded px-1.5 py-0.5" style={{ background: "rgba(245,158,11,0.14)", color: AMBER }}>cambio pendiente</span>
                        )}
                      </div>
                      <div className="text-[10px] mt-0.5" style={{ color: MUTED }}>{e.cita}</div>
                    </td>
                    <td className="px-3 py-2.5">
                      <span className="text-[10px] rounded px-1.5 py-0.5" style={{ background: sev.bg, color: sev.color }}>{sev.label}</span>
                    </td>
                    <td className="px-3 py-2.5 text-right" style={{ color: BONE }}>{num(e.metricas.disparos)}</td>
                    <td className="px-3 py-2.5 text-right" style={{ color: e.metricas.precision >= 0.5 ? GREEN : e.metricas.precision >= 0.25 ? AMBER : RED }}>{pct(e.metricas.precision)}</td>
                    <td className="px-3 py-2.5 text-right" style={{ color: BONE }}>{pct(e.metricas.recall)}</td>
                    <td className="px-3 py-2.5 text-right" style={{ color: MUTED }}>{e.metricas.lift}×</td>
                    <td className="px-4 py-2.5 text-right" style={{ color: MUTED }}>{num(e.aporte_exclusivo)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── ficha del escenario + simulador ───────────────────────────────── */}
      {sel && (
        <div className="rounded-xl p-5 space-y-5" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
          <div>
            <div className="flex flex-wrap items-baseline gap-2 mb-1">
              <span className="font-mono text-sm" style={{ color: BLUE }}>{sel.id}</span>
              <h2 className="text-base font-bold" style={{ color: BONE }}>{sel.nombre}</h2>
              <span className="text-[10px] rounded px-1.5 py-0.5" style={{ background: SEVERITY_STYLE[sel.severidad].bg, color: SEVERITY_STYLE[sel.severidad].color }}>
                Severidad {SEVERITY_STYLE[sel.severidad].label} · {sel.puntos_severidad} pts
              </span>
              <span className="text-[10px] rounded px-1.5 py-0.5" style={{ background: "rgba(34,197,94,0.12)", color: GREEN }}>Activo</span>
            </div>
            <p className="text-xs leading-relaxed mb-2" style={{ color: "rgba(237,234,230,0.75)" }}>{sel.descripcion}</p>
            <p className="text-[11px]" style={{ color: MUTED }}>
              Norma de respaldo: <b style={{ color: BONE }}>{sel.cita}</b> · Fuente: {sel.fuente} ·
              Marca en exclusiva {num(sel.aporte_exclusivo)} cuentas que ningún otro escenario detecta
            </p>
            {sel.cita_evidencia && (
              <p className="text-[11px] mt-1.5" style={{ color: MUTED }}>
                Escenario de <b style={{ color: GREEN }}>ventana temporal</b>: en cada alerta adjunta las
                operaciones concretas que lo dispararon, disponibles en el detalle del caso para
                transcribirlas al ROS.
              </p>
            )}
          </div>

          {/* umbrales vigentes */}
          {sel.umbrales.length > 0 && (
            <div>
              <h3 className="text-xs font-bold mb-2" style={{ color: BONE }}>Umbrales vigentes</h3>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {sel.umbrales.map(u => (
                  <div key={u.clave} className="rounded-lg p-3" style={{ background: "#07090F", border: `1px solid ${LINE}` }}>
                    <div className="text-[11px] mb-1" style={{ color: MUTED }}>{u.label}</div>
                    <div className="text-sm font-medium" style={{ color: BONE }}>{thresholdText(u.valor)}</div>
                    {u.segmentado && (
                      <div className="text-[10px] mt-1" style={{ color: BLUE }}>segmentado por tipo de cuenta</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* rendimiento por segmento */}
          {Object.keys(sel.por_tipo).length > 0 && (
            <div>
              <h3 className="text-xs font-bold mb-2" style={{ color: BONE }}>Rendimiento por segmento KYC</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr style={{ color: MUTED, borderBottom: `1px solid ${LINE}` }}>
                      <th className="text-left font-medium py-2">Segmento</th>
                      <th className="text-right font-medium py-2">Alertas</th>
                      <th className="text-right font-medium py-2">Verdaderos positivos</th>
                      <th className="text-right font-medium py-2">Precisión</th>
                      <th className="text-right font-medium py-2">Tasa de FP</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(sel.por_tipo).map(([seg, m]) => (
                      <tr key={seg} style={{ borderBottom: `1px solid ${LINE}` }}>
                        <td className="py-2" style={{ color: BONE }}>{SEG_LABEL[seg] ?? seg}</td>
                        <td className="py-2 text-right" style={{ color: BONE }}>{num(m.disparos)}</td>
                        <td className="py-2 text-right" style={{ color: MUTED }}>{num(m.tp)}</td>
                        <td className="py-2 text-right" style={{ color: m.precision >= 0.5 ? GREEN : AMBER }}>{pct(m.precision)}</td>
                        <td className="py-2 text-right" style={{ color: MUTED }}>{pct(m.tasa_fp)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* simulador */}
          {cal && impacto ? (
            <div>
              <h3 className="text-xs font-bold mb-1" style={{ color: BONE }}>Simulador de calibración — backtest sobre la cartera completa</h3>
              <p className="text-[11px] mb-3" style={{ color: MUTED }}>
                Mové el umbral <b style={{ color: BONE }}>{cal.label.toLowerCase()}</b> y mirá el efecto medido
                sobre las {num(data.poblacion.cuentas)} cuentas. Subir el umbral{" "}
                {cal.direccion === "menos_alertas" ? "reduce" : "aumenta"} el volumen de alertas.
              </p>

              <div className="rounded-lg p-4 mb-4" style={{ background: "#07090F", border: `1px solid ${LINE}` }}>
                <div className="flex flex-wrap items-center gap-4 mb-3">
                  <div>
                    <div className="text-[11px]" style={{ color: MUTED }}>Umbral vigente</div>
                    <div className="text-sm font-medium" style={{ color: BONE }}>{cal.valor_actual}</div>
                  </div>
                  <div className="text-lg" style={{ color: MUTED }}>→</div>
                  <div>
                    <div className="text-[11px]" style={{ color: MUTED }}>Umbral simulado ({factor}×)</div>
                    <div className="text-sm font-medium" style={{ color: factor === 1 ? BONE : BLUE }}>{impacto.hasta.valor}</div>
                  </div>
                  {cal.segmentado && (
                    <div className="text-[10px]" style={{ color: MUTED }}>valores por segmento: personal / empresa / comercio</div>
                  )}
                  {factor !== 1 && (
                    <button onClick={() => setFactorIdx(null)} className="ml-auto text-[11px]" style={{ color: MUTED }}>restablecer</button>
                  )}
                </div>
                <input type="range" min={0} max={cal.puntos.length - 1} step={1} value={idx}
                  onChange={e => setFactorIdx(Number(e.target.value))}
                  className="w-full" style={{ accentColor: "#2E6BFF" }}
                  aria-label={`Factor de calibración de ${cal.label}`} />
                <div className="flex justify-between text-[10px] mt-1" style={{ color: MUTED }}>
                  {cal.puntos.map(p => <span key={p.factor}>{p.factor}×</span>)}
                </div>
              </div>

              <CalibrationChart cal={cal} selected={factor} />

              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
                {[
                  { label: "Alertas", from: num(impacto.desde.disparos), to: num(impacto.hasta.disparos), delta: signed(impacto.dAlertas), good: impacto.dAlertas <= 0 },
                  { label: "Precisión", from: pct(impacto.desde.precision), to: pct(impacto.hasta.precision), delta: signedPct(impacto.dPrecision), good: impacto.dPrecision >= 0 },
                  { label: "Recall", from: pct(impacto.desde.recall), to: pct(impacto.hasta.recall), delta: signedPct(impacto.dRecall), good: impacto.dRecall >= 0 },
                  { label: "Falsos positivos", from: num(impacto.desde.fp), to: num(impacto.hasta.fp), delta: signed(impacto.dFalsosPositivos), good: impacto.dFalsosPositivos <= 0 },
                ].map(k => (
                  <div key={k.label} className="rounded-lg p-3" style={{ background: "#07090F", border: `1px solid ${LINE}` }}>
                    <div className="text-[11px] mb-1" style={{ color: MUTED }}>{k.label}</div>
                    <div className="text-sm" style={{ color: BONE }}>{k.from} → <b>{k.to}</b></div>
                    <div className="text-[11px] mt-0.5" style={{ color: factor === 1 ? MUTED : k.good ? GREEN : RED }}>{factor === 1 ? "sin cambios" : k.delta}</div>
                  </div>
                ))}
              </div>

              {factor !== 1 && impacto.perdidaCobertura !== 0 && (
                <div className="rounded-lg p-3 mt-3 text-[11px] leading-relaxed"
                  style={{
                    background: impacto.perdidaCobertura > 0 ? "rgba(239,68,68,0.08)" : "rgba(34,197,94,0.08)",
                    border: `1px solid ${impacto.perdidaCobertura > 0 ? "rgba(239,68,68,0.3)" : "rgba(34,197,94,0.3)"}`,
                    color: impacto.perdidaCobertura > 0 ? RED : GREEN,
                  }}>
                  {impacto.perdidaCobertura > 0
                    ? <>Este cambio dejaría <b>{num(impacto.perdidaCobertura)} casos de fraude</b> fuera del alcance de este escenario. Descargar la cola tiene un costo de cobertura que hay que asumir explícitamente ante el Comité.</>
                    : <>Este cambio sumaría <b>{num(-impacto.perdidaCobertura)} casos de fraude</b> al alcance del escenario, a costa de {signed(impacto.dFalsosPositivos)} falsos positivos.</>}
                </div>
              )}

              {/* proponer el cambio */}
              <div className="rounded-lg p-4 mt-4" style={{ background: "#07090F", border: `1px solid ${LINE}` }}>
                <h4 className="text-xs font-bold mb-2" style={{ color: BONE }}>Proponer el cambio de umbral</h4>
                {pendiente ? (
                  <p className="text-[11px]" style={{ color: AMBER }}>
                    Ya hay una propuesta pendiente para este escenario ({pendiente.valor_actual} → {pendiente.valor_propuesto}).
                    Debe resolverse antes de proponer otra.
                  </p>
                ) : !puedeProponer ? (
                  <p className="text-[11px]" style={{ color: MUTED }}>
                    Tu rol es de sólo lectura: auditoría interna revisa y cuestiona la calibración, no la modifica.
                  </p>
                ) : (
                  <div className="flex flex-wrap gap-2 items-center">
                    <select value={motivo} onChange={e => setMotivo(e.target.value)}
                      className="flex-1 min-w-[240px] rounded-lg border border-[#1E2430] bg-[#12161F] px-3 min-h-[38px] text-xs outline-none" style={{ color: BONE }}>
                      {MOTIVOS_CALIBRACION.map(m => <option key={m} value={m}>{m}</option>)}
                    </select>
                    <button onClick={proponer} disabled={factor === 1}
                      className="rounded-lg px-3 min-h-[38px] text-xs font-medium"
                      style={{
                        background: factor === 1 ? "transparent" : "rgba(46,107,255,0.12)",
                        color: factor === 1 ? MUTED : BLUE,
                        border: `1px solid ${factor === 1 ? LINE : "rgba(46,107,255,0.35)"}`,
                        cursor: factor === 1 ? "not-allowed" : "pointer",
                      }}>
                      {factor === 1 ? "Mové el umbral para proponer" : "Elevar a aprobación"}
                    </button>
                    <span className="text-[11px] w-full" style={{ color: MUTED }}>
                      El cambio queda pendiente de aprobación del Oficial de Cumplimiento y se asienta en el registro de auditoría.
                    </span>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="rounded-lg p-4 text-[11px] leading-relaxed" style={{ background: "#07090F", border: `1px solid ${LINE}`, color: MUTED }}>
              Este escenario no tiene umbral numérico que calibrar: se dispara por coincidencia contra
              listas de sanciones, y cada coincidencia se confirma o descarta a mano en el workbench de
              screening. Su tasa de descarte se gestiona ahí, no acá.
            </div>
          )}
        </div>
      )}

      {/* ── historial de cambios ──────────────────────────────────────────── */}
      {proposals.some(p => p.estado !== "pendiente") && (
        <div className="rounded-xl p-5" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
          <h2 className="text-sm font-bold mb-3" style={{ color: BONE }}>Historial de cambios de calibración</h2>
          <div className="space-y-2">
            {proposals.filter(p => p.estado !== "pendiente").map(p => (
              <div key={p.id} className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-[11px] rounded-lg p-3"
                style={{ background: "#07090F", border: `1px solid ${LINE}` }}>
                <span className="text-[10px] rounded px-1.5 py-0.5"
                  style={{ background: p.estado === "aprobada" ? "rgba(34,197,94,0.14)" : "rgba(239,68,68,0.12)", color: p.estado === "aprobada" ? GREEN : RED }}>
                  {p.estado === "aprobada" ? "Aprobado" : "Rechazado"}
                </span>
                <span className="font-mono" style={{ color: BLUE }}>{p.scenario_id}</span>
                <span style={{ color: BONE }}>{p.parametro}: {p.valor_actual} → {p.valor_propuesto}</span>
                <span style={{ color: MUTED }}>
                  propuso {p.proponente} · resolvió {p.aprobador} · {p.fecha_decision ? new Date(p.fecha_decision).toLocaleString("es-AR") : ""}
                  {p.comentario ? ` · ${p.comentario}` : ""}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
