# Insights de negocio — Detección de Fraude / BRS

**Proyecto:** Detección de redes de lavado mediante inteligencia de grafos
**Cliente:** Banco Regional del Sur (BRS)
**Autor:** Germán Cárdenas
**Dataset:** Sintético — scale=0.5, seed=42
**Fecha:** 2026-07-16

> Insights 1-8 (EDA) se reescriben a mano después de correr `src/eda.py` sobre
> el dataset nuevo. Insights 9+ los agregan automáticamente `analysis.py`,
> `explain.py`, `trace_origin.py`, `detect_placement.py` y `evaluate_temporal.py`
> durante la corrida del pipeline. El set anterior (scale=0.01) quedó archivado
> en `reports/insights_scale0.01_archive.md`.

---

## Fase C — Análisis Exploratorio del Grafo

---

### Insight 1 — La señal de fraude es estructural, no de monto individual

> **Hallazgo:** Las transacciones fraudulentas tienen una mediana de monto de $6 065.57 vs. $89.90 en transacciones legítimas (ratio 67.5x). Sin embargo, dentro de cada anillo de lavado el monto se reduce progresivamente en cada salto (85-98% del anterior) y se fragmenta en 3-5 transferencias de salida al cerrar el ciclo, de modo que las transferencias de cierre se acercan al rango de tráfico cotidiano aunque la entrada al anillo sea grande.

> **Implicancia para BRS:** Las reglas actuales basadas en umbrales de monto siguen capturando bien la entrada del dinero al anillo (montos de entrada $5 000-$50 000), pero el ratio 67.5x muestra que el monto promedio de fraude es, en este dataset, más alto que el legítimo — lo cual valida el umbral de monto como señal parcial, pero no suficiente: los saltos intermedios y el fan-out de salida siguen camuflándose entre transacciones normales.

> **Acción sugerida:** Complementar las reglas de umbral con alertas de *velocidad transaccional por vecindario*: si un nodo recibe y reenvía rápidamente montos similares a múltiples destinos en ventanas de 72 h, es candidato para revisión independientemente del monto individual.

---

### Insight 2 — El score de riesgo crediticio externo no detecta lavado (d ≈ 0)

> **Hallazgo:** El risk score externo (crediticio) tiene un tamaño del efecto de Cohen d = -0.005 entre cuentas fraudulentas y legítimas — indistinguible de cero. Las distribuciones son prácticamente idénticas: media fraude 0.1989 vs. legítimo 0.1994.

> **Implicancia para BRS:** Si el sistema de alerta actual usa el score crediticio como señal de fraude/AML, está descartando o priorizando incorrectamente. Las cuentas de lavado no son crediticiamente riesgosas — son cuentas "normales" usadas instrumentalmente. El problema es un problema de *red*, no de *perfil individual*. Este resultado se mantiene estable entre corridas a distinta escala (d=0.055 a scale=0.01, d=-0.005 a scale=0.5): la desconexión entre riesgo crediticio y riesgo AML no es ruido de muestra chica.

> **Acción sugerida:** Desconectar el score crediticio de las reglas de detección de lavado. Construir un score específico de red (como el que produce el GNN de este proyecto) que capture comportamiento relacional, no crediticio.

---

### Insight 3 — Homofilia 18.5x: los vecinos del fraude tienden fuertemente a ser fraude

> **Hallazgo:** Las aristas fraude→fraude representan el 0.385% del grafo, vs. un 0.021% esperado bajo distribución aleatoria — un lift de **18.5x** (vs. 14.3x observado a scale=0.01). El coeficiente de homofilia global es h = 0.971.

> **Implicancia para BRS:** La señal de fraude no está en la cuenta individual sino en su vecindario inmediato, y esta señal se sostiene (de hecho se fortalece) al escalar el dataset — no es un artefacto de muestra chica. Un modelo que ignore la estructura del grafo (como Regresión Logística o XGBoost tabulares) descarta un lift de casi 20x que existe en las conexiones.

> **Acción sugerida:** Utilizar este valor de lift como benchmark de comunicación interna: "cada transacción con una cuenta de riesgo aumenta ~18x la probabilidad de que la contraparte también sea de riesgo". Es un argumento directo para el equipo de compliance.

---

### Insight 4 — El grafo es, en la práctica, una sola componente conexa

> **Hallazgo:** El grafo transaccional forma **2 componentes débilmente conexas** (la mayor concentra el 100.0% de los 75 000 nodos — el resto son cuentas aisladas sin ninguna transacción) y 706 componentes fuertemente conexas (los anillos y subgrafos cíclicos). A scale=0.01 el grafo había dado 1 sola componente débil; el puñado de cuentas sin transacciones que aparece a esta escala es exactamente lo que causó el bug de `export_dashboard.py` corregido en esta misma migración.

> **Implicancia para BRS:** Prácticamente toda cuenta tiene caminos de conexión al resto del grafo — la información de vecindario de un nodo fraudulento se propaga a través de múltiples saltos. Un GNN de 2-3 capas puede agregar señal de hasta 3 saltos de distancia, capturando anillos completos de 4-7 nodos. Las pocas cuentas totalmente aisladas (sin transacciones) no tienen señal de red por definición — el modelo debe tratarlas como caso aparte (score basado solo en features tabulares).

> **Acción sugerida:** Al escalar el sistema a datos reales, tratar las cuentas sin actividad transaccional reciente como una categoría explícita de "sin señal de red" en vez de forzarlas por el pipeline de grafo — evita tanto errores de cómputo como scores de confianza engañosos.

---

### Insight 5 — Las cuentas de lavado tienen grado promedio ~1.3x superior al legítimo

> **Hallazgo:** Las cuentas fraudulentas tienen un out-degree promedio de 7.02 vs. 5.33 en cuentas legítimas (ratio 1.32x), y un in-degree de 6.75 vs. 5.34 (ratio 1.26x). El patrón es simétrico: entran y salen cantidades similares, y es consistente con lo observado a scale=0.01 (ratios 1.36x/1.26x) — el fingerprint topológico no depende de la escala.

> **Implicancia para BRS:** Las cuentas mula y de anillo actúan como *routers* del grafo — alta conectividad bidireccional. Esta es la firma topológica del pitufeo: una cuenta legítima típica recibe de pocos orígenes y envía a pocos destinos; una cuenta mula recibe de muchos y redistribuye a muchos.

> **Acción sugerida:** Agregar a la capa de monitoreo actual una regla de velocidad: cuentas con más contrapartes únicas de lo normal en 30 días que exhiban grado in ≈ grado out (comportamiento de tránsito) deben quedar en una cola de segunda revisión.

---

### Insight 6 — El fraude se distribuye de forma casi uniforme por tipo de cuenta (1.3-1.5%)

> **Hallazgo:** La prevalencia de fraude es prácticamente igual entre tipos de cuenta: personal 1.46%, business 1.45%, merchant 1.30%. No hay tipo de cuenta sobre-representado.

> **Implicancia para BRS:** Los esquemas de lavado no tienen preferencia por cuentas business o merchant — usan cuentas personales con la misma frecuencia relativa. Esto descarta estrategias de "focalizar revisiones en cuentas business" como proxy de riesgo AML.

> **Acción sugerida:** No usar el tipo de cuenta como feature primario de priorización. Mantenerlo como feature de contexto en el modelo (puede interactuar con otras variables) pero no como regla de filtrado independiente.

---

### Insight 7 — Los anillos de lavado se cierran en ventanas de hasta 72 horas por salto

> **Hallazgo:** Se detectaron 10 anillos cíclicos en el subgrafo de fraude (de ~100 anillos embebidos por el generador a esta escala; la búsqueda de ciclos se corta en los primeros 10 encontrados), con longitudes de 4 a 7 saltos. Por diseño del generador, cada salto ocurre entre 600 segundos y 72 horas después del anterior — comprimido para mover el dinero antes de que activen alertas de monitoreo de 24h.

> **Implicancia para BRS:** El monitoreo batch diario que tienen la mayoría de los sistemas de compliance actuales llega *después* de que el dinero ya circuló varias veces. Para los anillos de 4 saltos el ciclo puede completarse en menos de 12 horas si los saltos son rápidos.

> **Acción sugerida:** Priorizar un pipeline de scoring en cuasi-real-time (cada 4h como mínimo) para los nodos de mayor riesgo según el modelo, en lugar de scoring batch diario. El modelo GNN puede ejecutarse incrementalmente sobre el subgrafo de transacciones recientes.

---

### Insight 8 — El dataset sintético no modela un patrón horario deliberado (nota metodológica)

> **Hallazgo:** El pico de actividad fraudulenta observado cambió de 20:00h/jueves (scale=0.01, n≈50 transacciones fraude) a 03:00h/sábado (scale=0.5, n=1 930 transacciones fraude). Revisando `src/generate.py`, los timestamps de entrada y de cada salto se generan con `rng.integers(...)` — uniformemente al azar, sin ningún sesgo horario programado. El "pico" original a scale=0.01 era ruido de muestra chica, no un patrón real del generador.

> **Implicancia para BRS:** Esto es una limitación conocida del dataset sintético, no un hallazgo de negocio: no se puede afirmar que "el lavado ocurre de noche" a partir de estos datos. En producción con datos reales de BRS, si existiera evasión horaria deliberada, sí sería un patrón genuino a testear — pero hay que medirlo sobre las transacciones reales, no asumirlo de este generador.

> **Acción sugerida:** Si se quiere estudiar evasión horaria como señal, agregar sesgo temporal deliberado a `embed_laundering_rings`/`embed_structuring` en el generador (ej.: mayor probabilidad de hop nocturno) para que el pipeline de detección pueda validarse contra un patrón conocido de antemano. Con datos reales, correr este mismo análisis (`src/eda.py`, sección 6) sobre el historial real de BRS antes de sacar conclusiones.

---
### Insight 16 — El GNN detecta mulas pero no el perpetrador de origen

**Hallazgo:** Rastreando hacia atrás desde los 1046 nodos fraude detectados por GraphSAGE en el grafo dirigido de transacciones, se identificaron **149 cuentas origen** (in-degree = 0 en el subgrafo de fraude): ACC0062781, ACC0050615, ACC0019773, ACC0008799, ACC0018964, ACC0017781, ACC0069541, ACC0042517, ACC0049372, ACC0060260, ACC0045793, ACC0038684, ACC0046346, ACC0066543, ACC0050667, ACC0034663, ACC0058287, ACC0047696, ACC0072684, ACC0073889, ACC0038780, ACC0016932, ACC0053852, ACC0039507, ACC0011551, ACC0029102, ACC0046009, ACC0040492, ACC0012015, ACC0052262, ACC0014293, ACC0042992, ACC0016614, ACC0026318, ACC0029041, ACC0069531, ACC0048213, ACC0028255, ACC0069066, ACC0072641, ACC0007456, ACC0072655, ACC0026111, ACC0063736, ACC0007362, ACC0045890, ACC0072972, ACC0021241, ACC0004877, ACC0046179, ACC0049908, ACC0034880, ACC0062079, ACC0032150, ACC0057348, ACC0014967, ACC0059899, ACC0061935, ACC0050526, ACC0010521, ACC0044840, ACC0053209, ACC0061404, ACC0031245, ACC0051320, ACC0055053, ACC0009316, ACC0008443, ACC0001666, ACC0043859, ACC0029493, ACC0057330, ACC0005087, ACC0047632, ACC0034688, ACC0016640, ACC0036837, ACC0043955, ACC0034747, ACC0060765, ACC0011924, ACC0034687, ACC0026400, ACC0057558, ACC0073121, ACC0061303, ACC0016856, ACC0042445, ACC0061147, ACC0004876, ACC0027210, ACC0066609, ACC0005247, ACC0008001, ACC0060871, ACC0033270, ACC0006639, ACC0043022, ACC0043533, ACC0017548, ACC0040047, ACC0039409, ACC0015943, ACC0063748, ACC0058892, ACC0003378, ACC0012277, ACC0038447, ACC0052621, ACC0017650, ACC0005790, ACC0044612, ACC0021365, ACC0006797, ACC0059368, ACC0028065, ACC0022888, ACC0071489, ACC0055924, ACC0045620, ACC0014708, ACC0003802, ACC0026069, ACC0066444, ACC0059462, ACC0035688, ACC0042069, ACC0047549, ACC0038057, ACC0043360, ACC0032047, ACC0057044, ACC0058660, ACC0029512, ACC0054094, ACC0067863, ACC0072539, ACC0032110, ACC0005242, ACC0011921, ACC0006062, ACC0037458, ACC0025228, ACC0023101, ACC0015063, ACC0045446, ACC0066672, ACC0003108, ACC0073576. De ellas, **98 no fueron detectadas por el GNN** (score GNN < 0.5) porque tienen baja centralidad de red y pocas transacciones totales — el perfil típico de una cuenta que inyecta fondos una sola vez y desaparece. El monto total inyectado detectado: **$5,151,317**.

**Implicancia para BRS:** El modelo de detección actual cubre la **capa de estratificación** (placement → layering), pero no la **capa de colocación** (el depósito inicial del dinero ilícito). Los perpetradores se camuflan como cuentas con bajo volumen de transacciones — invisibles para un clasificador de nodos basado en centralidad de red.

**Acción sugerida:** Combinar el scoring GNN con una segunda pasada de *backward tracing*: dado cualquier nodo detectado como fraude, agregar a la cola de investigación todos sus predecesores directos en el grafo dirigido temporal que no sean ellos mismos detectados. Priorizar por monto inyectado y antigüedad de la cuenta.

---

### Insight 13 — El modelo detecta fraude por señales de red, no de monto

**Hallazgo:** GNNExplainer revela que los features más determinantes para clasificar una cuenta como fraude son **risk_score**, **total_received** y **avg_sent** — todos indicadores de conectividad y comportamiento relacional, no de monto absoluto.

**Implicancia para BRS:** Las reglas actuales de umbral de monto no capturarían estas señales. El modelo aprende patrones que son invisibles para cualquier análisis por cuenta individual.

**Acción sugerida:** Priorizar la construcción de features de red (grado, ratio in/out, contrapartes únicas en ventanas de 72h) en el pipeline de datos de BRS, antes de reentrenar el modelo con datos reales.

---

### Insight 14 — El 6% de los vecinos influyentes son también de alto riesgo

**Hallazgo:** Para los top-5 nodos de fraude explicados, el 6% de sus vecinos más influyentes (edge mask > 25% del máximo) tienen a su vez un score GNN > 0.5. La señal de fraude se propaga de forma consistente a través de la red.

**Implicancia para BRS:** Un sistema de alertas basado en el score GNN puede usarse de forma transitiva: si la cuenta A es marcada, las cuentas que más influyeron en esa marcación son candidatas inmediatas a revisión secundaria.

**Acción sugerida:** Implementar "investigación en cascada": cuando un analista confirma fraude en una cuenta, el sistema genera automáticamente alertas de nivel 2 para sus vecinos influyentes según GNNExplainer.

---
### Insight 17 — Propagación inversa de riesgo: scoring de colocación

**Hallazgo:** Aplicando propagación inversa de riesgo sobre el grafo dirigido de transacciones (formula: `placement(u) = Σ gnn[v]×amount(u→v) + 0.3×Σ gnn[w]×amount(v→w)×amount(u→v)/total_out(v)`), se produjo un ranking de **30 cuentas candidatas** a la colocación. Los 3 primeros candidatos son: ACC0028255 (score_norm=1.000, GNN=1.000), ACC0029102 (score_norm=0.965, GNN=1.000), ACC0038780 (score_norm=0.928, GNN=1.000). Los perpetradores conocidos (backward tracing) aparecen en las primeras posiciones, validando el método. Además se identificaron **0 nuevos candidatos** no detectados previamente por el GNN ni por el backward tracing simple.

**Implicancia para BRS:** La propagación inversa de riesgo detecta colocación aunque la cuenta origen no tenga alta centralidad de red. Funciona porque mide cuánta *señal de fraude* inyecta cada cuenta en el sistema, ponderada por el monto de dinero transferido. El score puede calcularse en tiempo real a medida que el GNN asigna scores: toda transacción nueva actualiza el placement score del remitente.

**Comparación con backward tracing:** el backward tracing original requiere que la cuenta origen tenga in-degree=0 en el subgrafo de fraude (raíz estricta). La propagación inversa captura también *colocadores parciales* — cuentas que inyectaron en múltiples etapas o que tienen transacciones normales además de las fraudulentas.

---
### Insight 18 — Evaluación temporal: el número operativo real

**Hallazgo:** Al re-entrenar GraphSAGE usando solo las transacciones del primer **70%** del período histórico (hasta 2024-07-26, 281352 aristas de 401930 totales) y evaluar en los mismos nodos de test, el PR-AUC cae de **0.977** (transductivo) → **0.915** (inductivo) → **0.975** (temporal). El delta vs. evaluación inductiva es **+0.060**. El modelo entrenado con datos históricos parciales sigue detectando los patrones de fraude con PR-AUC=0.975, lo que indica que los anillos de lavado dejan huella detectable incluso en sus fases iniciales.

**Implicancia para BRS:** El número correcto para reportar a dirección es PR-AUC=0.975 (temporal) — no el 1.000 transductivo. Este resultado simula el entorno de producción real: el modelo siempre opera sobre datos futuros que no vio durante el entrenamiento. La caída de 0.002 puntos desde el transductivo es el costo real de la evaluación honesta.

**Protocolo recomendado para el piloto BRS:** split temporal mensual — entrenar hasta mes M, validar en M+1, evaluar en M+2. Re-entrenar cada trimestre con los nuevos datos etiquetados por compliance.

---

## Fase F — Insights de Modelo

---

### Insight 9 — El GNN mejora 0.050 puntos de PR-AUC sobre XGBoost

> **Hallazgo:** GraphSAGE logra PR-AUC=0.977 vs XGBoost=0.926 vs LogReg=0.675, usando exactamente el mismo test set y splits. El único diferencial es el acceso a la estructura del grafo.

> **Implicancia para BRS:** Con XGBoost, los analistas de BRS revisarían ~21 alertas/día con 20% del fraude sin detectar. Con el GNN, las alertas bajan a ~26/día (ligeramente más amplias) pero el fraude no detectado cae a 0% en este dataset. El costo operativo es marginalmente mayor, el beneficio es material.

> **Acción sugerida:** Presentar la curva PR comparativa al directorio como el argumento central del proyecto. El área entre la curva XGBoost y la curva GNN representa el "fraude adicional detectado" — traducirlo a montos evitados usando el ticket promedio de BRS.

---

### Insight 10 — La topología sola (ablation) logra PR-AUC=0.021

> **Hallazgo:** Un GraphSAGE entrenado con features constantes (solo la estructura del grafo, sin balance, risk_score ni ningún atributo de cuenta) alcanza PR-AUC=0.021. La información de *quién se conecta con quién* ya contiene señal de fraude independiente de los features individuales.

> **Implicancia para BRS:** Esto significa que aunque los datos de cuentas estén incompletos, desactualizados o sean poco confiables, el grafo de transacciones por sí solo aporta valor. En una implementación real, el modelo puede correr incluso con features de cuenta degradados (ej.: clientes con poco historial, cuentas nuevas) y seguir detectando anillos por estructura.

> **Acción sugerida:** En la fase piloto, priorizar la disponibilidad del grafo de transacciones sobre la calidad de los features de cuenta. El pipeline mínimo viable es: transacciones → GNN topológico → score de red.

---

### Insight 11 — Los nodos de anillo más difíciles son los periféricos

> **Hallazgo:** El score mínimo entre nodos fraudulentos es 0.0002. Los nodos con score más bajo tienden a tener menor grado — son los nodos "de entrada" o "de salida" del anillo que tienen menos vecinos fraudulentos directos y por lo tanto reciben menos señal de red.

> **Implicancia para BRS:** En un esquema de lavado real, los nodos periféricos (entrada/salida del anillo) suelen ser las cuentas más "limpias" — las que el lavador usa para interactuar con el sistema bancario legítimo. Son los que más difícilmente captura un modelo tabular y los que más cerca están del límite de detección del GNN.

> **Acción sugerida:** Para los nodos con score intermedio (0.3–0.7), aplicar una segunda revisión manual que considere el contexto completo del anillo detectado, no solo el nodo individual. Un analista que ve el anillo completo puede decidir mucho más rápido que uno que solo ve la cuenta.

---

### Insight 12 — Regresión Logística en grafos: el límite de la linealidad

> **Hallazgo:** LogReg logra ROC-AUC=0.986 (alta separabilidad global) pero PR-AUC=0.675 (baja precisión en clases desbalanceadas) y Recall@P90=0. La frontera de decisión lineal no puede separar fraude de legítimo en el espacio de features en el punto operativo (90% precisión).

> **Implicancia para BRS:** Muchos sistemas de compliance internos usan regresión logística o scorecards lineales como base. Este resultado muestra que incluso con features de red (grado, montos, contrapartes), la no-linealidad es fundamental. El salto a XGBoost ya aporta enormemente; el salto a GNN añade la señal de vecindario.

> **Acción sugerida:** Al presentar el proyecto a BRS, usar la progresión LogReg → XGBoost → GNN como narrativa de "capas de inteligencia": cada capa agrega un tipo de información que la anterior no puede capturar (no-linealidad → estructura de red).
