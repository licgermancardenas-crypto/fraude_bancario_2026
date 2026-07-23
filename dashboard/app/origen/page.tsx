"use client";
import { Fragment, useState, useEffect, useRef } from "react";
import originRaw from "@/public/data/origin_trace.json";
import placementRaw from "@/public/data/placement_candidates.json";
import PageHeader from "@/components/PageHeader";

type PlacementCandidate = {
  account_id: string; placement_score: number; placement_score_norm: number;
  gnn_score: number; detected_by_gnn: boolean; is_fraud_label: boolean;
  is_known_perp: boolean; total_sent_to_fraud: number;
  n_fraud_recipients: number; n_txns: number; first_txn: string;
  nombre_completo?: string; dni?: number; ocupacion?: string;
  condicion_afip?: string; municipio?: string;
};
type PlacementData = {
  candidates: PlacementCandidate[]; n_flagged: number; n_new_discoveries: number;
  known_perpetrators: string[]; max_placement_score: number; formula: string;
};

const placement = placementRaw as PlacementData;

type RingNode = {
  node_id: string; role: string; gnn_score: number; out_degree: number; in_degree: number;
  nombre_completo?: string; ocupacion?: string; municipio?: string; condicion_afip?: string; dni?: number;
};
type RingEdge = { src: string; dst: string; amount: number; timestamp: string };
type Perpetrator = {
  node_id: string; n_mules_fed: number; amount_injected: number; gnn_score: number;
  first_transaction: string; mules: string[]; perpetrator_score: number;
  nombre_completo?: string; dni?: number; cuil?: string; ocupacion?: string;
  condicion_afip?: string; actividad_economica?: string;
  municipio?: string; provincia?: string; sucursal?: string;
};
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
  receptor_normal:   "#64748B",
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

const GRAPH_TOP_N = 15;

function RingGraphDirected() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [selected, setSelected] = useState<RingNode | null>(null);

  const topPerps = [...data.perpetrators]
    .sort((a, b) => b.amount_injected - a.amount_injected)
    .slice(0, GRAPH_TOP_N);

  useEffect(() => {
    if (!containerRef.current) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let cy: any;

    (async () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const cytoscape = (await import("cytoscape")).default as any;

      // Cap the graph to the top-N perpetrators by amount + their direct
      // mules — rendering all 1000+ nodes freezes the breadthfirst layout
      // and the result is unreadable regardless. Full detail stays in the
      // table above.
      const visibleIds = new Set<string>();
      topPerps.forEach(p => {
        visibleIds.add(p.node_id);
        p.mules.forEach(m => visibleIds.add(m));
      });
      const visibleNodes = data.ring_nodes.filter(n => visibleIds.has(n.node_id));
      const visibleEdges = data.ring_edges.filter(e => visibleIds.has(e.src) && visibleIds.has(e.dst));
      const nodeMap = new Map(visibleNodes.map(n => [n.node_id, n]));

      const elements = [
        ...visibleNodes.map(n => {
          const shortName = n.nombre_completo
            ? n.nombre_completo.split(" ").slice(0, 2).join(" ")
            : n.node_id.replace("ACC000", "#");
          return {
            data: {
              id:    n.node_id,
              label: shortName,
              color: ROLE_COLOR[n.role] ?? "#64748B",
              role:  n.role,
              score: n.gnn_score,
              size:  n.role === "perpetrador" ? 54 : n.role.startsWith("mula") ? 42 : 28,
            },
          };
        }),
        ...visibleEdges.map((e, i) => {
          const maxAmt = Math.max(...visibleEdges.map(x => x.amount), 1);
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
              "target-arrow-color": "#64748B",
              "target-arrow-shape": "triangle",
              "curve-style":        "bezier",
              opacity:              0.7,
            },
          },
          {
            selector: "node:selected",
            style: { "border-width": 4, "border-color": "#C9A227" },
          },
        ],
        // breadthfirst assumes one tree; with 15 disconnected perpetrator
        // clusters it crams everything into a single row. cose (force-
        // directed) spreads independent components across the canvas.
        layout: {
          name:            "cose",
          padding:         30,
          nodeRepulsion:   8000,
          idealEdgeLength: 60,
          animate:         false,
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
        style={{ height: 560, backgroundColor: "#F8FAFC", border: "1px solid #E2E8F0" }}
      />

      <div className="w-full lg:w-64 space-y-4">
        {/* legend */}
        <div className="rounded-xl p-4" style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0" }}>
          <p className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: "#64748B" }}>Referencias</p>
          {Object.entries(ROLE_LABEL).map(([role, label]) => (
            <div key={role} className="flex items-center gap-2 mb-2">
              <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: ROLE_COLOR[role] }} />
              <span className="text-xs" style={{ color: "#64748B" }}>{label}</span>
            </div>
          ))}
          <div className="mt-3 pt-3" style={{ borderTop: "1px solid #F1F5F9" }}>
            <p className="text-xs" style={{ color: "#64748B" }}>Grosor de arista = monto transferido</p>
          </div>
        </div>

        {/* selected node detail */}
        <div className="rounded-xl p-4" style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0" }}>
          {selected ? (
            <>
              <p className="text-xs font-semibold uppercase tracking-widest mb-1" style={{ color: "#0A1F44" }}>Nodo seleccionado</p>
              {selected.nombre_completo && (
                <div className="mb-3 pb-3" style={{ borderBottom: "1px solid #F1F5F9" }}>
                  <p className="text-sm font-bold" style={{ color: "#0F172A" }}>{selected.nombre_completo}</p>
                  {selected.dni && (
                    <p className="text-[11px] font-mono" style={{ color: "#64748B" }}>DNI {selected.dni.toLocaleString("es-AR")}</p>
                  )}
                  {selected.ocupacion && (
                    <p className="text-[11px]" style={{ color: "#64748B" }}>{selected.ocupacion}</p>
                  )}
                  {selected.municipio && (
                    <p className="text-[11px]" style={{ color: "#64748B" }}>{selected.municipio}</p>
                  )}
                </div>
              )}
              <dl className="space-y-2">
                {([
                  ["ID",            selected.node_id],
                  ["Rol",           ROLE_LABEL[selected.role] ?? selected.role],
                  ["Score GNN",     (selected.gnn_score * 100).toFixed(1) + "%"],
                  ["AFIP",          selected.condicion_afip ?? "—"],
                  ["Grado in/out",  `${selected.in_degree} / ${selected.out_degree}`],
                ] as [string, string][]).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-2">
                    <dt className="text-xs" style={{ color: "#64748B" }}>{k}</dt>
                    <dd className="font-semibold text-xs text-right" style={{ color: "#0F172A" }}>{v}</dd>
                  </div>
                ))}
              </dl>
            </>
          ) : (
            <p className="text-xs" style={{ color: "#64748B" }}>Hacé clic en un nodo para ver sus detalles.</p>
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

const PERPS_PER_PAGE = 20;

export default function OrigenPage() {
  const { summary, perpetrators } = data;
  const [expanded, setExpanded] = useState<string | null>(null);
  const [search, setSearch]     = useState("");
  const [page, setPage]         = useState(0);

  const filteredPerps = perpetrators.filter(p => {
    const q = search.toLowerCase();
    if (!q) return true;
    return (
      p.node_id.toLowerCase().includes(q) ||
      p.nombre_completo?.toLowerCase().includes(q) ||
      p.ocupacion?.toLowerCase().includes(q)
    );
  });
  const totalPages = Math.max(1, Math.ceil(filteredPerps.length / PERPS_PER_PAGE));
  const pageRows    = filteredPerps.slice(page * PERPS_PER_PAGE, (page + 1) * PERPS_PER_PAGE);

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
          { label: "Monto total",       value: fmt(summary.total_amount_laundered), sub: "en anillo completo",    color: "#0A1F44" },
        ].map(({ label, value, sub, color }) => (
          <div key={label} className="rounded-xl overflow-hidden" style={card}>
            <div className="h-1" style={{ backgroundColor: color }} />
            <div className="p-4">
              <p className="text-[11px] uppercase tracking-widest font-semibold mb-1" style={{ color: "#64748B" }}>{label}</p>
              <p className="text-2xl font-bold leading-none" style={{ color }}>{value}</p>
              <p className="text-xs mt-1" style={{ color: "#64748B" }}>{sub}</p>
            </div>
          </div>
        ))}
      </div>

      {/* perpetrators table */}
      <div>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
          <h2 className="text-base font-semibold" style={{ color: "#0F172A" }}>Cuentas Origen Identificadas</h2>
          <div className="flex items-center gap-3">
            <input
              type="text"
              placeholder="Buscar por nombre, ID u ocupación…"
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(0); }}
              className="rounded-lg px-3 py-1.5 text-sm outline-none w-64"
              style={{ backgroundColor: "#F8FAFC", border: "1px solid #E2E8F0", color: "#0F172A" }}
            />
            <span className="text-xs whitespace-nowrap" style={{ color: "#64748B" }}>
              {filteredPerps.length} de {perpetrators.length}
            </span>
          </div>
        </div>
        <div className="rounded-xl overflow-hidden" style={card}>
          <table className="w-full text-sm" style={{ backgroundColor: "#FFFFFF" }}>
            <thead>
              <tr style={{ backgroundColor: "#F8FAFC", borderBottom: "1px solid #E2E8F0" }}>
                {["Titular", "Estado en GNN", "Mulas alimentadas", "Monto inyectado", "Primera txn", ""].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: "#64748B" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pageRows.map(p => {
                const detected = p.gnn_score > 0.5;
                const isOpen   = expanded === p.node_id;
                return (
                  <Fragment key={p.node_id}>
                    <tr
                      className="transition-colors cursor-pointer"
                      style={{ borderTop: "1px solid #F1F5F9" }}
                      onClick={() => setExpanded(isOpen ? null : p.node_id)}
                      onMouseEnter={e => (e.currentTarget.style.backgroundColor = "#F8FAFC")}
                      onMouseLeave={e => (e.currentTarget.style.backgroundColor = "transparent")}
                    >
                      <td className="px-4 py-3 min-w-[180px]">
                        {p.nombre_completo ? (
                          <div>
                            <p className="text-sm font-semibold leading-tight" style={{ color: "#0F172A" }}>{p.nombre_completo}</p>
                            <p className="text-[11px] font-mono leading-tight mt-0.5" style={{ color: "#64748B" }}>
                              DNI {p.dni?.toLocaleString("es-AR")} · {p.node_id}
                            </p>
                            {p.ocupacion && (
                              <p className="text-[11px] leading-tight" style={{ color: "#64748B" }}>{p.ocupacion}</p>
                            )}
                          </div>
                        ) : (
                          <span className="font-mono text-xs font-semibold" style={{ color: "#0F172A" }}>{p.node_id}</span>
                        )}
                      </td>
                      <td className="px-4 py-3"><ScoreChip detected={detected} /></td>
                      <td className="px-4 py-3 text-center">
                        <span className="font-bold" style={{ color: "#0F172A" }}>{p.n_mules_fed}</span>
                      </td>
                      <td className="px-4 py-3 font-semibold" style={{ color: "#0A1F44" }}>{fmt(p.amount_injected)}</td>
                      <td className="px-4 py-3 text-xs font-mono" style={{ color: "#64748B" }}>{p.first_transaction}</td>
                      <td className="px-4 py-3 text-xs" style={{ color: "#64748B" }}>{isOpen ? "▲" : "▼"}</td>
                    </tr>
                    {isOpen && (
                      <tr key={`${p.node_id}-detail`}>
                        <td colSpan={6} className="px-6 py-4" style={{ backgroundColor: "#F8FAFC", borderTop: "1px solid #E2E8F0" }}>
                          {p.cuil && (
                            <div className="mb-3 grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-1 text-xs pb-3"
                                 style={{ borderBottom: "1px solid #E2E8F0" }}>
                              {([
                                ["CUIL",      p.cuil],
                                ["Ocupación", p.ocupacion ?? "—"],
                                ["AFIP",      p.condicion_afip ?? "—"],
                                ["Municipio", p.municipio ?? "—"],
                                ["Provincia", p.provincia ?? "—"],
                                ["Sucursal",  p.sucursal ?? "—"],
                              ] as [string, string][]).map(([k, v]) => (
                                <div key={k}>
                                  <span style={{ color: "#64748B" }}>{k}: </span>
                                  <span className="font-medium" style={{ color: "#0F172A" }}>{v}</span>
                                </div>
                              ))}
                            </div>
                          )}
                          <p className="text-xs uppercase tracking-wider font-semibold mb-2" style={{ color: "#64748B" }}>
                            Mulas alimentadas ({p.mules.length})
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {p.mules.map(m => {
                              const mNode = data.ring_nodes.find(n => n.node_id === m);
                              return (
                                <span
                                  key={m}
                                  className="px-2 py-1 rounded text-xs"
                                  style={{ backgroundColor: "#FEE2E2", color: "#DC2626", border: "1px solid #FECACA" }}
                                  title={m}
                                >
                                  {mNode?.nombre_completo
                                    ? mNode.nombre_completo.split(" ").slice(0, 2).join(" ")
                                    : m}
                                </span>
                              );
                            })}
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
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div className="flex items-center justify-between text-xs mt-3" style={{ color: "#64748B" }}>
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3 py-1.5 rounded-lg transition-colors disabled:opacity-30"
              style={{ border: "1px solid #E2E8F0", backgroundColor: "#FFFFFF" }}
            >
              ← Anterior
            </button>
            <span className="font-mono">{page + 1} / {totalPages}</span>
            <button
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page === totalPages - 1}
              className="px-3 py-1.5 rounded-lg transition-colors disabled:opacity-30"
              style={{ border: "1px solid #E2E8F0", backgroundColor: "#FFFFFF" }}
            >
              Siguiente →
            </button>
          </div>
        )}
      </div>

      {/* directed graph */}
      <div>
        <h2 className="text-base font-semibold mb-2" style={{ color: "#0F172A" }}>Grafo Dirigido del Anillo</h2>
        <p className="text-xs mb-4" style={{ color: "#64748B" }}>
          Las flechas indican dirección del flujo de dinero. Tamaño del nodo = relevancia en el anillo.
          Grosor de arista = monto transferido.
          Mostrando los <strong>{Math.min(GRAPH_TOP_N, perpetrators.length)} perpetradores</strong> de mayor
          monto inyectado (de {perpetrators.length} totales) y sus mulas directas —
          ver la tabla de arriba para el resto.
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
            <p className="text-xs mt-0.5" style={{ color: "#64748B" }}>
              {placement.formula}
            </p>
          </div>
          <div className="flex gap-3 text-xs flex-shrink-0">
            {[
              { label: "Candidatos", value: placement.n_flagged, color: "#0A1F44" },
              { label: "Nuevos desc.", value: placement.n_new_discoveries, color: "#DC2626" },
            ].map(({ label, value, color }) => (
              <div key={label} className="text-right">
                <p className="font-bold text-lg leading-none" style={{ color }}>{value}</p>
                <p style={{ color: "#64748B" }}>{label}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl overflow-hidden" style={card}>
          {/* legend */}
          <div className="flex flex-wrap gap-4 px-5 py-3" style={{ backgroundColor: "#F8FAFC", borderBottom: "1px solid #E2E8F0" }}>
            {[
              { color: "#F59E0B", label: "Perpetrador conocido (backward tracing)" },
              { color: "#0A1F44", label: "Detectado por GNN (mula)" },
              { color: "#DC2626", label: "Nuevo candidato" },
              { color: "#64748B", label: "Señal baja" },
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
                : c.detected_by_gnn ? "#0A1F44"
                : c.placement_score_norm > 0.15 ? "#DC2626"
                : "#64748B";
              const bgColor = c.is_known_perp ? "#FFFBEB"
                : c.detected_by_gnn ? "#EAEDF5"
                : c.placement_score_norm > 0.15 ? "#FEF2F2"
                : "transparent";

              return (
                <div
                  key={c.account_id}
                  className="flex items-center gap-4 px-5 py-3 text-sm"
                  style={{ backgroundColor: bgColor }}
                >
                  <span className="text-xs font-mono w-5 flex-shrink-0" style={{ color: "#64748B" }}>
                    {i + 1}
                  </span>
                  <div className="w-36 flex-shrink-0">
                    <p className="text-xs font-semibold leading-tight" style={{ color: "#0F172A" }}>
                      {c.nombre_completo
                        ? c.nombre_completo.split(" ").slice(0, 2).join(" ")
                        : c.account_id}
                    </p>
                    <p className="text-[10px] font-mono leading-tight" style={{ color: "#64748B" }}>{c.account_id}</p>
                  </div>
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
                  <span className="text-xs w-20 text-right font-mono" style={{ color: "#64748B" }}>
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
                          style={{ backgroundColor: "#EAEDF5", color: "#0A1F44" }}>
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
      <div className="rounded-xl p-5 text-sm" style={{ backgroundColor: "#EAEDF5", border: "1px solid #C7CFE2" }}>
        <p className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: "#0A1F44" }}>
          Insight 16 — Limitación del modelo
        </p>
        <p className="leading-relaxed" style={{ color: "#122855" }}>
          El GNN detecta la <strong style={{ color: "#0A1F44" }}>estratificación</strong> (las mulas que mueven y dispersan
          el dinero) pero no la <strong style={{ color: "#0A1F44" }}>colocación</strong> (el depósito inicial del perpetrador).
          Las cuentas origen tienen baja centralidad de red — hacen pocas transacciones de alto monto — y resultan
          invisibles para un clasificador basado en patrones de conectividad.
          El backward tracing identifica a <strong style={{ color: "#0A1F44" }}>ACC0000210</strong> y{" "}
          <strong style={{ color: "#0A1F44" }}>ACC0001046</strong> como perpetradores con score GNN ≈ 0%,
          inyectando <strong style={{ color: "#0A1F44" }}>$66,422</strong> al anillo desde cuentas aparentemente legítimas.
        </p>
        <p className="text-xs mt-3" style={{ color: "#3B82F6" }}>
          Acción sugerida: combinar el scoring GNN con backward tracing automático sobre el grafo dirigido temporal.
          Todo predecesor directo de un nodo detectado es candidato a revisión de segunda línea.
        </p>
      </div>
    </div>
  );
}
