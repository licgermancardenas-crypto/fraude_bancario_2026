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

Engagement simulado para *Banco Regional del Sur (BRS)*: prueba de concepto end-to-end de detección de redes de lavado de activos usando **Graph Neural Networks** sobre un grafo transaccional sintético de 75.000 cuentas y ~544.000 transacciones.

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
| Agregado (features de cuenta) | 8 | 3.885 | 35,8% | 65,0% | 12,5× |
| **Temporal (ventana sobre el stream)** | 5 | **1.797** | **84,0%** | **70,5%** | **29,4×** |

El motor temporal marca **menos de la mitad de cuentas** que el agregado y aun así
detecta más fraude, con una precisión más del doble. **325 fraudes los ve sólo el
motor temporal** (206 sólo el agregado, 1.184 los dos). Combinados, el recall del
motor de reglas sube de 65% a 80,1%.

Cada escenario temporal además **cita las operaciones concretas que lo dispararon** —
visibles en el detalle del caso y transcribibles al ROS. Un reporte de operación
sospechosa se sostiene con las operaciones citadas, no con el nombre de una regla.

**Dos salvedades honestas.** (1) La complementariedad con el GNN sigue dando
`solo_reglas = 0`: el modelo está saturado sobre este dataset sintético (detecta 2.134
de 2.140 fraudes), así que ninguna regla puede aportarle cobertura. El valor de las
reglas acá es la defendibilidad regulatoria — determinista, citable, auditable — no
la cobertura. (2) No hay escenario de umbral de efectivo: en este dataset las 60.250
extracciones son todas legítimas, así que una regla de efectivo sería un generador
puro de falsos positivos. El dataset no modela colocación en efectivo.

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
| Transferencia individual atípica (persona física) | $1.500.000 | 4,0 |
| Transferencia individual atípica (empresa) | $5.000.000 | 13,3 |
| Volumen agregado atípico (persona física) | $5.000.000 | 13,3 |
| U-turn: monto mínimo para emparejar | $5.000.000 | 13,3 |
| Referencia UIF — reporte sistemático de efectivo | $15.064.000 | 40,0 |

**El reescalado no toca el modelo.** Es un factor lineal sobre
`amount`/`comision`/`impuesto`/`balance`: no altera `src`/`dst`/`timestamp`/
`is_fraud`, así que el grafo es el mismo. Y como `build_graph` normaliza las
features con la media y el desvío de train, el factor se cancela exactamente —
`(Kx − Kμ)/(Kσ) = (x − μ)/σ` — con lo cual `data.x` queda idéntica (diferencia
máxima medida: 1,5e-4, ruido de representación float32) y **no hay
reentrenamiento**. `edge_attr` lleva el monto crudo pero los modelos nunca
reciben `edge_weight`, así que tampoco influye. Los umbrales de ambos motores
están en la misma escala: verificado que marcan **exactamente el mismo conjunto
de 3.432 cuentas con las mismas reglas disparadas** antes y después.

**Limitación declarada — densidad, no escala.** El dataset tiene ~14,5
movimientos por cuenta por año; una cuenta minorista real tiene entre 200 y 600.
Por eso ningún factor único deja bien las dos cosas a la vez: anclado al monto
individual (lo que se hizo), los montos de cada operación son plausibles pero el
volumen anual por cuenta queda por debajo del de una cartera real. Lo que falta
es densidad transaccional, no escala monetaria — y corregirlo implica regenerar
el grafo, con lo cual sí habría que reentrenar y recalibrar todo. Queda como
frente abierto y declarado, no disimulado.

## Reproducir

```bash
# Dependencias Python
uv venv venv && source venv/bin/activate
uv pip install -r requirements.txt

# Pipeline completo (en orden)
python -m src.generate              # dataset sintético (75K cuentas)
python -m src.build_graph           # grafo PyG + splits estratificados
python -m src.train_baseline        # LogReg + XGBoost
python -m src.train                 # GraphSAGE
python -m src.train_gat             # GAT
python -m src.train_node2vec        # Node2Vec + XGBoost
python -m src.explain               # GNNExplainer
python -m src.trace_origin          # backward tracing
python -m src.detect_placement      # scoring de colocación
python -m src.evaluate_temporal     # evaluación temporal
python -m src.analysis              # comparativa + figuras
python -m src.generate_entities     # empresas, PEPs, shell companies
python -m src.export_dashboard      # JSONs para dashboard
python -m src.export_scenarios      # backtest de calibración de los 13 escenarios ALD
python -m src.enrich_personas       # identidades sintéticas
python -m src.generate_report       # informe PDF

# Dashboard local
cd dashboard && npm install && npm run dev
# → http://localhost:3000

# API local
uvicorn api.main:app --reload
# → http://localhost:8000/docs
```

> **Nota de escala:** el pipeline fue validado a `scale_factor=0.5` (75K cuentas). A `scale_factor=1.0` (150K cuentas) el entrenamiento full-batch puede quedarse sin memoria en equipos con menos de 4 GB RAM. Se recomienda implementar `NeighborLoader` antes de escalar.

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
