# Phantom AI — Detección de Redes de Lavado mediante Inteligencia de Grafos

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.x-EE4C2C?logo=pytorch&logoColor=white)
![PyG](https://img.shields.io/badge/PyTorch_Geometric-2.x-orange)
![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)
![Vercel](https://img.shields.io/badge/Deploy-Vercel-black?logo=vercel)
![License](https://img.shields.io/badge/datos-100%25_sintéticos-green)

**Dashboard en vivo → [fraude-bancario-2026.vercel.app](https://fraude-bancario-2026.vercel.app)**

Engagement simulado para *Banco Regional del Sur (BRS)*: prueba de concepto end-to-end de detección de redes de lavado de activos usando **Graph Neural Networks** sobre un grafo transaccional sintético de 75.000 cuentas y ~400.000 transacciones.

El sistema detecta estructuras que los controles basados en reglas no pueden ver: **anillos cíclicos de lavado** (4–7 saltos), **pitufeo / estructuración**, y **perpetradores de origen** que inyectaron el dinero sin ser detectados por el modelo principal.

---

## Resultados

| Modelo | PR-AUC ↑ | ROC-AUC | Recall @ P90 | Fraude no detectado |
|---|---|---|---|---|
| Logistic Regression | 0.675 | 0.986 | 0% | 27.6% |
| XGBoost | 0.927 | 0.998 | 80% | 20.2% |
| GAT | 0.973 | 0.999 | 93% | 8.0% |
| **GraphSAGE** | **0.977** | **0.9995** | **95%** | **6.7%** |

> **PR-AUC** (Área bajo la curva Precisión-Recall) es la métrica principal para fraude: mide qué tan bien detecta casos raros sin generar falsas alarmas. Un clasificador aleatorio obtendría ~0.015 (la tasa base de fraude). **Por encima de 0.95 es excelente.**
>
> **Recall @ P90:** con la exigencia de que 9 de cada 10 alertas sean fraude real, GraphSAGE detecta el **95%** del fraude total.

**Hallazgo clave — homofilia 14.3×:** los vecinos de cuentas fraudulentas son 14.3× más propensos a ser también fraudulentos. Las cuentas mula son crediticiamente normales (Cohen d = 0.055) pero se delatan por sus conexiones. Esta es la justificación cuantitativa de por qué los GNN superan a los modelos tabulares.

**Rastreo de perpetradores:** el backward tracing sobre el grafo dirigido identificó 2 cuentas de origen no detectadas por el GNN (score ≈ 0%) que inyectaron $66K al esquema. La propagación inversa de riesgo las rankea en los puestos #1 y #9 sin etiquetas adicionales.

---

## Qué incluye el sistema

### Modelos de detección

| Módulo | Modelo | Arquitectura | PR-AUC |
|---|---|---|---|
| `src/train_baseline.py` | Logistic Regression + XGBoost | Tabular (18 features) | 0.675 / 0.927 |
| `src/train_node2vec.py` | Node2Vec + XGBoost | Random walks 64-dim | baseline de embeddings |
| `src/train_gat.py` | GAT — Graph Attention Network | GATConv(18→64, 4 heads) × 2 | 0.973 |
| `src/train.py` | **GraphSAGE** | SAGEConv(18→64→64) × 2 | **0.977** |

### Explicabilidad y trazabilidad

| Módulo | Función |
|---|---|
| `src/explain.py` | GNNExplainer: qué features y conexiones determinan cada predicción |
| `src/trace_origin.py` | Backward tracing: remonta desde mulas detectadas hasta perpetradores de origen |
| `src/detect_placement.py` | Propagación inversa de riesgo: scoring de colocación para todos los nodos |
| `src/evaluate_temporal.py` | Evaluación temporal: rendimiento sobre el período posterior al entrenamiento |
| `src/enrich_personas.py` | Capa de identidad: nombre, DNI, CUIL, AFIP y domicilio argentinos por cuenta |

### Dashboard (7 páginas + Compliance)

| Ruta | Contenido |
|---|---|
| `/` | KPIs globales, curvas PR comparativas, distribución de scores GNN |
| `/anillos` | Explorador de anillos cíclicos (Cytoscape.js interactivo) |
| `/origen` | Grafo dirigido del anillo + tabla de perpetradores identificados |
| `/cuentas` | Ranking de riesgo top 200, filtrable y ordenable |
| `/metodologia` | Documentación técnica del sistema |
| `/casos` | **Cola de alertas** con 80 casos pre-generados, filtros, KPIs, gestión de estado |
| `/entidades` | **Red de entidades** (personas, empresas, PEPs, shell companies) en Cytoscape.js |
| `/casos/[id]/sar` | **Formulario ROS/SAR** pre-completado, narrativa automática, referencia a Ley 25.246 / UIF |

### Informe institucional PDF

Informe de 9 secciones con identidad visual BRS: resultados, insights, roadmap de implementación, glosario de 20 términos y lenguaje accesible para directores y equipos de compliance. Generado vía HTML/CSS → Playwright/Chromium.

```bash
python -m src.generate_report   # → reports/informe_final.pdf
```

---

## Arquitectura

```
Datos sintéticos (gen-fraud-graph)
        │
        ▼
   src/generate.py          ← 75K cuentas · ~400K txns · escenarios AML
        │
        ▼
   src/build_graph.py       ← PyG Data object · splits 70/15/15 estratificados
        │
        ├──▶ src/train_baseline.py    LogReg + XGBoost
        ├──▶ src/train_node2vec.py    Node2Vec + XGBoost
        ├──▶ src/train_gat.py         GAT (4 heads)
        └──▶ src/train.py             GraphSAGE ← modelo principal
                    │
                    ├──▶ src/explain.py           GNNExplainer
                    ├──▶ src/trace_origin.py       Backward tracing
                    ├──▶ src/detect_placement.py   Placement scores
                    └──▶ src/evaluate_temporal.py  Evaluación temporal
                                │
                                ▼
                    src/export_dashboard.py   ← JSONs para el dashboard
                                │
                    ┌───────────┴────────────┐
                    ▼                        ▼
             Next.js 14                  generate_report.py
             (Vercel)                    (PDF institucional)
```

---

## Stack

**ML / Data:** Python 3.13 · PyTorch · PyTorch Geometric · XGBoost · scikit-learn · NetworkX · gensim · pandas · matplotlib · seaborn

**Dashboard:** Next.js 14 · TypeScript · Tailwind CSS · Recharts · Cytoscape.js

**PDF:** Playwright/Chromium · HTML/CSS → A4

**Deploy:** Vercel

---

## Estructura del proyecto

```
fraud-gnn/
├── src/
│   ├── generate.py            # grafo sintético: 75K nodos, ~400K aristas, escenarios AML
│   ├── features.py            # 18 features por nodo (grado, montos, conectividad, perfil)
│   ├── build_graph.py         # PyG Data object + splits estratificados (seed=42)
│   ├── train_baseline.py      # LogReg + XGBoost tabulares
│   ├── train.py               # GraphSAGE con early stopping
│   ├── train_gat.py           # GAT (Graph Attention Network, 4 heads)
│   ├── train_node2vec.py      # Node2Vec (random walks + Word2Vec + XGBoost)
│   ├── explain.py             # GNNExplainer — importancia de features y aristas
│   ├── trace_origin.py        # backward tracing — perpetradores desde mulas
│   ├── detect_placement.py    # propagación inversa de riesgo (placement score)
│   ├── evaluate_temporal.py   # evaluación sobre ventana temporal
│   ├── evaluate.py            # PR-AUC, Recall@P90, traducción operativa
│   ├── analysis.py            # comparativa, ablation, error analysis
│   ├── eda.py                 # análisis exploratorio del grafo
│   ├── export_dashboard.py    # JSONs para el dashboard (cuentas, anillos, casos, entidades)
│   ├── generate_entities.py   # empresas, shell companies, PEPs, directores
│   ├── enrich_personas.py     # identidades sintéticas argentinas (DNI, CUIL, AFIP)
│   ├── generate_report.py     # informe PDF institucional
│   └── models/
│       ├── graphsage.py       # SAGEConv(18→64→64) + Linear(64→2)
│       ├── gat.py             # GATConv(18→64→64, 4 heads) + Linear(64→2)
│       └── baseline.py        # LogReg + XGBoost tabulares
├── dashboard/                 # Next.js 14 (deploy en Vercel)
│   ├── app/
│   │   ├── page.tsx           # Overview: KPIs + curvas PR + distribución de scores
│   │   ├── anillos/           # explorador de anillos (Cytoscape.js)
│   │   ├── origen/            # rastreo de perpetradores
│   │   ├── cuentas/           # ranking de riesgo top 200
│   │   ├── metodologia/       # documentación técnica
│   │   ├── casos/             # cola de alertas + gestión de casos
│   │   ├── casos/[id]/        # detalle de caso con 4 tabs y acciones
│   │   ├── casos/[id]/sar/    # formulario ROS/SAR (Ley 25.246 / UIF)
│   │   └── entidades/         # red de entidades (Cytoscape.js)
│   └── public/data/           # JSONs exportados (cuentas, casos, entidades)
├── config/config.yaml         # hiperparámetros centralizados
├── reports/
│   ├── informe_final.pdf      # informe institucional (Playwright → PDF)
│   ├── informe_final.html     # versión HTML del informe
│   ├── insights.md            # 16+ insights de negocio
│   └── figures/               # gráficas (EDA, curvas PR, ablation, anillos)
├── data/
│   ├── raw/                   # CSVs del generador (gitignored)
│   └── processed/             # graph.pt + splits + scores (gitignored)
└── requirements.txt
```

---

## Reproducir

```bash
# Dependencias Python
uv venv venv && source venv/bin/activate
uv pip install -r requirements.txt

# Pipeline completo (en orden)
python -m src.generate              # dataset sintético (75K cuentas)
python -m src.build_graph           # grafo PyG + splits estratificados
python -m src.train_baseline        # LogReg + XGBoost
python -m src.train                 # GraphSAGE
python -m src.train_gat             # GAT
python -m src.train_node2vec        # Node2Vec + XGBoost
python -m src.explain               # GNNExplainer
python -m src.trace_origin          # backward tracing
python -m src.detect_placement      # scoring de colocación
python -m src.evaluate_temporal     # evaluación temporal
python -m src.analysis              # comparativa + figuras
python -m src.generate_entities     # empresas, PEPs, shell companies
python -m src.export_dashboard      # JSONs para dashboard
python -m src.enrich_personas       # identidades sintéticas
python -m src.generate_report       # informe PDF

# Dashboard local
cd dashboard && npm install && npm run dev
# → http://localhost:3000
```

> **Nota de escala:** el pipeline fue validado a `scale_factor=0.5` (75K cuentas). A `scale_factor=1.0` (150K cuentas) el entrenamiento full-batch puede quedarse sin memoria en equipos con menos de 4 GB RAM. Se recomienda implementar `NeighborLoader` antes de escalar.

---

## Contexto AML

El sistema implementa detección de las dos tipologías más comunes según GAFI:

- **Anillos cíclicos (layering):** el dinero circula por 4–7 cuentas intermedias en ventanas de 72 h, fragmentando el flujo bajo los umbrales de reporte y diluyendo la trazabilidad.
- **Estructuración / pitufeo (structuring):** sumas grandes se dividen en transferencias deliberadamente por debajo de los límites regulatorios, distribuidas en múltiples cuentas.

El módulo de Compliance incluye formularios de ROS pre-completados bajo **Ley 25.246** y **Resolución UIF N° 30/2017** (Argentina).

---

**Germán Cárdenas · Data & Analytics · Julio 2026**
