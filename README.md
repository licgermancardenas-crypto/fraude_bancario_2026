# Detección de Redes de Lavado mediante Inteligencia de Grafos

**Dashboard en vivo → [fraude-bancario-2026.vercel.app](https://fraude-bancario-2026.vercel.app)**

Engagement simulado para *Banco Regional del Sur (BRS)*: prueba de concepto end-to-end de detección de anillos de lavado de activos usando Graph Neural Networks sobre un grafo transaccional sintético.

---

## Resultados

| Modelo | PR-AUC (transductivo) | PR-AUC (inductivo) | Recall @ P90 |
|---|---|---|---|
| Logistic Regression | 0.555 | — | 0% |
| XGBoost | 0.925 | — | 80% |
| Node2Vec + XGBoost | 0.227 | — | 0% |
| GAT | 0.810 | — | 20% |
| **GraphSAGE** | **1.000** | **0.835** | **100%** |

**Nota metodológica:** el PR-AUC=1.0 corresponde a evaluación transductiva estándar (full-batch, el GNN ve todas las aristas durante el forward pass, incluyendo conexiones entre nodos de train y test). En evaluación inductiva —eliminando aristas de test durante la inferencia, que simula cuentas nuevas en producción— el PR-AUC baja a **0.835**, que es el número correcto para estimar rendimiento operativo. Sigue siendo el modelo más potente. Ver [Insight 15](reports/insights.md).

La clave del resultado: **lift fraude-fraude de 14.3×** — las cuentas mula son crediticiamente normales (Cohen d = 0.055) pero se delatan por sus conexiones.

## Stack

**ML:** Python 3.13 · PyTorch · PyTorch Geometric · XGBoost · scikit-learn · NetworkX  
**Dashboard:** Next.js 14 · Tailwind CSS · Recharts · Cytoscape.js  
**Deploy:** Vercel (static export)  
**Informe:** HTML/CSS → Playwright/Chromium → PDF A4

## Estructura del proyecto

```
fraud-gnn/
├── src/
│   ├── generate.py          # generador de grafo sintético (1 500 nodos, 8 050 aristas)
│   ├── features.py          # 18 features por nodo
│   ├── build_graph.py       # PyG Data object
│   ├── models/
│   │   ├── graphsage.py     # SAGEConv(18→64→64) + Linear(64→2)
│   │   └── baseline.py      # LogReg + XGBoost
│   ├── train.py             # entrenamiento GNN con early stopping
│   ├── train_baseline.py    # entrenamiento baselines
│   ├── evaluate.py          # PR-AUC, Recall@P90, traducción operativa
│   ├── analysis.py          # comparativa, ablation, error analysis
│   ├── export_dashboard.py  # JSONs para el dashboard
│   └── generate_report.py   # informe PDF institucional
├── dashboard/               # Next.js 14 app (deploy en Vercel)
│   ├── app/
│   │   ├── page.tsx         # Overview: KPIs + curva PR + score dist
│   │   ├── anillos/         # Explorador de anillos (Cytoscape.js)
│   │   ├── cuentas/         # Ranking de riesgo top 200
│   │   └── metodologia/     # Documentación técnica
│   └── public/data/         # JSONs exportados por export_dashboard.py
├── reports/
│   ├── informe_final.pdf    # Informe institucional (generado con Playwright)
│   ├── figures/             # 15 figuras (EDA, curvas, ablation)
│   └── insights.md          # 12 insights de negocio
├── notebooks/               # EDA, baselines, GNN (narrativa)
└── config/config.yaml       # hiperparámetros centralizados
```

## Reproducir

```bash
# Dependencias Python
uv venv venv && source venv/bin/activate
uv pip install -r requirements.txt

# Pipeline completo
python -m src.generate          # dataset sintético
python -m src.train_baseline    # LogReg + XGBoost
python -m src.build_graph       # grafo PyG
python -m src.train             # GraphSAGE
python -m src.analysis          # comparativa + insights
python -m src.export_dashboard  # JSONs para dashboard
python -m src.generate_report   # informe PDF

# Dashboard local
cd dashboard && npm install && npm run dev
```

## Informe PDF

El informe institucional completo (9 secciones, ~16 páginas, identidad visual BRS) se genera con:

```bash
python -m src.generate_report
# → reports/informe_final.pdf
```

---

**Germán Cárdenas · Data & Analytics** — Julio 2026
