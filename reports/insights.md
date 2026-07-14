# Insights de negocio — Detección de Fraude / BRS

**Proyecto:** Detección de redes de lavado mediante inteligencia de grafos  
**Cliente:** Banco Regional del Sur (BRS)  
**Autor:** Germán Cárdenas  
**Dataset:** Sintético — 1 500 cuentas, 8 030 transacciones, scale=0.01, seed=42  
**Fecha:** 2026-07-14

---

## Fase C — Análisis Exploratorio del Grafo

---

### Insight 1 — La señal de fraude es estructural, no de monto individual

> **Hallazgo:** Las transacciones fraudulentas tienen una mediana de monto de $1 296 vs. $94 en transacciones legítimas (ratio 13.7x). Sin embargo, dentro de cada anillo de lavado el monto se reduce progresivamente en cada salto (85-98% del anterior), de modo que los saltos intermedios se camuflan entre el tráfico cotidiano.

> **Implicancia para BRS:** Las reglas actuales basadas en umbrales de monto ($10 000+) capturan la entrada del dinero al anillo, pero pierden los saltos de "enfriamiento" intermedios y el exit estructurado. El monto por transacción individual no es el indicador operativo — el patrón de la cadena sí lo es.

> **Acción sugerida:** Complementar las reglas de umbral con alertas de *velocidad transaccional por vecindario*: si un nodo recibe y reenvía rápidamente montos similares a múltiples destinos en ventanas de 72 h, es candidato para revisión independientemente del monto individual.

---

### Insight 2 — El score de riesgo crediticio externo no detecta lavado (d = 0.055)

> **Hallazgo:** El risk score externo (crediticio) tiene un tamaño del efecto de Cohen d = 0.055 entre cuentas fraudulentas y legítimas — prácticamente cero. Las distribuciones son indistinguibles: media fraude 0.204 vs. legítimo 0.197.

> **Implicancia para BRS:** Si el sistema de alerta actual usa el score crediticio como señal de fraude/AML, está descartando o priorizando incorrectamente. Las cuentas de lavado no son crediticiamente riesgosas — son cuentas "normales" usadas instrumentalmente. El problema es un problema de *red*, no de *perfil individual*.

> **Acción sugerida:** Desconectar el score crediticio de las reglas de detección de lavado. Construir un score específico de red (como el que produce el GNN de este proyecto) que capture comportamiento relacional, no crediticio.

---

### Insight 3 — Homofilia 14.3x: los vecinos del fraude tienden fuertemente a ser fraude

> **Hallazgo:** Las aristas fraude→fraude representan el 0.535% del grafo, vs. un 0.037% esperado bajo distribución aleatoria — un lift de **14.3x**. El coeficiente de homofilia global es h = 0.96.

> **Implicancia para BRS:** La señal de fraude no está en la cuenta individual sino en su vecindario inmediato. Un modelo que ignore la estructura del grafo (como Regresión Logística o XGBoost tabulares) descarta el 14.3x de señal adicional que existe en las conexiones. Este resultado es la justificación cuantitativa para usar GNNs.

> **Acción sugerida:** Utilizar este valor de lift como benchmark de comunicación interna: "cada transacción con una cuenta de riesgo aumenta 14x la probabilidad de que el origen también sea de riesgo". Es un argumento directo para el equipo de compliance.

---

### Insight 4 — El grafo es una sola componente débilmente conexa

> **Hallazgo:** El grafo transaccional forma **1 única componente débilmente conexa** (todos los 1 500 nodos están interconectados) y 17 componentes fuertemente conexas (los anillos y subgrafos cíclicos).

> **Implicancia para BRS:** No hay cuentas aisladas. Toda cuenta tiene caminos de conexión a todo el resto del grafo — lo que significa que la información de vecindario de un nodo fraudulento se propaga a través de múltiples saltos. Un GNN de 2-3 capas puede agregar señal de hasta 3 saltos de distancia, capturando anillos completos de 4-7 nodos.

> **Acción sugerida:** Al escalar el sistema a datos reales (escala 1.0), verificar si el grafo sigue siendo una sola componente. Si se fragmenta, el scoring deberá hacerse por componente y las cuentas en componentes aisladas tendrán menor confianza de predicción.

---

### Insight 5 — Las cuentas de lavado tienen grado promedio 1.36x superior al legítimo

> **Hallazgo:** Las cuentas fraudulentas tienen un out-degree promedio de 7.24 vs. 5.32 en cuentas legítimas (ratio 1.36x), y un in-degree de 6.69 vs. 5.33 (ratio 1.26x). El patrón es simétrico: entran y salen cantidades similares.

> **Implicancia para BRS:** Las cuentas mula y de anillo actúan como *routers* del grafo — alta conectividad bidireccional. Esto es el fingerprint topológico del pitufeo: una cuenta legítima típica recibe de pocos orígenes y envía a pocos destinos; una cuenta mula recibe de muchos y redistribuye a muchos. Un simple feature de grado in/out entra como predictor en los baselines tabulares.

> **Acción sugerida:** Agregar a la capa de monitoreo actual una regla de velocidad: cuentas con más de N contrapartes únicas en 30 días que exhiban grado in ≈ grado out (comportamiento de tránsito) deben quedar en una cola de segunda revisión.

---

### Insight 6 — El fraude se distribuye uniformemente por tipo de cuenta (1.8-2.0%)

> **Hallazgo:** La prevalencia de fraude es prácticamente igual entre tipos de cuenta: personal 1.98%, merchant 1.89%, business 1.77%. No hay tipo de cuenta sobre-representado.

> **Implicancia para BRS:** Los esquemas de lavado no tienen preferencia por cuentas business o merchant — usan cuentas personales con la misma frecuencia. Esto descarta estrategias de "focalizar revisiones en cuentas business" como proxy de riesgo AML.

> **Acción sugerida:** No usar el tipo de cuenta como feature primario de priorización. Mantenerlo como feature de contexto en el modelo (puede interactuar con otras variables) pero no como regla de filtrado independiente.

---

### Insight 7 — Los anillos de lavado operan en ventanas de 72 horas

> **Hallazgo:** Se detectaron 3 anillos cíclicos en el grafo (7, 3 y 7 saltos). Las transacciones de cada anillo ocurren en ventanas de 600 segundos a 72 horas entre saltos consecutivos — comprimidas para mover el dinero antes de que activen alertas de monitoreo de 24h.

> **Implicancia para BRS:** El monitoreo batch diario que tienen la mayoría de los sistemas de compliance actuales llega *después* de que el dinero ya circuló 2-3 veces. Para los anillos de 4-5 saltos el ciclo puede completarse en menos de 12 horas.

> **Acción sugerida:** Priorizar un pipeline de scoring en cuasi-real-time (cada 4h como mínimo) para los nodos de mayor riesgo según el modelo, en lugar de scoring batch diario. El modelo GNN puede ejecutarse incrementalmente sobre el subgrafo de transacciones recientes.

---

### Insight 8 — Pico de actividad fraudulenta: 20:00 h y jueves

> **Hallazgo:** Las transacciones de fraude en el dataset se concentran temporalmente a las 20:00 h y los jueves — fuera del horario bancario tradicional de revisión manual.

> **Implicancia para BRS:** Los esquemas de lavado aprovechan deliberadamente franjas horarias de menor supervisión. Si el equipo de compliance de BRS opera en horario de oficina (9-18h), los anillos iniciados a las 20:00 completan 2-3 saltos antes de la apertura del día siguiente.

> **Acción sugerida:** Configurar alertas automáticas de alta prioridad para transacciones de alto monto (>$5 000) en horario nocturno, combinadas con el score de riesgo de red del modelo. La combinación temporal+topológica debería reducir significativamente los falsos positivos nocturnos.

---

## Estado del documento

- [x] Fase C — EDA: 8 insights completados
- [ ] Fase F — Modelo: hallazgos pendientes (comparativa LogReg / XGBoost / GraphSAGE)
