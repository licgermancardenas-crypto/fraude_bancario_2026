"use client";
import { AreaChart, Area, ResponsiveContainer } from "recharts";
import ProgressRing from "@/components/ProgressRing";
import ProgressBar from "@/components/ProgressBar";
import type { MonthCount } from "@/lib/caseAggregates";

interface Props {
  casosAbiertos: number;
  totalCasos: number;
  sparkline: MonthCount[];
  recallAtP90: number;       // 0..1 — mostrado en el ring
  prAucGnn: number;          // 0..1 — PR-AUC de GraphSAGE
  prAucDelta: number;        // ej. 0.038, GraphSAGE vs XGBoost (solo para el sub-label)
  pctBlindSpot: number;      // 0..1 — casos con KYC no-Alto pero score GNN alto
  pctScreeningOk: number;    // 0..1 — screening sin pendientes
}

export default function SystemPulseCard({
  casosAbiertos, totalCasos, sparkline, recallAtP90, prAucGnn, prAucDelta, pctBlindSpot, pctScreeningOk,
}: Props) {
  return (
    <div className="h-full rounded-xl p-5 flex flex-col gap-5" style={{ backgroundColor: "#0E1219", border: "1px solid #1E2430" }}>
      <div>
        <p className="text-[11px] font-bold uppercase tracking-widest mb-1" style={{ color: "#5A6478", fontFamily: "'JetBrains Mono', monospace" }}>
          Pulso del sistema
        </p>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-4xl font-bold leading-none tracking-tight" style={{ color: "#EDEAE6", fontFamily: "'JetBrains Mono', monospace" }}>
              {casosAbiertos}
            </p>
            <p className="text-xs mt-1.5" style={{ color: "#5A6478" }}>
              casos abiertos de {totalCasos} alertas generadas
            </p>
          </div>
          <div style={{ width: 140, height: 48 }} className="flex-shrink-0">
            <ResponsiveContainer width="100%" height={48}>
              <AreaChart data={sparkline} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="sparkGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#7AA2FF" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="#7AA2FF" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="count" stroke="#7AA2FF" strokeWidth={2} fill="url(#sparkGradient)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="h-px" style={{ backgroundColor: "#1E2430" }} />

      <div className="flex flex-col sm:flex-row items-center sm:items-start gap-5 flex-1">
        <ProgressRing value={recallAtP90} label="Recall @ P90" color="#2E6BFF" />
        <div className="w-full flex-1 space-y-3.5">
          <ProgressBar label="PR-AUC — GraphSAGE" value={prAucGnn} sub={`${prAucGnn.toFixed(3)} (+${prAucDelta.toFixed(3)})`} color="#22C55E" />
          <ProgressBar label="Punto ciego del onboarding" value={pctBlindSpot} color="#A78BFA" />
          <ProgressBar label="Screening sin pendientes" value={pctScreeningOk} color="#F59E0B" />
        </div>
      </div>
    </div>
  );
}
