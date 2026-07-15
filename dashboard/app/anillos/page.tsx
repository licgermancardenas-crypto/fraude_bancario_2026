"use client";
import { useState } from "react";
import RingGraph from "@/components/RingGraph";
import PageHeader from "@/components/PageHeader";
import type { Ring } from "@/lib/types";
import ringsRaw from "@/public/data/rings.json";

const rings: Ring[] = ringsRaw as Ring[];

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
        <p className="text-white/35">No se detectaron anillos en este dataset.</p>
      ) : (
        <>
          {/* ring selector */}
          <div className="flex flex-wrap gap-2">
            {rings.map((r, i) => (
              <button key={r.ring_id} onClick={() => setIdx(i)}
                className={`px-4 py-2 rounded-lg text-sm font-medium border transition-all ${
                  i === idx
                    ? "border-[#C9A227] text-[#C9A227] bg-[#C9A227]/8"
                    : "border-white/8 text-white/45 hover:text-white/70 hover:bg-white/4"
                }`}>
                Anillo #{r.ring_id} · {r.n_nodes} nodos
              </button>
            ))}
          </div>

          {/* ring detail */}
          <div className="rounded-xl border border-white/8 p-5" style={{ backgroundColor: "#0d1e38" }}>
            <div className="flex flex-wrap gap-6 mb-5">
              {[
                { label: "Saltos",            value: String(ring.n_nodes),                         color: "text-white" },
                { label: "Monto total",       value: "$" + ring.total_amount.toLocaleString("es-AR", { maximumFractionDigits: 0 }), color: "text-[#C9A227]" },
                { label: "Score promedio GNN", value: (ring.avg_score * 100).toFixed(1) + "%",      color: "text-white" },
              ].map(({ label, value, color }) => (
                <div key={label}>
                  <p className="text-[11px] font-bold uppercase tracking-widest text-white/30 mb-1">{label}</p>
                  <p className={`text-xl font-bold ${color}`}>{value}</p>
                </div>
              ))}
            </div>
            <RingGraph ring={ring} />
          </div>

          {/* nodes table */}
          <div className="rounded-xl border border-white/8 overflow-x-auto" style={{ backgroundColor: "#0d1e38" }}>
            <table className="w-full text-sm">
              <thead style={{ backgroundColor: "#0a1225" }}>
                <tr>
                  {["Cuenta", "Score GNN", "Tipo", "Balance", "Risk score"].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-widest text-white/30">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ring.nodes.map(n => (
                  <tr key={n.id} className="border-t border-white/5 hover:bg-white/4 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-white/55">{n.id}</td>
                    <td className="px-4 py-3">
                      <span className="font-semibold text-sm"
                            style={{ color: n.gnn_score > 0.5 ? "#C0392B" : "#27AE60" }}>
                        {(n.gnn_score * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 capitalize text-xs text-white/45">{n.account_type}</td>
                    <td className="px-4 py-3 font-mono text-xs text-white/55">
                      ${n.balance.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-white/40">{n.risk_score.toFixed(4)}</td>
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
