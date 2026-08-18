"use client";
import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine,
  ResponsiveContainer, Legend,
} from "recharts";
import type { Calibration } from "@/lib/scenarios";

/**
 * Curva de calibración de un escenario: volumen de alertas (barras) contra
 * precisión y recall (líneas) a medida que se mueve el umbral principal.
 *
 * Es el gráfico que hace visible el trade-off que gobierna todo sistema de
 * monitoreo transaccional: apretar el umbral sube la precisión y descarga al
 * equipo, pero deja fraude sin detectar. La línea punteada marca el umbral
 * vigente; el resaltado, el que se está simulando.
 */
export default function CalibrationChart({
  cal, selected,
}: { cal: Calibration; selected: number }) {
  const data = cal.puntos.map(p => ({
    factor: p.factor,
    etiqueta: `${p.factor}×`,
    valor: p.valor,
    disparos: p.disparos,
    precision: p.precision,
    recall: p.recall,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 10, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1E2430" vertical={false} />
        <XAxis dataKey="etiqueta" stroke="#1E2430" tick={{ fill: "#5A6478", fontSize: 11 }} />
        <YAxis yAxisId="vol" stroke="#1E2430" tick={{ fill: "#5A6478", fontSize: 11 }} width={52}
          tickFormatter={(v: number) => v.toLocaleString("es-AR")} />
        <YAxis yAxisId="pct" orientation="right" domain={[0, 1]} stroke="#1E2430"
          tick={{ fill: "#5A6478", fontSize: 11 }} width={38}
          tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
        <Tooltip
          contentStyle={{ backgroundColor: "#12161F", border: "1px solid #1E2430", borderRadius: 10 }}
          labelStyle={{ color: "#5A6478", fontSize: 12 }}
          itemStyle={{ color: "#EDEAE6" }}
          labelFormatter={(l: string, payload) => {
            const v = payload?.[0]?.payload?.valor;
            return v ? `Umbral ${l} — ${cal.label.toLowerCase()}: ${v}` : l;
          }}
          formatter={(v: number, name: string) =>
            name === "Alertas" ? [v.toLocaleString("es-AR"), name] : [`${(v * 100).toFixed(1)}%`, name]} />
        <Legend wrapperStyle={{ fontSize: 11, color: "#5A6478" }} iconSize={9} />
        <ReferenceLine yAxisId="vol" x="1×" stroke="#5A6478" strokeDasharray="4 4"
          label={{ value: "vigente", fill: "#5A6478", fontSize: 10, position: "insideTopLeft" }} />
        {selected !== 1 && (
          <ReferenceLine yAxisId="vol" x={`${selected}×`} stroke="#7AA2FF" strokeWidth={1.5}
            label={{ value: "simulado", fill: "#7AA2FF", fontSize: 10, position: "insideTopRight" }} />
        )}
        <Bar yAxisId="vol" dataKey="disparos" name="Alertas" fill="#2E6BFF" fillOpacity={0.28}
          barSize={22} radius={[3, 3, 0, 0]} />
        <Line yAxisId="pct" type="monotone" dataKey="precision" name="Precisión" stroke="#22C55E"
          strokeWidth={2.5} dot={{ r: 3, fill: "#22C55E", strokeWidth: 0 }} activeDot={{ r: 5 }} />
        <Line yAxisId="pct" type="monotone" dataKey="recall" name="Recall" stroke="#F59E0B"
          strokeWidth={2.5} dot={{ r: 3, fill: "#F59E0B", strokeWidth: 0 }} activeDot={{ r: 5 }} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
