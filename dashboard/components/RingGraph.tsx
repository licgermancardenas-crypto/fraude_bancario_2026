"use client";
import { useEffect, useRef, useState } from "react";
import type { Ring } from "@/lib/types";

interface Props { ring: Ring }

function scoreToColor(score: number): string {
  // 0 = grey (#95A5A6), 1 = red (#C0392B)
  const r = Math.round(149 + (192 - 149) * score);
  const g = Math.round(165 + (57 - 165) * score);
  const b = Math.round(166 + (43 - 166) * score);
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
              "border-color":      "#C9A227",
              "border-width":      2,
              "label":             "data(label)",
              "color":             "#fff",
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
              "line-color":         "#C9A227",
              "target-arrow-color": "#C9A227",
              "target-arrow-shape": "triangle",
              "curve-style":        "bezier",
              "opacity":            0.7,
            },
          },
          {
            selector: "node:selected",
            style: { "border-width": 4, "border-color": "#fff" },
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
           className="rounded-xl border border-white/10 flex-1"
           style={{ height: 380, backgroundColor: "#0d2554" }} />
      <div className="w-full lg:w-64 rounded-xl border border-white/10 p-4 text-sm"
           style={{ backgroundColor: "#122855" }}>
        {selected ? (
          <>
            <p className="font-bold text-[#C9A227] mb-3 text-xs uppercase tracking-wider">Cuenta seleccionada</p>
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
                  <dt className="text-white/50">{k}</dt>
                  <dd className={`font-medium ${k === "¿Fraude?" && v === "Sí" ? "text-red-400" : "text-white"}`}>{v}</dd>
                </div>
              ))}
            </dl>
          </>
        ) : (
          <p className="text-white/40 text-xs mt-2">Hacé clic en un nodo para ver sus detalles.</p>
        )}
        <div className="mt-6 pt-4 border-t border-white/10">
          <p className="text-xs text-white/40 font-medium uppercase tracking-wider mb-2">Referencias</p>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: "#C0392B" }} />
            <span className="text-xs text-white/60">Score alto (fraude)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: "#95A5A6" }} />
            <span className="text-xs text-white/60">Score bajo (legítimo)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
