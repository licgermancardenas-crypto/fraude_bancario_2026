"use client";
import { useEffect, useState, useRef } from "react";
import type { EntityGraph, EntityNode } from "@/lib/types";
import PageHeader from "@/components/PageHeader";

const COLORS = {
  cuenta_fraud: "#EF4444",
  cuenta_pep:   "#F59E0B",
  cuenta_legit: "#5A6478",
  empresa_shell:"#DC2626",
  empresa:      "#7C3AED",
};

type FilterType = "all" | "cuenta" | "empresa";

export default function EntidadesPage() {
  const [graph, setGraph]         = useState<EntityGraph | null>(null);
  const [selected, setSelected]   = useState<EntityNode | null>(null);
  const [filter, setFilter]       = useState<FilterType>("all");
  const [showShell, setShowShell] = useState(false);
  const [showPep, setShowPep]     = useState(false);
  const cyRef = useRef<HTMLDivElement>(null);
  const cyInstance = useRef<any>(null);

  useEffect(() => {
    fetch("/data/entities.json").then(r => r.json()).then(setGraph);
  }, []);

  useEffect(() => {
    if (!graph || !cyRef.current) return;

    let nodes = graph.nodes;
    let edges = graph.edges;

    if (filter !== "all") nodes = nodes.filter(n => n.type === filter);
    if (showShell) nodes = nodes.filter(n => n.type !== "empresa" || n.is_shell);
    if (showPep)   nodes = nodes.filter(n => n.type !== "cuenta" || n.is_pep);

    const visibleIds = new Set(nodes.map(n => n.id));
    edges = edges.filter(e => visibleIds.has(e.src) && visibleIds.has(e.dst));

    import("cytoscape").then(({ default: cytoscape }) => {
      if (cyInstance.current) cyInstance.current.destroy();
      cyInstance.current = cytoscape({
        container: cyRef.current,
        elements: [
          ...nodes.map(n => ({
            data: {
              id: n.id, label: n.label?.split(" ").slice(0, 2).join(" ") || n.id,
              nodeType: n.type,
              is_fraud: n.is_fraud, is_pep: n.is_pep, is_shell: n.is_shell,
              score: n.gnn_score,
            }
          })),
          ...edges.map((e, i) => ({
            data: { id: `e${i}`, source: e.src, target: e.dst, edgeType: e.type }
          })),
        ],
        style: [
          {
            selector: "node",
            style: {
              "width": 28, "height": 28,
              "label": "data(label)",
              "font-size": 9,
              "text-valign": "bottom", "text-margin-y": 4,
              "color": "#5A6478",
              "background-color": "#5A6478",
              "border-width": 0,
            }
          },
          {
            selector: "node[nodeType='cuenta'][is_fraud=1]",
            style: { "background-color": COLORS.cuenta_fraud, "border-width": 2, "border-color": "#7F1D1D" }
          },
          {
            selector: "node[nodeType='cuenta'][is_pep=true]",
            style: { "background-color": COLORS.cuenta_pep }
          },
          {
            selector: "node[nodeType='empresa'][is_shell=true]",
            style: { "background-color": COLORS.empresa_shell, shape: "diamond", width: 32, height: 32 }
          },
          {
            selector: "node[nodeType='empresa']",
            style: { "background-color": COLORS.empresa, shape: "rectangle", width: 36, height: 22 }
          },
          {
            selector: "node:selected",
            style: { "border-width": 3, "border-color": "#2E6BFF" }
          },
          {
            selector: "edge",
            style: {
              "width": 1.5,
              "line-color": "#3A4356",
              "target-arrow-color": "#3A4356",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
              "opacity": 0.7,
            }
          },
          {
            selector: "edge[edgeType='es_titular']",
            style: { "line-color": "#7C3AED", "target-arrow-color": "#7C3AED" }
          },
          {
            selector: "edge[edgeType='es_director']",
            style: { "line-color": "#F59E0B", "target-arrow-color": "#F59E0B", "line-style": "dashed" }
          },
        ],
        layout: { name: "cose", idealEdgeLength: 80, nodeOverlap: 20, animate: false },
        userZoomingEnabled: true,
        userPanningEnabled: true,
      });

      cyInstance.current.on("tap", "node", (evt: any) => {
        const nodeId = evt.target.id();
        const node   = graph.nodes.find(n => n.id === nodeId) || null;
        setSelected(node);
      });
      cyInstance.current.on("tap", (evt: any) => {
        if (evt.target === cyInstance.current) setSelected(null);
      });
    });

    return () => { if (cyInstance.current) cyInstance.current.destroy(); };
  }, [graph, filter, showShell, showPep]);

  const stats = graph ? {
    cuentas: graph.nodes.filter(n => n.type === "cuenta").length,
    empresas: graph.nodes.filter(n => n.type === "empresa").length,
    shells: graph.nodes.filter(n => n.is_shell).length,
    peps: graph.nodes.filter(n => n.is_pep).length,
    fraud: graph.nodes.filter(n => n.is_fraud === 1).length,
  } : null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Red de Entidades"
        subtitle="Grafo de cuentas, personas y empresas con vínculos societarios y de titularidad"
      />

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {[
            { label: "Cuentas", value: stats.cuentas, color: "#7AA2FF" },
            { label: "Empresas", value: stats.empresas, color: "#7C3AED" },
            { label: "Shells", value: stats.shells, color: "#DC2626" },
            { label: "PEPs", value: stats.peps, color: "#F59E0B" },
            { label: "Alto riesgo", value: stats.fraud, color: "#EF4444" },
          ].map(s => (
            <div key={s.label} className="bg-[#0E1219] rounded-xl p-3 border border-[#1E2430] text-center">
              <p className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</p>
              <p className="text-xs text-[#5A6478] mt-0.5">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-4 flex-col lg:flex-row">
        {/* Graph */}
        <div className="flex-1 bg-[#0E1219] rounded-xl border border-[#1E2430] overflow-hidden" style={{ minHeight: 520 }}>
          {/* Toolbar */}
          <div className="flex flex-wrap gap-2 p-3 border-b border-[#1E2430] items-center">
            <span className="text-xs font-semibold text-[#5A6478] mr-1">Filtrar:</span>
            {(["all", "cuenta", "empresa"] as FilterType[]).map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className="px-2.5 py-1 rounded-full text-xs font-medium transition-colors"
                style={{
                  backgroundColor: filter === f ? "#2E6BFF" : "#1E2430",
                  color: filter === f ? "#fff" : "#5A6478",
                }}
              >
                {f === "all" ? "Todos" : f === "cuenta" ? "Cuentas" : "Empresas"}
              </button>
            ))}
            <div className="h-4 w-px bg-[#1E2430] mx-1" />
            <label className="flex items-center gap-1.5 text-xs text-[#5A6478] cursor-pointer">
              <input type="checkbox" checked={showShell} onChange={e => setShowShell(e.target.checked)} className="rounded" />
              Solo shells
            </label>
            <label className="flex items-center gap-1.5 text-xs text-[#5A6478] cursor-pointer">
              <input type="checkbox" checked={showPep} onChange={e => setShowPep(e.target.checked)} className="rounded" />
              Solo PEPs
            </label>
            {/* Legend */}
            <div className="ml-auto flex items-center gap-3 text-[10px] text-[#5A6478]">
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full inline-block" style={{background:COLORS.cuenta_fraud}}/>Fraude</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full inline-block" style={{background:COLORS.cuenta_pep}}/>PEP</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm inline-block" style={{background:COLORS.empresa_shell}}/>Shell</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm inline-block" style={{background:COLORS.empresa}}/>Empresa</span>
            </div>
          </div>
          {!graph ? (
            <div className="flex items-center justify-center h-96 text-[#5A6478] text-sm">Cargando red…</div>
          ) : (
            <div ref={cyRef} style={{ width: "100%", height: 480 }} />
          )}
        </div>

        {/* Detail panel */}
        {selected && (
          <div className="w-full lg:w-72 bg-[#0E1219] rounded-xl border border-[#1E2430] p-4 space-y-4 self-start">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-widest text-[#5A6478]">
                {selected.type === "empresa" ? "Empresa" : "Cuenta"}
              </span>
              <button
                onClick={() => setSelected(null)}
                aria-label="Cerrar panel de detalle"
                className="w-11 h-11 -m-2 flex items-center justify-center text-[#5A6478] hover:text-[#5A6478] text-lg leading-none"
              >×</button>
            </div>

            <div>
              <p className="font-semibold text-[#EDEAE6] text-sm leading-snug">{selected.label}</p>
              <p className="text-xs text-[#5A6478] mt-0.5">{selected.id}</p>
            </div>

            {selected.type === "cuenta" && (
              <div className="space-y-2 text-sm">
                {selected.gnn_score !== undefined && (
                  <Row label="Score GNN">
                    <span className="font-bold" style={{ color: selected.gnn_score > 0.7 ? "#EF4444" : selected.gnn_score > 0.4 ? "#F59E0B" : "#22C55E" }}>
                      {selected.gnn_score.toFixed(4)}
                    </span>
                  </Row>
                )}
                {selected.is_pep && <Badge color="#F59E0B" text="PEP — Persona Expuesta Políticamente" />}
                {selected.is_fraud === 1 && <Badge color="#EF4444" text="Marcado como fraude" />}
                {selected.ocupacion && <Row label="Ocupación">{selected.ocupacion}</Row>}
                {selected.municipio && <Row label="Municipio">{selected.municipio}</Row>}
                {selected.cuil && <Row label="CUIL">{selected.cuil}</Row>}
                {selected.balance !== undefined && <Row label="Balance">${selected.balance?.toLocaleString("es-AR")}</Row>}
                {selected.account_type && <Row label="Tipo">{selected.account_type}</Row>}
              </div>
            )}

            {selected.type === "empresa" && (
              <div className="space-y-2 text-sm">
                {selected.is_shell && <Badge color="#DC2626" text="Empresa de fachada (shell)" />}
                {selected.razon_social && <Row label="Razón social">{selected.razon_social}</Row>}
                {selected.cuit_empresa && <Row label="CUIT">{selected.cuit_empresa}</Row>}
                {selected.sector && <Row label="Sector">{selected.sector}</Row>}
                {selected.pais_constitucion && <Row label="País">{selected.pais_constitucion}</Row>}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-[#5A6478] shrink-0">{label}</span>
      <span className="text-[#EDEAE6] font-medium text-right">{children}</span>
    </div>
  );
}

function Badge({ color, text }: { color: string; text: string }) {
  return (
    <div className="flex items-center gap-1.5 text-xs font-medium rounded-full px-2.5 py-1"
         style={{ backgroundColor: color + "18", color }}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
      {text}
    </div>
  );
}
