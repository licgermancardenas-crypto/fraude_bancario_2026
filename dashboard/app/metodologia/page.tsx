export default function MetodologiaPage() {
  const models = [
    { name: "Logistic Regression", prauc: "0.555", color: "#BDC3C7", desc: "Baseline lineal. Usa 18 features tabulares por nodo. No captura interacciones ni estructura de red." },
    { name: "XGBoost",             prauc: "0.925", color: "#C9A227", desc: "Baseline no lineal. Captura interacciones de features pero sigue siendo ciego a la topología del grafo." },
    { name: "GraphSAGE",           prauc: "1.000", color: "#C0392B", desc: "2 capas SAGEConv(18→64→64) + Linear(64→2). Agrega señal de vecinos hasta 2 saltos. Detecta anillos por estructura." },
  ];

  const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <section className="rounded-xl border border-white/10 p-6 space-y-3" style={{ backgroundColor: "#122855" }}>
      <h2 className="text-base font-semibold text-[#C9A227]">{title}</h2>
      {children}
    </section>
  );

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-[#C9A227] mb-1">Documentación técnica</p>
        <h1 className="text-2xl font-bold text-white">Metodología del Modelo</h1>
        <p className="text-sm text-white/50 mt-1">Para el equipo de compliance y analistas de BRS.</p>
      </div>

      <Section title="¿Qué problema resuelve?">
        <p className="text-sm text-white/70 leading-relaxed">
          Las reglas tradicionales de AML detectan transacciones individuales sospechosas por monto o frecuencia.
          Sin embargo, los esquemas de lavado estructurado (<em>pitufeo</em> y <em>anillos cíclicos</em>)
          dividen grandes sumas en transacciones pequeñas que parecen normales individualmente,
          pero forman un patrón de red detectable.
        </p>
        <p className="text-sm text-white/70 leading-relaxed">
          Este sistema analiza el <strong className="text-white">grafo de transacciones completo</strong>:
          cada cuenta es un nodo, cada transferencia es una arista. El modelo aprende que
          los vecinos de cuentas fraudulentas tienden a ser fraudulentos
          (<span className="text-[#C9A227]">lift 14.3×</span> observado en los datos).
        </p>
      </Section>

      <Section title="Modelos evaluados">
        <div className="space-y-4">
          {models.map(m => (
            <div key={m.name} className="flex gap-4 items-start">
              <div className="w-2 h-2 rounded-full mt-1.5 shrink-0" style={{ backgroundColor: m.color }} />
              <div>
                <p className="font-semibold text-sm text-white">
                  {m.name}{" "}
                  <span className="font-mono text-xs text-white/50">PR-AUC={m.prauc}</span>
                </p>
                <p className="text-sm text-white/60 leading-relaxed">{m.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Arquitectura GraphSAGE">
        <pre className="text-xs text-[#C9A227] bg-[#0d2554] rounded-lg p-4 overflow-x-auto leading-relaxed">
{`SAGEConv(18 → 64)   # agrega vecinos a 1 salto
→ ReLU → Dropout(0.3)
SAGEConv(64 → 64)   # agrega vecinos a 2 saltos
→ ReLU → Dropout(0.3)
Linear(64 → 2)      # clasificación: legítimo / fraude

Parámetros: 10 754
Optimizador: Adam lr=0.005  wd=5e-4
Loss: CrossEntropy (weight fraude = 51.45×)
Early stopping: val PR-AUC, paciencia=20
Detuvo en época 78`}
        </pre>
      </Section>

      <Section title="¿Por qué GraphSAGE y no GCN?">
        <ul className="text-sm text-white/70 space-y-2 list-none">
          {[
            ["Inductivo", "Puede asignar score a cuentas nuevas sin reentrenar el modelo — crítico para producción donde aparecen cuentas todos los días."],
            ["Escalable", "Soporta neighbour sampling para grafos de millones de nodos (cuando escale a los datos reales de BRS)."],
            ["Robusto", "Mean aggregation es estable ante grafos dispersos y heterofílicos."],
          ].map(([t, d]) => (
            <li key={t} className="flex gap-3">
              <span className="text-[#C9A227] font-semibold shrink-0">{t}:</span>
              <span>{d}</span>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Protocolo de validación">
        <ul className="text-sm text-white/70 space-y-1.5">
          <li>• Split estratificado <strong className="text-white">70/15/15</strong> (train/val/test), seed=42, compartido entre los 3 modelos.</li>
          <li>• Features normalizados con estadísticas del train set únicamente (sin leakage).</li>
          <li>• Early stopping monitoreado sobre val PR-AUC, evaluación final sobre test set.</li>
          <li>• Métrica primaria: <strong className="text-white">PR-AUC</strong> (no accuracy — el desbalance 1.9% domina cualquier métrica que no distinga clases).</li>
        </ul>
      </Section>

      <div className="rounded-xl border border-[#C9A227]/30 p-5 text-sm text-white/60 leading-relaxed"
           style={{ backgroundColor: "#0d2554" }}>
        <p className="text-[#C9A227] font-semibold mb-2">Disclaimer — Datos sintéticos</p>
        <p>
          Este dashboard y todos los resultados presentados se basan en datos 100% sintéticos
          generados para simular un engagement de consultoría. No representan datos reales de
          ninguna institución financiera. Los patrones de fraude son estilizados para demostrar
          la capacidad del enfoque GNN; en producción, los indicadores de rendimiento variarán
          según la calidad y características de los datos reales del cliente.
        </p>
      </div>
    </div>
  );
}
