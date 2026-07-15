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
    color: "#2563EB",
    bg: "#EFF6FF",
    text: "Lift fraude→fraude de 14.3× sobre el esperado por azar. El lavado no se detecta por monto — se detecta por patrón de red.",
  },
  {
    tag: "Score crediticio ciego",
    color: "#D97706",
    bg: "#FFFBEB",
    text: "Cohen d = 0.055 entre cuentas fraude y legítimas. El riesgo crediticio es ortogonal al riesgo AML.",
  },
  {
    tag: "Ventana de 72 h",
    color: "#DC2626",
    bg: "#FEF2F2",
    text: "Los anillos completan sus ciclos antes de que activen los sistemas de monitoreo batch diario.",
  },
];

export default function OverviewPage() {
  const sageCurve = curves.find(c => c.model === "GraphSAGE");
  const xgbCurve  = curves.find(c => c.model === "XGBoost");
  const delta     = ((sageCurve?.pr_auc ?? 1) - (xgbCurve?.pr_auc ?? 0)).toFixed(3);

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
          color="#64748B"
          dim
        />
        <KPICard
          label="PR-AUC — GraphSAGE"
          value={kpis.pr_auc_gnn.toFixed(3)}
          sub={`+${delta} sobre XGBoost tabular`}
          color="#2563EB"
        />
        <KPICard
          label="Recall @ Precisión 90%"
          value={(kpis.recall_at_p90 * 100).toFixed(0) + "%"}
          sub="Con 9/10 alertas correctas"
          color="#7C3AED"
        />
        <KPICard
          label="Fraude no detectado"
          value="0%"
          sub="vs 20% con XGBoost y LogReg"
          color="#16A34A"
        />
      </div>

      {/* Charts */}
      <div className="grid lg:grid-cols-5 gap-4">
        <div
          className="lg:col-span-3 rounded-xl p-5"
          style={{
            backgroundColor: "#FFFFFF",
            border: "1px solid #E2E8F0",
            boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
          }}
        >
          <p className="text-[11px] font-bold uppercase tracking-widest mb-1" style={{ color: "#94A3B8" }}>
            Comparativa de modelos
          </p>
          <h2 className="text-sm font-semibold mb-4" style={{ color: "#0F172A" }}>Curva Precisión-Recall</h2>
          <PRCurveChart curves={curves} />
          <p className="text-xs mt-3 leading-relaxed" style={{ color: "#94A3B8" }}>
            El GNN supera en{" "}
            <span style={{ color: "#2563EB", fontWeight: 600 }}>+{delta} PR-AUC</span>{" "}
            al mejor baseline tabular (XGBoost).
            Evaluación transductiva: 1.000 · Inductiva (cuentas nuevas): 0.835.
          </p>
        </div>

        <div
          className="lg:col-span-2 rounded-xl p-5"
          style={{
            backgroundColor: "#FFFFFF",
            border: "1px solid #E2E8F0",
            boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
          }}
        >
          <p className="text-[11px] font-bold uppercase tracking-widest mb-1" style={{ color: "#94A3B8" }}>
            Separabilidad
          </p>
          <h2 className="text-sm font-semibold mb-4" style={{ color: "#0F172A" }}>Distribución de Scores GNN</h2>
          <ScoreDistChart dist={dist} />
          <p className="text-xs mt-3 leading-relaxed" style={{ color: "#94A3B8" }}>
            Separación casi perfecta: legítimas → 0, fraude → 1.
          </p>
        </div>
      </div>

      {/* Insights */}
      <div>
        <p className="text-[11px] font-bold uppercase tracking-widest mb-3" style={{ color: "#94A3B8" }}>
          Hallazgos clave
        </p>
        <div className="grid md:grid-cols-3 gap-3">
          {insights.map(ins => (
            <div
              key={ins.tag}
              className="rounded-xl p-5 space-y-2 transition-shadow hover:shadow-md"
              style={{
                backgroundColor: "#FFFFFF",
                border: "1px solid #E2E8F0",
                boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
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
              <p className="text-sm leading-relaxed" style={{ color: "#64748B" }}>{ins.text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
