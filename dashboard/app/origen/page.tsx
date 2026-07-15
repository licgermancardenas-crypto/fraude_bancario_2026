"use client";
import { useState, useEffect, useRef } from "react";
import originRaw from "@/public/data/origin_trace.json";
import PageHeader from "@/components/PageHeader";

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
  perpetrador:       "#E67E22",
  mula_detectada:    "#C0392B",
  mula_no_detectada: "#8E44AD",
  receptor_normal:   "#4A5568",
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

function ScoreChip({ score, detected }: { score: number; detected: boolean }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold"
      style={{ backgroundColor: detected ? "#C0392B22" : "#27AE6022", color: detected ? "#E57373" : "#66BB6A" }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: detected ? "#E57373" : "#66BB6A" }} />
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
            color: ROLE_COLOR[n.role] ?? "#4A5568",
            role:  n.role,
            score: n.gnn_score,
            size:  n.role === "perpetrador" ? 54 : n.role.startsWith("mula") ? 42 : 28,
          },
        })),
        ...data.ring_edges.map((e, i) => {
          const maxAmt = Math.max(...data.ring_edges.map(x => x.amount));
          const w = 1 + 4 * (e.amount / maxAmt);
          return {
            data: { id: `e${i}`, source: e.src, target: e.dst, amount: e.amount, width: w },
          };
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
              "border-color":     "#C9A227",
              "border-width":     1.5,
              label:              "data(label)",
              color:              "#fff",
              "font-size":        "9px",
              "font-weight":      "bold",
              "text-valign":      "center",
              width:              "data(size)",
              height:             "data(size)",
            },
          },
          {
            selector: "node[role='perpetrador']",
            style: {
              "border-width":  3,
              "border-color":  "#E67E22",
              "font-size":     "10px",
            },
          },
          {
            selector: "edge",
            style: {
              width:                "data(width)",
              "line-color":         "#C9A22755",
              "target-arrow-color": "#C9A227",
              "target-arrow-shape": "triangle",
              "curve-style":        "bezier",
              opacity:              0.8,
            },
          },
          {
            selector: "node:selected",
            style: { "border-width": 4, "border-color": "#fff" },
          },
        ],
        layout: {
          name:    "breadthfirst",
          roots:   data.perpetrators.map(p => p.node_id),
          directed: true,
          padding:  30,
          spacingFactor: 1.4,
        },
        userZoomingEnabled: true,
        userPanningEnabled: true,
      });

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      cy.on("tap", "node", (evt: any) => {
        const id   = evt.target.id();
        const node = nodeMap.get(id) ?? null;
        setSelected(node);
      });
    })();

    return () => { cy?.destroy?.(); };
  }, []);

  return (
    <div className="flex gap-4 flex-col lg:flex-row">
      <div ref={containerRef}
           className="rounded-xl border border-white/8 flex-1"
           style={{ height: 440, backgroundColor: "#0a1225" }} />

      <div className="w-full lg:w-64 space-y-4">
        {/* legend */}
        <div className="rounded-xl border border-white/8 p-4" style={{ backgroundColor: "#0d1e38" }}>
          <p className="text-xs font-semibold uppercase tracking-widest text-white/40 mb-3">Referencias</p>
          {Object.entries(ROLE_LABEL).map(([role, label]) => (
            <div key={role} className="flex items-center gap-2 mb-2">
              <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: ROLE_COLOR[role] }} />
              <span className="text-xs text-white/60">{label}</span>
            </div>
          ))}
          <div className="mt-3 pt-3 border-t border-white/8">
            <p className="text-xs text-white/40">Grosor de arista = monto transferido</p>
          </div>
        </div>

        {/* selected node detail */}
        <div className="rounded-xl border border-white/8 p-4" style={{ backgroundColor: "#0d1e38" }}>
          {selected ? (
            <>
              <p className="text-xs font-semibold uppercase tracking-widest text-[#C9A227] mb-3">Nodo seleccionado</p>
              <dl className="space-y-2 text-sm">
                {([
                  ["ID",        selected.node_id],
                  ["Rol",       ROLE_LABEL[selected.role] ?? selected.role],
                  ["Score GNN", (selected.gnn_score * 100).toFixed(1) + "%"],
                  ["Grado in",  String(selected.in_degree)],
                  ["Grado out", String(selected.out_degree)],
                ] as [string, string][]).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-2">
                    <dt className="text-white/50">{k}</dt>
                    <dd className="font-medium text-white text-xs">{v}</dd>
                  </div>
                ))}
              </dl>
            </>
          ) : (
            <p className="text-white/40 text-xs">Hacé clic en un nodo para ver sus detalles.</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function OrigenPage() {
  const { summary, perpetrators } = data;
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Rastreo de origen"
        title="Perpetradores del Anillo"
        description="El GNN detecta las cuentas mula (alta centralidad, flujo anómalo). Este módulo traza hacia atrás en el grafo dirigido de transacciones para identificar las cuentas que inyectaron el dinero al anillo — los perpetradores originales."
      />

      {/* KPI row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Perpetradores",     value: String(summary.n_perpetrators),   sub: "raíces del anillo",          color: "#E67E22" },
          { label: "Mulas detectadas",  value: String(summary.n_mules_detected), sub: "score GNN > 0.5",            color: "#C0392B" },
          { label: "Mulas no detect.",  value: String(summary.n_mules_missed),   sub: "en cadena fraude",           color: "#8E44AD" },
          { label: "Monto total",       value: fmt(summary.total_amount_laundered), sub: "en anillo completo",      color: "#C9A227" },
        ].map(({ label, value, sub, color }) => (
          <div key={label} className="rounded-xl border border-white/8 p-4" style={{ backgroundColor: "#0d1e38" }}>
            <p className="text-xs text-white/40 uppercase tracking-wider mb-1">{label}</p>
            <p className="text-2xl font-bold" style={{ color }}>{value}</p>
            <p className="text-xs text-white/40 mt-0.5">{sub}</p>
          </div>
        ))}
      </div>

      {/* perpetrators table */}
      <div>
        <h2 className="text-base font-semibold text-white mb-3">Cuentas Origen Identificadas</h2>
        <div className="rounded-xl border border-white/8 overflow-hidden" style={{ backgroundColor: "#0d1e38" }}>
          <table className="w-full text-sm">
            <thead style={{ backgroundColor: "#0a1225" }}>
              <tr>
                {["Cuenta", "Estado en GNN", "Mulas alimentadas", "Monto inyectado", "Primera txn", ""].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white/60">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {perpetrators.map(p => {
                const detected = p.gnn_score > 0.5;
                const isOpen   = expanded === p.node_id;
                return (
                  <>
                    <tr key={p.node_id}
                        className="border-t border-white/5 hover:bg-white/5 transition-colors cursor-pointer"
                        onClick={() => setExpanded(isOpen ? null : p.node_id)}>
                      <td className="px-4 py-3 font-mono text-xs text-white/80 font-semibold">{p.node_id}</td>
                      <td className="px-4 py-3">
                        <ScoreChip score={p.gnn_score} detected={detected} />
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="font-bold text-white">{p.n_mules_fed}</span>
                      </td>
                      <td className="px-4 py-3 font-semibold" style={{ color: "#C9A227" }}>
                        {fmt(p.amount_injected)}
                      </td>
                      <td className="px-4 py-3 text-xs text-white/50 font-mono">{p.first_transaction}</td>
                      <td className="px-4 py-3 text-white/30 text-xs">{isOpen ? "▲" : "▼"}</td>
                    </tr>
                    {isOpen && (
                      <tr key={`${p.node_id}-detail`} className="border-t border-white/5">
                        <td colSpan={6} className="px-6 py-4" style={{ backgroundColor: "#0a1225" }}>
                          <p className="text-xs text-white/40 uppercase tracking-wider mb-2">Mulas alimentadas</p>
                          <div className="flex flex-wrap gap-2">
                            {p.mules.map(m => (
                              <span key={m} className="px-2 py-1 rounded text-xs font-mono"
                                    style={{ backgroundColor: "#C0392B22", color: "#E57373", border: "1px solid #C0392B44" }}>
                                {m}
                              </span>
                            ))}
                          </div>
                          {!detected && (
                            <p className="mt-3 text-xs text-amber-400/80 flex items-center gap-1.5">
                              <span className="text-amber-400">⚠</span>
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
        <h2 className="text-base font-semibold text-white mb-3">Grafo Dirigido del Anillo</h2>
        <p className="text-xs text-white/40 mb-4">
          Las flechas indican dirección del flujo de dinero. Tamaño del nodo = relevancia en el anillo.
          Grosor de arista = monto transferido.
        </p>
        <RingGraphDirected />
      </div>

      {/* insight box */}
      <div className="rounded-xl border p-5 text-sm"
           style={{ backgroundColor: "#080f1d", borderColor: "#C9A22733" }}>
        <p className="text-xs font-semibold uppercase tracking-widest text-[#C9A227] mb-2">Insight 16 — Limitación del modelo</p>
        <p className="text-white/70 leading-relaxed">
          El GNN detecta la <strong className="text-white">estratificación</strong> (las mulas que mueven y dispersan
          el dinero) pero no la <strong className="text-white">colocación</strong> (el depósito inicial del perpetrador).
          Las cuentas origen tienen baja centralidad de red — hacen pocas transacciones de alto monto — y resultan
          invisibles para un clasificador basado en patrones de conectividad.
          El backward tracing identifica a <strong className="text-amber-400">ACC0000210</strong> y{" "}
          <strong className="text-amber-400">ACC0001046</strong> como perpetradores con score GNN ≈ 0%,
          inyectando <strong className="text-white">$66,422</strong> al anillo desde cuentas aparentemente legítimas.
        </p>
        <p className="text-white/50 text-xs mt-3">
          Acción sugerida: combinar el scoring GNN con backward tracing automático sobre el grafo dirigido temporal.
          Todo predecesor directo de un nodo detectado es candidato a revisión de segunda línea.
        </p>
      </div>
    </div>
  );
}
