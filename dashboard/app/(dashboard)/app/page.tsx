import KPICard from "@/components/KPICard";
import PRCurveChart from "@/components/PRCurveChart";
import ScoreDistChart from "@/components/ScoreDistChart";
import PageHeader from "@/components/PageHeader";
import InfoTooltip from "@/components/InfoTooltip";
import SystemPulseCard from "@/components/SystemPulseCard";
import PatternDonut from "@/components/PatternDonut";
import AlertsAreaChart from "@/components/AlertsAreaChart";
import { casesByPattern, casesByMonth } from "@/lib/caseAggregates";
import { isBlindSpot } from "@/lib/kyc";
import type { KPIs, PRCurve, ScoreDistribution, Case } from "@/lib/types";

import kpisRaw     from "@/public/data/kpis.json";
import curvesRaw   from "@/public/data/pr_curves.json";
import distRaw     from "@/public/data/score_distribution.json";
import temporalRaw from "@/public/data/temporal_eval.json";
import casesRaw     from "@/public/data/cases.json";

const kpis:   KPIs              = kpisRaw as KPIs;
const curves: PRCurve[]         = curvesRaw as PRCurve[];
const dist:   ScoreDistribution = distRaw as ScoreDistribution;
const cases:  Case[]            = casesRaw as unknown as Case[];

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
    tooltip: "Lift: cuántas veces más probable es un evento respecto del azar. 14.3× significa que una cuenta conectada a una cuenta fraudulenta es 14 veces más propensa a ser fraude ella misma.",
  },
  {
    tag: "Score crediticio ciego",
    color: "#F59E0B",
    bg: "rgba(217,119,6,0.15)",
    text: "Cohen d = 0.055 entre cuentas fraude y legítimas. El riesgo crediticio es ortogonal al riesgo ALD.",
    tooltip: "Cohen d mide qué tan distintos son dos grupos. 0.055 es prácticamente cero: el score de riesgo crediticio no distingue cuentas fraudulentas de legítimas — por eso hace falta mirar la red, no el perfil.",
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
  const deltaNum    = (sageCurve?.pr_auc ?? 1) - (xgbCurve?.pr_auc ?? 0);
  const delta       = deltaNum.toFixed(3);

  const sageMissedPct   = Math.round((1 - kpis.recall_at_p90) * 100);
  const xgbMissedPct    = Math.round((1 - recallAtPrecision(xgbCurve, 0.9)) * 100);
  const logregMissedPct = Math.round((1 - recallAtPrecision(logregCurve, 0.9)) * 100);

  const transductivePrAuc = temporal.conditions.random_transductive?.pr_auc;
  const inductivePrAuc    = temporal.conditions.random_inductive?.pr_auc;

  const patternCounts   = casesByPattern(cases);
  const monthlyCounts   = casesByMonth(cases);
  const casosAbiertos   = cases.filter(c => c.status === "abierto").length;
  const pctBlindSpot    = cases.length ? cases.filter(c => isBlindSpot(c.risk_score, c.gnn_score)).length / cases.length : 0;
  const pctScreeningOk  = cases.length ? 1 - cases.filter(c => c.screening.hit_directo?.estado === "pendiente").length / cases.length : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Banco Regional del Sur · Engagement simulado"
        title="Detección de Redes de Lavado mediante GNNs"
        description="GraphSAGE sobre grafo transaccional sintético — prueba de concepto end-to-end · Germán Cárdenas · 2026"
      />

      {/* Pulso del sistema + Casos por patrón */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3">
          <SystemPulseCard
            casosAbiertos={casosAbiertos}
            totalCasos={cases.length}
            sparkline={monthlyCounts}
            recallAtP90={kpis.recall_at_p90}
            prAucGnn={kpis.pr_auc_gnn}
            prAucDelta={deltaNum}
            pctBlindSpot={pctBlindSpot}
            pctScreeningOk={pctScreeningOk}
          />
        </div>
        <div
          className="lg:col-span-2 rounded-xl p-5"
          style={{ backgroundColor: "#0E1219", border: "1px solid #1E2430" }}
        >
          <p className="text-[11px] font-bold uppercase tracking-widest mb-1" style={{ color: "#5A6478", fontFamily: "'JetBrains Mono', monospace" }}>
            Cola de alertas
          </p>
          <h2 className="text-sm font-semibold mb-4" style={{ color: "#EDEAE6", fontFamily: "'Space Grotesk', sans-serif" }}>Casos por patrón</h2>
          <PatternDonut data={patternCounts} />
        </div>
      </div>

      {/* Evolución de alertas */}
      <div className="rounded-xl p-5" style={{ backgroundColor: "#0E1219", border: "1px solid #1E2430" }}>
        <p className="text-[11px] font-bold uppercase tracking-widest mb-1" style={{ color: "#5A6478", fontFamily: "'JetBrains Mono', monospace" }}>
          Serie temporal
        </p>
        <h2 className="text-sm font-semibold mb-4" style={{ color: "#EDEAE6", fontFamily: "'Space Grotesk', sans-serif" }}>Alertas generadas por mes</h2>
        <AlertsAreaChart data={monthlyCounts} />
      </div>

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
          tooltip="Área bajo la curva Precisión-Recall: qué tan bien el modelo distingue fraude de legítimo sin generar falsas alarmas. Cerca de 1.0 es excelente; al azar rondaría ~0.02 (la tasa base de fraude)."
        />
        <KPICard
          label="Recall @ Precisión 90%"
          value={(kpis.recall_at_p90 * 100).toFixed(0) + "%"}
          sub="Con 9/10 alertas correctas"
          color="#A78BFA"
          tooltip="Exigiendo que 9 de cada 10 alertas sean fraude real (precisión 90%), este es el porcentaje del fraude total que el modelo efectivamente detecta."
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
                {ins.tooltip && <InfoTooltip text={ins.tooltip} />}
              </div>
              <p className="text-sm leading-relaxed" style={{ color: "#5A6478" }}>{ins.text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
