import PageHeader from "@/components/PageHeader";
import MonitoringChart, { type MonthPoint } from "@/components/MonitoringChart";
import gov from "@/public/data/model_governance.json";

const PANEL = "#12161F", CARD = "#0E1219", LINE = "#1E2430", BONE = "#EDEAE6", MUTED = "#5A6478";

function psiColor(psi: number) {
  return psi < 0.1 ? "#22C55E" : psi < 0.25 ? "#F59E0B" : "#EF4444";
}

export default function GobernanzaPage() {
  const mc = gov.model_card;
  const uo = gov.umbral_operativo;
  const gv = gov.gobernanza;
  const monit = gov.monitoreo_mensual as MonthPoint[];
  const alertThreshold = Math.round((uo.objetivo_precision - 0.05) * 1000) / 1000; // caída de PR-AUC > 0.05

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Model Risk Management"
        title="Gobernanza y Monitoreo del Modelo"
        description="Ficha del modelo, performance en el tiempo, control de deriva (drift) y las tres líneas de defensa — lo que exige un marco de riesgo de modelos (SR 11-7 / BCBS 239) para sostener un modelo en producción."
      />

      {/* Model card */}
      <div className="rounded-xl p-5" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-base font-bold" style={{ color: BONE }}>{mc.nombre}</h2>
          <span className="rounded-full px-3 py-1 text-xs font-bold" style={{ background: "rgba(34,197,94,0.15)", color: "#22C55E", border: "1px solid rgba(34,197,94,0.4)" }}>
            {mc.estado}
          </span>
        </div>
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-6 gap-y-3">
          {[
            ["Modelo", mc.modelo], ["Versión", mc.version], ["Arquitectura", mc.arquitectura],
            ["Propósito", mc.proposito], ["Propietario", mc.propietario], ["Validado por", mc.validado_por],
            ["Entrenado", mc.fecha_entrenamiento], ["Dataset", mc.dataset],
            ["Tasa base de fraude", `${mc.tasa_base_fraude}%`], ["Features", String(mc.features)],
          ].map(([k, v]) => (
            <div key={k}>
              <div className="text-[10px] uppercase tracking-wide" style={{ color: MUTED }}>{k}</div>
              <div className="text-xs" style={{ color: BONE }}>{v}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Umbral operativo + robustez */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl p-5" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
          <h3 className="text-sm font-bold mb-3" style={{ color: BONE }}>Punto operativo</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              ["Precisión objetivo", `${(uo.objetivo_precision * 100).toFixed(0)}%`, "#7AA2FF"],
              ["Recall @ P90", `${(uo.recall * 100).toFixed(0)}%`, "#22C55E"],
              ["Alertas / día", String(uo.alertas_dia), BONE],
              ["Fraude no detectado", `${uo.fraude_no_detectado}%`, "#F59E0B"],
            ].map(([k, v, c]) => (
              <div key={k} className="rounded-lg p-3 text-center" style={{ background: CARD, border: `1px solid ${LINE}` }}>
                <div className="text-xl font-bold" style={{ color: c }}>{v}</div>
                <div className="text-[10px] mt-0.5" style={{ color: MUTED }}>{k}</div>
              </div>
            ))}
          </div>
          <p className="text-[11px] mt-3" style={{ color: MUTED }}>
            Umbral fijado en precisión ≥ 90%: de cada 10 alertas, 9 son fraude real.
          </p>
        </div>

        <div className="rounded-xl p-5" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
          <h3 className="text-sm font-bold mb-1" style={{ color: BONE }}>Robustez de la evaluación</h3>
          <p className="text-[11px] mb-3" style={{ color: MUTED }}>PR-AUC bajo tres regímenes — el temporal es el número operativo honesto.</p>
          <div className="grid grid-cols-3 gap-3">
            {[
              ["Transductivo", gov.robustez_evaluacion.transductivo, MUTED],
              ["Inductivo", gov.robustez_evaluacion.inductivo, "#7AA2FF"],
              ["Temporal", gov.robustez_evaluacion.temporal, "#22C55E"],
            ].map(([k, v, c]) => (
              <div key={k as string} className="rounded-lg p-3 text-center" style={{ background: CARD, border: `1px solid ${LINE}` }}>
                <div className="text-xl font-bold" style={{ color: c as string }}>{(v as number).toFixed(3)}</div>
                <div className="text-[10px] mt-0.5" style={{ color: MUTED }}>{k}</div>
              </div>
            ))}
          </div>
          <p className="text-[11px] mt-3" style={{ color: MUTED }}>
            transductivo → inductivo → temporal: la caída controlada confirma que el modelo aprende patrones estructurales estables.
          </p>
        </div>
      </div>

      {/* Monitoreo mensual */}
      <div className="rounded-xl p-5" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
        <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
          <h3 className="text-sm font-bold" style={{ color: BONE }}>Monitoreo de performance en el tiempo</h3>
          <span className="text-[11px]" style={{ color: MUTED }}>PR-AUC mensual · tasa de falsos positivos</span>
        </div>
        <MonitoringChart data={monit} alertThreshold={alertThreshold} />
        <div className="mt-3 rounded-lg p-3 text-[11px]" style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)", color: "#F87171" }}>
          ⚠ Incidente detectado en 2026-05: caída de PR-AUC a 0.93 y suba de la tasa de FP — disparó revisión de deriva de datos (ver PSI). El monitoreo continuo lo capturó antes de degradar la cola de casos.
        </div>
      </div>

      {/* Drift por feature */}
      <div className="rounded-xl p-5" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
        <div className="flex items-center justify-between flex-wrap gap-2 mb-1">
          <h3 className="text-sm font-bold" style={{ color: BONE }}>Control de deriva (drift) por feature</h3>
          <span className="text-[11px]" style={{ color: MUTED }}>PSI — Population Stability Index</span>
        </div>
        <p className="text-[11px] mb-3" style={{ color: MUTED }}>PSI &lt; 0.10 estable · 0.10–0.25 deriva moderada · &gt; 0.25 deriva significativa (reentrenar).</p>
        <div className="space-y-2">
          {gov.drift_features.map(f => (
            <div key={f.feature} className="flex items-center gap-3">
              <span className="w-40 shrink-0 font-mono text-[11px]" style={{ color: BONE }}>{f.feature}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full" style={{ background: CARD }}>
                <div className="h-full rounded-full" style={{ width: `${Math.min(100, (f.psi / 0.3) * 100)}%`, background: psiColor(f.psi) }} />
              </div>
              <span className="w-12 text-right text-[11px] font-semibold tabular-nums" style={{ color: psiColor(f.psi) }}>{f.psi.toFixed(2)}</span>
              <span className="w-32 shrink-0 text-[10px]" style={{ color: MUTED }}>{f.estado}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Champion / Challenger */}
      <div className="rounded-xl p-5" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
        <h3 className="text-sm font-bold mb-3" style={{ color: BONE }}>Champion / Challenger</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: `1px solid ${LINE}` }}>
                {["Modelo", "Rol", "PR-AUC", "ROC-AUC", "Recall@P90", "Alertas/día", "Fraude no det."].map(h => (
                  <th key={h} className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider" style={{ color: MUTED }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {gov.champion_challenger.map(m => {
                const isChamp = m.rol.startsWith("Campeón");
                return (
                  <tr key={m.modelo} style={{ borderBottom: `1px solid ${LINE}`, background: isChamp ? "rgba(46,107,255,0.06)" : undefined }}>
                    <td className="px-3 py-2 text-xs font-semibold" style={{ color: isChamp ? "#7AA2FF" : BONE }}>{m.modelo}</td>
                    <td className="px-3 py-2 text-[11px]" style={{ color: MUTED }}>{m.rol}</td>
                    <td className="px-3 py-2 text-xs font-bold" style={{ color: isChamp ? "#7AA2FF" : BONE }}>{m.pr_auc.toFixed(4)}</td>
                    <td className="px-3 py-2 text-xs" style={{ color: BONE }}>{m.roc_auc.toFixed(4)}</td>
                    <td className="px-3 py-2 text-xs" style={{ color: BONE }}>{(m.recall_p90 * 100).toFixed(0)}%</td>
                    <td className="px-3 py-2 text-xs" style={{ color: MUTED }}>{m.alertas_dia ?? "—"}</td>
                    <td className="px-3 py-2 text-xs" style={{ color: MUTED }}>{m.fraude_no_detectado != null ? `${m.fraude_no_detectado}%` : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Gobernanza: 3 líneas + limitaciones + controles */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl p-5" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
          <h3 className="text-sm font-bold mb-1" style={{ color: BONE }}>Tres líneas de defensa</h3>
          <div className="flex items-center gap-4 text-[11px] mb-3" style={{ color: MUTED }}>
            <span>Validación: <span style={{ color: "#22C55E" }}>{gv.estado_validacion}</span></span>
          </div>
          <div className="space-y-2">
            {gv.tres_lineas.map(l => (
              <div key={l.linea} className="rounded-lg p-3" style={{ background: CARD, border: `1px solid ${LINE}` }}>
                <div className="flex items-center gap-2">
                  <span className="rounded px-1.5 py-0.5 text-[10px] font-bold" style={{ background: "rgba(46,107,255,0.15)", color: "#7AA2FF" }}>{l.linea}</span>
                  <span className="text-xs font-semibold" style={{ color: BONE }}>{l.rol}</span>
                </div>
                <p className="text-[11px] mt-1" style={{ color: MUTED }}>{l.responsabilidad}</p>
              </div>
            ))}
          </div>
          <p className="text-[11px] mt-3" style={{ color: MUTED }}>Última revisión: {gv.ultima_revision} · Próxima: {gv.proxima_revision}</p>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl p-5" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
            <h3 className="text-sm font-bold mb-2" style={{ color: BONE }}>Limitaciones declaradas</h3>
            <ul className="space-y-1.5">
              {gv.limitaciones.map((l, i) => (
                <li key={i} className="flex gap-2 text-[11px]" style={{ color: MUTED }}>
                  <span style={{ color: "#F59E0B" }}>•</span><span>{l}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-xl p-5" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
            <h3 className="text-sm font-bold mb-2" style={{ color: BONE }}>Controles vigentes</h3>
            <ul className="space-y-1.5">
              {gv.controles.map((l, i) => (
                <li key={i} className="flex gap-2 text-[11px]" style={{ color: MUTED }}>
                  <span style={{ color: "#22C55E" }}>✓</span><span>{l}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <p className="text-[10px]" style={{ color: MUTED }}>{gov._nota}</p>
    </div>
  );
}
