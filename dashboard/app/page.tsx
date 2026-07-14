import KPICard from "@/components/KPICard";
import PRCurveChart from "@/components/PRCurveChart";
import ScoreDistChart from "@/components/ScoreDistChart";
import type { KPIs, PRCurve, ScoreDistribution } from "@/lib/types";

import kpisRaw    from "@/public/data/kpis.json";
import curvesRaw  from "@/public/data/pr_curves.json";
import distRaw    from "@/public/data/score_distribution.json";

const kpis:   KPIs              = kpisRaw as KPIs;
const curves: PRCurve[]         = curvesRaw as PRCurve[];
const dist:   ScoreDistribution = distRaw as ScoreDistribution;

const insights = [
  {
    tag: "Hallazgo clave",
    text: "Las aristas fraude→fraude tienen un lift de 14.3x sobre el esperado por azar. La señal de lavado es estructural, no de monto individual.",
  },
  {
    tag: "Risk score externo",
    text: "Cohen d = 0.055 entre cuentas fraude y legítimas: el score crediticio es ciego al lavado estructurado. El problema es de red, no de perfil.",
  },
  {
    tag: "Ventana de 72 h",
    text: "Los anillos de lavado detectados completan sus ciclos en ventanas de 600 s a 72 h, antes de que activen los sistemas de monitoreo batch diario.",
  },
];

export default function OverviewPage() {
  const gnnCurve = curves.find(c => c.model === "GraphSAGE");

  return (
    <div className="space-y-8">
      {/* header */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-[#C9A227] mb-1">
          Banco Regional del Sur · Engagement simulado
        </p>
        <h1 className="text-2xl sm:text-3xl font-bold text-white">
          Detección de Redes de Lavado mediante GNNs
        </h1>
        <p className="mt-1 text-sm text-white/50">
          GraphSAGE sobre grafo transaccional sintético · Germán Cárdenas · 2026
        </p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard label="Cuentas analizadas" value={kpis.n_accounts.toLocaleString("es-AR")} sub={`${kpis.n_fraud} fraud nodes (${kpis.pct_fraud}%)`} />
        <KPICard label="PR-AUC — GraphSAGE" value={kpis.pr_auc_gnn.toFixed(3)} sub="Métrica primaria (clases desbalanceadas)" accent />
        <KPICard label="Recall @ Precision 90%" value={(kpis.recall_at_p90 * 100).toFixed(0) + "%"} sub="Con 9/10 alertas correctas, % fraude detectado" accent />
        <KPICard label="Fraude no detectado" value="0%" sub="vs 20% con XGBoost y LogReg" />
      </div>

      {/* PR curves */}
      <div className="rounded-xl border border-white/10 p-5" style={{ backgroundColor: "#122855" }}>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-white/60 mb-4">
          Curva Precisión-Recall — Comparativa de Modelos
        </h2>
        <PRCurveChart curves={curves} />
        <p className="text-xs text-white/40 mt-3">
          Cada punto representa un threshold de decisión. El área bajo la curva (PR-AUC) es la métrica principal
          en datasets desbalanceados. El GNN supera a XGBoost en {((gnnCurve?.pr_auc ?? 1) - (curves.find(c => c.model === "XGBoost")?.pr_auc ?? 0)).toFixed(3)} puntos de PR-AUC.
        </p>
      </div>

      {/* score distribution */}
      <div className="rounded-xl border border-white/10 p-5" style={{ backgroundColor: "#122855" }}>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-white/60 mb-4">
          Distribución de Scores GNN — Fraude vs. Legítimo
        </h2>
        <ScoreDistChart dist={dist} />
        <p className="text-xs text-white/40 mt-3">
          El modelo separa claramente las dos poblaciones: cuentas legítimas se acumulan cerca de 0,
          cuentas fraudulentas cerca de 1.
        </p>
      </div>

      {/* insights */}
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-white/60 mb-4">
          Insights de negocio
        </h2>
        <div className="grid md:grid-cols-3 gap-4">
          {insights.map(ins => (
            <div key={ins.tag} className="rounded-xl border p-5 space-y-2"
                 style={{ backgroundColor: "#122855", borderColor: "#C9A227" + "40" }}>
              <span className="text-xs font-bold uppercase tracking-wider text-[#C9A227]">{ins.tag}</span>
              <p className="text-sm text-white/75 leading-relaxed">{ins.text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
