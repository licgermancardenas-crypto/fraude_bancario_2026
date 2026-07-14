import AccountsTable from "@/components/AccountsTable";
import type { Account } from "@/lib/types";
import accountsRaw from "@/public/data/top_accounts.json";

const accounts: Account[] = accountsRaw as Account[];

export default function CuentasPage() {
  const nFraud = accounts.filter(a => a.is_fraud).length;

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-[#C9A227] mb-1">Cola de trabajo</p>
        <h1 className="text-2xl font-bold text-white">Ranking de Riesgo — Top {accounts.length} Cuentas</h1>
        <p className="text-sm text-white/50 mt-1">
          Ordenadas por score de riesgo GNN descendente. {nFraud} cuentas marcadas como fraude en el dataset.
          Filtrá, buscá o reordenás por cualquier columna.
        </p>
      </div>

      <div className="rounded-xl border border-white/10 p-5" style={{ backgroundColor: "#122855" }}>
        <AccountsTable accounts={accounts} />
      </div>

      <div className="rounded-xl border border-white/10 p-4 text-xs text-white/40"
           style={{ backgroundColor: "#0d2554" }}>
        <span className="text-[#C9A227] font-semibold">Nota operativa:</span>{" "}
        En producción, esta tabla sería la "cola de trabajo" del equipo de compliance de BRS.
        Los analistas revisarían las cuentas de mayor score en orden descendente, con una meta
        de 90% de precisión (9 de cada 10 revisiones deben confirmar fraude).
      </div>
    </div>
  );
}
