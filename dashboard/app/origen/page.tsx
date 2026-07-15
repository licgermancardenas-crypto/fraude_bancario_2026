"use client";
import { useState, useEffect, useRef } from "react";
import originRaw from "@/public/data/origin_trace.json";
import placementRaw from "@/public/data/placement_candidates.json";
import PageHeader from "@/components/PageHeader";

type PlacementCandidate = {
  account_id: string; placement_score: number; placement_score_norm: number;
  gnn_score: number; detected_by_gnn: boolean; is_fraud_label: boolean;
  is_known_perp: boolean; total_sent_to_fraud: number;
  n_fraud_recipients: number; n_txns: number; first_txn: string;
};
type PlacementData = {
  candidates: PlacementCandidate[]; n_flagged: number; n_new_discoveries: number;
  known_perpetrators: string[]; max_placement_score: number; formula: string;
};

const placement = placementRaw as PlacementData;

type RingNode = { node_id: string; role: string; gnn_score: number; out_degree: number; in_degree: number };
type RingEdge = { src: string; dst: string; amount: number; timestamp: string };
type Perpetrator = { node_id: string; n_mules_fed: number; amount_injected: number; gnn_score: number; first_transaction: string; mules: string[]; perpetrator_score: number };
type Summary = { n_perpetrators: number; n_mules_detected: number; n_mules_missed: number; total_amount_laundered: number };

const data = originRaw as {
  perpetrators: Perpetrator[];
  ring_nodes: RingNode[];
  ring_edges: RingEdge[];
  summary: Summary;
};

const ROLE_COLOR: Record<string, string> = {
  perpetrador:       "#F59E0B",
  mula_detectada:    "#DC2626",
  mula_no_detectada: "#7C3AED",
  receptor_normal:   "#94A3B8",
};
const ROLE_LABEL: Record<string, string> = {
  perpetrador:       "Perpetrador",
  mula_detectada:    "Mula detectada",
  mula_no_detectada: "Mula no detectada",
  receptor_normal:   "Receptor legítimo",
};

function fmt(n: number) {
  return "$" + n.toLocaleString("es-AR", { maximumFractionDigits: 0 });
}

function ScoreChip({ detected }: { detected: boolean }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold"
      style={detected
        ? { backgroundColor: "#DCFCE7", color: "#16A34A" }
        : { backgroundColor: "#FEE2E2", color: "#DC2626" }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: detected ? "#16A34A" : "#DC2626" }} />
      {detected ? "Detectado" : "No detectado"}
    </span>
  );
}

function RingGraphDirected() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [selected, setSelected] = useState<RingNode | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let cy: any;

    (async () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const cytoscape = (await import("cytoscape")).default as any;
      const nodeMap = new Map(data.ring_nodes.map(n => [n.node_id, n]));

      const elements = [
        ...data.ring_nodes.map(n => ({
          data: {
            id:    n.node_id,
            label: n.node_id.replace("ACC000", "#"),
            color: ROLE_COLOR[n.role] ?? "#94A3B8",
            role:  n.role,
            score: n.gnn_score,
            size:  n.role === "perpetrador" ? 54 : n.role.startsWith("mula") ? 42 : 28,
          },
        })),
        ...data.ring_edges.map((e, i) => {
          const maxAmt = Math.max(...data.ring_edges.map(x => x.amount));
          const w = 1 + 4 * (e.amount / maxAmt);
          return { data: { id: `e${i}`, source: e.src, target: e.dst, amount: e.amount, width: w } };
        }),
      ];

      cy = cytoscape({
        container: containerRef.current,
        elements,
        style: [
          {
            selector: "node",
            style: {
              "background-color": "data(color)",
              "border-color":     "#FFFFFF",
              "border-width":     2,
              label:              "data(label)",
              color:              "#1E293B",
              "font-size":        "9px",
              "font-weight":      "600",
              "text-valign":      "bottom",
              "text-margin-y":    4,
              width:              "data(size)",
              height:             "data(size)",
            },
          },
          {
            selector: "node[role='perpetrador']",
            style: { "border-width": 3, "border-color": "#F59E0B", "font-size": "10px" },
          },
          {
            selector: "edge",
            style: {
              width:                "data(width)",
              "line-color":         "#CBD5E1",
              "target-arrow-color": "#94A3B8",
              "target-arrow-shape": "triangle",
              "curve-style":        "bezier",
              opacity:              0.7,
            },
          },
          {
            selector: "node:selected",
            style: { "border-width": 4, "border-color": "#2563EB" },
          },
        ],
        layout: {
          name:          "breadthfirst",
          roots:         data.perpetrators.map(p => p.node_id),
          directed:      true,
          padding:       30,
          spacingFactor: 1.4,
        },
        userZoomingEnabled: true,
        userPanningEnabled: true,
      });

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      cy.on("tap", "node", (evt: any) => {
        setSelected(nodeMap.get(evt.target.id()) ?? null);
      });
    })();

    return () => { cy?.destroy?.(); };
  }, []);

  return (
    <div className="flex gap-4 flex-col lg:flex-row">
      <div
        ref={containerRef}
        className="rounded-xl flex-1"
        style={{ height: 440, backgroundColor: "#F8FAFC", border: "1px solid #E2E8F0" }}
      />

      <div className="w-full lg:w-64 space-y-4">
        {/* legend */}
        <div className="rounded-xl p-4" style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0" }}>
          <p className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: "#94A3B8" }}>Referencias</p>
          {Object.entries(ROLE_LABEL).map(([role, label]) => (
            <div key={role} className="flex items-center gap-2 mb-2">
              <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: ROLE_COLOR[role] }} />
              <span className="text-xs" style={{ color: "#64748B" }}>{label}</span>
            </div>
          ))}
          <div className="mt-3 pt-3" style={{ borderTop: "1px solid #F1F5F9" }}>
            <p className="text-xs" style={{ color: "#94A3B8" }}>Grosor de arista = monto transferido</p>
          </div>
        </div>

        {/* selected node detail */}
        <div className="rounded-xl p-4" style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0" }}>
          {selected ? (
            <>
              <p className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: "#2563EB" }}>Nodo seleccionado</p>
              <dl className="space-y-2 text-sm">
                {([
                  ["ID",        selected.node_id],
                  ["Rol",       ROLE_LABEL[selected.role] ?? selected.role],
                  ["Score GNN", (selected.gnn_score * 100).toFixed(1) + "%"],
                  ["Grado in",  String(selected.in_degree)],
                  ["Grado out", String(selected.out_degree)],
                ] as [string, string][]).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-2">
                    <dt className="text-xs" style={{ color: "#94A3B8" }}>{k}</dt>
                    <dd className="font-semibold text-xs" style={{ color: "#0F172A" }}>{v}</dd>
                  </div>
                ))}
              </dl>
            </>
          ) : (
            <p className="text-xs" style={{ color: "#94A3B8" }}>Hacé clic en un nodo para ver sus detalles.</p>
          )}
        </div>
      </div>
    </div>
  );
}

const card = {
  backgroundColor: "#FFFFFF",
  border: "1px solid #E2E8F0",
  boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
};

export default function OrigenPage() {
  const { summary, perpetrators } = data;
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Rastreo de origen"
        title="Perpetradores del Anillo"
        description="El GNN detecta las cuentas mula (alta centralidad, flujo anómalo). Este módulo traza hacia atrás en el grafo dirigido para identificar las cuentas que inyectaron el dinero — los perpetradores originales."
      />

      {/* KPI row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Perpetradores",     value: String(summary.n_perpetrators),      sub: "raíces del anillo",     color: "#F59E0B" },
          { label: "Mulas detectadas",  value: String(summary.n_mules_detected),    sub: "score GNN > 0.5",       color: "#DC2626" },
          { label: "Mulas no detect.",  value: String(summary.n_mules_missed),      sub: "en cadena fraude",      color: "#7C3AED" },
          { label: "Monto total",       value: fmt(summary.total_amount_laundered), sub: "en anillo completo",    color: "#2563EB" },
        ].map(({ label, value, sub, color }) => (
          <div key={label} className="rounded-xl overflow-hidden" style={card}>
            <div className="h-1" style={{ backgroundColor: color }} />
            <div className="p-4">
              <p className="text-[11px] uppercase tracking-widest font-semibold mb-1" style={{ color: "#94A3B8" }}>{label}</p>
              <p className="text-2xl font-bold leading-none" style={{ color }}>{value}</p>
              <p className="text-xs mt-1" style={{ color: "#94A3B8" }}>{sub}</p>
            </div>
          </div>
        ))}
      </div>

      {/* perpetrators table */}
      <div>
        <h2 className="text-base font-semibold mb-3" style={{ color: "#0F172A" }}>Cuentas Origen Identificadas</h2>
        <div className="rounded-xl overflow-hidden" style={card}>
          <table className="w-full text-sm" style={{ backgroundColor: "#FFFFFF" }}>
            <thead>
              <tr style={{ backgroundColor: "#F8FAFC", borderBottom: "1px solid #E2E8F0" }}>
                {["Cuenta", "Estado en GNN", "Mulas alimentadas", "Monto inyectado", "Primera txn", ""].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: "#94A3B8" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {perpetrators.map(p => {
                const detected = p.gnn_score > 0.5;
                const isOpen   = expanded === p.node_id;
                return (
                  <>
                    <tr
                      key={p.node_id}
                      className="transition-colors cursor-pointer"
                      style={{ borderTop: "1px solid #F1F5F9" }}
                      onClick={() => setExpanded(isOpen ? null : p.node_id)}
                      onMouseEnter={e => (e.currentTarget.style.backgroundColor = "#F8FAFC")}
                      onMouseLeave={e => (e.currentTarget.style.backgroundColor = "transparent")}
                    >
                      <td className="px-4 py-3 font-mono text-xs font-semibold" style={{ color: "#0F172A" }}>{p.node_id}</td>
                      <td className="px-4 py-3"><ScoreChip detected={detected} /></td>
                      <td className="px-4 py-3 text-center">
                        <span className="font-bold" style={{ color: "#0F172A" }}>{p.n_mules_fed}</span>
                      </td>
                      <td className="px-4 py-3 font-semibold" style={{ color: "#2563EB" }}>{fmt(p.amount_injected)}</td>
                      <td className="px-4 py-3 text-xs font-mono" style={{ color: "#64748B" }}>{p.first_transaction}</td>
                      <td className="px-4 py-3 text-xs" style={{ color: "#94A3B8" }}>{isOpen ? "▲" : "▼"}</td>
                    </tr>
                    {isOpen && (
                      <tr key={`${p.node_id}-detail`}>
                        <td colSpan={6} className="px-6 py-4" style={{ backgroundColor: "#F8FAFC", borderTop: "1px solid #E2E8F0" }}>
                          <p className="text-xs uppercase tracking-wider font-semibold mb-2" style={{ color: "#94A3B8" }}>Mulas alimentadas</p>
                          <div className="flex flex-wrap gap-2">
                            {p.mules.map(m => (
                              <span
                                key={m}
                                className="px-2 py-1 rounded text-xs font-mono"
                                style={{ backgroundColor: "#FEE2E2", color: "#DC2626", border: "1px solid #FECACA" }}
                              >
                                {m}
                              </span>
                            ))}
                          </div>
                          {!detected && (
                            <p className="mt-3 text-xs flex items-center gap-1.5" style={{ color: "#D97706" }}>
                              <span>⚠</span>
                              Esta cuenta no fue detectada por el GNN (score = {(p.gnn_score * 100).toFixed(2)}%).
                              Baja centralidad de red: realizó pocas transacciones pero de alto monto.
                            </p>
                          )}
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* directed graph */}
      <div>
        <h2 className="text-base font-semibold mb-2" style={{ color: "#0F172A" }}>Grafo Dirigido del Anillo</h2>
        <p className="text-xs mb-4" style={{ color: "#94A3B8" }}>
          Las flechas indican dirección del flujo de dinero. Tamaño del nodo = relevancia en el anillo.
          Grosor de arista = monto transferido.
        </p>
        <RingGraphDirected />
      </div>

      {/* placement scoring section */}
      <div>
        <div className="flex items-end justify-between mb-3">
          <div>
            <h2 className="text-base font-semibold" style={{ color: "#0F172A" }}>
              Ranking de Colocación — Propagación Inversa de Riesgo
            </h2>
            <p className="text-xs mt-0.5" style={{ color: "#94A3B8" }}>
              {placement.formula}
            </p>
          </div>
          <div className="flex gap-3 text-xs flex-shrink-0">
            {[
              { label: "Candidatos", value: placement.n_flagged, color: "#2563EB" },
              { label: "Nuevos desc.", value: placement.n_new_discoveries, color: "#DC2626" },
            ].map(({ label, value, color }) => (
              <div key={label} className="text-right">
                <p className="font-bold text-lg leading-none" style={{ color }}>{value}</p>
                <p style={{ color: "#94A3B8" }}>{label}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl overflow-hidden" style={card}>
          {/* legend */}
          <div className="flex flex-wrap gap-4 px-5 py-3" style={{ backgroundColor: "#F8FAFC", borderBottom: "1px solid #E2E8F0" }}>
            {[
              { color: "#F59E0B", label: "Perpetrador conocido (backward tracing)" },
              { color: "#2563EB", label: "Detectado por GNN (mula)" },
              { color: "#DC2626", label: "Nuevo candidato" },
              { color: "#94A3B8", label: "Señal baja" },
            ].map(({ color, label }) => (
              <div key={label} className="flex items-center gap-1.5 text-xs" style={{ color: "#64748B" }}>
                <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: color }} />
                {label}
              </div>
            ))}
          </div>

          {/* top 15 rows */}
          <div className="divide-y" style={{ borderColor: "#F1F5F9" }}>
            {placement.candidates.slice(0, 15).map((c, i) => {
              const barColor = c.is_known_perp ? "#F59E0B"
                : c.detected_by_gnn ? "#2563EB"
                : c.placement_score_norm > 0.15 ? "#DC2626"
                : "#94A3B8";
              const bgColor = c.is_known_perp ? "#FFFBEB"
                : c.detected_by_gnn ? "#EFF6FF"
                : c.placement_score_norm > 0.15 ? "#FEF2F2"
                : "transparent";

              return (
                <div
                  key={c.account_id}
                  className="flex items-center gap-4 px-5 py-3 text-sm"
                  style={{ backgroundColor: bgColor }}
                >
                  <span className="text-xs font-mono w-5 flex-shrink-0" style={{ color: "#CBD5E1" }}>
                    {i + 1}
                  </span>
                  <span className="font-mono text-xs font-semibold w-28 flex-shrink-0" style={{ color: "#0F172A" }}>
                    {c.account_id}
                  </span>
                  {/* score bar */}
                  <div className="flex-1 flex items-center gap-2">
                    <div className="flex-1 h-2 rounded-full" style={{ backgroundColor: "#E2E8F0" }}>
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${c.placement_score_norm * 100}%`, backgroundColor: barColor }}
                      />
                    </div>
                    <span className="text-xs font-mono w-10 text-right" style={{ color: barColor }}>
                      {(c.placement_score_norm * 100).toFixed(1)}%
                    </span>
                  </div>
                  <span className="text-xs w-16 text-right font-mono" style={{ color: "#64748B" }}>
                    GNN {(c.gnn_score * 100).toFixed(1)}%
                  </span>
                  <span className="text-xs w-20 text-right font-mono" style={{ color: "#94A3B8" }}>
                    ${c.total_sent_to_fraud.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                  </span>
                  {c.is_known_perp && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0"
                          style={{ backgroundColor: "#FEF3C7", color: "#D97706" }}>
                      PERP
                    </span>
                  )}
                  {!c.detected_by_gnn && !c.is_known_perp && c.placement_score_norm > 0.15 && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0"
                          style={{ backgroundColor: "#FEE2E2", color: "#DC2626" }}>
                      NUEVO
                    </span>
                  )}
                  {c.detected_by_gnn && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0"
                          style={{ backgroundColor: "#EFF6FF", color: "#2563EB" }}>
                      MULA
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* insight box */}
      <div className="rounded-xl p-5 text-sm" style={{ backgroundColor: "#EFF6FF", border: "1px solid #BFDBFE" }}>
        <p className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: "#1E3A8A" }}>
          Insight 16 — Limitación del modelo
        </p>
        <p className="leading-relaxed" style={{ color: "#1D4ED8" }}>
          El GNN detecta la <strong style={{ color: "#1E3A8A" }}>estratificación</strong> (las mulas que mueven y dispersan
          el dinero) pero no la <strong style={{ color: "#1E3A8A" }}>colocación</strong> (el depósito inicial del perpetrador).
          Las cuentas origen tienen baja centralidad de red — hacen pocas transacciones de alto monto — y resultan
          invisibles para un clasificador basado en patrones de conectividad.
          El backward tracing identifica a <strong style={{ color: "#1E3A8A" }}>ACC0000210</strong> y{" "}
          <strong style={{ color: "#1E3A8A" }}>ACC0001046</strong> como perpetradores con score GNN ≈ 0%,
          inyectando <strong style={{ color: "#1E3A8A" }}>$66,422</strong> al anillo desde cuentas aparentemente legítimas.
        </p>
        <p className="text-xs mt-3" style={{ color: "#3B82F6" }}>
          Acción sugerida: combinar el scoring GNN con backward tracing automático sobre el grafo dirigido temporal.
          Todo predecesor directo de un nodo detectado es candidato a revisión de segunda línea.
        </p>
      </div>
    </div>
  );
}
