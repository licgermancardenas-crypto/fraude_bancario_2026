"use client";

import { useEffect, useMemo, useState } from "react";
import PageHeader from "@/components/PageHeader";

const PANEL = "#0E1219", LINE = "#1E2430", BONE = "#EDEAE6", MUTED = "#5A6478";

interface Txn {
  id: string; ts: number; src: string; dst: string; src_name: string; dst_name: string;
  src_type: string; dst_type: string; amount: number; tipo: string; canal: string; concepto: string; moneda: string; is_fraud: number;
}

const fdt = (ts: number) => new Date(ts * 1000).toLocaleString("es-AR", { day: "2-digit", month: "2-digit", year: "2-digit", hour: "2-digit", minute: "2-digit" });
const money = (n: number) => "$ " + n.toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const PAGE = 40;

type SortCol = "ts" | "amount";

export default function TransaccionesPage() {
  const [txns, setTxns] = useState<Txn[]>([]);
  const [q, setQ] = useState("");
  const [tipo, setTipo] = useState("all");
  const [canal, setCanal] = useState("all");
  const [min, setMin] = useState(""); const [max, setMax] = useState("");
  const [from, setFrom] = useState(""); const [to, setTo] = useState("");
  const [fraudOnly, setFraudOnly] = useState(false);
  const [sort, setSort] = useState<{ col: SortCol; dir: 1 | -1 }>({ col: "ts", dir: -1 });
  const [page, setPage] = useState(0);

  useEffect(() => {
    fetch("/data/transactions_sample.json").then(r => r.json()).then(setTxns);
    const urlq = new URLSearchParams(window.location.search).get("q");
    if (urlq) setQ(urlq);
  }, []);

  const canales = useMemo(() => Array.from(new Set(txns.map(t => t.canal))).sort(), [txns]);
  const tipos = useMemo(() => Array.from(new Set(txns.map(t => t.tipo))).sort(), [txns]);

  const filtered = useMemo(() => {
    const ql = q.trim().toLowerCase();
    const mn = min ? parseFloat(min) : -Infinity;
    const mx = max ? parseFloat(max) : Infinity;
    const tf = from ? new Date(from).getTime() / 1000 : -Infinity;
    const tt = to ? new Date(to).getTime() / 1000 + 86400 : Infinity;
    const res = txns.filter(t =>
      (!ql || t.src.toLowerCase().includes(ql) || t.dst.toLowerCase().includes(ql) ||
        t.src_name.toLowerCase().includes(ql) || t.dst_name.toLowerCase().includes(ql) ||
        t.concepto.toLowerCase().includes(ql) || t.id.toLowerCase().includes(ql)) &&
      (tipo === "all" || t.tipo === tipo) &&
      (canal === "all" || t.canal === canal) &&
      t.amount >= mn && t.amount <= mx && t.ts >= tf && t.ts <= tt &&
      (!fraudOnly || t.is_fraud === 1));
    res.sort((a, b) => (a[sort.col] - b[sort.col]) * sort.dir);
    return res;
  }, [txns, q, tipo, canal, min, max, from, to, fraudOnly, sort]);

  useEffect(() => setPage(0), [q, tipo, canal, min, max, from, to, fraudOnly]);

  const pageRows = filtered.slice(page * PAGE, page * PAGE + PAGE);
  const pages = Math.ceil(filtered.length / PAGE);
  const totalAmount = useMemo(() => filtered.reduce((a, t) => a + t.amount, 0), [filtered]);

  const exportCsv = () => {
    const head = ["id", "fecha", "origen", "origen_nombre", "destino", "destino_nombre", "tipo", "canal", "concepto", "monto", "moneda", "fraude"];
    const lines = filtered.map(t => [t.id, new Date(t.ts * 1000).toISOString(), t.src, t.src_name, t.dst, t.dst_name, t.tipo, t.canal, t.concepto, t.amount, t.moneda, t.is_fraud]
      .map(v => `"${String(v).replace(/"/g, '""')}"`).join(","));
    const blob = new Blob([[head.join(","), ...lines].join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "transacciones.csv"; a.click(); URL.revokeObjectURL(a.href);
  };

  const sortBtn = (col: SortCol) => () => setSort(s => ({ col, dir: s.col === col ? (s.dir === 1 ? -1 : 1) : -1 }));
  const arrow = (col: SortCol) => sort.col === col ? (sort.dir === 1 ? " ▲" : " ▼") : "";
  const inp = "rounded-lg border border-[#1E2430] bg-[#12161F] px-2 min-h-[40px] text-sm outline-none";

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Exploración" title="Explorador de Transacciones"
        description="Tabla operativa con filtros avanzados por campo, rango de monto y fecha, canal y tipo. Exportá el resultado a CSV. Muestra representativa del libro transaccional." />

      {/* Filtros */}
      <div className="rounded-xl p-4 space-y-3" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
        <div className="flex flex-wrap gap-2 items-center">
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="Buscar por cuenta, nombre, concepto o ID…"
            className={inp + " flex-1 min-w-[220px]"} style={{ color: BONE }} />
          <select value={tipo} onChange={e => setTipo(e.target.value)} className={inp} style={{ color: BONE }}>
            <option value="all">Todo tipo</option>{tipos.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <select value={canal} onChange={e => setCanal(e.target.value)} className={inp} style={{ color: BONE }}>
            <option value="all">Todo canal</option>{canales.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <button onClick={exportCsv} className="rounded-lg px-3 min-h-[40px] text-sm font-medium" style={{ background: "rgba(34,197,94,0.12)", color: "#22C55E", border: "1px solid rgba(34,197,94,0.35)" }}>⭳ CSV</button>
        </div>
        <div className="flex flex-wrap gap-2 items-center text-xs" style={{ color: MUTED }}>
          <span>Monto:</span>
          <input value={min} onChange={e => setMin(e.target.value)} type="number" placeholder="mín" className={inp + " w-24"} style={{ color: BONE }} />
          <input value={max} onChange={e => setMax(e.target.value)} type="number" placeholder="máx" className={inp + " w-24"} style={{ color: BONE }} />
          <span className="ml-2">Fecha:</span>
          <input value={from} onChange={e => setFrom(e.target.value)} type="date" className={inp} style={{ color: BONE }} />
          <input value={to} onChange={e => setTo(e.target.value)} type="date" className={inp} style={{ color: BONE }} />
          <label className="flex items-center gap-1.5 ml-2 cursor-pointer" style={{ color: fraudOnly ? "#EF4444" : MUTED }}>
            <input type="checkbox" checked={fraudOnly} onChange={e => setFraudOnly(e.target.checked)} /> Solo fraudulentas
          </label>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs" style={{ color: MUTED }}>
        <span><b style={{ color: BONE }}>{filtered.length.toLocaleString("es-AR")}</b> transacciones · monto total <b style={{ color: BONE }}>{money(totalAmount)}</b></span>
        {pages > 1 && (
          <div className="flex items-center gap-2">
            <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} className="px-2 py-1 rounded disabled:opacity-40" style={{ border: `1px solid ${LINE}` }}>←</button>
            <span>{page + 1} / {pages}</span>
            <button onClick={() => setPage(p => Math.min(pages - 1, p + 1))} disabled={page >= pages - 1} className="px-2 py-1 rounded disabled:opacity-40" style={{ border: `1px solid ${LINE}` }}>→</button>
          </div>
        )}
      </div>

      <div className="rounded-xl overflow-hidden" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: "#12161F", borderBottom: `1px solid ${LINE}` }}>
                <th onClick={sortBtn("ts")} className="px-3 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider cursor-pointer whitespace-nowrap" style={{ color: MUTED }}>Fecha{arrow("ts")}</th>
                {["Origen", "Destino", "Tipo", "Canal", "Concepto"].map(h => (
                  <th key={h} className="px-3 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider" style={{ color: MUTED }}>{h}</th>
                ))}
                <th onClick={sortBtn("amount")} className="px-3 py-2.5 text-right text-[10px] font-semibold uppercase tracking-wider cursor-pointer whitespace-nowrap" style={{ color: MUTED }}>Monto{arrow("amount")}</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map((t, i) => (
                <tr key={t.id} className={t.is_fraud ? "bg-[#EF4444]/8" : ""} style={{ borderBottom: i < pageRows.length - 1 ? `1px solid ${LINE}` : undefined }}>
                  <td className="px-3 py-2 text-[11px] whitespace-nowrap" style={{ color: "#8A93A6" }}>{fdt(t.ts)}</td>
                  <td className="px-3 py-2">
                    <p className="text-xs" style={{ color: BONE }}>{t.src_name || t.src}</p>
                    <p className="text-[10px] font-mono" style={{ color: MUTED }}>{t.src} · {t.src_type}</p>
                  </td>
                  <td className="px-3 py-2">
                    <p className="text-xs" style={{ color: BONE }}>{t.dst_name || t.dst}</p>
                    <p className="text-[10px] font-mono" style={{ color: MUTED }}>{t.dst} · {t.dst_type}</p>
                  </td>
                  <td className="px-3 py-2 text-[11px]" style={{ color: MUTED }}>{t.tipo}</td>
                  <td className="px-3 py-2 text-[11px] whitespace-nowrap" style={{ color: MUTED }}>{t.canal}</td>
                  <td className="px-3 py-2 text-[11px] whitespace-nowrap" style={{ color: MUTED }}>{t.concepto}</td>
                  <td className="px-3 py-2 text-right text-xs font-semibold whitespace-nowrap" style={{ color: t.is_fraud ? "#F87171" : BONE }}>{money(t.amount)}</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={7} className="px-3 py-10 text-center text-sm" style={{ color: MUTED }}>Sin transacciones para los filtros aplicados.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
