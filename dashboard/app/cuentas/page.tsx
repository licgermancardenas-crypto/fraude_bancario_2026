import AccountsTable from "@/components/AccountsTable";
import PageHeader from "@/components/PageHeader";
import type { Account } from "@/lib/types";
import accountsRaw from "@/public/data/top_accounts.json";

const accounts: Account[] = accountsRaw as Account[];

export default function CuentasPage() {
  const nFraud = accounts.filter(a => a.is_fraud).length;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Cola de trabajo"
        title={`Ranking de Riesgo — Top ${accounts.length} Cuentas`}
        description={`Ordenadas por score GNN descendente. ${nFraud} marcadas como fraude en el dataset. Filtrá, buscá o reordenás por cualquier columna.`}
      />

      <div
        className="rounded-xl p-5"
        style={{
          backgroundColor: "#FFFFFF",
          border: "1px solid #E2E8F0",
          boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
        }}
      >
        <AccountsTable accounts={accounts} />
      </div>

      <div
        className="rounded-xl px-5 py-4 text-xs leading-relaxed"
        style={{ backgroundColor: "#EAEDF5", border: "1px solid #C7CFE2" }}
      >
        <span className="font-semibold" style={{ color: "#0A1F44" }}>Nota operativa — </span>
        <span style={{ color: "#122855" }}>
          En producción esta tabla es la cola de trabajo del equipo de compliance de BRS.
          Los analistas revisan en orden descendente con una meta de 90% de precisión
          (9 de cada 10 revisiones deben confirmar fraude).
        </span>
      </div>
    </div>
  );
}
