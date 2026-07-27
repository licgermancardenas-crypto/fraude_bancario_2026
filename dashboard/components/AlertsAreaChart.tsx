"use client";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceDot, ResponsiveContainer } from "recharts";
import type { MonthCount } from "@/lib/caseAggregates";

interface Props { data: MonthCount[] }

export default function AlertsAreaChart({ data }: Props) {
  const peak = data.reduce((max, d) => (d.count > max.count ? d : max), data[0] ?? { key: "", label: "", count: 0 });

  return (
    <div>
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={data} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="alertsGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2E6BFF" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#2E6BFF" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1E2430" vertical={false} />
        <XAxis dataKey="label" stroke="#1E2430" tick={{ fill: "#5A6478", fontSize: 11 }} />
        <YAxis stroke="#1E2430" tick={{ fill: "#5A6478", fontSize: 11 }} allowDecimals={false} width={28} />
        <Tooltip
          contentStyle={{ backgroundColor: "#12161F", border: "1px solid #1E2430", borderRadius: 10 }}
          labelStyle={{ color: "#5A6478", fontSize: 12 }}
          itemStyle={{ color: "#EDEAE6" }}
          formatter={(v: number) => [`${v} alertas`, "Casos"]}
        />
        <Area
          type="monotone" dataKey="count"
          stroke="#7AA2FF" strokeWidth={2.5}
          fill="url(#alertsGradient)"
          dot={{ r: 3, fill: "#7AA2FF", strokeWidth: 0 }}
          activeDot={{ r: 5, fill: "#7AA2FF" }}
        />
        {peak.key && (
          <ReferenceDot x={peak.label} y={peak.count} r={5} fill="#7AA2FF" stroke="#07090F" strokeWidth={2} />
        )}
      </AreaChart>
    </ResponsiveContainer>
    {peak.key && (
      <p className="text-xs mt-3" style={{ color: "#5A6478" }}>
        Pico: <span style={{ color: "#7AA2FF", fontWeight: 600 }}>{peak.count} alertas</span> en {peak.label}.
      </p>
    )}
    </div>
  );
}
