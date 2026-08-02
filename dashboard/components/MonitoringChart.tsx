"use client";
import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer,
} from "recharts";

export interface MonthPoint {
  mes: string;
  pr_auc: number;
  alertas: number;
  fp_rate: number;
  psi: number;
}

/** PR-AUC mensual (línea) + tasa de FP (barras), con umbral de alerta de drift. */
export default function MonitoringChart({ data, alertThreshold }: { data: MonthPoint[]; alertThreshold: number }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 10, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1E2430" vertical={false} />
        <XAxis dataKey="mes" stroke="#1E2430" tick={{ fill: "#5A6478", fontSize: 11 }} />
        <YAxis yAxisId="pr" domain={[0.85, 1]} stroke="#1E2430" tick={{ fill: "#5A6478", fontSize: 11 }} width={38}
          tickFormatter={(v: number) => v.toFixed(2)} />
        <YAxis yAxisId="fp" orientation="right" domain={[0, 0.4]} stroke="#1E2430" tick={{ fill: "#5A6478", fontSize: 11 }} width={38}
          tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
        <Tooltip
          contentStyle={{ backgroundColor: "#12161F", border: "1px solid #1E2430", borderRadius: 10 }}
          labelStyle={{ color: "#5A6478", fontSize: 12 }}
          itemStyle={{ color: "#EDEAE6" }}
          formatter={(v: number, name: string) =>
            name === "PR-AUC" ? [v.toFixed(4), name] : [`${(v * 100).toFixed(1)}%`, name]} />
        <ReferenceLine yAxisId="pr" y={alertThreshold} stroke="#EF4444" strokeDasharray="4 4"
          label={{ value: "umbral de alerta", fill: "#EF4444", fontSize: 10, position: "insideBottomRight" }} />
        <Bar yAxisId="fp" dataKey="fp_rate" name="Tasa de FP" fill="#F59E0B" fillOpacity={0.35} barSize={22} radius={[3, 3, 0, 0]} />
        <Line yAxisId="pr" type="monotone" dataKey="pr_auc" name="PR-AUC" stroke="#7AA2FF" strokeWidth={2.5}
          dot={{ r: 3, fill: "#7AA2FF", strokeWidth: 0 }} activeDot={{ r: 5, fill: "#7AA2FF" }} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
