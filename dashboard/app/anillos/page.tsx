"use client";
import { useState } from "react";
import RingGraph from "@/components/RingGraph";
import PageHeader from "@/components/PageHeader";
import type { Ring } from "@/lib/types";
import ringsRaw from "@/public/data/rings.json";

const rings: Ring[] = ringsRaw as Ring[];

const card = {
  backgroundColor: "#FFFFFF",
  border: "1px solid #E2E8F0",
  boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
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
        <p style={{ color: "#94A3B8" }}>No se detectaron anillos en este dataset.</p>
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
                  backgroundColor: "#EFF6FF",
                  border: "1px solid #2563EB",
                  color: "#2563EB",
                } : {
                  backgroundColor: "#FFFFFF",
                  border: "1px solid #E2E8F0",
                  color: "#64748B",
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
                { label: "Saltos",             value: String(ring.n_nodes),                                                            color: "#0F172A" },
                { label: "Monto total",        value: "$" + ring.total_amount.toLocaleString("es-AR", { maximumFractionDigits: 0 }), color: "#2563EB" },
                { label: "Score promedio GNN", value: (ring.avg_score * 100).toFixed(1) + "%",                                        color: "#DC2626" },
              ].map(({ label, value, color }) => (
                <div key={label}>
                  <p className="text-[11px] font-bold uppercase tracking-widest mb-1" style={{ color: "#94A3B8" }}>{label}</p>
                  <p className="text-xl font-bold" style={{ color }}>{value}</p>
                </div>
              ))}
            </div>
            <RingGraph ring={ring} />
          </div>

          {/* nodes table */}
          <div className="rounded-xl overflow-x-auto" style={card}>
            <table className="w-full text-sm" style={{ backgroundColor: "#FFFFFF" }}>
              <thead>
                <tr style={{ backgroundColor: "#F8FAFC", borderBottom: "1px solid #E2E8F0" }}>
                  {["Cuenta", "Score GNN", "Tipo", "Balance", "Risk score"].map(h => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-widest"
                      style={{ color: "#94A3B8" }}
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
                    style={{ borderTop: "1px solid #F1F5F9" }}
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = "#F8FAFC")}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = "transparent")}
                  >
                    <td className="px-4 py-3 font-mono text-xs font-medium" style={{ color: "#0F172A" }}>{n.id}</td>
                    <td className="px-4 py-3">
                      <span
                        className="font-semibold text-sm"
                        style={{ color: n.gnn_score > 0.5 ? "#DC2626" : "#16A34A" }}
                      >
                        {(n.gnn_score * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 capitalize text-xs" style={{ color: "#64748B" }}>{n.account_type}</td>
                    <td className="px-4 py-3 font-mono text-xs" style={{ color: "#0F172A" }}>
                      ${n.balance.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs" style={{ color: "#64748B" }}>{n.risk_score.toFixed(4)}</td>
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
