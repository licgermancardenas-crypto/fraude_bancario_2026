"use client";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import type { PatternCount } from "@/lib/caseAggregates";

interface Props { data: PatternCount[] }

export default function PatternDonut({ data }: Props) {
  const total = data.reduce((s, d) => s + d.count, 0);

  return (
    <div className="flex flex-col sm:flex-row items-center gap-4">
      <div className="relative flex-shrink-0" style={{ width: 180, height: 180 }}>
        <ResponsiveContainer width={180} height={180}>
          <PieChart>
            <Pie
              data={data}
              dataKey="count"
              nameKey="label"
              cx="50%" cy="50%"
              innerRadius={56}
              outerRadius={82}
              paddingAngle={2}
              stroke="none"
            >
              {data.map(d => <Cell key={d.pattern} fill={d.color} />)}
            </Pie>
            <Tooltip
              contentStyle={{ backgroundColor: "#12161F", border: "1px solid #1E2430", borderRadius: 10 }}
              labelStyle={{ color: "#EDEAE6", fontSize: 12 }}
              itemStyle={{ color: "#5A6478" }}
              formatter={(value: number, name: string) => [`${value} casos`, name]}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-2xl font-bold" style={{ color: "#EDEAE6", fontFamily: "'JetBrains Mono', monospace" }}>
            {total}
          </span>
          <span className="text-[10px] uppercase tracking-widest" style={{ color: "#5A6478" }}>
            casos
          </span>
        </div>
      </div>
      <div className="flex-1 w-full space-y-2.5">
        {data.map(d => (
          <div key={d.pattern} className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: d.color }} />
              <span className="text-xs truncate" style={{ color: "#5A6478" }}>{d.label}</span>
            </div>
            <span className="text-xs font-mono flex-shrink-0" style={{ color: "#EDEAE6" }}>
              {d.count} · {total ? Math.round((d.count / total) * 100) : 0}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
