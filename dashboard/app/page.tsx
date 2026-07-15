import KPICard from "@/components/KPICard";
import PRCurveChart from "@/components/PRCurveChart";
import ScoreDistChart from "@/components/ScoreDistChart";
import PageHeader from "@/components/PageHeader";
import type { KPIs, PRCurve, ScoreDistribution } from "@/lib/types";

import kpisRaw   from "@/public/data/kpis.json";
import curvesRaw from "@/public/data/pr_curves.json";
import distRaw   from "@/public/data/score_distribution.json";

const kpis:   KPIs              = kpisRaw as KPIs;
const curves: PRCurve[]         = curvesRaw as PRCurve[];
const dist:   ScoreDistribution = distRaw as ScoreDistribution;

const insights = [
  {
    tag: "Señal estructural",
    text: "Lift fraude→fraude de 14.3× sobre el esperado por azar. El lavado no se detecta por monto — se detecta por patrón de red.",
  },
  {
    tag: "Score crediticio ciego",
    text: "Cohen d = 0.055 entre cuentas fraude y legítimas. El riesgo crediticio es ortogonal al riesgo AML.",
  },
  {
    tag: "Ventana de 72 h",
    text: "Los anillos completan sus ciclos antes de que activen los sistemas de monitoreo batch diario.",
  },
];

export default function OverviewPage() {
  const sageCurve = curves.find(c => c.model === "GraphSAGE");
  const xgbCurve  = curves.find(c => c.model === "XGBoost");
  const delta     = ((sageCurve?.pr_auc ?? 1) - (xgbCurve?.pr_auc ?? 0)).toFixed(3);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Banco Regional del Sur · Engagement simulado"
        title="Detección de Redes de Lavado mediante GNNs"
        description="GraphSAGE sobre grafo transaccional sintético — prueba de concepto end-to-end · Germán Cárdenas · 2026"
      />

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KPICard
          label="Cuentas analizadas"
          value={kpis.n_accounts.toLocaleString("es-AR")}
          sub={`${kpis.n_fraud} fraudulentas · ${kpis.pct_fraud}% prevalencia`}
          color="#6B8CC7"
          dim
        />
        <KPICard
          label="PR-AUC — GraphSAGE"
          value={kpis.pr_auc_gnn.toFixed(3)}
          sub={`+${delta} sobre XGBoost tabular`}
        />
        <KPICard
          label="Recall @ Precisión 90%"
          value={(kpis.recall_at_p90 * 100).toFixed(0) + "%"}
          sub="Con 9/10 alertas correctas"
        />
        <KPICard
          label="Fraude no detectado"
          value="0%"
          sub="vs 20% con XGBoost y LogReg"
          color="#27AE60"
        />
      </div>

      {/* Charts — 2 column */}
      <div className="grid lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3 rounded-xl border border-white/8 p-5"
             style={{ backgroundColor: "#0d1e38" }}>
          <p className="text-[11px] font-bold uppercase tracking-widest text-white/35 mb-1">
            Comparativa de modelos
          </p>
          <h2 className="text-sm font-semibold text-white mb-4">Curva Precisión-Recall</h2>
          <PRCurveChart curves={curves} />
          <p className="text-xs text-white/30 mt-3 leading-relaxed">
            El GNN supera en <span className="text-white/60">+{delta} PR-AUC</span> al mejor baseline tabular (XGBoost).
            La curva perfecta llega a PR-AUC=1.0 en evaluación transductiva; 0.835 en evaluación inductiva.
          </p>
        </div>

        <div className="lg:col-span-2 rounded-xl border border-white/8 p-5"
             style={{ backgroundColor: "#0d1e38" }}>
          <p className="text-[11px] font-bold uppercase tracking-widest text-white/35 mb-1">
            Separabilidad
          </p>
          <h2 className="text-sm font-semibold text-white mb-4">Distribución de Scores GNN</h2>
          <ScoreDistChart dist={dist} />
          <p className="text-xs text-white/30 mt-3 leading-relaxed">
            Separación casi perfecta: legítimas → 0, fraude → 1.
          </p>
        </div>
      </div>

      {/* Insights */}
      <div>
        <p className="text-[11px] font-bold uppercase tracking-widest text-white/35 mb-3">
          Hallazgos clave
        </p>
        <div className="grid md:grid-cols-3 gap-3">
          {insights.map(ins => (
            <div key={ins.tag}
                 className="rounded-xl border border-white/8 p-5 space-y-2 hover:border-white/15 transition-colors"
                 style={{ backgroundColor: "#0d1e38" }}>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: "#C9A227" }} />
                <span className="text-[11px] font-bold uppercase tracking-widest"
                      style={{ color: "#C9A227" }}>
                  {ins.tag}
                </span>
              </div>
              <p className="text-sm text-white/60 leading-relaxed">{ins.text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
