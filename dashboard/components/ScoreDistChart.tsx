"use client";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import type { ScoreDistribution } from "@/lib/types";

interface Props { dist: ScoreDistribution }

export default function ScoreDistChart({ dist }: Props) {
  const totalLegit = dist.legit.reduce((s, n) => s + n, 0) || 1;
  const totalFraud = dist.fraud.reduce((s, n) => s + n, 0) || 1;

  const data = dist.bin_centers.map((c, i) => ({
    score: c.toFixed(2),
    Legítimo: +(dist.legit[i] / totalLegit * 100).toFixed(1),
    Fraude: +(dist.fraud[i] / totalFraud * 100).toFixed(1),
    legitCount: dist.legit[i],
    fraudCount: dist.fraud[i],
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 10, right: 20, bottom: 20, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1E2430" />
        <XAxis dataKey="score" stroke="#1E2430" interval={7} tick={{ fill: "#5A6478", fontSize: 11 }}
          label={{ value: "Score GNN (P(fraude))", position: "insideBottom", offset: -10, fill: "#5A6478", fontSize: 12 }} />
        <YAxis stroke="#1E2430" tick={{ fill: "#5A6478", fontSize: 11 }} unit="%"
          label={{ value: "% de la clase", angle: -90, position: "insideLeft", fill: "#5A6478", fontSize: 12 }} />
        <Tooltip
          contentStyle={{
            backgroundColor: "#12161F",
            border: "1px solid #1E2430",
            borderRadius: 10,
          }}
          labelStyle={{ color: "#5A6478", fontSize: 12 }}
          itemStyle={{ color: "#EDEAE6" }}
          labelFormatter={v => `Score: ${v}`}
          formatter={(value, name, props) => {
            const count = name === "Legítimo" ? props.payload.legitCount : props.payload.fraudCount;
            return [`${value}% (${count} cuentas)`, name];
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8, color: "#5A6478" }} />
        <Bar dataKey="Legítimo" fill="#5A6478" opacity={0.7} radius={[2, 2, 0, 0]} />
        <Bar dataKey="Fraude"   fill="#EF4444" opacity={0.85} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
