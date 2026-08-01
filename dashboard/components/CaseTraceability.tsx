"use client";

import { useEffect, useMemo, useState } from "react";
import type { Case, TraceHop } from "@/lib/types";

/* ── palette (Phantom dark) ───────────────────────────────────────────────── */
const VOID = "#07090F", PANEL = "#12161F", LINE = "#1E2430";
const BONE = "#EDEAE6", MUTED = "#5A6478";
const PULSE = "#2E6BFF", PULSE_L = "#7AA2FF";
const DANGER = "#EF4444", AMBER = "#D97706", AMBER_L = "#F59E0B";

/* ── helpers ──────────────────────────────────────────────────────────────── */
const money = (n: number) =>
  "$" + Math.round(n).toLocaleString("es-AR");
const shortDate = (ts: number) =>
  new Date(ts * 1000).toLocaleDateString("es-AR", { day: "2-digit", month: "short", year: "2-digit" });
const nameOrId = (name: string | null | undefined, id: string) =>
  name ? name.split(" ").slice(0, 2).join(" ") : id.slice(-6);

/* a single normalised event shared by the flow diagram and the timeline */
type TEvent = {
  id: string;
  kind: "inflow" | "outflow" | "alert";
  ts: number;
  amount?: number;
  account?: string;
  name?: string | null;
  score?: number;
  isFraud?: boolean;
  isPerp?: boolean;
  dirty?: boolean;
  label: string;
};

/* ── node geometry ────────────────────────────────────────────────────────── */
const COL_W = 158, NODE_R = 19, PAD_L = 30, TOP = 34, ROW_GAP = 52;

type RailNode = { id: string; name?: string | null; score?: number; isFraud?: boolean; isPerp?: boolean };

export default function CaseTraceability({ caseData }: { caseData: Case }) {
  const trace = caseData.traceability;
  const [sel, setSel] = useState<string | null>(null);

  const up: TraceHop[] = trace?.upstream ?? [];
  const down: TraceHop[] = trace?.downstream ?? [];

  /* rail nodes: origin → … → case account (last). Each intermediate node is the
     `to` of hop i and the `from` of hop i+1, so we read its fraud/score flags
     from the next hop's `from_*` fields. The last node is the case account. */
  const rail = useMemo<RailNode[]>(() => {
    if (up.length === 0) return [{ id: caseData.account_id, name: caseData.persona?.nombre_completo }];
    return [
      { id: up[0].from, name: up[0].from_name, score: up[0].from_gnn_score, isFraud: !!up[0].from_is_fraud, isPerp: !!up[0].from_is_perp },
      ...up.map((h, i) => {
        const nxt = up[i + 1];
        return nxt
          ? { id: h.to, name: nxt.from_name, score: nxt.from_gnn_score, isFraud: !!nxt.from_is_fraud, isPerp: !!nxt.from_is_perp }
          : { id: h.to, name: caseData.persona?.nombre_completo };
      }),
    ];
  }, [up, caseData]);

  const centerIdx = rail.length - 1;
  const centerX = PAD_L + centerIdx * COL_W;
  const flowH = Math.max(200, down.length * ROW_GAP + 60);
  const rowY = flowH / 2;
  const downX = centerX + COL_W;
  const width = downX + 150;

  /* normalise all events (for timeline + selection) */
  const events: TEvent[] = useMemo(() => {
    const ev: TEvent[] = [];
    up.forEach((h, i) => ev.push({
      id: `in-${i}`, kind: "inflow", ts: h.timestamp, amount: h.amount,
      account: h.from, name: h.from_name, score: h.from_gnn_score,
      isFraud: !!h.from_is_fraud, isPerp: !!h.from_is_perp, dirty: !!h.is_fraud_edge,
      label: h.from_is_perp ? "Inyección de origen" : "Entrada de fondos",
    }));
    down.forEach((h, i) => ev.push({
      id: `out-${i}`, kind: "outflow", ts: h.timestamp, amount: h.amount,
      account: h.to, name: h.to_name, score: h.to_gnn_score,
      isFraud: !!h.to_is_fraud, dirty: !!h.is_fraud_edge,
      label: h.is_fraud_edge ? "Salida fragmentada (layering)" : "Salida",
    }));
    const alertTs = Math.floor(new Date(caseData.alert_date + "T12:00:00").getTime() / 1000);
    ev.push({ id: "alert", kind: "alert", ts: alertTs, label: "Alerta generada (GNN)" });
    return ev.sort((a, b) => a.ts - b.ts);
  }, [up, down, caseData.alert_date]);

  const selEvent = events.find(e => e.id === sel) ?? null;
  /* timeline keeps the story beats: inflows, fraudulent (layering) exits, alert —
     tiny legitimate outflows are dropped to keep the axis readable. */
  const timelineEvents = useMemo(
    () => events.filter(e => e.kind !== "outflow" || e.dirty),
    [events],
  );

  /* ── "seguir el dinero": chronological step-by-step playback ─────────────── */
  const [playing, setPlaying] = useState(false);
  const [step, setStep] = useState(-1);
  useEffect(() => {
    if (!playing) return;
    if (step >= timelineEvents.length - 1) { setPlaying(false); return; }
    const t = setTimeout(() => {
      const n = step + 1;
      setStep(n);
      setSel(timelineEvents[n].id);
    }, step < 0 ? 250 : 1700);
    return () => clearTimeout(t);
  }, [playing, step, timelineEvents]);
  const togglePlay = () => {
    if (playing) { setPlaying(false); return; }
    if (step >= timelineEvents.length - 1) setStep(-1);
    setSel(null);
    setPlaying(true);
  };

  if (!trace || (up.length === 0 && down.length === 0)) {
    return (
      <div className="rounded-lg p-6 text-sm" style={{ background: PANEL, border: `1px solid ${LINE}`, color: MUTED }}>
        No hay cadena de trazabilidad reconstruible para esta cuenta (sin flujos fraudulentos vinculados).
      </div>
    );
  }

  /* colour of a rail/exit node */
  const nodeFill = (n: { isPerp?: boolean; isFraud?: boolean }, isCenter: boolean) =>
    isCenter ? VOID : n.isPerp ? AMBER : n.isFraud ? DANGER : MUTED;
  const nodeStroke = (n: { isPerp?: boolean; isFraud?: boolean }, isCenter: boolean) =>
    isCenter ? PULSE : n.isPerp ? AMBER_L : n.isFraud ? "#F87171" : LINE;

  const dim = (id: string) => (sel && sel !== id ? 0.35 : 1);

  return (
    <div className="space-y-4">
      {/* ── flow diagram ─────────────────────────────────────────────────── */}
      <div className="rounded-lg p-3" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
        <div className="mb-2 flex items-center justify-between gap-2">
          <h3 className="text-sm font-bold" style={{ color: BONE }}>Flujo del dinero</h3>
          <div className="flex items-center gap-2">
            <span className="hidden text-[11px] sm:inline" style={{ color: MUTED }}>origen → cuenta → destino</span>
            <button onClick={togglePlay}
              className="rounded-md px-3 py-1 text-[11px] font-semibold transition-colors"
              style={{
                background: playing ? "rgba(217,119,6,0.15)" : "rgba(46,107,255,0.15)",
                color: playing ? AMBER_L : PULSE_L,
                border: `1px solid ${playing ? AMBER : PULSE}`,
              }}>
              {playing ? "⏸ Pausar" : step >= timelineEvents.length - 1 && step >= 0 ? "↻ Repetir" : "▶ Seguir el dinero"}
            </button>
          </div>
        </div>
        <div style={{ overflowX: "auto" }}>
          <svg width={width} height={flowH} style={{ display: "block", minWidth: "100%" }}>
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path d="M0,0 L10,5 L0,10 z" fill={MUTED} />
              </marker>
              <marker id="arrowHot" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path d="M0,0 L10,5 L0,10 z" fill={DANGER} />
              </marker>
            </defs>

            {/* upstream edges (between consecutive rail nodes) */}
            {up.map((h, i) => {
              const x1 = PAD_L + i * COL_W, x2 = PAD_L + (i + 1) * COL_W;
              const id = `in-${i}`, hot = h.is_fraud_edge === 1, active = sel === id;
              const d = `M ${x1 + NODE_R} ${rowY} L ${x2 - NODE_R} ${rowY}`;
              return (
                <g key={id} opacity={dim(id)} style={{ cursor: "pointer" }} onClick={() => setSel(active ? null : id)}>
                  <path d={d} fill="none" stroke={active ? DANGER : hot ? "#7F1D1D" : MUTED} strokeWidth={active ? 3 : 2}
                    markerEnd={`url(#${hot ? "arrowHot" : "arrow"})`} />
                  <text x={(x1 + x2) / 2} y={rowY - 9} textAnchor="middle" fontSize={10} fontWeight={700}
                    fill={hot ? "#F87171" : MUTED}>{money(h.amount)}</text>
                  {active && <MoneyPulse d={d} />}
                </g>
              );
            })}

            {/* downstream edges (center → exits) */}
            {down.map((h, i) => {
              const y2 = TOP + i * ROW_GAP + 20;
              const id = `out-${i}`, hot = h.is_fraud_edge === 1, active = sel === id;
              const mx = (centerX + downX) / 2;
              const path = `M ${centerX + NODE_R} ${rowY} C ${mx} ${rowY}, ${mx} ${y2}, ${downX - NODE_R} ${y2}`;
              return (
                <g key={id} opacity={dim(id)} style={{ cursor: "pointer" }} onClick={() => setSel(active ? null : id)}>
                  <path d={path} fill="none" stroke={active ? DANGER : hot ? "#7F1D1D" : LINE}
                    strokeWidth={active ? 3 : 2} markerEnd={`url(#${hot ? "arrowHot" : "arrow"})`} />
                  <text x={mx} y={(rowY + y2) / 2 - 4} textAnchor="middle" fontSize={9} fontWeight={700}
                    fill={hot ? "#F87171" : MUTED}>{money(h.amount)}</text>
                  {active && <MoneyPulse d={path} />}
                </g>
              );
            })}

            {/* rail nodes */}
            {rail.map((n, i) => {
              const x = PAD_L + i * COL_W, isCenter = i === centerIdx;
              const evId = i === 0 && up.length ? "in-0" : isCenter ? "center" : `in-${i - 1}`;
              return (
                <g key={n.id} opacity={dim(evId)} style={{ cursor: "pointer" }}
                   onClick={() => setSel(sel === evId ? null : (evId === "center" ? null : evId))}>
                  <circle cx={x} cy={rowY} r={isCenter ? NODE_R + 3 : NODE_R}
                    fill={nodeFill(n, isCenter)} stroke={nodeStroke(n, isCenter)} strokeWidth={isCenter ? 3 : 2} />
                  {n.isPerp && (
                    <text x={x} y={rowY + 3} textAnchor="middle" fontSize={13}>🎭</text>
                  )}
                  <text x={x} y={rowY + NODE_R + 14} textAnchor="middle" fontSize={10} fontWeight={isCenter ? 700 : 600}
                    fill={isCenter ? PULSE_L : BONE}>{nameOrId(n.name, n.id)}</text>
                  <text x={x} y={rowY + NODE_R + 26} textAnchor="middle" fontSize={8} fill={MUTED}>
                    {isCenter ? "CUENTA DEL CASO" : n.isPerp ? "perpetrador" : n.isFraud ? "mula" : n.id.slice(-6)}
                  </text>
                </g>
              );
            })}

            {/* exit nodes */}
            {down.map((h, i) => {
              const y = TOP + i * ROW_GAP + 20, id = `out-${i}`;
              return (
                <g key={id} opacity={dim(id)} style={{ cursor: "pointer" }} onClick={() => setSel(sel === id ? null : id)}>
                  <circle cx={downX} cy={y} r={14} fill={h.to_is_fraud ? DANGER : MUTED}
                    stroke={sel === id ? DANGER : LINE} strokeWidth={sel === id ? 3 : 1.5} />
                  <text x={downX + 22} y={y - 2} fontSize={10} fontWeight={600} fill={BONE}>{nameOrId(h.to_name, h.to)}</text>
                  <text x={downX + 22} y={y + 9} fontSize={8} fill={MUTED}>{h.to.slice(-6)} · {money(h.amount)}</text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* legend */}
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[10px]" style={{ color: MUTED }}>
          <Legend color={AMBER} label="Perpetrador de origen (invisible al GNN)" />
          <Legend color={DANGER} label="Cuenta fraude / mula" />
          <Legend color={VOID} ring={PULSE} label="Cuenta del caso" />
          <Legend color={MUTED} label="Contraparte legítima aparente" />
          <span>— arista roja = transacción fraudulenta</span>
        </div>
      </div>

      {/* ── timeline ─────────────────────────────────────────────────────── */}
      <div className="rounded-lg p-3" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
        <h3 className="mb-3 text-sm font-bold" style={{ color: BONE }}>Línea de tiempo del caso</h3>
        <div style={{ overflowX: "auto" }}>
          <div className="relative flex items-start" style={{ minWidth: timelineEvents.length * 88, paddingTop: 4 }}>
            {/* baseline */}
            <div className="absolute" style={{ top: 10, left: 20, right: 20, height: 2, background: LINE }} />
            {timelineEvents.map((e) => {
              const active = sel === e.id;
              const c = e.kind === "alert" ? PULSE : e.isPerp ? AMBER : e.dirty ? DANGER : MUTED;
              return (
                <button key={e.id} onClick={() => setSel(active ? null : e.id)}
                  className="relative z-10 flex flex-col items-center text-center"
                  style={{ width: 88, cursor: "pointer" }}>
                  <span style={{
                    width: active ? 16 : 12, height: active ? 16 : 12, borderRadius: "50%",
                    background: c, boxShadow: active ? `0 0 0 4px ${c}33` : "none",
                    border: e.kind === "alert" ? `2px solid ${PULSE_L}` : "none", transition: "all .15s",
                  }} />
                  <span className="mt-1 text-[9px]" style={{ color: MUTED }}>{shortDate(e.ts)}</span>
                  <span className="mt-0.5 text-[10px] font-semibold leading-tight" style={{ color: active ? BONE : "#8A93A6" }}>
                    {e.kind === "alert" ? "🚨 Alerta" : e.amount ? money(e.amount) : e.label}
                  </span>
                  {e.kind !== "alert" && (
                    <span className="text-[8px] leading-tight" style={{ color: MUTED }}>
                      {e.kind === "inflow" ? "↓ " : "↑ "}{nameOrId(e.name, e.account!)}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── detail of selected event ─────────────────────────────────────── */}
      {selEvent && selEvent.kind !== "alert" && (
        <div className="rounded-lg p-4" style={{ background: VOID, border: `1px solid ${selEvent.dirty ? "#7F1D1D" : LINE}` }}>
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-bold" style={{ color: BONE }}>
              {selEvent.isPerp ? "🎭 " : ""}{selEvent.label}
            </h4>
            <button onClick={() => setSel(null)} className="text-[11px]" style={{ color: MUTED }}>cerrar ✕</button>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 text-xs sm:grid-cols-4">
            <Field label="Contraparte" value={nameOrId(selEvent.name, selEvent.account!)} />
            <Field label="Cuenta" value={selEvent.account!} mono />
            <Field label="Monto" value={money(selEvent.amount!)} strong />
            <Field label="Fecha" value={shortDate(selEvent.ts)} />
            <Field label="Score GNN" value={((selEvent.score ?? 0) * 100).toFixed(1) + "%"} />
            <Field label="Etiqueta" value={selEvent.isFraud ? "Fraude" : "Legítima"} color={selEvent.isFraud ? DANGER : MUTED} />
            <Field label="Transacción" value={selEvent.dirty ? "Fraudulenta" : "Normal"} color={selEvent.dirty ? DANGER : MUTED} />
            {selEvent.isPerp && <Field label="Rol" value="Perpetrador de origen" color={AMBER_L} />}
          </div>
          {selEvent.isPerp && (
            <p className="mt-3 text-[11px] leading-relaxed" style={{ color: MUTED }}>
              Inyector de fondos rastreado por <em>backward tracing</em>: score GNN ≈ {((selEvent.score ?? 0) * 100).toFixed(1)}%
              (invisible para el clasificador de nodos), pero alimenta la cadena de lavado. El rastreo aguas arriba lo
              prioriza sin necesidad de etiquetas adicionales.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/* a gold dot travelling along an edge path — the "money in motion" cue */
function MoneyPulse({ d }: { d: string }) {
  return (
    <circle r={5} fill={AMBER_L} stroke="#FDE68A" strokeWidth={1} style={{ filter: "drop-shadow(0 0 3px #F59E0B)" }}>
      <animateMotion dur="1.15s" repeatCount="indefinite" path={d} />
    </circle>
  );
}

function Legend({ color, ring, label }: { color: string; ring?: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span style={{ width: 10, height: 10, borderRadius: "50%", background: color, border: ring ? `2px solid ${ring}` : "none", display: "inline-block" }} />
      {label}
    </span>
  );
}

function Field({ label, value, mono, strong, color }: { label: string; value: string; mono?: boolean; strong?: boolean; color?: string }) {
  return (
    <div>
      <div className="text-[9px] uppercase tracking-wide" style={{ color: MUTED }}>{label}</div>
      <div className={mono ? "font-mono" : ""} style={{ color: color ?? BONE, fontWeight: strong ? 700 : 500, fontSize: mono ? 11 : 12 }}>{value}</div>
    </div>
  );
}
