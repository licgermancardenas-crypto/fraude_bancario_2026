"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";

const PANEL = "#0E1219", LINE = "#1E2430", BONE = "#EDEAE6", MUTED = "#5A6478";

interface Alert {
  alert_id: string; fecha: string; account_id: string; entidad: string; account_type: string;
  disparador: string; detalle: string; score_gnn: number; rule_score: number; prioridad: number;
  estado: string; disposicion: string; is_fraud: number; caso_ref: string | null; analista: string;
}
interface Summary {
  total: number; auto_cerradas: number; cerradas_fp: number; en_revision: number; escaladas: number;
  tasa_fp: number; reduccion_carga: number;
}

const ESTADO: Record<string, { label: string; color: string }> = {
  escalada:     { label: "Escalada a caso", color: "#EF4444" },
  en_revision:  { label: "En revisión",     color: "#F59E0B" },
  cerrada_fp:   { label: "Cerrada — FP",     color: "#5A6478" },
  auto_cerrada: { label: "Auto-cerrada",     color: "#5A6478" },
};
const fdate = (s: string) => { try { return new Date(s + "T00:00:00").toLocaleDateString("es-AR"); } catch { return s; } };
const PAGE = 40;

export default function AlertasPage() {
  const [data, setData] = useState<{ summary: Summary; alerts: Alert[] } | null>(null);
  const [q, setQ] = useState("");
  const [fEstado, setFEstado] = useState("all");
  const [fDisp, setFDisp] = useState("all");
  const [page, setPage] = useState(0);

  useEffect(() => { fetch("/data/alerts.json").then(r => r.json()).then(setData); }, []);

  const disparadores = useMemo(() => data ? Array.from(new Set(data.alerts.map(a => a.disparador))).sort() : [], [data]);
  const rows = useMemo(() => {
    if (!data) return [];
    const ql = q.trim().toLowerCase();
    return data.alerts
      .filter(a => fEstado === "all" || a.estado === fEstado)
      .filter(a => fDisp === "all" || a.disparador === fDisp)
      .filter(a => !ql || a.entidad.toLowerCase().includes(ql) || a.account_id.toLowerCase().includes(ql) || a.alert_id.toLowerCase().includes(ql))
      .sort((a, b) => b.prioridad - a.prioridad);
  }, [data, q, fEstado, fDisp]);

  useEffect(() => setPage(0), [q, fEstado, fDisp]);

  if (!data) return <div className="flex items-center justify-center h-64 text-[#5A6478]">Cargando alertas…</div>;
  const s = data.summary;
  const pageRows = rows.slice(page * PAGE, page * PAGE + PAGE);
  const pages = Math.ceil(rows.length / PAGE);
  const ruido = s.auto_cerradas + s.cerradas_fp;

  const funnel = [
    { label: "Alertas generadas", value: s.total, color: "#7AA2FF" },
    { label: "Cerradas (ruido / FP)", value: ruido, color: "#5A6478" },
    { label: "En revisión", value: s.en_revision, color: "#F59E0B" },
    { label: "Escaladas a caso", value: s.escaladas, color: "#EF4444" },
  ];

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Monitoreo transaccional" title="Alertas y Triage"
        description="El embudo real de un sistema de monitoreo: muchas alertas, la mayoría falsos positivos. El triage cierra el ruido y sólo una fracción escala a caso. Los FP son cuentas legítimas que disparan una regla o tienen score moderado." />

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {[
          { label: "Alertas del período", value: s.total.toLocaleString("es-AR"), color: BONE },
          { label: "Auto-cerradas", value: s.auto_cerradas.toLocaleString("es-AR"), color: "#5A6478" },
          { label: "En revisión", value: s.en_revision.toLocaleString("es-AR"), color: "#F59E0B" },
          { label: "Escaladas a caso", value: s.escaladas.toLocaleString("es-AR"), color: "#EF4444" },
          { label: "Tasa de falsos positivos", value: `${Math.round(s.tasa_fp * 100)}%`, color: "#F59E0B" },
        ].map(k => (
          <div key={k.label} className="rounded-xl p-4" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
            <div className="text-2xl font-bold" style={{ color: k.color }}>{k.value}</div>
            <div className="text-[11px] mt-1" style={{ color: MUTED }}>{k.label}</div>
          </div>
        ))}
      </div>

      {/* Embudo */}
      <div className="rounded-xl p-5" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
        <h3 className="text-sm font-bold mb-3" style={{ color: BONE }}>Embudo de triage</h3>
        <div className="space-y-2">
          {funnel.map(f => (
            <div key={f.label} className="flex items-center gap-3">
              <span className="w-40 shrink-0 text-xs" style={{ color: MUTED }}>{f.label}</span>
              <div className="h-6 flex-1 rounded-md overflow-hidden" style={{ background: "#07090F" }}>
                <div className="h-full rounded-md flex items-center px-2" style={{ width: `${Math.max(4, (f.value / s.total) * 100)}%`, background: f.color }}>
                  <span className="text-[11px] font-bold" style={{ color: "#07090F" }}>{f.value.toLocaleString("es-AR")}</span>
                </div>
              </div>
              <span className="w-12 text-right text-[11px]" style={{ color: MUTED }}>{Math.round((f.value / s.total) * 100)}%</span>
            </div>
          ))}
        </div>
        <p className="text-[11px] mt-3" style={{ color: MUTED }}>
          El triage automático cierra el <b style={{ color: "#7AA2FF" }}>{Math.round(s.reduccion_carga * 100)}%</b> del volumen sin intervención del analista, que se concentra en las <b style={{ color: "#EF4444" }}>{s.escaladas}</b> alertas escaladas a caso.
        </p>
      </div>

      {/* Filtros */}
      <div className="rounded-xl p-4 flex flex-wrap gap-2 items-center" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="Buscar por entidad, cuenta o ID de alerta…"
          className="flex-1 min-w-[220px] rounded-lg border border-[#1E2430] bg-[#12161F] px-3 min-h-[40px] text-sm outline-none" style={{ color: BONE }} />
        <select value={fEstado} onChange={e => setFEstado(e.target.value)} className="rounded-lg border border-[#1E2430] bg-[#12161F] px-2 min-h-[40px] text-sm outline-none" style={{ color: BONE }}>
          <option value="all">Todo estado</option>
          {Object.entries(ESTADO).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
        <select value={fDisp} onChange={e => setFDisp(e.target.value)} className="rounded-lg border border-[#1E2430] bg-[#12161F] px-2 min-h-[40px] text-sm outline-none" style={{ color: BONE }}>
          <option value="all">Todo disparador</option>
          {disparadores.map(d => <option key={d} value={d}>{d}</option>)}
        </select>
        <span className="text-xs ml-auto" style={{ color: MUTED }}>{rows.length.toLocaleString("es-AR")} alertas</span>
      </div>

      {pages > 1 && (
        <div className="flex items-center justify-end gap-2 text-xs" style={{ color: MUTED }}>
          <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} className="px-2 py-1 rounded disabled:opacity-40" style={{ border: `1px solid ${LINE}` }}>←</button>
          <span>{page + 1} / {pages}</span>
          <button onClick={() => setPage(p => Math.min(pages - 1, p + 1))} disabled={page >= pages - 1} className="px-2 py-1 rounded disabled:opacity-40" style={{ border: `1px solid ${LINE}` }}>→</button>
        </div>
      )}

      <div className="rounded-xl overflow-hidden" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: "#12161F", borderBottom: `1px solid ${LINE}` }}>
                {["Alerta", "Fecha", "Entidad", "Disparador", "Prioridad", "Estado", "Disposición", ""].map(h => (
                  <th key={h} className="px-3 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider" style={{ color: MUTED }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pageRows.map((a, i) => {
                const est = ESTADO[a.estado] ?? ESTADO.auto_cerrada;
                return (
                  <tr key={a.alert_id} style={{ borderBottom: i < pageRows.length - 1 ? `1px solid ${LINE}` : undefined }} className="hover:bg-[#12161F]">
                    <td className="px-3 py-2 text-[11px] font-mono" style={{ color: MUTED }}>{a.alert_id}</td>
                    <td className="px-3 py-2 text-[11px] whitespace-nowrap" style={{ color: "#8A93A6" }}>{fdate(a.fecha)}</td>
                    <td className="px-3 py-2">
                      <p className="text-xs" style={{ color: BONE }}>{a.entidad}</p>
                      <p className="text-[10px] font-mono" style={{ color: MUTED }}>{a.account_id}</p>
                    </td>
                    <td className="px-3 py-2">
                      <p className="text-[11px]" style={{ color: BONE }}>{a.disparador}</p>
                      <p className="text-[10px]" style={{ color: MUTED }}>{a.detalle}</p>
                    </td>
                    <td className="px-3 py-2"><span className="text-xs font-bold" style={{ color: a.prioridad >= 60 ? "#EF4444" : a.prioridad >= 35 ? "#F59E0B" : MUTED }}>{a.prioridad}</span></td>
                    <td className="px-3 py-2"><span className="rounded-full px-2 py-0.5 text-[10px] font-semibold whitespace-nowrap" style={{ background: `${est.color}22`, color: est.color }}>{est.label}</span></td>
                    <td className="px-3 py-2 text-[11px]" style={{ color: a.is_fraud ? "#F87171" : MUTED }}>{a.disposicion}</td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {a.caso_ref
                        ? <Link href={`/app/casos/${a.caso_ref}`} className="text-[11px]" style={{ color: "#7AA2FF" }}>{a.caso_ref} →</Link>
                        : <Link href={`/app/clientes/${a.account_id}`} className="text-[11px]" style={{ color: MUTED }}>legajo →</Link>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
