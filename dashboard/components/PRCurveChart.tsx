"use client";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, ResponsiveContainer } from "recharts";
import type { PRCurve } from "@/lib/types";

const MODEL_COLORS: Record<string, string> = {
  "Logistic Regression": "#BDC3C7",
  "XGBoost":             "#C9A227",
  "GraphSAGE":           "#C0392B",
};

interface Props { curves: PRCurve[] }

export default function PRCurveChart({ curves }: Props) {
  // Merge all curves into a single dataset keyed by recall (0..1, 100 points)
  const points = Array.from({ length: 101 }, (_, i) => {
    const r = i / 100;
    const entry: Record<string, number> = { recall: r };
    curves.forEach(curve => {
      // interpolate precision at this recall level
      let prec = 0;
      for (let j = 0; j < curve.recall.length - 1; j++) {
        if (curve.recall[j] >= r && curve.recall[j + 1] <= r) {
          prec = curve.precision[j];
          break;
        }
        if (Math.abs(curve.recall[j] - r) < 0.02) {
          prec = curve.precision[j];
          break;
        }
      }
      entry[curve.model] = prec;
    });
    return entry;
  });

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={points} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
        <XAxis dataKey="recall" type="number" domain={[0, 1]}
          tickFormatter={v => v.toFixed(1)} stroke="rgba(255,255,255,0.3)"
          label={{ value: "Recall", position: "insideBottom", offset: -4, fill: "rgba(255,255,255,0.5)", fontSize: 12 }} />
        <YAxis domain={[0, 1]} stroke="rgba(255,255,255,0.3)"
          tickFormatter={v => v.toFixed(1)}
          label={{ value: "Precisión", angle: -90, position: "insideLeft", fill: "rgba(255,255,255,0.5)", fontSize: 12 }} />
        <Tooltip
          contentStyle={{ backgroundColor: "#122855", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
          labelStyle={{ color: "rgba(255,255,255,0.6)" }}
          formatter={(v: number, name: string) => {
            const curve = curves.find(c => c.model === name);
            return [`${(v * 100).toFixed(1)}%`, `${name} (PR-AUC=${curve?.pr_auc.toFixed(3)})`];
          }}
          labelFormatter={v => `Recall: ${(Number(v) * 100).toFixed(0)}%`}
        />
        <Legend wrapperStyle={{ paddingTop: 12, fontSize: 12 }} />
        <ReferenceLine y={0.9} stroke="rgba(255,255,255,0.2)" strokeDasharray="4 4"
          label={{ value: "P=90%", fill: "rgba(255,255,255,0.3)", fontSize: 10, position: "insideTopRight" }} />
        {curves.map(c => (
          <Line key={c.model} type="stepAfter" dataKey={c.model}
            stroke={MODEL_COLORS[c.model] ?? "#fff"} strokeWidth={2.5}
            dot={false} activeDot={{ r: 3 }} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
