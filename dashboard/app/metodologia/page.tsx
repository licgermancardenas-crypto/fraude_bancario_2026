import PageHeader from "@/components/PageHeader";

export default function MetodologiaPage() {
  const models = [
    { name: "Logistic Regression", prauc: "0.555", color: "#94A3B8",
      desc: "Baseline lineal. Usa 18 features tabulares por nodo. No captura interacciones ni estructura de red." },
    { name: "XGBoost",             prauc: "0.925", color: "#F59E0B",
      desc: "Baseline no lineal. Captura interacciones de features pero es ciego a la topología del grafo." },
    { name: "Node2Vec + XGBoost",  prauc: "0.227", color: "#A78BFA",
      desc: "Embeddings de grafo por random walks + XGBoost. Sin features tabulares — solo posición estructural." },
    { name: "GAT",                 prauc: "0.810", color: "#34D399",
      desc: "Graph Attention Network. Aprende pesos por arista. Mejor arquitectura pero inferior a SAGE en este dataset." },
    { name: "GraphSAGE",           prauc: "1.000", color: "#2563EB",
      desc: "2 capas SAGEConv(18→64→64) + Linear(64→2). Agrega señal de vecinos hasta 2 saltos. Mejor modelo." },
  ];

  const card = {
    backgroundColor: "#FFFFFF",
    border: "1px solid #E2E8F0",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <PageHeader
        eyebrow="Documentación técnica"
        title="Metodología del Modelo"
        description="Para el equipo de compliance y analistas de BRS."
      />

      {/* What it solves */}
      <div className="rounded-xl p-6 space-y-3" style={card}>
        <h2 className="text-sm font-semibold" style={{ color: "#2563EB" }}>¿Qué problema resuelve?</h2>
        <p className="text-sm leading-relaxed" style={{ color: "#64748B" }}>
          Las reglas tradicionales de AML detectan transacciones individuales sospechosas por monto o frecuencia.
          Sin embargo, los esquemas de <em>pitufeo</em> y <em>anillos cíclicos</em> dividen grandes sumas en
          transacciones pequeñas que parecen normales individualmente, pero forman un patrón de red detectable.
        </p>
        <p className="text-sm leading-relaxed" style={{ color: "#64748B" }}>
          Este sistema analiza el{" "}
          <strong style={{ color: "#0F172A" }}>grafo de transacciones completo</strong>: cada cuenta es un nodo,
          cada transferencia una arista. El modelo aprende que los vecinos de cuentas fraudulentas tienden a ser
          fraudulentos (<span style={{ color: "#2563EB", fontWeight: 600 }}>lift 14.3×</span> observado en los datos).
        </p>
      </div>

      {/* Models */}
      <div className="rounded-xl p-6 space-y-4" style={card}>
        <h2 className="text-sm font-semibold" style={{ color: "#2563EB" }}>Modelos evaluados</h2>
        <div className="space-y-4">
          {models.map(m => (
            <div key={m.name} className="flex gap-4 items-start">
              <div className="mt-1.5 flex-shrink-0">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: m.color }} />
              </div>
              <div>
                <p className="text-sm font-semibold" style={{ color: "#0F172A" }}>
                  {m.name}{" "}
                  <span className="font-mono text-xs" style={{ color: "#94A3B8" }}>PR-AUC={m.prauc}</span>
                </p>
                <p className="text-sm leading-relaxed mt-0.5" style={{ color: "#64748B" }}>{m.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Architecture */}
      <div className="rounded-xl p-6 space-y-3" style={card}>
        <h2 className="text-sm font-semibold" style={{ color: "#2563EB" }}>Arquitectura GraphSAGE</h2>
        <pre
          className="text-xs rounded-lg p-4 overflow-x-auto leading-relaxed"
          style={{ backgroundColor: "#F8FAFC", color: "#1E3A8A", border: "1px solid #E2E8F0" }}
        >
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
      </div>

      {/* Why SAGE */}
      <div className="rounded-xl p-6 space-y-3" style={card}>
        <h2 className="text-sm font-semibold" style={{ color: "#2563EB" }}>¿Por qué GraphSAGE y no GCN?</h2>
        <ul className="space-y-3">
          {[
            ["Inductivo",  "Asigna score a cuentas nuevas sin reentrenar — crítico cuando aparecen cuentas nuevas todos los días."],
            ["Escalable",  "Soporta neighbour sampling para grafos de millones de nodos (escala real de BRS)."],
            ["Robusto",    "Mean aggregation es estable ante grafos dispersos y heterofílicos."],
          ].map(([t, d]) => (
            <li key={t} className="flex gap-3 text-sm">
              <span className="font-semibold shrink-0" style={{ color: "#2563EB" }}>{t}</span>
              <span className="leading-relaxed" style={{ color: "#64748B" }}>{d}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Validation */}
      <div className="rounded-xl p-6 space-y-2" style={card}>
        <h2 className="text-sm font-semibold mb-3" style={{ color: "#2563EB" }}>Protocolo de validación</h2>
        {[
          "Split estratificado 70/15/15 (train/val/test), seed=42, compartido entre los 5 modelos.",
          "Features normalizados con estadísticas del train set únicamente (sin leakage).",
          "Early stopping sobre val PR-AUC; evaluación final sobre test set.",
          "Métrica primaria: PR-AUC — el desbalance 1.9% hace que accuracy sea inútil.",
          "PR-AUC=1.0 es evaluación transductiva. Inductiva (cuentas nuevas): 0.835.",
        ].map(t => (
          <p key={t} className="text-sm leading-relaxed flex gap-2" style={{ color: "#64748B" }}>
            <span className="mt-0.5 flex-shrink-0" style={{ color: "#CBD5E1" }}>·</span>
            <span>{t}</span>
          </p>
        ))}
      </div>

      {/* Disclaimer */}
      <div
        className="rounded-xl p-5 text-xs leading-relaxed"
        style={{ backgroundColor: "#EFF6FF", border: "1px solid #BFDBFE" }}
      >
        <p className="font-semibold mb-1.5" style={{ color: "#1E3A8A" }}>Disclaimer — Datos sintéticos</p>
        <p style={{ color: "#1D4ED8" }}>
          Este dashboard y todos sus resultados se basan en datos 100% sintéticos generados para simular un
          engagement de consultoría. No representan datos reales de ninguna institución financiera.
          Los indicadores de rendimiento variarán según la calidad de los datos reales del cliente.
        </p>
      </div>
    </div>
  );
}
