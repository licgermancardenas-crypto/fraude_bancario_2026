"use client";
import { useState, useMemo } from "react";
import type { Account } from "@/lib/types";

interface Props { accounts: Account[] }

type SortKey = keyof Account;

export default function AccountsTable({ accounts }: Props) {
  const [search, setSearch]         = useState("");
  const [sortKey, setSortKey]       = useState<SortKey>("gnn_score");
  const [sortDir, setSortDir]       = useState<"asc" | "desc">("desc");
  const [filterFraud, setFilterFraud] = useState(false);
  const [page, setPage]             = useState(0);
  const PER_PAGE = 20;

  const sorted = useMemo(() => {
    let rows = accounts.filter(a => {
      const q = search.toLowerCase();
      return a.account_id.toLowerCase().includes(q) ||
             a.account_type.toLowerCase().includes(q);
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

  const pageRows  = sorted.slice(page * PER_PAGE, (page + 1) * PER_PAGE);
  const totalPages = Math.ceil(sorted.length / PER_PAGE);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
    setPage(0);
  };

  const th = (key: SortKey, label: string) => (
    <th key={key}
        className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider cursor-pointer whitespace-nowrap text-white/60 hover:text-white transition-colors select-none"
        onClick={() => toggleSort(key)}>
      {label} {sortKey === key ? (sortDir === "desc" ? "↓" : "↑") : ""}
    </th>
  );

  const scoreBadge = (score: number) => {
    const pct   = (score * 100).toFixed(1);
    const color = score > 0.7 ? "#C0392B" : score > 0.3 ? "#E67E22" : "#27AE60";
    return (
      <span className="inline-flex items-center gap-1.5 font-mono font-semibold" style={{ color }}>
        <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: color }} />
        {pct}%
      </span>
    );
  };

  return (
    <div className="space-y-4">
      {/* filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <input type="text" placeholder="Buscar por ID o tipo de cuenta…"
          value={search} onChange={e => { setSearch(e.target.value); setPage(0); }}
          className="flex-1 rounded-lg px-4 py-2 text-sm text-white placeholder-white/30 border border-white/10 outline-none focus:border-[#C9A227]"
          style={{ backgroundColor: "#122855" }} />
        <label className="flex items-center gap-2 text-sm text-white/60 cursor-pointer whitespace-nowrap">
          <input type="checkbox" checked={filterFraud}
            onChange={e => { setFilterFraud(e.target.checked); setPage(0); }}
            className="accent-[#C9A227]" />
          Solo fraude
        </label>
        <p className="text-xs text-white/30 self-center whitespace-nowrap">{sorted.length} cuentas</p>
      </div>

      {/* table */}
      <div className="rounded-xl border border-white/10 overflow-x-auto">
        <table className="w-full text-sm">
          <thead style={{ backgroundColor: "#0d2554" }}>
            <tr>
              {th("gnn_score",    "Score GNN")}
              {th("account_id",   "Cuenta")}
              {th("is_fraud",     "Fraude")}
              {th("account_type", "Tipo")}
              {th("balance",      "Balance")}
              {th("degree_in",    "Grado in")}
              {th("degree_out",   "Grado out")}
              {th("total_sent",   "Total enviado")}
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white/60">Anillo</th>
            </tr>
          </thead>
          <tbody>
            {pageRows.map((a, i) => (
              <tr key={a.account_id}
                  className={`border-t border-white/5 hover:bg-white/5 transition-colors ${a.is_fraud ? "bg-red-900/10" : ""}`}>
                <td className="px-4 py-3">{scoreBadge(a.gnn_score)}</td>
                <td className="px-4 py-3 font-mono text-xs text-white/70">{a.account_id}</td>
                <td className="px-4 py-3">
                  {a.is_fraud
                    ? <span className="text-xs font-bold text-red-400">SÍ</span>
                    : <span className="text-xs text-white/30">no</span>}
                </td>
                <td className="px-4 py-3 capitalize text-white/60">{a.account_type}</td>
                <td className="px-4 py-3 font-mono text-xs">
                  ${a.balance.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                </td>
                <td className="px-4 py-3 text-center text-white/70">{a.degree_in}</td>
                <td className="px-4 py-3 text-center text-white/70">{a.degree_out}</td>
                <td className="px-4 py-3 font-mono text-xs">
                  ${a.total_sent.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                </td>
                <td className="px-4 py-3">
                  {a.in_ring
                    ? <span className="text-xs font-semibold text-[#C9A227]">Sí</span>
                    : <span className="text-xs text-white/20">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-white/40">
          <button onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="px-3 py-1.5 rounded border border-white/10 disabled:opacity-30 hover:bg-white/5 transition-colors">
            ← Anterior
          </button>
          <span>Pág. {page + 1} de {totalPages}</span>
          <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                  disabled={page === totalPages - 1}
                  className="px-3 py-1.5 rounded border border-white/10 disabled:opacity-30 hover:bg-white/5 transition-colors">
            Siguiente →
          </button>
        </div>
      )}
    </div>
  );
}
