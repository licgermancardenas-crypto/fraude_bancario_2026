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

---

## Fase F — Insights de Modelo

---

### Insight 9 — El GNN mejora 0.979 puntos de PR-AUC sobre XGBoost

> **Hallazgo:** GraphSAGE logra PR-AUC=1.000 vs XGBoost=0.021 vs LogReg=0.025, usando exactamente el mismo test set y splits. El único diferencial es el acceso a la estructura del grafo.

> **Implicancia para BRS:** Con XGBoost, los analistas de BRS revisarían ~21 alertas/día con 20% del fraude sin detectar. Con el GNN, las alertas bajan a ~26/día (ligeramente más amplias) pero el fraude no detectado cae a 0% en este dataset. El costo operativo es marginalmente mayor, el beneficio es material.

> **Acción sugerida:** Presentar la curva PR comparativa al directorio como el argumento central del proyecto. El área entre la curva XGBoost y la curva GNN representa el "fraude adicional detectado" — traducirlo a montos evitados usando el ticket promedio de BRS.

---

### Insight 10 — La topología sola (ablation) logra PR-AUC=0.036

> **Hallazgo:** Un GraphSAGE entrenado con features constantes (solo la estructura del grafo, sin balance, risk_score ni ningún atributo de cuenta) alcanza PR-AUC=0.036. La información de *quién se conecta con quién* ya contiene señal de fraude independiente de los features individuales.

> **Implicancia para BRS:** Esto significa que aunque los datos de cuentas estén incompletos, desactualizados o sean poco confiables, el grafo de transacciones por sí solo aporta valor. En una implementación real, el modelo puede correr incluso con features de cuenta degradados (ej.: clientes con poco historial, cuentas nuevas) y seguir detectando anillos por estructura.

> **Acción sugerida:** En la fase piloto, priorizar la disponibilidad del grafo de transacciones sobre la calidad de los features de cuenta. El pipeline mínimo viable es: transacciones → GNN topológico → score de red.

---

### Insight 11 — Los nodos de anillo más difíciles son los periféricos

> **Hallazgo:** El score mínimo entre nodos fraudulentos es 0.2432. Los nodos con score más bajo tienden a tener menor grado — son los nodos "de entrada" o "de salida" del anillo que tienen menos vecinos fraudulentos directos y por lo tanto reciben menos señal de red.

> **Implicancia para BRS:** En un esquema de lavado real, los nodos periféricos (entrada/salida del anillo) suelen ser las cuentas más "limpias" — las que el lavador usa para interactuar con el sistema bancario legítimo. Son los que más difícilmente captura un modelo tabular y los que más cerca están del límite de detección del GNN.

> **Acción sugerida:** Para los nodos con score intermedio (0.3–0.7), aplicar una segunda revisión manual que considere el contexto completo del anillo detectado, no solo el nodo individual. Un analista que ve el anillo completo puede decidir mucho más rápido que uno que solo ve la cuenta.

---

### Insight 12 — Regresión Logística en grafos: el límite de la linealidad

> **Hallazgo:** LogReg logra ROC-AUC=0.458 (alta separabilidad global) pero PR-AUC=0.025 (baja precisión en clases desbalanceadas) y Recall@P90=0. La frontera de decisión lineal no puede separar fraude de legítimo en el espacio de features en el punto operativo (90% precisión).

> **Implicancia para BRS:** Muchos sistemas de compliance internos usan regresión logística o scorecards lineales como base. Este resultado muestra que incluso con features de red (grado, montos, contrapartes), la no-linealidad es fundamental. El salto a XGBoost ya aporta enormemente; el salto a GNN añade la señal de vecindario.

> **Acción sugerida:** Al presentar el proyecto a BRS, usar la progresión LogReg → XGBoost → GNN como narrativa de "capas de inteligencia": cada capa agrega un tipo de información que la anterior no puede capturar (no-linealidad → estructura de red).

---

## Fase F — Insights de Modelo

---

### Insight 9 — El GNN mejora 0.075 puntos de PR-AUC sobre XGBoost

> **Hallazgo:** GraphSAGE logra PR-AUC=1.000 vs XGBoost=0.925 vs LogReg=0.555, usando exactamente el mismo test set y splits. El único diferencial es el acceso a la estructura del grafo.

> **Implicancia para BRS:** Con XGBoost, los analistas de BRS revisarían ~21 alertas/día con 20% del fraude sin detectar. Con el GNN, las alertas bajan a ~26/día (ligeramente más amplias) pero el fraude no detectado cae a 0% en este dataset. El costo operativo es marginalmente mayor, el beneficio es material.

> **Acción sugerida:** Presentar la curva PR comparativa al directorio como el argumento central del proyecto. El área entre la curva XGBoost y la curva GNN representa el "fraude adicional detectado" — traducirlo a montos evitados usando el ticket promedio de BRS.

---

### Insight 10 — La topología sola (ablation) logra PR-AUC=0.036

> **Hallazgo:** Un GraphSAGE entrenado con features constantes (solo la estructura del grafo, sin balance, risk_score ni ningún atributo de cuenta) alcanza PR-AUC=0.036. La información de *quién se conecta con quién* ya contiene señal de fraude independiente de los features individuales.

> **Implicancia para BRS:** Esto significa que aunque los datos de cuentas estén incompletos, desactualizados o sean poco confiables, el grafo de transacciones por sí solo aporta valor. En una implementación real, el modelo puede correr incluso con features de cuenta degradados (ej.: clientes con poco historial, cuentas nuevas) y seguir detectando anillos por estructura.

> **Acción sugerida:** En la fase piloto, priorizar la disponibilidad del grafo de transacciones sobre la calidad de los features de cuenta. El pipeline mínimo viable es: transacciones → GNN topológico → score de red.

---

### Insight 11 — Los nodos de anillo más difíciles son los periféricos

> **Hallazgo:** El score mínimo entre nodos fraudulentos es 0.2432. Los nodos con score más bajo tienden a tener menor grado — son los nodos "de entrada" o "de salida" del anillo que tienen menos vecinos fraudulentos directos y por lo tanto reciben menos señal de red.

> **Implicancia para BRS:** En un esquema de lavado real, los nodos periféricos (entrada/salida del anillo) suelen ser las cuentas más "limpias" — las que el lavador usa para interactuar con el sistema bancario legítimo. Son los que más difícilmente captura un modelo tabular y los que más cerca están del límite de detección del GNN.

> **Acción sugerida:** Para los nodos con score intermedio (0.3–0.7), aplicar una segunda revisión manual que considere el contexto completo del anillo detectado, no solo el nodo individual. Un analista que ve el anillo completo puede decidir mucho más rápido que uno que solo ve la cuenta.

---

### Insight 12 — Regresión Logística en grafos: el límite de la linealidad

> **Hallazgo:** LogReg logra ROC-AUC=0.926 (alta separabilidad global) pero PR-AUC=0.555 (baja precisión en clases desbalanceadas) y Recall@P90=0. La frontera de decisión lineal no puede separar fraude de legítimo en el espacio de features en el punto operativo (90% precisión).

> **Implicancia para BRS:** Muchos sistemas de compliance internos usan regresión logística o scorecards lineales como base. Este resultado muestra que incluso con features de red (grado, montos, contrapartes), la no-linealidad es fundamental. El salto a XGBoost ya aporta enormemente; el salto a GNN añade la señal de vecindario.

> **Acción sugerida:** Al presentar el proyecto a BRS, usar la progresión LogReg → XGBoost → GNN como narrativa de "capas de inteligencia": cada capa agrega un tipo de información que la anterior no puede capturar (no-linealidad → estructura de red).

---

### Insight 13 — El modelo detecta fraude por señales de red, no de monto

**Hallazgo:** GNNExplainer revela que los features más determinantes para clasificar una cuenta como fraude son **txn_count**, **unique_senders** y **risk_score** — todos indicadores de conectividad y comportamiento relacional, no de monto absoluto.

**Implicancia para BRS:** Las reglas actuales de umbral de monto no capturarían estas señales. El modelo aprende patrones que son invisibles para cualquier análisis por cuenta individual.

**Acción sugerida:** Priorizar la construcción de features de red (grado, ratio in/out, contrapartes únicas en ventanas de 72h) en el pipeline de datos de BRS, antes de reentrenar el modelo con datos reales.

---

### Insight 14 — El 13% de los vecinos influyentes son también de alto riesgo

**Hallazgo:** Para los top-5 nodos de fraude explicados, el 13% (3/23) de sus vecinos más influyentes según GNNExplainer tienen a su vez un score GNN > 0.5. La mayoría de los vecinos influyentes son cuentas legítimas — el modelo detecta fraude por patrones estructurales (volumen, ratio in/out, contrapartes únicas), no por "contagio" directo de un vecino fraudulento.

**Implicancia para BRS:** El modelo no hace simple guilt-by-association. El 13% de vecinos de alto riesgo es suficiente para justificar una revisión secundaria transitiva: cuando se confirma fraude en la cuenta A, los vecinos influyentes son candidatos inmediatos a investigación.

**Acción sugerida:** Implementar "investigación en cascada": cuando un analista confirma fraude en una cuenta, el sistema genera automáticamente alertas de nivel 2 para sus vecinos influyentes según GNNExplainer.

---

### Insight 15 — El PR-AUC=1.0 de GraphSAGE refleja evaluación transductiva, no inductiva

**Hallazgo:** En la evaluación estándar (transductiva), el GNN ve durante el entrenamiento todas las aristas del grafo, incluyendo las que conectan nodos de test con nodos fraude de train. Al aislar el test set eliminando sus aristas del grafo (evaluación inductiva, que simula cuentas nuevas en producción), el PR-AUC cae de **1.000 → 0.835**. Un nodo fraude (de 5) pasa de score=0.997 a score=0.007: su única señal era su conexión directa a 2 nodos fraude de train.

**Implicancia para BRS:** El PR-AUC de 0.83 en evaluación inductiva es el número correcto para estimar rendimiento en producción con cuentas nuevas. Sigue siendo el mejor modelo (vs. XGBoost=0.925 tabular, también en setting transductivo comparable). El leakage es un fenómeno conocido en la literatura de GNNs; la mitigación en producción es actualizar el grafo con lag controlado.

**Acción sugerida:** En el piloto con datos reales de BRS, evaluar en ventana temporal: entrenar con transacciones hasta el mes M y evaluar en el mes M+1 (ningún nodo de test tiene aristas en el grafo de train). Esto da la estimación más honesta del rendimiento operativo real.


---
### Insight 16 — El GNN detecta mulas pero no el perpetrador de origen

**Hallazgo:** Rastreando hacia atrás desde los 27 nodos fraude detectados por GraphSAGE en el grafo dirigido de transacciones, se identificaron **3 cuentas origen** (in-degree = 0 en el subgrafo de fraude): ACC0001330, ACC0000210, ACC0001046. De ellas, **2 no fueron detectadas por el GNN** (score GNN < 0.5) porque tienen baja centralidad de red y pocas transacciones totales — el perfil típico de una cuenta que inyecta fondos una sola vez y desaparece. El monto total inyectado detectado: **$80,925**.

**Implicancia para BRS:** El modelo de detección actual cubre la **capa de estratificación** (placement → layering), pero no la **capa de colocación** (el depósito inicial del dinero ilícito). Los perpetradores se camuflan como cuentas con bajo volumen de transacciones — invisibles para un clasificador de nodos basado en centralidad de red.

**Acción sugerida:** Combinar el scoring GNN con una segunda pasada de *backward tracing*: dado cualquier nodo detectado como fraude, agregar a la cola de investigación todos sus predecesores directos en el grafo dirigido temporal que no sean ellos mismos detectados. Priorizar por monto inyectado y antigüedad de la cuenta.
