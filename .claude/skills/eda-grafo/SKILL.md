---
name: eda-grafo
description: Análisis exploratorio estándar de grafos transaccionales
  financieros. Usar cuando se pida EDA, exploración de datos, o análisis
  de estructura del grafo de transacciones.
---

# EDA de grafos transaccionales

Al hacer EDA sobre el grafo de fraude, cubrir SIEMPRE:
1. Tamaño: nodos, aristas, densidad, componentes conexos
2. Prevalencia de fraude (% nodos y % aristas) — reportar el desbalance
3. Distribución de grado in/out, segmentada fraude vs. legítimo (log-log)
4. Distribución de montos, segmentada fraude vs. legítimo
5. Homofilia: fracción de aristas fraude-fraude vs. esperado por azar
6. Detección y visualización de al menos 3 anillos de fraude con networkx
   (layout spring, fraude en #C0392B, legítimo en #BDC3C7)

Convenciones de figuras:
- matplotlib puro, sin seaborn; estilo sobrio, grid sutil
- Títulos y ejes en español; exportar PNG 150dpi a reports/figures/
- Cada figura acompañada de 2-3 líneas de interpretación de NEGOCIO
  (qué significa para un equipo de compliance, no solo estadística)

Cerrar todo EDA actualizando reports/insights.md con los hallazgos.
