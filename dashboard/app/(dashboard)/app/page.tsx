import KPICard from "@/components/KPICard";
import PRCurveChart from "@/components/PRCurveChart";
import ScoreDistChart from "@/components/ScoreDistChart";
import PageHeader from "@/components/PageHeader";
import type { KPIs, PRCurve, ScoreDistribution } from "@/lib/types";

import kpisRaw     from "@/public/data/kpis.json";
import curvesRaw   from "@/public/data/pr_curves.json";
import distRaw     from "@/public/data/score_distribution.json";
import temporalRaw from "@/public/data/temporal_eval.json";

const kpis:   KPIs              = kpisRaw as KPIs;
const curves: PRCurve[]         = curvesRaw as PRCurve[];
const dist:   ScoreDistribution = distRaw as ScoreDistribution;

type TemporalEval = { conditions: Record<string, { pr_auc: number }> };
const temporal = temporalRaw as TemporalEval;

/** Mirrors evaluate.py::recall_at_precision — highest recall where precision >= target. */
function recallAtPrecision(curve: PRCurve | undefined, target = 0.9): number {
  if (!curve) return 0;
  for (let i = 0; i < curve.precision.length; i++) {
    if (curve.precision[i] >= target) return curve.recall[i];
  }
  return 0;
}

const insights = [
  {
    tag: "Señal estructural",
    color: "#7AA2FF",
    bg: "rgba(46,107,255,0.15)",
    text: "Lift fraude→fraude de 14.3× sobre el esperado por azar. El lavado no se detecta por monto — se detecta por patrón de red.",
  },
  {
    tag: "Score crediticio ciego",
    color: "#F59E0B",
    bg: "rgba(217,119,6,0.15)",
    text: "Cohen d = 0.055 entre cuentas fraude y legítimas. El riesgo crediticio es ortogonal al riesgo AML.",
  },
  {
    tag: "Ventana de 72 h",
    color: "#EF4444",
    bg: "rgba(239,68,68,0.15)",
    text: "Los anillos completan sus ciclos antes de que activen los sistemas de monitoreo batch diario.",
  },
];

export default function OverviewPage() {
  const sageCurve   = curves.find(c => c.model === "GraphSAGE");
  const xgbCurve    = curves.find(c => c.model === "XGBoost");
  const logregCurve = curves.find(c => c.model === "Logistic Regression");
  const delta       = ((sageCurve?.pr_auc ?? 1) - (xgbCurve?.pr_auc ?? 0)).toFixed(3);

  const sageMissedPct   = Math.round((1 - kpis.recall_at_p90) * 100);
  const xgbMissedPct    = Math.round((1 - recallAtPrecision(xgbCurve, 0.9)) * 100);
  const logregMissedPct = Math.round((1 - recallAtPrecision(logregCurve, 0.9)) * 100);

  const transductivePrAuc = temporal.conditions.random_transductive?.pr_auc;
  const inductivePrAuc    = temporal.conditions.random_inductive?.pr_auc;

  return (
    <div className="space-y-6">
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
          color="#5A6478"
          dim
        />
        <KPICard
          label="PR-AUC — GraphSAGE"
          value={kpis.pr_auc_gnn.toFixed(3)}
          sub={`+${delta} sobre XGBoost tabular`}
          color="#2E6BFF"
        />
        <KPICard
          label="Recall @ Precisión 90%"
          value={(kpis.recall_at_p90 * 100).toFixed(0) + "%"}
          sub="Con 9/10 alertas correctas"
          color="#A78BFA"
        />
        <KPICard
          label="Fraude no detectado"
          value={`${sageMissedPct}%`}
          sub={`vs ${xgbMissedPct}% XGBoost · ${logregMissedPct}% LogReg`}
          color="#22C55E"
        />
      </div>

      {/* Charts */}
      <div className="grid lg:grid-cols-5 gap-4">
        <div
          className="lg:col-span-3 rounded-xl p-5"
          style={{
            backgroundColor: "#0E1219",
            border: "1px solid #1E2430",
          }}
        >
          <p className="text-[11px] font-bold uppercase tracking-widest mb-1" style={{ color: "#5A6478", fontFamily: "'JetBrains Mono', monospace" }}>
            Comparativa de modelos
          </p>
          <h2 className="text-sm font-semibold mb-4" style={{ color: "#EDEAE6", fontFamily: "'Space Grotesk', sans-serif" }}>Curva Precisión-Recall</h2>
          <PRCurveChart curves={curves} />
          <p className="text-xs mt-3 leading-relaxed" style={{ color: "#5A6478" }}>
            El GNN supera en{" "}
            <span style={{ color: "#7AA2FF", fontWeight: 600 }}>+{delta} PR-AUC</span>{" "}
            al mejor baseline tabular (XGBoost).
            Evaluación transductiva: {transductivePrAuc?.toFixed(3)} · Inductiva (cuentas nuevas): {inductivePrAuc?.toFixed(3)}.
          </p>
        </div>

        <div
          className="lg:col-span-2 rounded-xl p-5"
          style={{
            backgroundColor: "#0E1219",
            border: "1px solid #1E2430",
          }}
        >
          <p className="text-[11px] font-bold uppercase tracking-widest mb-1" style={{ color: "#5A6478", fontFamily: "'JetBrains Mono', monospace" }}>
            Separabilidad
          </p>
          <h2 className="text-sm font-semibold mb-4" style={{ color: "#EDEAE6", fontFamily: "'Space Grotesk', sans-serif" }}>Distribución de Scores GNN</h2>
          <ScoreDistChart dist={dist} />
          <p className="text-xs mt-3 leading-relaxed" style={{ color: "#5A6478" }}>
            Separación casi perfecta: legítimas → 0, fraude → 1.
          </p>
        </div>
      </div>

      {/* Insights */}
      <div>
        <p className="text-[11px] font-bold uppercase tracking-widest mb-3" style={{ color: "#5A6478", fontFamily: "'JetBrains Mono', monospace" }}>
          Hallazgos clave
        </p>
        <div className="grid md:grid-cols-3 gap-3">
          {insights.map(ins => (
            <div
              key={ins.tag}
              className="rounded-xl p-5 space-y-2 transition-colors"
              style={{
                backgroundColor: "#0E1219",
                border: "1px solid #1E2430",
              }}
            >
              <div className="flex items-center gap-2">
                <span
                  className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
                  style={{ backgroundColor: ins.bg, color: ins.color }}
                >
                  {ins.tag}
                </span>
              </div>
              <p className="text-sm leading-relaxed" style={{ color: "#5A6478" }}>{ins.text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
