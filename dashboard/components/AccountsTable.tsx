"use client";
import { useState, useMemo } from "react";
import type { Account } from "@/lib/types";

interface Props { accounts: Account[] }
type SortKey = keyof Account;

function ScoreBar({ score }: { score: number }) {
  const color = score > 0.7 ? "#C0392B" : score > 0.3 ? "#E67E22" : "#27AE60";
  const label = (score * 100).toFixed(1) + "%";
  return (
    <div className="flex items-center gap-2 min-w-[100px]">
      <div className="flex-1 h-1.5 rounded-full bg-white/8 overflow-hidden">
        <div className="h-full rounded-full transition-all"
             style={{ width: `${score * 100}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs font-mono font-semibold w-11 text-right" style={{ color }}>
        {label}
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
    <th className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-widest cursor-pointer whitespace-nowrap text-white/35 hover:text-white/70 transition-colors select-none"
        onClick={() => toggleSort(k)}>
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
          className="flex-1 rounded-lg px-4 py-2 text-sm text-white placeholder-white/25 border border-white/8 outline-none focus:border-[#C9A227]/60 transition-colors"
          style={{ backgroundColor: "#0a1628" }}
        />
        <label className="flex items-center gap-2 text-sm text-white/50 cursor-pointer whitespace-nowrap">
          <input type="checkbox" checked={filterFraud}
                 onChange={e => { setFilterFraud(e.target.checked); setPage(0); }}
                 className="accent-[#C9A227]" />
          Solo fraude
        </label>
        <span className="text-xs text-white/25 whitespace-nowrap">{sorted.length} cuentas</span>
      </div>

      {/* table */}
      <div className="rounded-xl border border-white/8 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr style={{ backgroundColor: "#0a1628" }}>
              <th className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-widest text-white/25 w-10">#</th>
              <Th k="gnn_score"    label="Score GNN" />
              <Th k="account_id"   label="Cuenta" />
              <Th k="is_fraud"     label="Fraude" />
              <Th k="account_type" label="Tipo" />
              <Th k="balance"      label="Balance" />
              <Th k="degree_in"    label="Grado in" />
              <Th k="degree_out"   label="Grado out" />
              <Th k="total_sent"   label="Enviado" />
              <th className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-widest text-white/25">Anillo</th>
            </tr>
          </thead>
          <tbody>
            {pageRows.map((a, i) => {
              const rank   = globalStart + i + 1;
              const isFraud = a.is_fraud === 1;
              return (
                <tr key={a.account_id}
                    className="border-t border-white/5 hover:bg-white/4 transition-colors group"
                    style={isFraud ? { borderLeft: "2px solid #C0392B" } : {}}>
                  <td className="px-4 py-3 text-xs text-white/20 font-mono">{rank}</td>
                  <td className="px-4 py-3">
                    <ScoreBar score={a.gnn_score} />
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-white/55">{a.account_id}</td>
                  <td className="px-4 py-3">
                    {isFraud
                      ? <span className="inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-full"
                               style={{ backgroundColor: "#C0392B22", color: "#E57373" }}>
                          ● Sí
                        </span>
                      : <span className="text-xs text-white/20">—</span>}
                  </td>
                  <td className="px-4 py-3 capitalize text-xs text-white/45">{a.account_type}</td>
                  <td className="px-4 py-3 font-mono text-xs text-white/55">
                    ${a.balance.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                  </td>
                  <td className="px-4 py-3 text-center text-xs text-white/50">{a.degree_in}</td>
                  <td className="px-4 py-3 text-center text-xs text-white/50">{a.degree_out}</td>
                  <td className="px-4 py-3 font-mono text-xs text-white/50">
                    ${a.total_sent.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                  </td>
                  <td className="px-4 py-3">
                    {a.in_ring
                      ? <span className="text-xs font-semibold" style={{ color: "#C9A227" }}>Sí</span>
                      : <span className="text-xs text-white/15">—</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-white/35">
          <button onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="px-3 py-1.5 rounded-lg border border-white/8 disabled:opacity-25 hover:bg-white/5 hover:text-white/60 transition-colors">
            ← Anterior
          </button>
          <span className="font-mono">{page + 1} / {totalPages}</span>
          <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                  disabled={page === totalPages - 1}
                  className="px-3 py-1.5 rounded-lg border border-white/8 disabled:opacity-25 hover:bg-white/5 hover:text-white/60 transition-colors">
            Siguiente →
          </button>
        </div>
      )}
    </div>
  );
}
