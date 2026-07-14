---
name: dashboard-fraude
description: Convenciones del dashboard de fraude en Next.js para deploy
  en Vercel. Usar al crear o modificar cualquier parte del dashboard.
---

# Dashboard de fraude — convenciones

Stack: Next.js 14 (App Router) + Tailwind + Recharts (charts)
+ Cytoscape.js (visualización de grafo). Sitio ESTÁTICO: los datos
se leen de JSONs en public/data/ exportados por src/export_dashboard.py.
Sin backend, sin base de datos, sin API keys — deploy directo en Vercel.

Páginas:
- / (Overview): KPIs (cuentas, % fraude, PR-AUC, recall@p90),
  curva PR comparativa, distribución de scores
- /anillos: explorador de anillos de fraude con Cytoscape
  (nodos coloreados por score del modelo)
- /cuentas: tabla rankeada por score de riesgo, con filtros
- /metodologia: explicación breve del modelo para el analista

Estética: dark theme navy #0A1F44, acentos gold #C9A227,
tipografía Inter. Responsive. Textos de UI en español.
Performance: JSONs < 2MB; si el grafo es grande, exportar solo
el subgrafo de los top-N anillos.
