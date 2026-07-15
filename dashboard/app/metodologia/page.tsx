import PageHeader from "@/components/PageHeader";

const card = {
  backgroundColor: "#FFFFFF",
  border: "1px solid #E2E8F0",
  boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
};

const models = [
  { name: "Logistic Regression", prauc: "0.555", color: "#94A3B8",
    desc: "Baseline lineal. 18 features tabulares por nodo. No captura interacciones ni estructura de red." },
  { name: "XGBoost",             prauc: "0.925", color: "#F59E0B",
    desc: "Baseline no lineal. Captura interacciones de features pero es ciego a la topología del grafo." },
  { name: "Node2Vec + XGBoost",  prauc: "0.227", color: "#A78BFA",
    desc: "Embeddings de grafo por random walks + XGBoost. Sin features tabulares — solo posición estructural." },
  { name: "GAT",                 prauc: "0.810", color: "#34D399",
    desc: "Graph Attention Network. Aprende pesos por arista. Compite bien pero inferior a SAGE en este dataset." },
  { name: "GraphSAGE",           prauc: "1.000 / 0.835 / 0.810", color: "#2563EB",
    desc: "2 capas SAGEConv(18→64→64) + Linear(64→2). Mejor modelo. Ver tabla de evaluación abajo." },
];

const evalConditions = [
  { condition: "Transductivo", prauc: "1.000", color: "#94A3B8",
    desc: "El modelo ve todas las aristas durante el forward pass, incluyendo las que conectan nodos de test con nodos fraude de train.",
    uso: "Límite superior teórico. No reportar a dirección." },
  { condition: "Inductivo",    prauc: "0.835", color: "#F59E0B",
    desc: "Aristas de test ocultadas durante la inferencia. Simula cuentas sin historia previa en el grafo.",
    uso: "Cota conservadora para cuentas nuevas." },
  { condition: "Temporal",     prauc: "0.810", color: "#2563EB",
    desc: "Reentrenado con transacciones hasta 2024-07-25 (70% del período). Evaluado en los 4 meses siguientes.",
    uso: "Número operativo real. El que se presenta a dirección." },
];

const detectionLayers = [
  {
    step: "1",
    title: "GNN de nodos — estratificación",
    color: "#2563EB",
    bg: "#EFF6FF",
    module: "src/train.py",
    desc: "GraphSAGE asigna un score de riesgo (0–1) a cada cuenta basándose en sus features tabulares y sus conexiones en el grafo. Detecta las cuentas mula: alta centralidad, flujo anómalo, conectadas entre sí.",
    output: "Score GNN por cuenta → ranking de riesgo para la cola de compliance.",
    limitation: "Detecta la estratificación (mulas), pero no la colocación (cuentas origen con baja centralidad).",
  },
  {
    step: "2",
    title: "Backward tracing — origen exacto",
    color: "#F59E0B",
    bg: "#FFFBEB",
    module: "src/trace_origin.py",
    desc: "Sobre el subgrafo de transacciones fraudulentas (is_fraud=1), busca los nodos con in-degree=0: las cuentas que inyectaron dinero al anillo sin recibirlo de él. Son los perpetradores de origen.",
    output: "3 perpetradores identificados: ACC0001330 (detectado), ACC0000210 y ACC0001046 (no detectados por GNN, score≈0%).",
    limitation: "Solo captura raíces estrictas (in-degree=0). No detecta colocadores parciales.",
  },
  {
    step: "3",
    title: "Placement scoring — colocación parcial",
    color: "#7C3AED",
    bg: "#F5F3FF",
    module: "src/detect_placement.py",
    desc: "Propagación inversa de riesgo en dos niveles: directo (gnn[v]×amount(u→v)) + indirecto (0.3×gnn[w]×amount(v→w)×amount(u→v)/total_out(v)). Rankea a todos los nodos por cuánta señal de fraude inyectan.",
    output: "ACC0000210 rankea #1 (score_norm=1.0, GNN=0%), ACC0001046 rankea #9. Valida el método sin etiquetas adicionales.",
    limitation: "No requiere reentrenamiento. Opera sobre scores GNN existentes.",
  },
];

export default function MetodologiaPage() {
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
          Los esquemas de <em>pitufeo</em> y <em>anillos cíclicos</em> dividen grandes sumas en transacciones
          pequeñas que parecen normales individualmente — pero forman un patrón de red detectable.
        </p>
        <p className="text-sm leading-relaxed" style={{ color: "#64748B" }}>
          Este sistema analiza el{" "}
          <strong style={{ color: "#0F172A" }}>grafo de transacciones completo</strong>: cada cuenta es un nodo,
          cada transferencia una arista. El modelo detecta por{" "}
          <span style={{ color: "#2563EB", fontWeight: 600 }}>conectividad</span>, no por monto —
          lift fraude→fraude de <span style={{ color: "#2563EB", fontWeight: 600 }}>14.3×</span>.
        </p>
      </div>

      {/* 3-layer detection pipeline */}
      <div className="rounded-xl p-6 space-y-5" style={card}>
        <h2 className="text-sm font-semibold" style={{ color: "#2563EB" }}>
          Pipeline de detección — 3 capas
        </h2>
        <div className="space-y-4">
          {detectionLayers.map(layer => (
            <div key={layer.step} className="rounded-lg p-4 space-y-2"
                 style={{ backgroundColor: layer.bg, border: `1px solid ${layer.color}22` }}>
              <div className="flex items-center gap-3">
                <span className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-black text-white flex-shrink-0"
                      style={{ backgroundColor: layer.color }}>
                  {layer.step}
                </span>
                <div>
                  <p className="text-sm font-semibold" style={{ color: "#0F172A" }}>{layer.title}</p>
                  <p className="text-[10px] font-mono" style={{ color: "#94A3B8" }}>{layer.module}</p>
                </div>
              </div>
              <p className="text-xs leading-relaxed" style={{ color: "#64748B" }}>{layer.desc}</p>
              <div className="flex gap-4 text-xs">
                <div className="flex-1">
                  <span className="font-semibold" style={{ color: "#0F172A" }}>Output: </span>
                  <span style={{ color: "#64748B" }}>{layer.output}</span>
                </div>
              </div>
              {layer.limitation && (
                <p className="text-[11px] italic" style={{ color: "#94A3B8" }}>
                  Nota: {layer.limitation}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Models */}
      <div className="rounded-xl p-6 space-y-4" style={card}>
        <h2 className="text-sm font-semibold" style={{ color: "#2563EB" }}>5 modelos evaluados</h2>
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

      {/* Temporal evaluation */}
      <div className="rounded-xl p-6 space-y-4" style={card}>
        <h2 className="text-sm font-semibold" style={{ color: "#2563EB" }}>
          Evaluación temporal — el número que le presentás a un banco
        </h2>
        <p className="text-sm leading-relaxed" style={{ color: "#64748B" }}>
          GraphSAGE fue evaluado bajo tres condiciones de creciente honestidad metodológica.
          El modelo fue <strong style={{ color: "#0F172A" }}>reentrenado desde cero</strong> usando
          solo el 70% del período histórico (transacciones hasta 2024-07-25) y evaluado en los
          4 meses siguientes.
        </p>
        <div className="space-y-3">
          {evalConditions.map(e => (
            <div key={e.condition} className="flex gap-4 items-start rounded-lg p-3"
                 style={{ backgroundColor: "#F8FAFC", border: "1px solid #E2E8F0" }}>
              <div className="flex-shrink-0 text-center w-20">
                <p className="text-xl font-black" style={{ color: e.color }}>{e.prauc}</p>
                <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "#94A3B8" }}>
                  {e.condition}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-xs leading-relaxed" style={{ color: "#64748B" }}>{e.desc}</p>
                <p className="text-[11px] font-semibold" style={{ color: e.color }}>{e.uso}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="rounded-lg p-3 text-xs leading-relaxed"
             style={{ backgroundColor: "#EFF6FF", border: "1px solid #BFDBFE" }}>
          <strong style={{ color: "#1E3A8A" }}>Delta temporal: -0.025 vs inductivo. </strong>
          <span style={{ color: "#1D4ED8" }}>
            El modelo aprende patrones estructurales estables que persisten en el tiempo —
            condición necesaria para un sistema AML en producción.
          </span>
        </div>
      </div>

      {/* Architecture */}
      <div className="rounded-xl p-6 space-y-3" style={card}>
        <h2 className="text-sm font-semibold" style={{ color: "#2563EB" }}>Arquitectura GraphSAGE</h2>
        <pre className="text-xs rounded-lg p-4 overflow-x-auto leading-relaxed"
             style={{ backgroundColor: "#F8FAFC", color: "#1E3A8A", border: "1px solid #E2E8F0" }}>
{`SAGEConv(18 → 64)   # agrega vecinos a 1 salto
→ ReLU → Dropout(0.3)
SAGEConv(64 → 64)   # agrega vecinos a 2 saltos
→ ReLU → Dropout(0.3)
Linear(64 → 2)      # clasificación: legítimo / fraude

Parámetros: 10 754
Optimizador: Adam lr=0.005  wd=5e-4
Loss: CrossEntropy (weight fraude = 51.45×)
Early stopping: val PR-AUC, paciencia=20`}
        </pre>
      </div>

      {/* Why SAGE */}
      <div className="rounded-xl p-6 space-y-3" style={card}>
        <h2 className="text-sm font-semibold" style={{ color: "#2563EB" }}>¿Por qué GraphSAGE?</h2>
        <ul className="space-y-3">
          {[
            ["Inductivo",  "Asigna score a cuentas nuevas sin reentrenar — crítico cuando aparecen cuentas nuevas todos los días."],
            ["Escalable",  "Soporta neighbour sampling para grafos de millones de nodos (escala real de BRS ~500K cuentas)."],
            ["Robusto",    "Mean aggregation es estable ante grafos dispersos y heterofílicos."],
            ["Temporal",   "PR-AUC=0.810 en evaluación temporal confirma que los patrones aprendidos se mantienen en el tiempo."],
          ].map(([t, d]) => (
            <li key={t} className="flex gap-3 text-sm">
              <span className="font-semibold shrink-0 w-20" style={{ color: "#2563EB" }}>{t}</span>
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
          "Evaluación temporal: reentrenamiento sobre grafo histórico parcial (70% del tiempo), evaluación en los últimos 4 meses.",
          "PR-AUC operativo recomendado: 0.810 (temporal) — no el 1.000 transductivo.",
        ].map(t => (
          <p key={t} className="text-sm leading-relaxed flex gap-2" style={{ color: "#64748B" }}>
            <span className="mt-0.5 flex-shrink-0" style={{ color: "#CBD5E1" }}>·</span>
            <span>{t}</span>
          </p>
        ))}
      </div>

      {/* Disclaimer */}
      <div className="rounded-xl p-5 text-xs leading-relaxed"
           style={{ backgroundColor: "#EFF6FF", border: "1px solid #BFDBFE" }}>
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
