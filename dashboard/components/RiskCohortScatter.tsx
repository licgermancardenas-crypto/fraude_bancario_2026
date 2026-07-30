"use client";
import { ScatterChart, Scatter, XAxis, YAxis, ZAxis, CartesianGrid, Tooltip, ReferenceLine, ReferenceArea, ResponsiveContainer } from "recharts";
import type { EntityNode } from "@/lib/types";

interface Props { accounts: EntityNode[] }

const KYC_ALTO = 0.30;
const BLIND_SPOT_GNN = 0.7;

export default function RiskCohortScatter({ accounts }: Props) {
  const legit = accounts.filter(a => !a.is_fraud).map(a => ({ x: a.risk_score ?? 0, y: a.gnn_score ?? 0, id: a.id }));
  const fraud = accounts.filter(a => a.is_fraud).map(a => ({ x: a.risk_score ?? 0, y: a.gnn_score ?? 0, id: a.id }));
  const maxRisk = Math.max(0.4, ...accounts.map(a => a.risk_score ?? 0));

  return (
    <div>
      <ResponsiveContainer width="100%" height={280}>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1E2430" />
          <ReferenceArea
            x1={0} x2={KYC_ALTO} y1={BLIND_SPOT_GNN} y2={1}
            fill="#A78BFA" fillOpacity={0.08} stroke="none"
          />
          <XAxis type="number" dataKey="x" domain={[0, maxRisk]} stroke="#1E2430"
            tick={{ fill: "#5A6478", fontSize: 11 }} tickFormatter={v => v.toFixed(2)}
            label={{ value: "Rating KYC (risk_score, estático)", position: "insideBottom", offset: -12, fill: "#5A6478", fontSize: 12 }} />
          <YAxis type="number" dataKey="y" domain={[0, 1]} stroke="#1E2430"
            tick={{ fill: "#5A6478", fontSize: 11 }}
            label={{ value: "Score GNN (dinámico)", angle: -90, position: "insideLeft", fill: "#5A6478", fontSize: 12 }} />
          <ZAxis range={[36, 36]} />
          <ReferenceLine x={KYC_ALTO} stroke="#5A6478" strokeDasharray="4 4" />
          <ReferenceLine y={BLIND_SPOT_GNN} stroke="#5A6478" strokeDasharray="4 4" />
          <Tooltip
            cursor={{ strokeDasharray: "3 3", stroke: "#1E2430" }}
            contentStyle={{ backgroundColor: "#12161F", border: "1px solid #1E2430", borderRadius: 10 }}
            labelStyle={{ color: "#5A6478", fontSize: 12 }}
            itemStyle={{ color: "#EDEAE6" }}
            formatter={(v: number, name: string) => [name === "x" ? v.toFixed(3) : v.toFixed(3), name === "x" ? "KYC" : "Score GNN"]}
            labelFormatter={() => ""}
          />
          <Scatter name="Legítima" data={legit} fill="#5A6478" fillOpacity={0.65} />
          <Scatter name="Fraude"   data={fraud} fill="#EF4444" fillOpacity={0.85} />
        </ScatterChart>
      </ResponsiveContainer>
      <div className="flex flex-wrap items-center gap-4 mt-1">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: "#5A6478" }} />
          <span className="text-xs" style={{ color: "#5A6478" }}>Legítima</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: "#EF4444" }} />
          <span className="text-xs" style={{ color: "#5A6478" }}>Fraude</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: "rgba(167,139,250,0.35)" }} />
          <span className="text-xs" style={{ color: "#5A6478" }}>Punto ciego del onboarding (KYC bajo/medio, score GNN alto)</span>
        </div>
      </div>
    </div>
  );
}
