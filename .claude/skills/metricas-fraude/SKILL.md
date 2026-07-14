---
name: metricas-fraude
description: Evaluación de modelos de detección de fraude con métricas
  operativas bancarias. Usar al evaluar o comparar cualquier modelo.
---

# Métricas operativas de fraude

Para TODO modelo evaluado, reportar sobre el MISMO test set:
- PR-AUC (métrica principal — clases desbalanceadas)
- ROC-AUC (secundaria, para lectores acostumbrados)
- Recall @ precision=0.90 ("con 9 de 10 alertas correctas,
  ¿qué % del fraude atrapamos?")
- F1 en el threshold óptimo + matriz de confusión
- Tabla comparativa acumulada en reports/ (CSV + markdown)

Traducción a negocio obligatoria: convertir la matriz de confusión en
"alertas/día que revisaría un analista" y "% de fraude no detectado",
asumiendo el volumen del cliente BRS (500K cuentas).

Prohibido: reportar accuracy sola; comparar modelos con splits distintos;
tunear hiperparámetros mirando el test set.
