"use client";
import { useEffect, useRef, useState } from "react";
import type { Ring } from "@/lib/types";

interface Props { ring: Ring }

function scoreToColor(score: number): string {
  // 0 = steel (#5A6478), 1 = red (#EF4444)
  const r = Math.round(90 + (239 - 90) * score);
  const g = Math.round(100 + (68 - 100) * score);
  const b = Math.round(120 + (68 - 120) * score);
  return `rgb(${r},${g},${b})`;
}

export default function RingGraph({ ring }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [selected, setSelected] = useState<(typeof ring.nodes)[0] | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    let cy: unknown;

    (async () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const cytoscape = (await import("cytoscape")).default as any;

      const elements = [
        ...ring.nodes.map(n => ({
          data: {
            id:    n.id,
            label: n.id.slice(-4),
            color: scoreToColor(n.gnn_score),
            score: n.gnn_score,
          },
        })),
        ...ring.edges.map((e, i) => ({
          data: { id: `e${i}`, source: e.src, target: e.dst, amount: e.amount },
        })),
      ];

      cy = cytoscape({
        container: containerRef.current,
        elements,
        style: [
          {
            selector: "node",
            style: {
              "background-color":  "data(color)",
              "border-color":      "#1E2430",
              "border-width":      2,
              "label":             "data(label)",
              "color":             "#EDEAE6",
              "font-size":         "11px",
              "text-valign":       "center",
              "width":             44,
              "height":            44,
            },
          },
          {
            selector: "edge",
            style: {
              "width":              2,
              "line-color":         "#5A6478",
              "target-arrow-color": "#5A6478",
              "target-arrow-shape": "triangle",
              "curve-style":        "bezier",
              "opacity":            0.7,
            },
          },
          {
            selector: "node:selected",
            style: { "border-width": 4, "border-color": "#2E6BFF" },
          },
        ],
        layout:  { name: "circle", padding: 40 },
        userZoomingEnabled: true,
        userPanningEnabled: true,
      });

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (cy as any).on("tap", "node", (evt: any) => {
        const nodeId = evt.target.id();
        const node   = ring.nodes.find(n => n.id === nodeId) ?? null;
        setSelected(node);
      });
    })();

    return () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (cy as any)?.destroy?.();
    };
  }, [ring]);

  return (
    <div className="flex gap-4 flex-col lg:flex-row">
      <div ref={containerRef}
           className="rounded-xl border flex-1"
           style={{ height: 380, backgroundColor: "#0E1219", borderColor: "#1E2430" }} />
      <div className="w-full lg:w-64 rounded-xl border p-4 text-sm"
           style={{ backgroundColor: "#12161F", borderColor: "#1E2430" }}>
        {selected ? (
          <>
            <p className="font-bold text-[#7AA2FF] mb-3 text-xs uppercase tracking-wider">Cuenta seleccionada</p>
            <dl className="space-y-2">
              {[
                ["ID",          selected.id],
                ["Score GNN",   (selected.gnn_score * 100).toFixed(1) + "%"],
                ["Tipo",        selected.account_type],
                ["Balance",     "$" + selected.balance.toLocaleString("es-AR", { maximumFractionDigits: 0 })],
                ["Risk score",  selected.risk_score.toFixed(4)],
                ["¿Fraude?",    selected.is_fraud ? "Sí" : "No"],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between gap-2">
                  <dt className="text-[#5A6478]">{k}</dt>
                  <dd className={`font-medium ${k === "¿Fraude?" && v === "Sí" ? "text-red-400" : "text-[#EDEAE6]"}`}>{v}</dd>
                </div>
              ))}
            </dl>
          </>
        ) : (
          <p className="text-[#5A6478] text-xs mt-2">Hacé clic en un nodo para ver sus detalles.</p>
        )}
        <div className="mt-6 pt-4 border-t" style={{ borderColor: "#1E2430" }}>
          <p className="text-xs text-[#5A6478] font-medium uppercase tracking-wider mb-2">Referencias</p>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: "#EF4444" }} />
            <span className="text-xs text-[#5A6478]">Score alto (fraude)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: "#5A6478" }} />
            <span className="text-xs text-[#5A6478]">Score bajo (legítimo)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
