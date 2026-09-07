# Phantom AI — Detección de Redes de Lavado mediante Inteligencia de Grafos

![CI](https://github.com/licgermancardenas-crypto/fraude_bancario_2026/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.x-EE4C2C?logo=pytorch&logoColor=white)
![PyG](https://img.shields.io/badge/PyTorch_Geometric-2.x-orange)
![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)
![Vercel](https://img.shields.io/badge/Deploy-Vercel-black?logo=vercel)
![Render](https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render&logoColor=white)
![License](https://img.shields.io/badge/datos-100%25_sintéticos-green)

**Dashboard en vivo → [fraude-bancario-2026.vercel.app](https://fraude-bancario-2026.vercel.app)**
**API en vivo → [phantom-rcs9.onrender.com/docs](https://phantom-rcs9.onrender.com/docs)**

Engagement simulado para *Banco Regional del Sur (BRS)*: prueba de concepto end-to-end de detección de redes de lavado de activos usando **Graph Neural Networks** sobre un grafo transaccional sintético de 75.000 cuentas y ~11,2 millones de transacciones.

El sistema detecta **8 tipologías de lavado** alineadas con GAFI que los controles basados en reglas no pueden ver: **anillos cíclicos** (4–7 saltos), **estructuración / pitufeo**, **agregación de fondos**, **cuentas de paso** (flow-through), **sociedades pantalla**, **cuentas durmientes reactivadas**, **redes de mulas** y **round-tripping** (integración) — además de rastrear a los **perpetradores de origen** que inyectaron el dinero sin ser detectados por el modelo principal.

---

## Resultados

| Modelo | PR-AUC ↑ | ROC-AUC | Recall @ P90 | Fraude no detectado |
|---|---|---|---|---|
| Logistic Regression | 0.728 | 0.976 | 18% | 22.4% |
| XGBoost | 0.950 | 0.996 | 88% | 11.8% |
| GAT | 0.908 | 0.997 | 77% | 11.5% |
| **GraphSAGE** | **0.978** | **0.9996** | **97%** | **3.4%** |

> **PR-AUC** (Área bajo la curva Precisión-Recall) es la métrica principal para fraude: mide qué tan bien detecta casos raros sin generar falsas alarmas. Un clasificador aleatorio obtendría ~0.029 (la tasa base de fraude). **Por encima de 0.95 es excelente.**
>
> **Recall @ P90:** con la exigencia de que 9 de cada 10 alertas sean fraude real, GraphSAGE detecta el **97%** del fraude total.

**Hallazgo clave — homofilia 7.0× + señal conductual:** los vecinos de cuentas fraudulentas son 7.0× más propensos a ser también fraudulentos que los de una cuenta legítima. Las cuentas mula son crediticiamente normales (Cohen d ≈ -0.01, sin poder discriminante) pero se delatan por sus **conexiones** y por su **comportamiento** (velocidad, retención near-cero, ráfagas, reactivación). Esta combinación —estructura + features de comportamiento— es la justificación cuantitativa de por qué los GNN superan a los modelos tabulares y a los embeddings puramente topológicos.

**Rastreo de perpetradores:** el backward tracing sobre el grafo dirigido identificó 392 cuentas de origen que alimentaron a 2.075 mulas detectadas, de las cuales 300 eran prácticamente invisibles para el modelo principal (score GNN < 0.3). El principal inyector oculto —con score ≈ 2%— colocó $239K en el esquema; en conjunto el rastreo remonta ~$78,8M en fondos movidos. La propagación inversa de riesgo prioriza a estos perpetradores sin necesidad de etiquetas adicionales.

---

## Qué incluye el sistema

### Modelos de detección

| Módulo | Modelo | Arquitectura | PR-AUC |
|---|---|---|---|
| `src/train_baseline.py` | Logistic Regression + XGBoost | Tabular (27 features) | 0.728 / 0.950 |
| `src/train_node2vec.py` | Node2Vec + XGBoost | Random walks 64-dim | 0.06 — ablación (ver nota) |
| `src/train_gat.py` | GAT — Graph Attention Network | GATConv(27→64, 4 heads) × 2 | 0.908 |
| `src/train.py` | **GraphSAGE** | SAGEConv(27→64→64) × 2 | **0.978** |

> **Nota sobre Node2Vec:** actúa como **ablación deliberada** — aprende embeddings a partir de la topología pura (random walks), sin features de nodo. Sobre las tipologías conductuales (cuentas de paso, durmientes, round-tripping), que no forman comunidades densas, colapsa a PR-AUC ≈ 0.06. Esto cuantifica *por qué* hacen falta GNNs que combinen estructura **y** comportamiento: la señal no es puramente topológica.

### Explicabilidad y trazabilidad

| Módulo | Función |
|---|---|
| `src/explain.py` | GNNExplainer: qué features y conexiones determinan cada predicción |
| `src/trace_origin.py` | Backward tracing: remonta desde mulas detectadas hasta perpetradores de origen |
| `src/detect_placement.py` | Propagación inversa de riesgo: scoring de colocación para todos los nodos |
| `src/evaluate_temporal.py` | Evaluación temporal: rendimiento sobre el período posterior al entrenamiento |
| `src/enrich_personas.py` | Capa de identidad: nombre, DNI, CUIL, AFIP y domicilio argentinos por cuenta |

### Landing + Dashboard (8 páginas + Compliance)

El proyecto Next.js tiene dos árboles de rutas independientes (route groups,
cada uno con su propio root layout): `app/(marketing)` es la landing pública
en `/`, `app/(dashboard)` es la herramienta real bajo `/app/*`.

| Ruta | Contenido |
|---|---|
| `/` | **Landing de marketing** — Phantom AI, financial crime intelligence (`app/(marketing)/page.tsx`) |
| `/app` | Overview tipo "producto": pulso del sistema (casos, sparkline, Recall@P90, KPIs de compliance), casos por patrón (donut), alertas por mes (área), cohortes de riesgo KYC vs. score GNN (scatter, punto ciego del onboarding), casos por provincia (mapa de Argentina), KPIs globales, curvas PR comparativas, distribución de scores GNN |
| `/app/anillos` | Explorador de anillos cíclicos (Cytoscape.js interactivo) |
| `/app/origen` | Grafo dirigido del anillo + tabla de perpetradores identificados |
| `/app/cuentas` | Ranking de riesgo top 200, filtrable y ordenable |
| `/app/metodologia` | Documentación técnica del sistema |
| `/app/escenarios` | **Gestión de escenarios** — catálogo de los dos motores de reglas (agregado y de ventana temporal) con norma de respaldo, performance medida por escenario y segmento KYC, simulador what-if de umbrales (backtest sobre la cartera) y cambio de calibración con aprobación de cuatro ojos |
| `/app/casos` | **Cola de alertas** con 80 casos pre-generados, filtros, KPIs, gestión de estado |
| `/app/entidades` | **Red de entidades** (personas, empresas, PEPs, shell companies) en Cytoscape.js |
| `/app/casos/[id]/ros` | **Formulario ROS** (Reporte de Operación Sospechosa) pre-completado, narrativa automática, control de cuatro ojos, referencia a Ley 25.246 / UIF |
| `/app/en-vivo` | Consola de scoring en vivo contra la API FastAPI (Render) |

Identidad visual (colores, tipografía, isotipo) centralizada en
[`dashboard/brand-kit/`](dashboard/brand-kit/BRAND.md) — fuente de verdad
compartida entre la landing y el dashboard.

### API de scoring (FastAPI)

**API en vivo → [phantom-rcs9.onrender.com](https://phantom-rcs9.onrender.com) · [docs interactivas](https://phantom-rcs9.onrender.com/docs)**

Servicio independiente en `api/` (FastAPI, deploy en Render free tier) que expone las cuentas, casos, anillos y scores pre-computados vía REST. El dashboard sigue siendo un deploy 100% estático (JSONs en `dashboard/public/data/`) para la navegación principal — rápido y sin dependencia de un servicio externo. La página **`/app/en-vivo`** del dashboard sí llama a esta API en tiempo real (`POST /accounts/score`, `GET /health`), como consola de demostración de la integración REST para sistemas externos (core bancario, SIEM, etc.).

| Endpoint | Contenido |
|---|---|
| `GET /health`, `/stats` | Estado del servicio y métricas agregadas del modelo |
| `GET /accounts`, `/accounts/{id}`, `POST /accounts/score` | Ranking de riesgo y scoring de cuentas |
| `GET /cases`, `/cases/{id}` | Cola de alertas y detalle de casos |
| `GET /rings`, `/perpetrators`, `/placement` | Anillos, perpetradores de origen y scores de colocación |
| `GET /models/performance` | Métricas comparativas de los 5 modelos entrenados |

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
   src/generate.py          ← 75K cuentas · ~544K txns · escenarios AML
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
                    ┌───────────┴────────────┬─────────────────────┐
                    ▼                        ▼                     ▼
             Next.js 14                  generate_report.py    api/main.py
             (Vercel)                    (PDF institucional)   FastAPI (Render)
                    │                                                 ▲
                    └──────────────── /app/en-vivo (fetch runtime) ───────┘
```

> `api/` lee los mismos artefactos pre-computados (`data/processed/`) y los expone vía REST. El dashboard la consume en runtime solo desde `/app/en-vivo` (consola de scoring en vivo); el resto de las páginas siguen sirviendo los JSONs estáticos para no depender de la disponibilidad de un servicio externo.

---

## Stack

**ML / Data:** Python 3.13 · PyTorch · PyTorch Geometric · XGBoost · scikit-learn · NetworkX · gensim · pandas · matplotlib · seaborn

**Dashboard:** Next.js 14 · TypeScript · Tailwind CSS · Recharts · Cytoscape.js

**API:** FastAPI · Uvicorn/Gunicorn

**PDF:** Playwright/Chromium · HTML/CSS → A4

**Deploy:** Vercel (dashboard) · Render (API)

---

## Estructura del proyecto

```
fraud-gnn/
├── src/
│   ├── generate.py            # grafo sintético: 75K nodos, ~544K aristas, escenarios AML
│   ├── features.py            # 27 features por nodo (grado, montos, conectividad, perfil, comportamiento temporal)
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
│   ├── rules_engine.py        # motor agregado: 8 escenarios ALD sobre features de cuenta
│   ├── rules_temporal.py      # motor temporal: 5 escenarios de ventana móvil sobre el stream
│   ├── export_scenarios.py    # gestión de escenarios: performance por regla + curva de calibración
│   ├── generate_entities.py   # empresas, shell companies, PEPs, directores
│   ├── enrich_personas.py     # identidades sintéticas argentinas (DNI, CUIL, AFIP)
│   ├── generate_report.py     # informe PDF institucional
│   └── models/
│       ├── graphsage.py       # SAGEConv(27→64→64) + Linear(64→2)
│       ├── gat.py             # GATConv(27→64→64, 4 heads) + Linear(64→2)
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
│   │   ├── casos/[id]/ros/    # formulario ROS (Ley 25.246 / UIF)
│   │   └── entidades/         # red de entidades (Cytoscape.js)
│   └── public/data/           # JSONs exportados (cuentas, casos, entidades)
├── api/                        # FastAPI scoring service (deploy en Render)
│   ├── main.py                 # 11 endpoints — cuentas, casos, anillos, placement, modelos
│   ├── loader.py                # carga de artefactos pre-computados (data/processed/)
│   └── requirements.txt         # dependencias livianas para el deploy
├── render.yaml                 # config de deploy (Render, plan free)
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


## Los dos motores de reglas

El programa corre **13 escenarios ALD deterministas** repartidos en dos motores que
miran los mismos datos de forma distinta.

El **motor agregado** (`src/rules_engine.py`, R01–R08) evalúa features de cuenta:
totales, grados, promedios y ratios calculados sobre todo el período. Es barato y
cubre los red flags clásicos, pero es estructuralmente ciego a la dimensión que
define media tipología ALD — *cuándo* pasaron las cosas. Diez transferencias a diez
destinatarios distintos son operatoria normal en un año y son pitufeo en cuarenta y
ocho horas: el agregado no distingue los dos casos.

El **motor temporal** (`src/rules_temporal.py`, R09–R13) evalúa la secuencia de
operaciones dentro de ventanas móviles sobre el stream de transacciones, que es como
razona un sistema de monitoreo transaccional real. Cubre dispersión en ráfaga
(pitufeo), agregación en ráfaga, operación circular (U-turn), tránsito emparejado
entrada-salida y desvío contra la baseline de la propia cuenta.

| Motor | Escenarios | Cuentas marcadas | Precisión | Recall | Lift |
|---|---|---|---|---|---|
| Agregado (features de cuenta) | 8 | 3.950 | 20,6% | 36,1% | 6,9× |
| **Temporal (ventana sobre el stream)** | 5 | **2.121** | **51,2%** | **48,1%** | **17,0×** |

El motor temporal marca **casi la mitad de cuentas** que el agregado y aun así detecta
más fraude, con una precisión dos veces y media mayor. **351 fraudes los ve sólo el
motor temporal** (81 sólo el agregado, 734 los dos). Combinados, el recall del motor
de reglas sube de 36,1% a 51,7%.

Cada escenario temporal además **cita las operaciones concretas que lo dispararon** —
visibles en el detalle del caso y transcribibles al ROS. Un reporte de operación
sospechosa se sostiene con las operaciones citadas, no con el nombre de una regla.

**El agregado se cayó al densificar, y eso es el hallazgo.** Los umbrales están
recalibrados sobre el libro denso —percentil ~99 de la población legítima de cada
segmento, que es lo calibrable sin etiquetas en producción— así que los números de
arriba no son un desajuste de umbral: son la consecuencia medida. Contra un fondo de
~300 movimientos anuales, el fan-in y el fan-out **anuales** de una cuenta de fraude
son indistinguibles de los de una cuenta legítima activa: **R05 dispara con 6,4% de
precisión y R06 con 6,2%, sobre una tasa base de 3,01%** — lift 2,1× es no decir nada.
Sobre el libro esparso esos mismos escenarios parecían funcionar. Es exactamente la
razón por la que un sistema ALD real monitorea ventanas móviles y no agregados
anuales, y acá queda medido en vez de afirmado.

**Dos salvedades honestas.** (1) La complementariedad con el GNN da `solo_reglas = 11`
sobre 2.255 fraudes: el modelo detecta 2.213 y las reglas apenas le agregan once casos.
Es una mejora contra el `solo_reglas = 0` del libro esparso —donde el modelo saturaba
y las reglas no aportaban literalmente nada— pero el orden de magnitud no cambia: el
valor de las reglas acá es la defendibilidad regulatoria (determinista, citable,
auditable), no la cobertura. (2) No hay escenario de umbral de efectivo: en este
dataset las 973.375 extracciones son todas legítimas, así que una regla de efectivo
sería un generador puro de falsos positivos. El dataset no modela colocación en
efectivo.

Los umbrales viven en `config/config.yaml` (`rules:` y `rules_temporal:`),
segmentados por tipo de cuenta donde el comportamiento comercial legítimo —nómina,
cobros de comercio— produce el mismo patrón por motivos lícitos.


## Escala monetaria y anclaje regulatorio

El generador emite montos en una unidad sintética adimensional. `monetary.scale`
en `config/config.yaml` los lleva a pesos argentinos plausibles para 2026
(`generate.py::rescale_amounts`), de modo que las cifras del dashboard, del
explorador de transacciones y de los ROS se lean como un extracto real y no como
números de laboratorio.

**El anclaje es declarado, no inventado.** La UIF indexa sus umbrales en Salarios
Mínimos, Vitales y Móviles desde la Res. 78/2025 — el reporte sistemático de
operaciones en efectivo es de 40 SMVM. Tomando el SMVM de agosto de 2026
($376.600), los umbrales del motor de reglas quedan expresados en múltiplos
auditables contra la norma en vez de ser números sueltos:

| Umbral | Pesos | En SMVM |
|---|---:|---:|
| Transferencia individual atípica (persona física) | $4.000.000 | 10,6 |
| Transferencia individual atípica (empresa) | $20.000.000 | 53,1 |
| Volumen agregado atípico (persona física) | $123.000.000 | 326,6 |
| U-turn: monto mínimo para emparejar | $5.000.000 | 13,3 |
| Tránsito emparejado: monto mínimo | $1.800.000 | 4,8 |
| Referencia UIF — reporte sistemático de efectivo | $15.064.000 | 40,0 |

**El reescalado no toca el modelo.** Es un factor lineal sobre
`amount`/`comision`/`impuesto`/`balance`: no altera `src`/`dst`/`timestamp`/
`is_fraud`, así que el grafo es el mismo. Y como `build_graph` normaliza las
features con la media y el desvío de train, el factor se cancela exactamente —
`(Kx − Kμ)/(Kσ) = (x − μ)/σ` — con lo cual `data.x` queda idéntica (diferencia
máxima medida: 1,5e-4, ruido de representación float32) y **no hay
reentrenamiento**. `edge_attr` lleva el monto crudo pero los modelos nunca
reciben `edge_weight`, así que tampoco influye. Los umbrales de ambos motores
estaban en la misma escala: verificado que marcaban **exactamente el mismo
conjunto de 3.432 cuentas con las mismas reglas disparadas** antes y después del
reescalado. Esa verificación se hizo sobre el libro esparso vigente entonces —
las 3.432 son el conteo de aquella corrida, no del dataset actual; los umbrales
de la tabla de arriba son los mismos y hoy marcan 4.927 cuentas sobre el libro
denso (ver "Densificación transaccional").

**Densidad transaccional — limitación saldada.** La versión anterior de este
README declaraba que el dataset tenía ~14,5 movimientos por cuenta y por año
contra los 200-600 de una cuenta minorista real, y que corregirlo obligaba a
regenerar el grafo y reentrenar todo. Se hizo: ver la sección siguiente.

## Densificación transaccional

La versión anterior del dataset tenía **14,5 movimientos por cuenta y por año**,
contra los 200-600 de una cuenta minorista real, y estaba declarado como
limitación abierta. Al ir a corregirlo apareció que el problema no era sólo de
volumen.

**El diagnóstico.** La capa legítima sorteaba `src` y `dst` uniformemente sobre
el padrón, lo que produce un grafo aleatorio de Erdős–Rényi: **1,09 transacciones
por arista**, el 93% de las aristas de un solo uso. La consecuencia medible:

| | degree medio | contrapartes distintas | ratio |
|---|---:|---:|---:|
| Cuentas legítimas | 14,5 | 13,2 | **0,913** |
| Cuentas de fraude | 15,2 | 14,9 | **0,980** |

La **concentración de contrapartes** —de las señales más fuertes que usa un
sistema ALD real— no distinguía nada. Una cuenta minorista real tiene degree
~250 contra ~30 contrapartes distintas (ratio ~0,12); una mula opera con
contrapartes casi siempre nuevas. El dataset no modelaba esa diferencia porque
nadie repetía contraparte, y **densificar subiendo el total de transacciones
sobre el sorteo uniforme lo habría empeorado**: más aristas de un solo uso
empujan el ratio legítimo aún más cerca de 1,0 y convierten el grafo en un
hairball donde el fan-in y el fan-out dejan de discriminar.

**La corrección.** `src/economy.py` construye la economía legítima sobre
**círculos de contrapartes recurrentes**: cada cuenta elige un conjunto estable
—el supermercado de siempre, el empleador, cuatro servicios con débito
automático, un puñado de pares— y opera repetidamente con él durante el año, con
un ticket característico por vínculo y cadencia mensual donde corresponde
(servicios, nómina, proveedores). Se agregan niveles de actividad, incluido un
6% de cuentas genuinamente durmientes.

| | antes | ahora |
|---|---:|---:|
| Transacciones | 544.157 | **11.240.742** |
| Movimientos por cuenta y año | 14,5 | **300** (mediana 221) |
| Transacciones por arista | 1,09 | **7,40** |
| Aristas únicas | 497.799 | 1.518.706 |
| Ratio contrapartes/degree (legítimas) | 0,913 | **0,144** |

**Lo que la densificación arrastró.** Tres frentes que no eran opcionales:

1. **Almacén columnar** (`src/txn_store.py`). El CSV con strings costaba 786
   bytes por fila; a 11,2M de filas son ~8,8 GB en pandas, imposible en el equipo
   de trabajo (5,2 GB de RAM). El almacén guarda un `.npy` por columna con
   dtypes compactos y deriva al vuelo lo que es función de las demás
   (`transaction_id`, CBU, alias, rubro, glosa, referencia): **29 bytes por
   fila**, 327 MB en disco, y cada módulo carga sólo las columnas que usa.
2. **Agregación de aristas paralelas** (`src/build_graph.py`). Las 11,2M de
   transacciones se colapsan a 1,52M de aristas por par, con la intensidad de la
   relación en `edge_attr`. Además de ser lo correcto para el paso de mensajes
   —un supermercado visitado 40 veces no debe pesar 40 veces más que la
   contraparte de una sola operación, que es la que interesa— es lo que mantiene
   el entrenamiento full-batch viable: 3,7 s por época y 1,5 GB de pico.
3. **Recalibración de los 13 escenarios.** Los umbrales de grado del motor
   agregado (`fanin_degree: 12`) perdían todo sentido a 300 movimientos anuales.
   Se recalibraron sobre el percentil ~99 de la población legítima de cada
   segmento, que es lo calibrable sin etiquetas en producción.

### Dos hallazgos honestos

**El motor agregado pierde casi todo su poder contra un fondo realista.** Con 300
movimientos anuales por cuenta, el fan-in y el fan-out *anuales* de una cuenta de
fraude son indistinguibles de los de una cuenta legítima activa: R05 y R06 caen a
~6% de precisión y ~0,2% de recall. El motor completo pasa de 35,8% de precisión
y 65,0% de recall a **22,2% / 34,3%**. El motor **temporal**, que mira ventanas
móviles, rinde **51,2% de precisión y 48,1% de recall con lift 17,0×** sobre 2.121
alertas — menos alertas, más del doble de precisión y 1,4× el recall del agregado.
Es la razón por la que un sistema ALD real monitorea ventanas y no agregados
anuales, y acá queda medido en vez de afirmado.

**La ventaja del GNN se ensancha.** Sobre el dataset anterior GraphSAGE le sacaba
2,8 puntos de PR-AUC a XGBoost (0,978 contra 0,950), una diferencia que era fácil
atribuir a saturación. Sobre el grafo denso la diferencia es de **6,1 puntos**
(0,943 contra 0,882) y contra la regresión logística, de 47 puntos. El fondo
lícito realista diluye los agregados tabulares, y la topología —que es lo que el
GNN explota— sigue en pie. El problema es más difícil para todos y la brecha se
abre: 0,978 sobre un grafo aleatorio decía menos que 0,943 sobre uno realista.

## Reproducir

```bash
# Dependencias Python
uv venv venv && source venv/bin/activate
uv pip install -r requirements.txt

# Pipeline completo (en orden)
python -m src.generate              # dataset sintético (75K cuentas, 11,2M txns)
python -m src.generate_entities     # empresas, PEPs, shell companies, screening
python -m src.enrich_personas       # identidades sintéticas (DNI/CUIL/AFIP)
python -m src.train_baseline        # LogReg + XGBoost (crea los splits)
python -m src.build_graph           # grafo PyG (aristas paralelas agregadas)
python -m src.train                 # GraphSAGE
python -m src.train_gat             # GAT
python -m src.train_node2vec        # Node2Vec + XGBoost
python -m src.explain               # GNNExplainer
python -m src.trace_origin          # backward tracing
python -m src.detect_placement      # scoring de colocación
python -m src.evaluate_temporal     # evaluación temporal
python -m src.analysis              # comparativa + figuras
python -m src.business_impact       # traducción a impacto económico
python -m src.export_dashboard      # JSONs para dashboard
python -m src.export_transactions   # muestra para el explorador de transacciones
python -m src.export_screening      # cola de screening de sanciones
python -m src.export_alerts         # capa de alertas + embudo de triage
python -m src.kyc_profiles          # legajos de cliente (CDD)
python -m src.model_governance      # model card + monitoreo
python -m src.fairness              # impacto dispar del score
python -m src.export_scenarios      # backtest de calibración de los 13 escenarios ALD
python -m src.generate_report       # informe PDF

# Dashboard local
cd dashboard && npm install && npm run dev
# → http://localhost:3000

# API local
uvicorn api.main:app --reload
# → http://localhost:8000/docs
```

> **Nota de escala:** el pipeline fue validado a `scale_factor=0.5` (75K cuentas, 11,2M transacciones) en un equipo de 4 núcleos y 5,2 GB de RAM. El entrenamiento full-batch sigue siendo viable a esa escala **porque `build_graph` agrega las aristas paralelas** (11,2M transacciones → 1,52M aristas únicas): 3,7 s por época y 1,5 GB de pico. A `scale_factor=1.0` (150K cuentas, ~23M transacciones) haría falta un `NeighborLoader`.

---

## Contexto AML

El sistema implementa detección de **8 tipologías** alineadas con las fases GAFI de colocación, estratificación e integración:

**Estratificación (layering)**
- **Anillos cíclicos:** el dinero circula por 4–7 cuentas intermedias en ventanas de 72 h, fragmentando el flujo bajo los umbrales de reporte y diluyendo la trazabilidad.
- **Cuentas de paso (flow-through):** conductos que reciben y reenvían fondos en horas, con saldo residual near-cero (entrada ≈ salida).
- **Sociedades pantalla (shell layering):** los fondos atraviesan cuentas de empresas fantasma que les dan apariencia comercial.

**Colocación (placement)**
- **Estructuración / pitufeo (structuring):** sumas grandes se dividen en transferencias deliberadamente por debajo de los límites regulatorios.
- **Agregación de fondos (fan-in):** múltiples mulas concentran fondos en un colector.
- **Redes de mulas:** un reclutador reparte montos bajo umbral a decenas de cuentas recién abiertas que reenvían a un punto de retiro.
- **Cuentas durmientes reactivadas:** cuentas inactivas por largos períodos que de golpe mueven sumas altas en ráfagas concentradas.

**Integración**
- **Round-tripping / U-turn:** los fondos salen y regresan a la cuenta de origen simulando ingresos legítimos (préstamos, retornos de inversión).

Las tipologías conductuales (cuentas de paso, durmientes, round-tripping) se detectan combinando estructura de grafo con **features de comportamiento** —velocidad, retención, dormancia, ráfagas— que replican las señales de los sistemas de monitoreo transaccional reales.

El módulo de Compliance incluye formularios de ROS pre-completados bajo **Ley 25.246** y **Resolución UIF N° 30/2017** (Argentina).

---

**Germán Cárdenas · Data & Analytics · Julio 2026**
