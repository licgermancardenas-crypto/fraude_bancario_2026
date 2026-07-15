"use client";
import { useState, useMemo } from "react";
import type { Account } from "@/lib/types";

interface Props { accounts: Account[] }
type SortKey = keyof Account;

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

export default function AccountsTable({ accounts }: Props) {
  const [search, setSearch]           = useState("");
  const [sortKey, setSortKey]         = useState<SortKey>("gnn_score");
  const [sortDir, setSortDir]         = useState<"asc" | "desc">("desc");
  const [filterFraud, setFilterFraud] = useState(false);
  const [page, setPage]               = useState(0);
  const PER_PAGE = 20;

  const sorted = useMemo(() => {
    let rows = accounts.filter(a => {
      const q = search.toLowerCase();
      return a.account_id.toLowerCase().includes(q) || a.account_type.toLowerCase().includes(q);
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
      className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-widest cursor-pointer whitespace-nowrap select-none transition-colors"
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
          placeholder="Buscar por ID o tipo…"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(0); }}
          className="flex-1 rounded-lg px-4 py-2 text-sm outline-none transition-colors"
          style={{
            backgroundColor: "#F8FAFC",
            border: "1px solid #E2E8F0",
            color: "#0F172A",
          }}
          onFocus={e => (e.target.style.borderColor = "#2563EB")}
          onBlur={e => (e.target.style.borderColor = "#E2E8F0")}
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
              <th className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-widest w-10" style={{ color: "#94A3B8" }}>#</th>
              <Th k="gnn_score"    label="Score GNN" />
              <Th k="account_id"   label="Cuenta" />
              <Th k="is_fraud"     label="Fraude" />
              <Th k="account_type" label="Tipo" />
              <Th k="balance"      label="Balance" />
              <Th k="degree_in"    label="Grado in" />
              <Th k="degree_out"   label="Grado out" />
              <Th k="total_sent"   label="Enviado" />
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
                  <td className="px-4 py-3"><ScoreBar score={a.gnn_score} /></td>
                  <td className="px-4 py-3 font-mono text-xs font-medium" style={{ color: "#0F172A" }}>{a.account_id}</td>
                  <td className="px-4 py-3">
                    {isFraud
                      ? <span className="inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-full"
                               style={{ backgroundColor: "#FEE2E2", color: "#DC2626" }}>
                          ● Sí
                        </span>
                      : <span className="text-xs" style={{ color: "#CBD5E1" }}>—</span>}
                  </td>
                  <td className="px-4 py-3 capitalize text-xs" style={{ color: "#64748B" }}>{a.account_type}</td>
                  <td className="px-4 py-3 font-mono text-xs" style={{ color: "#0F172A" }}>
                    ${a.balance.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                  </td>
                  <td className="px-4 py-3 text-center text-xs" style={{ color: "#64748B" }}>{a.degree_in}</td>
                  <td className="px-4 py-3 text-center text-xs" style={{ color: "#64748B" }}>{a.degree_out}</td>
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
            onMouseEnter={e => !page && (e.currentTarget.style.backgroundColor = "#F8FAFC")}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = "#FFFFFF")}
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
