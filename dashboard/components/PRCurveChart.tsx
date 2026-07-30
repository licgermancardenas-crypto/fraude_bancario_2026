"use client";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, ResponsiveContainer } from "recharts";
import type { PRCurve } from "@/lib/types";

const MODEL_COLORS: Record<string, string> = {
  "Logistic Regression": "#5A6478",
  "XGBoost":             "#F59E0B",
  "Node2Vec + XGBoost":  "#A78BFA",
  "GAT":                 "#34D399",
  "GraphSAGE":           "#2E6BFF",
};

interface Props { curves: PRCurve[] }

export default function PRCurveChart({ curves }: Props) {
  const points = Array.from({ length: 101 }, (_, i) => {
    const r = i / 100;
    const entry: Record<string, number> = { recall: r };
    curves.forEach(curve => {
      let prec = 0;
      for (let j = 0; j < curve.recall.length - 1; j++) {
        const rec0 = curve.recall[j];
        const rec1 = curve.recall[j + 1];
        if (rec0 >= r && rec1 <= r) { prec = curve.precision[j]; break; }
        if (Math.abs(rec0 - r) < 0.02) { prec = curve.precision[j]; break; }
      }
      entry[curve.model] = prec;
    });
    return entry;
  });

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={points} margin={{ top: 10, right: 20, bottom: 20, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1E2430" />
        <XAxis dataKey="recall" type="number" domain={[0, 1]}
          tickFormatter={v => v.toFixed(1)} stroke="#1E2430" tick={{ fill: "#5A6478", fontSize: 11 }}
          label={{ value: "Recall", position: "insideBottom", offset: -10, fill: "#5A6478", fontSize: 12 }} />
        <YAxis domain={[0, 1]} stroke="#1E2430" tick={{ fill: "#5A6478", fontSize: 11 }}
          tickFormatter={v => v.toFixed(1)}
          label={{ value: "Precisión", angle: -90, position: "insideLeft", fill: "#5A6478", fontSize: 12 }} />
        <Tooltip
          contentStyle={{
            backgroundColor: "#12161F",
            border: "1px solid #1E2430",
            borderRadius: 10,
          }}
          labelStyle={{ color: "#5A6478", fontSize: 12 }}
          itemStyle={{ color: "#EDEAE6" }}
          formatter={(v: number, name: string) => {
            const curve = curves.find(c => c.model === name);
            return [`${(v * 100).toFixed(1)}%`, `${name} (PR-AUC=${curve?.pr_auc.toFixed(3)})`];
          }}
          labelFormatter={v => `Recall: ${(Number(v) * 100).toFixed(0)}%`}
        />
        <Legend wrapperStyle={{ paddingTop: 12, fontSize: 12, color: "#5A6478" }} />
        <ReferenceLine y={0.9} stroke="#1E2430" strokeDasharray="4 4"
          label={{ value: "P=90%", fill: "#5A6478", fontSize: 10, position: "insideTopRight" }} />
        {curves.map(c => (
          <Line key={c.model} type="stepAfter" dataKey={c.model}
            stroke={MODEL_COLORS[c.model] ?? "#5A6478"} strokeWidth={2.5}
            dot={false} activeDot={{ r: 3 }} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
