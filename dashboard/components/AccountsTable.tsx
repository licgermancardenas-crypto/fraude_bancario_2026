"use client";
import { useState, useMemo } from "react";
import type { Account } from "@/lib/types";

interface Props { accounts: Account[] }

function ScoreBar({ score }: { score: number }) {
  const color = score > 0.7 ? "#DC2626" : score > 0.3 ? "#D97706" : "#16A34A";
  const bg    = score > 0.7 ? "#FEE2E2" : score > 0.3 ? "#FEF3C7" : "#DCFCE7";
  return (
    <div className="flex items-center gap-2 min-w-[110px]">
      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: bg }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${score * 100}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs font-mono font-semibold w-11 text-right" style={{ color }}>
        {(score * 100).toFixed(1)}%
      </span>
    </div>
  );
}

function AfipBadge({ cond, cat }: { cond?: string; cat?: string | null }) {
  if (!cond) return <span className="text-xs" style={{ color: "#CBD5E1" }}>—</span>;
  const map: Record<string, { bg: string; color: string; short: string }> = {
    "Monotributista":          { bg: "#EFF6FF", color: "#2563EB", short: cat ? `Mono ${cat}` : "Mono" },
    "Responsable Inscripto":   { bg: "#F0FDF4", color: "#16A34A", short: "RI" },
    "Relación de dependencia": { bg: "#F8FAFC", color: "#64748B", short: "RD" },
    "No inscripto":            { bg: "#FEF3C7", color: "#D97706", short: "No inscr." },
    "Exento":                  { bg: "#F5F3FF", color: "#7C3AED", short: "Exento" },
  };
  const style = map[cond] ?? { bg: "#F1F5F9", color: "#94A3B8", short: cond.slice(0, 6) };
  return (
    <span className="inline-block px-2 py-0.5 rounded text-[11px] font-semibold whitespace-nowrap"
          style={{ backgroundColor: style.bg, color: style.color }}>
      {style.short}
    </span>
  );
}

type SortKey = keyof Account;

export default function AccountsTable({ accounts }: Props) {
  const [search, setSearch]           = useState("");
  const [sortKey, setSortKey]         = useState<SortKey>("gnn_score");
  const [sortDir, setSortDir]         = useState<"asc" | "desc">("desc");
  const [filterFraud, setFilterFraud] = useState(false);
  const [page, setPage]               = useState(0);
  const PER_PAGE = 20;

  const sorted = useMemo(() => {
    const q = search.toLowerCase();
    let rows = accounts.filter(a => {
      if (!q) return true;
      return (
        a.account_id.toLowerCase().includes(q) ||
        (a.nombre_completo ?? "").toLowerCase().includes(q) ||
        String(a.dni ?? "").includes(q) ||
        (a.ocupacion ?? "").toLowerCase().includes(q) ||
        (a.municipio ?? "").toLowerCase().includes(q) ||
        (a.provincia ?? "").toLowerCase().includes(q)
      );
    });
    if (filterFraud) rows = rows.filter(a => a.is_fraud === 1);
    rows.sort((a, b) => {
      const va = a[sortKey] as number | string | boolean;
      const vb = b[sortKey] as number | string | boolean;
      if (va < vb) return sortDir === "asc" ? -1 : 1;
      if (va > vb) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    return rows;
  }, [accounts, search, sortKey, sortDir, filterFraud]);

  const pageRows   = sorted.slice(page * PER_PAGE, (page + 1) * PER_PAGE);
  const totalPages = Math.ceil(sorted.length / PER_PAGE);
  const globalStart = page * PER_PAGE;

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
    setPage(0);
  };

  const Th = ({ k, label }: { k: SortKey; label: string }) => (
    <th
      className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-widest cursor-pointer whitespace-nowrap select-none"
      style={{ color: sortKey === k ? "#2563EB" : "#94A3B8" }}
      onClick={() => toggleSort(k)}
    >
      {label}{sortKey === k ? (sortDir === "desc" ? " ↓" : " ↑") : ""}
    </th>
  );

  return (
    <div className="space-y-4">
      {/* filters */}
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
        <input
          type="text"
          placeholder="Buscar por nombre, DNI, ocupación, ciudad…"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(0); }}
          className="flex-1 rounded-lg px-4 py-2 text-sm outline-none"
          style={{ backgroundColor: "#F8FAFC", border: "1px solid #E2E8F0", color: "#0F172A" }}
          onFocus={e => (e.target.style.borderColor = "#2563EB")}
          onBlur={e  => (e.target.style.borderColor = "#E2E8F0")}
        />
        <label className="flex items-center gap-2 text-sm cursor-pointer whitespace-nowrap" style={{ color: "#64748B" }}>
          <input type="checkbox" checked={filterFraud}
                 onChange={e => { setFilterFraud(e.target.checked); setPage(0); }}
                 className="accent-blue-600" />
          Solo fraude
        </label>
        <span className="text-xs whitespace-nowrap" style={{ color: "#94A3B8" }}>{sorted.length} cuentas</span>
      </div>

      {/* table */}
      <div className="rounded-xl overflow-x-auto" style={{ border: "1px solid #E2E8F0", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
        <table className="w-full text-sm" style={{ backgroundColor: "#FFFFFF" }}>
          <thead>
            <tr style={{ backgroundColor: "#F8FAFC", borderBottom: "1px solid #E2E8F0" }}>
              <th className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-widest w-8" style={{ color: "#94A3B8" }}>#</th>
              <Th k="nombre_completo" label="Titular" />
              <Th k="gnn_score"       label="Score GNN" />
              <Th k="is_fraud"        label="Fraude" />
              <Th k="condicion_afip"  label="AFIP" />
              <Th k="balance"         label="Balance" />
              <Th k="degree_in"       label="Grado" />
              <Th k="total_sent"      label="Enviado" />
              <th className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-widest" style={{ color: "#94A3B8" }}>Anillo</th>
            </tr>
          </thead>
          <tbody>
            {pageRows.map((a, i) => {
              const rank    = globalStart + i + 1;
              const isFraud = a.is_fraud === 1;
              return (
                <tr
                  key={a.account_id}
                  className="transition-colors"
                  style={{
                    borderTop: "1px solid #F1F5F9",
                    borderLeft: isFraud ? "3px solid #DC2626" : "3px solid transparent",
                  }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = "#F8FAFC")}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = "transparent")}
                >
                  <td className="px-4 py-3 text-xs font-mono" style={{ color: "#CBD5E1" }}>{rank}</td>

                  {/* Titular — nombre + DNI + ocupacion/ciudad */}
                  <td className="px-4 py-3 min-w-[200px]">
                    {a.nombre_completo ? (
                      <div>
                        <p className="text-sm font-semibold leading-tight" style={{ color: "#0F172A" }}>
                          {a.nombre_completo}
                        </p>
                        <p className="text-[11px] font-mono leading-tight mt-0.5" style={{ color: "#94A3B8" }}>
                          DNI {a.dni?.toLocaleString("es-AR")} · {a.account_id}
                        </p>
                        {a.ocupacion && (
                          <p className="text-[11px] leading-tight mt-0.5" style={{ color: "#64748B" }}>
                            {a.ocupacion} · {a.municipio}
                          </p>
                        )}
                      </div>
                    ) : (
                      <span className="font-mono text-xs" style={{ color: "#0F172A" }}>{a.account_id}</span>
                    )}
                  </td>

                  <td className="px-4 py-3"><ScoreBar score={a.gnn_score} /></td>

                  <td className="px-4 py-3">
                    {isFraud
                      ? <span className="inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-full"
                               style={{ backgroundColor: "#FEE2E2", color: "#DC2626" }}>● Sí</span>
                      : <span className="text-xs" style={{ color: "#CBD5E1" }}>—</span>}
                  </td>

                  <td className="px-4 py-3">
                    <AfipBadge cond={a.condicion_afip} cat={a.categoria_mono} />
                  </td>

                  <td className="px-4 py-3 font-mono text-xs" style={{ color: "#0F172A" }}>
                    ${a.balance.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                  </td>

                  <td className="px-4 py-3 text-center text-xs" style={{ color: "#64748B" }}>
                    <span title="Grado de entrada">{a.degree_in}</span>
                    <span style={{ color: "#CBD5E1" }}>/</span>
                    <span title="Grado de salida">{a.degree_out}</span>
                  </td>

                  <td className="px-4 py-3 font-mono text-xs" style={{ color: "#64748B" }}>
                    ${a.total_sent.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                  </td>

                  <td className="px-4 py-3">
                    {a.in_ring
                      ? <span className="text-xs font-bold" style={{ color: "#2563EB" }}>Sí</span>
                      : <span className="text-xs" style={{ color: "#CBD5E1" }}>—</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs" style={{ color: "#64748B" }}>
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-3 py-1.5 rounded-lg transition-colors disabled:opacity-30"
            style={{ border: "1px solid #E2E8F0", backgroundColor: "#FFFFFF" }}
          >
            ← Anterior
          </button>
          <span className="font-mono">{page + 1} / {totalPages}</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
            disabled={page === totalPages - 1}
            className="px-3 py-1.5 rounded-lg transition-colors disabled:opacity-30"
            style={{ border: "1px solid #E2E8F0", backgroundColor: "#FFFFFF" }}
          >
            Siguiente →
          </button>
        </div>
      )}
    </div>
  );
}
