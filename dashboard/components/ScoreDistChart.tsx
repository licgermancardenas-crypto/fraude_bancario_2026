"use client";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import type { ScoreDistribution } from "@/lib/types";

interface Props { dist: ScoreDistribution }

export default function ScoreDistChart({ dist }: Props) {
  const data = dist.bin_centers.map((c, i) => ({
    score: c.toFixed(2),
    Legítimo: dist.legit[i],
    Fraude: dist.fraud[i],
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
        <XAxis dataKey="score" stroke="rgba(255,255,255,0.3)" interval={7}
          label={{ value: "Score GNN (P(fraude))", position: "insideBottom", offset: -4, fill: "rgba(255,255,255,0.5)", fontSize: 12 }} />
        <YAxis stroke="rgba(255,255,255,0.3)"
          label={{ value: "Cuentas", angle: -90, position: "insideLeft", fill: "rgba(255,255,255,0.5)", fontSize: 12 }} />
        <Tooltip
          contentStyle={{ backgroundColor: "#122855", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
          labelStyle={{ color: "rgba(255,255,255,0.6)" }}
          labelFormatter={v => `Score: ${v}`}
        />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
        <Bar dataKey="Legítimo" fill="#BDC3C7" opacity={0.7} radius={[2, 2, 0, 0]} />
        <Bar dataKey="Fraude"   fill="#C0392B" opacity={0.9} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
