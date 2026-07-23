"use client";
import { useState } from "react";
import RingGraph from "@/components/RingGraph";
import PageHeader from "@/components/PageHeader";
import type { Ring } from "@/lib/types";
import ringsRaw from "@/public/data/rings.json";

const rings: Ring[] = ringsRaw as Ring[];

const card = {
  backgroundColor: "#12161F",
  border: "1px solid #1E2430",
};

export default function AnillosPage() {
  const [idx, setIdx] = useState(0);
  const ring = rings[idx];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Explorador"
        title="Anillos de Lavado Detectados"
        description="Ciclos en el grafo de transacciones donde el dinero circula antes de ser extraído en fracciones. Nodos coloreados por score de riesgo GNN."
      />

      {rings.length === 0 ? (
        <p style={{ color: "#5A6478" }}>No se detectaron anillos en este dataset.</p>
      ) : (
        <>
          {/* ring selector */}
          <div className="flex flex-wrap gap-2">
            {rings.map((r, i) => (
              <button
                key={r.ring_id}
                onClick={() => setIdx(i)}
                className="px-4 py-2 rounded-lg text-sm font-medium transition-all"
                style={i === idx ? {
                  backgroundColor: "rgba(46,107,255,0.12)",
                  border: "1px solid #2E6BFF",
                  color: "#7AA2FF",
                } : {
                  backgroundColor: "#12161F",
                  border: "1px solid #1E2430",
                  color: "#5A6478",
                }}
              >
                Anillo #{r.ring_id} · {r.n_nodes} nodos
              </button>
            ))}
          </div>

          {/* ring detail */}
          <div className="rounded-xl p-5" style={card}>
            <div className="flex flex-wrap gap-6 mb-5">
              {[
                { label: "Saltos",             value: String(ring.n_nodes),                                                            color: "#EDEAE6" },
                { label: "Monto total",        value: "$" + ring.total_amount.toLocaleString("es-AR", { maximumFractionDigits: 0 }), color: "#7AA2FF" },
                { label: "Score promedio GNN", value: (ring.avg_score * 100).toFixed(1) + "%",                                        color: "#EF4444" },
              ].map(({ label, value, color }) => (
                <div key={label}>
                  <p className="text-[11px] font-bold uppercase tracking-widest mb-1" style={{ color: "#5A6478" }}>{label}</p>
                  <p className="text-xl font-bold" style={{ color }}>{value}</p>
                </div>
              ))}
            </div>
            <RingGraph ring={ring} />
          </div>

          {/* nodes table */}
          <div className="rounded-xl overflow-x-auto" style={card}>
            <table className="w-full text-sm" style={{ backgroundColor: "#0E1219" }}>
              <thead>
                <tr style={{ backgroundColor: "#12161F", borderBottom: "1px solid #1E2430" }}>
                  {["Cuenta", "Score GNN", "Tipo", "Balance", "Risk score"].map(h => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-widest"
                      style={{ color: "#5A6478" }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ring.nodes.map(n => (
                  <tr
                    key={n.id}
                    className="transition-colors"
                    style={{ borderTop: "1px solid #1E2430" }}
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = "#12161F")}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = "transparent")}
                  >
                    <td className="px-4 py-3 font-mono text-xs font-medium" style={{ color: "#EDEAE6" }}>{n.id}</td>
                    <td className="px-4 py-3">
                      <span
                        className="font-semibold text-sm"
                        style={{ color: n.gnn_score > 0.5 ? "#EF4444" : "#22C55E" }}
                      >
                        {(n.gnn_score * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 capitalize text-xs" style={{ color: "#5A6478" }}>{n.account_type}</td>
                    <td className="px-4 py-3 font-mono text-xs" style={{ color: "#EDEAE6" }}>
                      ${n.balance.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs" style={{ color: "#5A6478" }}>{n.risk_score.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
