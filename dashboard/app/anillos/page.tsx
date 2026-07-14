"use client";
import { useState } from "react";
import RingGraph from "@/components/RingGraph";
import type { Ring } from "@/lib/types";
import ringsRaw from "@/public/data/rings.json";

const rings: Ring[] = ringsRaw as Ring[];

export default function AnillosPage() {
  const [idx, setIdx] = useState(0);
  const ring = rings[idx];

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-[#C9A227] mb-1">Explorador</p>
        <h1 className="text-2xl font-bold text-white">Anillos de Lavado Detectados</h1>
        <p className="text-sm text-white/50 mt-1">
          Ciclos cíclicos en el grafo de transacciones donde el dinero circula antes de ser
          extraído en pequeñas fracciones. Nodos coloreados por score de riesgo GNN.
        </p>
      </div>

      {rings.length === 0 ? (
        <p className="text-white/40">No se detectaron anillos en este dataset.</p>
      ) : (
        <>
          {/* ring selector */}
          <div className="flex flex-wrap gap-2">
            {rings.map((r, i) => (
              <button key={r.ring_id} onClick={() => setIdx(i)}
                 className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors
                   ${i === idx
                     ? "border-[#C9A227] text-[#C9A227] bg-[#C9A227]/10"
                     : "border-white/10 text-white/60 hover:bg-white/5"}`}>
                Anillo #{r.ring_id} · {r.n_nodes} nodos
              </button>
            ))}
          </div>

          {/* ring detail */}
          <div className="rounded-xl border border-white/10 p-5" style={{ backgroundColor: "#122855" }}>
            <div className="flex flex-wrap gap-6 mb-5 text-sm">
              <div>
                <p className="text-xs text-white/40 uppercase tracking-wider">Saltos</p>
                <p className="font-bold text-white text-lg">{ring.n_nodes}</p>
              </div>
              <div>
                <p className="text-xs text-white/40 uppercase tracking-wider">Monto total</p>
                <p className="font-bold text-[#C9A227] text-lg">
                  ${ring.total_amount.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                </p>
              </div>
              <div>
                <p className="text-xs text-white/40 uppercase tracking-wider">Score promedio GNN</p>
                <p className="font-bold text-white text-lg">{(ring.avg_score * 100).toFixed(1)}%</p>
              </div>
            </div>

            <RingGraph ring={ring} />
          </div>

          {/* nodes table */}
          <div className="rounded-xl border border-white/10 overflow-x-auto" style={{ backgroundColor: "#122855" }}>
            <table className="w-full text-sm">
              <thead style={{ backgroundColor: "#0d2554" }}>
                <tr>
                  {["Cuenta", "Score GNN", "Tipo", "Balance", "Risk score"].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white/60">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ring.nodes.map(n => (
                  <tr key={n.id} className="border-t border-white/5 hover:bg-white/5 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-white/70">{n.id}</td>
                    <td className="px-4 py-3">
                      <span className="font-semibold" style={{ color: n.gnn_score > 0.5 ? "#C0392B" : "#27AE60" }}>
                        {(n.gnn_score * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 capitalize text-white/60">{n.account_type}</td>
                    <td className="px-4 py-3 font-mono text-xs">
                      ${n.balance.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-white/60">{n.risk_score.toFixed(4)}</td>
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
