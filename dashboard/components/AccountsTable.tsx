"use client";
import { useState, useMemo } from "react";
import type { Account } from "@/lib/types";

interface Props { accounts: Account[] }

function ScoreBar({ score }: { score: number }) {
  const color = score > 0.7 ? "#EF4444" : score > 0.3 ? "#D97706" : "#22C55E";
  const bg    = score > 0.7 ? "rgba(239,68,68,0.15)" : score > 0.3 ? "rgba(217,119,6,0.15)" : "rgba(34,197,94,0.15)";
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
  if (!cond) return <span className="text-xs" style={{ color: "#5A6478" }}>—</span>;
  const map: Record<string, { bg: string; color: string; short: string }> = {
    "Monotributista":          { bg: "rgba(46,107,255,0.15)", color: "#7AA2FF", short: cat ? `Mono ${cat}` : "Mono" },
    "Responsable Inscripto":   { bg: "rgba(34,197,94,0.15)", color: "#22C55E", short: "RI" },
    "Relación de dependencia": { bg: "rgba(90,100,120,0.15)", color: "#8A93A6", short: "RD" },
    "No inscripto":            { bg: "rgba(217,119,6,0.15)", color: "#D97706", short: "No inscr." },
    "Exento":                  { bg: "rgba(124,58,237,0.15)", color: "#A78BFA", short: "Exento" },
  };
  const style = map[cond] ?? { bg: "rgba(90,100,120,0.15)", color: "#5A6478", short: cond.slice(0, 6) };
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

  const Th = ({ k, label }: { k: SortKey; label: string }) => {
    const active = sortKey === k;
    const ariaSort: "ascending" | "descending" | "none" =
      !active ? "none" : sortDir === "asc" ? "ascending" : "descending";
    return (
      <th
        className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-widest whitespace-nowrap"
        aria-sort={ariaSort}
      >
        <button
          type="button"
          onClick={() => toggleSort(k)}
          className="cursor-pointer select-none bg-transparent p-0"
          style={{ color: active ? "#7AA2FF" : "#5A6478" }}
        >
          {label}{active ? (sortDir === "desc" ? " ↓" : " ↑") : ""}
        </button>
      </th>
    );
  };

  return (
    <div className="space-y-4">
      {/* filters */}
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
        <input
          type="text"
          placeholder="Buscar por nombre, DNI, ocupación, ciudad…"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(0); }}
          className="flex-1 rounded-lg px-4 py-2.5 min-h-[44px] text-sm outline-none"
          style={{ backgroundColor: "#0E1219", border: "1px solid #1E2430", color: "#EDEAE6" }}
          onFocus={e => (e.target.style.borderColor = "#2E6BFF")}
          onBlur={e  => (e.target.style.borderColor = "#1E2430")}
        />
        <label className="flex items-center gap-2 text-sm cursor-pointer whitespace-nowrap min-h-[44px] px-1" style={{ color: "#5A6478" }}>
          <input type="checkbox" checked={filterFraud}
                 onChange={e => { setFilterFraud(e.target.checked); setPage(0); }}
                 className="accent-[#2E6BFF]" />
          Solo fraude
        </label>
        <span className="text-xs whitespace-nowrap" style={{ color: "#5A6478" }}>{sorted.length} cuentas</span>
      </div>

      {/* table */}
      <div className="rounded-xl overflow-x-auto" style={{ border: "1px solid #1E2430" }}>
        <table className="w-full text-sm" style={{ backgroundColor: "#0E1219" }}>
          <thead>
            <tr style={{ backgroundColor: "#12161F", borderBottom: "1px solid #1E2430" }}>
              <th className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-widest w-8" style={{ color: "#5A6478" }}>#</th>
              <Th k="nombre_completo" label="Titular" />
              <Th k="gnn_score"       label="Score GNN" />
              <Th k="is_fraud"        label="Fraude" />
              <Th k="condicion_afip"  label="AFIP" />
              <Th k="balance"         label="Balance" />
              <Th k="degree_in"       label="Grado" />
              <Th k="total_sent"      label="Enviado" />
              <th className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-widest" style={{ color: "#5A6478" }}>Anillo</th>
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
                    borderTop: "1px solid #1E2430",
                    borderLeft: isFraud ? "3px solid #EF4444" : "3px solid transparent",
                  }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = "#12161F")}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = "transparent")}
                >
                  <td className="px-4 py-3 text-xs font-mono" style={{ color: "#5A6478" }}>{rank}</td>

                  {/* Titular — nombre + DNI + ocupacion/ciudad */}
                  <td className="px-4 py-3 min-w-[200px]">
                    {a.nombre_completo ? (
                      <div>
                        <p className="text-sm font-semibold leading-tight" style={{ color: "#EDEAE6" }}>
                          {a.nombre_completo}
                        </p>
                        <p className="text-[11px] font-mono leading-tight mt-0.5" style={{ color: "#5A6478" }}>
                          DNI {a.dni?.toLocaleString("es-AR")} · {a.account_id}
                        </p>
                        {a.ocupacion && (
                          <p className="text-[11px] leading-tight mt-0.5" style={{ color: "#5A6478" }}>
                            {a.ocupacion} · {a.municipio}
                          </p>
                        )}
                      </div>
                    ) : (
                      <span className="font-mono text-xs" style={{ color: "#EDEAE6" }}>{a.account_id}</span>
                    )}
                  </td>

                  <td className="px-4 py-3"><ScoreBar score={a.gnn_score} /></td>

                  <td className="px-4 py-3">
                    {isFraud
                      ? <span className="inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-full"
                               style={{ backgroundColor: "rgba(239,68,68,0.15)", color: "#EF4444" }}>● Sí</span>
                      : <span className="text-xs" style={{ color: "#5A6478" }}>—</span>}
                  </td>

                  <td className="px-4 py-3">
                    <AfipBadge cond={a.condicion_afip} cat={a.categoria_mono} />
                  </td>

                  <td className="px-4 py-3 font-mono text-xs" style={{ color: "#EDEAE6" }}>
                    ${a.balance.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                  </td>

                  <td className="px-4 py-3 text-center text-xs" style={{ color: "#5A6478" }}>
                    <span title="Grado de entrada">{a.degree_in}</span>
                    <span style={{ color: "#3A4356" }}>/</span>
                    <span title="Grado de salida">{a.degree_out}</span>
                  </td>

                  <td className="px-4 py-3 font-mono text-xs" style={{ color: "#5A6478" }}>
                    ${a.total_sent.toLocaleString("es-AR", { maximumFractionDigits: 0 })}
                  </td>

                  <td className="px-4 py-3">
                    {a.in_ring
                      ? <span className="text-xs font-bold" style={{ color: "#7AA2FF" }}>Sí</span>
                      : <span className="text-xs" style={{ color: "#5A6478" }}>—</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs" style={{ color: "#5A6478" }}>
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-4 min-h-[44px] rounded-lg transition-colors disabled:opacity-30"
            style={{ border: "1px solid #1E2430", backgroundColor: "#12161F", color: "#EDEAE6" }}
          >
            ← Anterior
          </button>
          <span className="font-mono">{page + 1} / {totalPages}</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
            disabled={page === totalPages - 1}
            className="px-4 min-h-[44px] rounded-lg transition-colors disabled:opacity-30"
            style={{ border: "1px solid #1E2430", backgroundColor: "#12161F", color: "#EDEAE6" }}
          >
            Siguiente →
          </button>
        </div>
      )}
    </div>
  );
}
