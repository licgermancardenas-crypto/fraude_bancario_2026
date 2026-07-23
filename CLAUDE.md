# Proyecto: Detección de fraude con GNNs — Germán Cárdenas

## Contexto
Engagement simulado para "Banco Regional del Sur (BRS)": detección de anillos
de lavado en grafo transaccional sintético (gen-fraud-graph, Santander AI Lab).
Entregables finales: dashboard en Vercel + informe PDF institucional.

## Stack
- Python 3.13 en Linux, venv en ./venv
- PyTorch + PyTorch Geometric (CPU-only, sin GPU)
- pandas, scikit-learn, xgboost, networkx, matplotlib
- Dashboard: Next.js 14 + Tailwind + Recharts + Cytoscape.js, deploy en Vercel
- API: FastAPI (api/), deploy en Render (free tier) — servicio separado, no conectado al dashboard
- PDF: HTML/CSS → Playwright/Chromium (pipeline HTML → PDF)

## Convenciones
- Código y docstrings en inglés; textos de negocio e informes en español
- Lógica en src/, notebooks solo para narrativa
- Config centralizada en config/config.yaml — nada hardcodeado
- Métricas obligatorias: PR-AUC, recall@precision=0.90, F1. NUNCA accuracy sola
  (fraude ≈ 1-3% de los nodos; el desbalance domina todo)
- Seed=42 en todo. Splits guardados en data/processed/ y compartidos
  entre baselines y GNN (comparación justa)
- Estética de entregables: paleta navy (#0A1F44) y gold (#C9A227), marca personal GC

## Skills disponibles (.claude/skills/)
- eda-grafo: análisis exploratorio estándar de grafos transaccionales
- metricas-fraude: evaluación con métricas operativas bancarias
- informe-gc: generación de PDFs institucionales navy/gold
- dashboard-fraude: convenciones del dashboard Next.js

## Comandos frecuentes
- source venv/bin/activate
- python -m src.generate --scale 0.01
- python -m src.build_graph
- python -m src.train
- python -m src.evaluate
- python -m src.export_dashboard
- cd dashboard && npm run dev
- uvicorn api.main:app --reload

## Estado actual
[2026-07-23] Las 8 fases del roadmap original (A-H) están completas, más extensiones:
5 modelos entrenados (mejor: GraphSAGE, PR-AUC 0.977), explicabilidad (GNNExplainer),
backward tracing de perpetradores, placement scoring, dashboard de 7 páginas + módulo
Compliance (casos/entidades/SAR), informe PDF institucional, y API FastAPI (api/) con
11 endpoints deployada en Render (confirmada viva en https://phantom-rcs9.onrender.com).
La API es un servicio independiente — no está cableada al dashboard, que sigue siendo
deploy estático (JSONs en dashboard/public/data/).
README.md es la fuente de verdad del estado del proyecto; actualizar esta sección junto
con el README cuando cambie algo relevante.
