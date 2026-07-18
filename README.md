# Phantom AI — Detección de Redes de Lavado mediante Inteligencia de Grafos

**Dashboard en vivo → [fraude-bancario-2026.vercel.app](https://fraude-bancario-2026.vercel.app)**

Engagement simulado para *Banco Regional del Sur (BRS)*: prueba de concepto end-to-end de detección de anillos de lavado de activos usando Graph Neural Networks sobre un grafo transaccional sintético.

---

## Resultados

| Modelo | PR-AUC | ROC-AUC | Recall @ P90 | Fraude no detectado |
|---|---|---|---|---|
| Logistic Regression | 0.646 | 0.969 | 43% | 51.4% |
| XGBoost | 0.843 | 0.989 | 54% | 17.1% |
| Node2Vec + XGBoost | 0.057 | 0.758 | 0% | 82.9% |
| GAT | 0.950 | 0.999 | 89% | 11.4% |
| **GraphSAGE** | **0.946** | **0.997** | **89%** | **11.4%** |

**Nota metodológica — tres condiciones de evaluación:**
- **Transductivo** (1.000): el modelo ve todas las aristas durante el forward pass — estimación optimista.
- **Inductivo** (0.835): aristas de test ocultas durante la inferencia — simula cuentas nuevas.
- **Temporal** (0.810): reentrenado solo con transacciones hasta 2024-07-25 (70% del período); evaluado en los últimos 4 meses — el número operativo real para un banco.

**0.810 es el número que se presenta a dirección.** La caída de -0.025 vs inductivo muestra que el modelo es robusto al shift temporal.

**Hallazgo clave:** lift fraude→fraude de **14.3×** — las cuentas mula son crediticiamente normales (Cohen d = 0.055) pero se delatan por sus conexiones.

**Rastreo de origen:** el backward tracing sobre el grafo dirigido identificó 2 perpetradores no detectados por el GNN (score ≈ 0%), que inyectaron $66K al anillo desde cuentas aparentemente legítimas. El GNN detecta la estratificación; el backward tracing detecta la colocación.

**Scoring de colocación:** la propagación inversa de riesgo (`placement(u) = Σ gnn[v]×amount(u→v) + 0.3×Σ gnn[w]×amount(v→w)×amount(u→v)/total_out(v)`) rankea a ACC0000210 en el puesto #1 (score_norm=1.0, GNN=0%) — validando el método sin supervisión adicional. Captura colocadores parciales que el backward tracing simple no alcanza.

---

## Stack

**ML:** Python 3.13 · PyTorch · PyTorch Geometric · XGBoost · scikit-learn · NetworkX · gensim  
**Dashboard:** Next.js 14 · Tailwind CSS · Recharts · Cytoscape.js  
**Deploy:** Vercel (static export)  
**Informe:** HTML/CSS → Playwright/Chromium → PDF A4

---

## Estructura del proyecto

```
fraud-gnn/
├── src/
│   ├── generate.py          # generador de grafo sintético (1 500 nodos, 8 050 aristas)
│   ├── features.py          # 18 features por nodo
│   ├── build_graph.py       # PyG Data object + splits estratificados
│   ├── train_baseline.py    # LogReg + XGBoost
│   ├── train.py             # GraphSAGE con early stopping
│   ├── train_gat.py         # GAT (Graph Attention Network)
│   ├── train_node2vec.py    # Node2Vec (random walks + Word2Vec + XGBoost)
│   ├── explain.py           # GNNExplainer — importancia de features y aristas
│   ├── trace_origin.py      # Backward tracing — perpetradores desde mulas
│   ├── evaluate.py          # PR-AUC, Recall@P90, traducción operativa
│   ├── analysis.py          # comparativa, ablation, error analysis
│   ├── export_dashboard.py  # JSONs para el dashboard
│   ├── generate_report.py   # informe PDF institucional
│   ├── eda.py               # análisis exploratorio del grafo
│   └── models/
│       ├── graphsage.py     # SAGEConv(18→64→64) + Linear(64→2)
│       ├── gat.py           # GATConv(18→64→64, 4 heads) + Linear(64→2)
│       └── baseline.py      # LogReg + XGBoost tabulares
├── dashboard/               # Next.js 14 app (deploy en Vercel)
│   ├── app/
│   │   ├── page.tsx         # Overview: KPIs + curvas PR + distribución de scores
│   │   ├── anillos/         # Explorador de anillos (Cytoscape.js)
│   │   ├── origen/          # Rastreo de perpetradores (backward tracing)
│   │   ├── cuentas/         # Ranking de riesgo top 200
│   │   └── metodologia/     # Documentación técnica
│   └── public/data/         # JSONs exportados
├── reports/
│   ├── informe_final.pdf    # Informe institucional (Playwright → PDF)
│   ├── insights.md          # 16 insights de negocio
│   └── figures/             # 22 figuras (EDA, curvas, ablation, anillo)
├── config/config.yaml       # hiperparámetros centralizados
└── requirements.txt
```

---

## Módulos del pipeline

### Modelos entrenados

| Archivo | Modelo | Params | Resultado |
|---|---|---|---|
| `src/train_baseline.py` | LogReg + XGBoost | — | PR-AUC 0.555 / 0.925 |
| `src/train.py` | GraphSAGE | 10 754 | PR-AUC 1.000 (0.835 inductivo) |
| `src/train_gat.py` | GAT (4 heads) | 5 762 | PR-AUC 0.810 |
| `src/train_node2vec.py` | Node2Vec + XGBoost | 64-dim emb. | PR-AUC 0.227 |

### Explicabilidad y trazabilidad

| Archivo | Función |
|---|---|
| `src/explain.py` | GNNExplainer: importancia de features y aristas por nodo fraude |
| `src/trace_origin.py` | Backward tracing: remonta desde mulas detectadas hasta perpetradores |
| `src/detect_placement.py` | Propagación inversa de riesgo: scoring de colocación para todos los nodos |
| `src/evaluate_temporal.py` | Evaluación temporal: reentrenamiento sobre grafo histórico parcial, PR-AUC operativo |
| `src/enrich_personas.py` | Capa de identidad: genera nombre, DNI, CUIL, AFIP y domicilio argentinos para los 1 500 nodos |

### Dashboard (5 páginas)

| Ruta | Contenido |
|---|---|
| `/` | KPIs globales, curvas PR comparativas, distribución de scores |
| `/anillos` | Explorador de anillos cíclicos (Cytoscape.js interactivo) |
| `/origen` | Grafo dirigido del anillo + tabla de perpetradores identificados |
| `/cuentas` | Ranking de riesgo top 200, filtrable y ordenable |
| `/metodologia` | Documentación técnica para el equipo de compliance |

---

## Reproducir

```bash
# Dependencias Python
uv venv venv && source venv/bin/activate
uv pip install -r requirements.txt

# Pipeline completo
python -m src.generate          # dataset sintético
python -m src.build_graph       # grafo PyG + splits
python -m src.train_baseline    # LogReg + XGBoost
python -m src.train             # GraphSAGE
python -m src.train_gat         # GAT
python -m src.train_node2vec    # Node2Vec + XGBoost
python -m src.explain           # GNNExplainer
python -m src.trace_origin      # backward tracing
python -m src.detect_placement  # scoring de colocación
python -m src.evaluate_temporal # evaluación temporal
python -m src.analysis          # comparativa + figuras
python -m src.export_dashboard  # JSONs para dashboard
python -m src.enrich_personas   # identidades sintéticas + enriquecimiento de JSONs
python -m src.generate_report   # informe PDF

# Dashboard local
cd dashboard && npm install && npm run dev
```

---

## Informe PDF

Informe institucional completo (9 secciones, ~16 páginas, identidad visual BRS):

```bash
python -m src.generate_report
# → reports/informe_final.pdf
```

---

## Insights seleccionados

De los **16 insights** documentados en [`reports/insights.md`](reports/insights.md):

- **Insight 3** — Homofilia 14.3×: lift fraude→fraude, justificación cuantitativa para usar GNNs
- **Insight 7** — Los anillos completan sus ciclos en ventanas de 72 h, antes del monitoreo batch diario
- **Insight 13** — GNNExplainer revela que txn_count, unique_senders y risk_score son los features más determinantes
- **Insight 15** — PR-AUC=1.0 es evaluación transductiva; PR-AUC=0.835 es el número correcto para producción
- **Insight 16** — El GNN detecta la estratificación pero no la colocación; el backward tracing cierra esa brecha
- **Insight 17** — La propagación inversa de riesgo rankea a los perpetradores en el top-1/top-9 sin etiquetas adicionales, validando el método y capturando colocadores parciales que el backward tracing simple no alcanza
- **Insight 18** — Evaluación temporal (PR-AUC=0.810): reentrenando sobre el 70% histórico y evaluando en los 4 meses siguientes, la caída es de solo -0.025 vs inductivo — el modelo es robusto al shift temporal

---

**Germán Cárdenas · Data & Analytics** — Julio 2026
