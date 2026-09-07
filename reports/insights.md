# Insights de negocio — Detección de Fraude / BRS

**Proyecto:** Detección de redes de lavado mediante inteligencia de grafos
**Cliente:** Banco Regional del Sur (BRS)
**Autor:** Germán Cárdenas
**Dataset:** Sintético — scale=0.5, seed=42
**Fecha:** 2026-07-16

> **Todos los insights se generan durante la corrida del pipeline**, ninguno se
> escribe a mano: los 1-8 (EDA) los reescribe `src/eda.py` desde las cifras que
> también publica en `reports/eda_stats.json`, y los 9+ los agregan `analysis.py`,
> `explain.py`, `trace_origin.py`, `detect_placement.py` y `evaluate_temporal.py`.
> Hasta 2026-09-07 los 1-8 sí se transcribían a mano, y por eso quedaron
> publicando cifras de una corrida vieja. El set anterior (scale=0.01) quedó
> archivado en `reports/insights_scale0.01_archive.md`.

---

## Fase C — Análisis Exploratorio del Grafo

---

### Insight 1 — La señal de fraude es de forma, no de monto individual

> **Hallazgo:** Las transacciones fraudulentas tienen una mediana de $684.352 contra $43.710 de las legítimas (ratio 15,7x), y una media de $1.794.626 contra $193.084. Pero dentro de cada anillo el monto se reduce en cada salto y se fragmenta al cerrar el ciclo, de modo que las transferencias intermedias caen dentro del rango cotidiano aunque la entrada al anillo sea grande.

> **Implicancia para BRS:** El umbral de monto sigue sirviendo para capturar la *entrada* del dinero al anillo, pero no los saltos intermedios ni el fan-out de salida, que es donde el esquema se vuelve invisible. Como señal única deja pasar la mayor parte del recorrido.

> **Acción sugerida:** Complementar los umbrales con alertas de *velocidad transaccional por vecindario*: un nodo que recibe y reenvía montos similares a múltiples destinos en ventanas de 72 h es candidato a revisión, sin importar el monto individual.

---

### Insight 2 — El score de riesgo crediticio externo no detecta lavado (d ≈ 0)

> **Hallazgo:** El risk score externo (crediticio) tiene un tamaño del efecto de Cohen d = 0,002 entre cuentas fraudulentas y legítimas — indistinguible de cero. Las medias son 0,1997 y 0,1994.

> **Implicancia para BRS:** Si el sistema de alertas usa el score crediticio como señal AML, está priorizando mal. Las cuentas de lavado no son crediticiamente riesgosas: son cuentas normales usadas instrumentalmente. El problema es de *red*, no de *perfil individual*. El resultado se mantiene entre corridas a distinta escala y densidad, así que no es ruido de muestra chica.

> **Acción sugerida:** Desconectar el score crediticio de las reglas de detección de lavado y construir un score específico de red, como el que produce el GNN de este proyecto.

---

### Insight 3 — Homofilia 2,9x: los vecinos del fraude tienden a ser fraude

> **Hallazgo:** Las aristas fraude→fraude son el 0,261% del grafo contra el 0,090% esperado bajo distribución aleatoria — un lift de **2,9x**. El coeficiente de homofilia global es h = 0,953.

> **Implicancia para BRS:** La señal existe en el vecindario, no en la cuenta. Pero el lift bajó fuerte respecto de versiones anteriores del dataset (era 7,3x sobre el libro esparso): al densificar la operatoria legítima y sumar tipologías conductuales —cuenta de paso, durmiente reactivada, round-tripping— el fraude deja de formar comunidades densas y pasa a esconderse *dentro* del tráfico normal. La señal de vecindario sigue siendo real y sigue justificando el uso de GNNs, pero ya no es el argumento dominante que era.

> **Acción sugerida:** No apoyar la comunicación interna sólo en el lift de homofilia. El argumento fuerte pasó a ser la brecha medida entre el GNN y los baselines tabulares sobre el mismo test set.

---

### Insight 4 — El grafo es, en la práctica, una sola componente conexa

> **Hallazgo:** El 94,0% de las 75.000 cuentas está en una única componente débilmente conexa (4.480 componentes en total, 8.604 fuertemente conexas). La densidad del grafo es 2.70e-04.

> **Implicancia para BRS:** Casi ninguna cuenta está aislada, así que la señal se propaga a varios saltos y un GNN de 2 capas alcanza un vecindario informativo para casi todo el padrón.

> **Acción sugerida:** Al escalar a datos reales, verificar si el grafo se fragmenta. Las cuentas que queden en componentes chicas van a tener menos señal de vecindario y merecen menor confianza de predicción.

---

### Insight 5 — El grado ya no delata a la mula: 0,77x de entrada

> **Hallazgo:** Las cuentas de lavado tienen grado de entrada 0,77x y de salida 0,95x el de una cuenta legítima (15,7 contra 20,4 de entrada). Operan **menos** que una cuenta minorista activa, no más.

> **Implicancia para BRS:** Es una inversión respecto de lo que este mismo análisis reportaba sobre el libro esparso (1,36x superior, el clásico "comportamiento de router"). Contra un fondo realista de cientos de movimientos anuales por cuenta, el volumen dejó de discriminar: una mula que mueve dinero treinta veces al año parece menos activa que un comercio. Cualquier regla de velocidad calibrada sobre volumen bruto va a marcar comercios y dejar pasar mulas.

> **Acción sugerida:** No usar grado ni volumen como regla de filtrado. Lo que distingue a la mula es la *forma* de la operatoria — simetría entrada/salida, retención de saldo cercana a cero, concentración de contrapartes — que es lo que capturan las features de comportamiento del modelo.

---

### Insight 6 — El fraude se distribuye casi uniforme por tipo de cuenta (2,9–3,4%)

> **Hallazgo:** La prevalencia por tipo es business 3,4%, merchant 2,9%, personal 2,9%. Ningún tipo está marcadamente sobre-representado.

> **Implicancia para BRS:** El tipo de cuenta no sirve como proxy de riesgo AML. Segmentar la cola de alertas por tipo de titular no concentra fraude.

> **Acción sugerida:** Mantener el tipo de cuenta como feature de contexto del modelo y como eje de segmentación de *umbrales* (el comportamiento comercial legítimo difiere del minorista), pero no como regla de filtrado de riesgo.

---

### Insight 7 — Los anillos son cortos y cerrados: 10 detectados, 4,7 nodos promedio

> **Hallazgo:** Se detectaron 10 anillos de lavado de hasta 8 saltos, con tamaños de 4 nodos, 5 nodos, 6 nodos, 7 nodos y un promedio de 4,7 nodos. Las aristas fraude→fraude son el 3,46% del total de relaciones del grafo.

> **Implicancia para BRS:** Los ciclos son cortos, así que un GNN de 2 capas cubre buena parte del anillo desde cualquiera de sus nodos. Pero también significa que el dinero completa el circuito rápido: si el monitoreo es batch diario, el ciclo se cierra antes de la alerta.

> **Acción sugerida:** Priorizar scoring en cuasi-real-time (cada 4 h) para los nodos de mayor riesgo, en lugar de batch diario.

---

### Insight 8 — Pico horario de fraude a las 02:00, día Jue

> **Hallazgo:** La actividad fraudulenta se concentra a las 02:00 y el día de mayor volumen es Jue.

> **Implicancia para BRS:** El pico cae fuera del horario bancario. Si compliance opera de 9 a 18, un anillo iniciado de madrugada completa varios saltos antes de la apertura. **Salvedad metodológica:** este patrón lo introduce deliberadamente el generador sintético; no es un hallazgo empírico sobre conducta real de lavado y no debe presentarse como tal.

> **Acción sugerida:** Verificar el patrón horario sobre datos reales de BRS antes de construir cualquier regla que dependa de él. Sobre este dataset sirve para demostrar la capacidad, no para calibrar.

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

### Insight 9 — El GNN mejora 0.061 puntos de PR-AUC sobre XGBoost

> **Hallazgo:** GraphSAGE logra PR-AUC=0.943 vs XGBoost=0.882 vs LogReg=0.471, usando exactamente el mismo test set y splits. El único diferencial es el acceso a la estructura del grafo.

> **Implicancia para BRS:** Con XGBoost los analistas revisarían ~23 alertas/día dejando el 20.6% del fraude sin detectar; con el GNN, ~24 alertas/día y 13.0% sin detectar. El costo operativo es comparable y el beneficio, material.

> **Acción sugerida:** Presentar la curva PR comparativa al directorio como el argumento central del proyecto. El área entre la curva XGBoost y la curva GNN representa el "fraude adicional detectado" — traducirlo a montos evitados usando el ticket promedio de BRS.

---

### Insight 10 — La topología sola (ablation) logra PR-AUC=0.042

> **Hallazgo:** Un GraphSAGE entrenado con features constantes (solo la estructura del grafo, sin balance, risk_score ni ningún atributo de cuenta) alcanza PR-AUC=0.042. La información de *quién se conecta con quién* ya contiene señal de fraude independiente de los features individuales.

> **Implicancia para BRS:** Esto significa que aunque los datos de cuentas estén incompletos, desactualizados o sean poco confiables, el grafo de transacciones por sí solo aporta valor. En una implementación real, el modelo puede correr incluso con features de cuenta degradados (ej.: clientes con poco historial, cuentas nuevas) y seguir detectando anillos por estructura.

> **Acción sugerida:** En la fase piloto, priorizar la disponibilidad del grafo de transacciones sobre la calidad de los features de cuenta. El pipeline mínimo viable es: transacciones → GNN topológico → score de red.

---

### Insight 11 — Los nodos de anillo más difíciles son los periféricos

> **Hallazgo:** El score mínimo entre nodos fraudulentos es 0.0025. Los nodos con score más bajo tienden a tener menor grado — son los nodos "de entrada" o "de salida" del anillo que tienen menos vecinos fraudulentos directos y por lo tanto reciben menos señal de red.

> **Implicancia para BRS:** En un esquema de lavado real, los nodos periféricos (entrada/salida del anillo) suelen ser las cuentas más "limpias" — las que el lavador usa para interactuar con el sistema bancario legítimo. Son los que más difícilmente captura un modelo tabular y los que más cerca están del límite de detección del GNN.

> **Acción sugerida:** Para los nodos con score intermedio (0.3–0.7), aplicar una segunda revisión manual que considere el contexto completo del anillo detectado, no solo el nodo individual. Un analista que ve el anillo completo puede decidir mucho más rápido que uno que solo ve la cuenta.

---

### Insight 12 — Regresión Logística en grafos: el límite de la linealidad

> **Hallazgo:** LogReg logra ROC-AUC=0.928 (alta separabilidad global) pero PR-AUC=0.471 (baja precisión en clases desbalanceadas) y Recall@P90=10.6%. La frontera de decisión lineal no puede separar fraude de legítimo en el espacio de features en el punto operativo (90% precisión).

> **Implicancia para BRS:** Muchos sistemas de compliance internos usan regresión logística o scorecards lineales como base. Este resultado muestra que incluso con features de red (grado, montos, contrapartes), la no-linealidad es fundamental. El salto a XGBoost ya aporta enormemente; el salto a GNN añade la señal de vecindario.

> **Acción sugerida:** Al presentar el proyecto a BRS, usar la progresión LogReg → XGBoost → GNN como narrativa de "capas de inteligencia": cada capa agrega un tipo de información que la anterior no puede capturar (no-linealidad → estructura de red).
