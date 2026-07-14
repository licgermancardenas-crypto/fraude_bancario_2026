# Proyecto: Detección de Fraude Financiero con Graph Neural Networks
### Guía integral de punta a punta — de la generación de datos al entregable bancario
**Autor:** Germán Cárdenas
**Entorno:** Windows + Claude Code (terminal cmd)
**Dataset:** `gen-fraud-graph` (Santander AI Lab) — datos 100% sintéticos

---

## 1. Objetivo del proyecto

### 1.1 Objetivo general

Desarrollar de punta a punta un **sistema de detección de fraude y lavado de dinero basado en Graph Neural Networks**, replicando el ciclo completo de un engagement real de consultoría de datos para una institución financiera: desde la ingesta y análisis de datos transaccionales, pasando por el modelado predictivo y la extracción de insights de negocio, hasta la entrega de un dashboard interactivo desplegado en la web y un informe ejecutivo en PDF con estándar de consultoría.

### 1.2 Objetivos específicos

1. **Datos:** generar y documentar un dataset sintético de transacciones financieras con patrones de fraude realistas (anillos de lavado cíclicos de 4-7 saltos) usando `gen-fraud-graph`.
2. **Análisis:** realizar un análisis exploratorio del grafo que produzca insights accionables sobre la estructura del fraude (topología de anillos, homofilia, distribuciones de grado y montos).
3. **Modelado:** entrenar un modelo GraphSAGE que supere a baselines tabulares (Regresión Logística, XGBoost) en detección de nodos fraudulentos, evaluado con métricas operativas bancarias (PR-AUC, recall@precision=0.90).
4. **Producto:** desplegar un dashboard interactivo en Vercel que permita a un analista de compliance explorar métricas, visualizar anillos de fraude detectados y revisar el ranking de cuentas de mayor riesgo.
5. **Entregable comercial:** producir un informe PDF de calidad institucional (identidad visual propia, estructura de consultoría top-tier) listo para presentar a un banco, fintech o regulador.

### 1.3 Criterio de éxito del proyecto

El proyecto está terminado cuando podés enviarle a un potencial cliente **un solo email con dos links**: el dashboard en vivo (Vercel) y el PDF ejecutivo — y que ambos se sostengan solos sin que tengas que explicar nada por teléfono.

### 1.4 Simulación de cliente (para máximo realismo)

Trabajá todo el proyecto como si el cliente fuera real. Cliente ficticio sugerido: **"Banco Regional del Sur (BRS)"** — banco mediano argentino, ~500K cuentas activas, equipo de compliance de 6 analistas que hoy revisan alertas generadas por reglas fijas (umbrales de monto), con una tasa de falsos positivos del ~90%. El dolor de negocio: los analistas pierden tiempo en alertas malas y los esquemas de lavado estructurados (pitufeo, anillos) pasan por debajo del radar de las reglas. Todo insight, gráfico y recomendación del proyecto se escribe **para este cliente**.

---

## 2. Alcance y fases (visión punta a punta)

| Fase | Entregable | Duración estimada |
|---|---|---|
| A. Fundaciones | Repo + entorno + skills de Claude Code configuradas | 1 sesión |
| B. Datos | Dataset generado + esquema documentado | 1 sesión |
| C. EDA e insights | Notebook + documento de insights de negocio | 2-3 sesiones |
| D. Baselines | LogReg + XGBoost con métricas | 1 sesión |
| E. GNN | GraphSAGE entrenado y evaluado | 2-3 sesiones |
| F. Análisis comparativo | Tabla final + análisis de errores + insights de modelo | 1-2 sesiones |
| G. Dashboard | App Next.js desplegada en Vercel | 2-3 sesiones |
| H. Informe PDF | PDF institucional con marca personal | 1-2 sesiones |

**Total realista: 3-4 semanas a ritmo part-time.** No lo comprimas: el diferencial del portfolio está en las fases C, G y H, que son las que un recruiter o cliente efectivamente mira.

---

## 3. Estructura del proyecto

```
fraud-gnn/
├── CLAUDE.md                      # Contexto persistente para Claude Code
├── .claude/
│   └── skills/                    # Skills de Claude Code (ver sección 5)
│       ├── eda-grafo/
│       │   └── SKILL.md
│       ├── metricas-fraude/
│       │   └── SKILL.md
│       ├── informe-gc/
│       │   └── SKILL.md
│       └── dashboard-fraude/
│           └── SKILL.md
├── README.md
├── requirements.txt
├── config/
│   └── config.yaml                # scale_factor, hiperparámetros, paths, seed
├── data/
│   ├── raw/                       # Output de gen-fraud-graph
│   └── processed/                 # Tensores PyG, splits, scores exportados
├── src/
│   ├── generate.py                # Generación de datos
│   ├── build_graph.py             # CSV → torch_geometric Data
│   ├── features.py                # Feature engineering
│   ├── models/
│   │   ├── baseline.py            # LogReg, XGBoost
│   │   └── graphsage.py           # GNN principal
│   ├── train.py
│   ├── evaluate.py
│   └── export_dashboard.py        # Genera los JSON que consume el dashboard
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_baseline.ipynb
│   └── 03_gnn.ipynb
├── dashboard/                     # App Next.js (Fase G) — repo propio o subcarpeta
│   ├── app/
│   ├── components/
│   ├── public/data/               # JSONs exportados desde src/
│   └── package.json
├── reports/
│   ├── figures/
│   ├── insights.md                # Documento de insights (Fase C y F)
│   ├── informe_final.md           # Fuente del PDF
│   └── informe_final.pdf          # ENTREGABLE
└── tests/
    └── test_build_graph.py
```

**Regla de oro:** notebooks para explorar y narrar; lógica reutilizable en `src/`. El dashboard consume **archivos JSON estáticos exportados** desde el pipeline — no una API — lo que simplifica el deploy en Vercel a costo cero.

---

## 4. CLAUDE.md — contexto persistente

Claude Code lee `CLAUDE.md` automáticamente al inicio de cada sesión. Creálo con este contenido y mantenelo vivo:

```markdown
# Proyecto: Detección de fraude con GNNs — Germán Cárdenas

## Contexto
Engagement simulado para "Banco Regional del Sur (BRS)": detección de anillos
de lavado en grafo transaccional sintético (gen-fraud-graph, Santander AI Lab).
Entregables finales: dashboard en Vercel + informe PDF institucional.

## Stack
- Python 3.11 en Windows (cmd), venv en ./venv
- PyTorch + PyTorch Geometric (CPU-only, sin GPU)
- pandas, scikit-learn, xgboost, networkx, matplotlib
- Dashboard: Next.js 14 + Tailwind + Recharts + Cytoscape.js, deploy en Vercel
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
- venv\Scripts\activate
- python -m src.generate --scale 0.01
- python -m src.build_graph
- python -m src.train
- python -m src.evaluate
- python -m src.export_dashboard
- cd dashboard && npm run dev

## Estado actual
[Actualizar al cierre de CADA sesión: hecho / pendiente / decisiones tomadas]
```

---

## 5. Skills de Claude Code

Las **Agent Skills** de Claude Code son carpetas con un archivo `SKILL.md` dentro de `.claude/skills/` en tu proyecto. Claude las descubre automáticamente y las invoca cuando la tarea coincide con su descripción. Te definen *cómo* querés que se haga cada tipo de trabajo, una sola vez, en lugar de repetirlo en cada prompt.

Creá estas cuatro (podés pedirle a Claude Code que las genere: *"creá la skill eda-grafo según la especificación del documento de proyecto"*):

### 5.1 `eda-grafo/SKILL.md`

```markdown
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
```

### 5.2 `metricas-fraude/SKILL.md`

```markdown
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
```

### 5.3 `informe-gc/SKILL.md`

```markdown
---
name: informe-gc
description: Generación de informes PDF institucionales con la identidad
  personal de Germán Cárdenas. Usar cuando se pida crear el informe final,
  el PDF entregable, o documentos para cliente.
---

# Informes institucionales — Germán Cárdenas

Pipeline: markdown/HTML con CSS print → render con Playwright/Chromium
a PDF A4. NUNCA generar PDF con librerías de bajo nivel (reportlab/fpdf).

Identidad visual:
- Paleta: navy #0A1F44 (principal), gold #C9A227 (acentos), gris #F4F5F7
- Tipografía: serif para títulos (Georgia), sans para cuerpo (Inter/Arial)
- Portada: título, cliente, fecha, wordmark "GERMÁN CÁRDENAS · Data & Analytics"
- Header/footer en cada página: nombre del documento + paginación
- Callout boxes gold para hallazgos clave ("Insight" / "Recomendación")

Estructura obligatoria (estilo consultoría):
1. Portada  2. Disclaimer de confidencialidad y datos sintéticos
3. Resumen ejecutivo (1 página, cero jerga)  4. Contexto y problema
5. Datos y metodología  6. Resultados  7. Insights y recomendaciones
8. Roadmap de implementación  9. Anexo técnico

Tono: consultor senior escribiendo para un directorio de banco.
Cada gráfico con título, fuente y una lectura en una línea.
```

### 5.4 `dashboard-fraude/SKILL.md`

```markdown
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
```

> **Nota:** las skills se complementan con el CLAUDE.md — el CLAUDE.md da el contexto del proyecto; las skills dan procedimientos reutilizables. Si más adelante hacés las Fases 2-4 del roadmap original (u otros clientes de fraude), estas skills se copian tal cual a los proyectos nuevos.

---

## 6. Paso a paso detallado

### FASE A — Fundaciones (1 sesión)

En cmd:

```cmd
mkdir fraud-gnn
cd fraud-gnn
python -m venv venv
venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install torch_geometric gen-fraud-graph pandas scikit-learn xgboost matplotlib jupyter pyyaml networkx playwright
playwright install chromium
pip freeze > requirements.txt
git init
```

**Prompt para Claude Code:**
> "Leé el documento de proyecto. Creá la estructura de carpetas completa, el CLAUDE.md de la sección 4, las cuatro skills de la sección 5 en .claude/skills/, un config.yaml inicial (scale_factor: 0.01, seed: 42, paths relativos) y un .gitignore para Python + Node + data/. Commiteá como 'chore: project scaffolding'."

**Criterio de salida:** `python -c "import torch_geometric"` OK; skills visibles al preguntarle a Claude Code "¿qué skills tenés disponibles?".

---

### FASE B — Generación de datos (1 sesión)

Empezá chico — `scale_factor=0.01`. Escalás recién cuando el pipeline completo funcione de punta a punta.

```cmd
gen-fraud-graph --scale 0.01 --workers 4 --output data\raw
```

**Prompt:**
> "Ejecutá la generación con scale 0.01, inspeccioná los CSVs (columnas, tipos, filas, % de fraude a nivel nodo y arista) y documentá el esquema en docs/data_schema.md. Señalá cualquier sorpresa del formato."

**Preguntas que tenés que poder responder vos** (no solo Claude): ¿cuántos nodos/aristas hay? ¿qué % es fraude? ¿el label es a nivel nodo, arista o ambos? ¿qué features vienen (balance, risk score, embeddings, timestamps)?

---

### FASE C — EDA e insights de negocio (2-3 sesiones)

Acá se produce el primer entregable de valor: **`reports/insights.md`**, el documento de hallazgos que después alimenta tanto el dashboard como el PDF. La skill `eda-grafo` define el análisis técnico; tu trabajo es la capa de interpretación.

**Análisis mínimo** (notebook `01_eda.ipynb`): tamaño y densidad del grafo, prevalencia del fraude, distribuciones de grado y montos segmentadas, homofilia, y la visualización de 3+ anillos de lavado concretos.

**El test de homofilia es la decisión metodológica clave:** si los vecinos de nodos fraudulentos no tienden a ser fraudulentos, un GNN no aporta sobre un modelo tabular. Medilo explícitamente y documentá el resultado — justifica (o cuestiona) todo lo que viene después.

**Formato de cada insight en `insights.md`** — obligatorio, es lo que separa análisis de consultoría:

> **Hallazgo:** [el dato — ej.: "las cuentas en anillos tienen grado promedio 3.2x mayor que las legítimas, concentrado en ventanas de 72hs"]
> **Implicancia para BRS:** [qué significa — ej.: "las reglas por umbral de monto no capturan este patrón porque cada transacción individual es chica (pitufeo)"]
> **Acción sugerida:** [qué haría el cliente — ej.: "monitoreo de velocidad transaccional por vecindario, no por cuenta individual"]

Apuntá a **6-10 insights** con este formato. Estos textos van casi directo al PDF y a la página de overview del dashboard.

---

### FASE D — Baselines tabulares (1 sesión)

**Nunca presentes un GNN sin baseline.** El argumento comercial es "el GNN mejora X puntos de PR-AUC sobre lo que el banco haría con XGBoost", no "hice un GNN".

1. Features tabulares por nodo: grado in/out, montos totales y promedio enviados/recibidos, contrapartes únicas, balance, risk score.
2. Modelos: LogReg (`class_weight='balanced'`) y XGBoost (`scale_pos_weight`).
3. Split estratificado 70/15/15, seed fija, **índices guardados** en `data/processed/` — el GNN usa exactamente el mismo split.
4. Evaluación vía skill `metricas-fraude` (PR-AUC, recall@p90, traducción a alertas/día).

---

### FASE E — GraphSAGE (2-3 sesiones)

**Por qué GraphSAGE:** inductivo (generaliza a cuentas nuevas sin reentrenar — argumento de producción clave para el cliente), escala con neighbor sampling, estándar de industria en fraude.

Arquitectura inicial:

```
SAGEConv(in → 64) → ReLU → Dropout(0.3)
→ SAGEConv(64 → 64) → ReLU → Dropout(0.3)
→ Linear(64 → 2)
```

Entrenamiento (`src/train.py`): CrossEntropy con pesos de clase (Focal Loss si el desbalance supera 1:50), Adam lr=0.005 wd=5e-4, early stopping por PR-AUC de validación (paciencia 20), full-batch en CPU con scale 0.01 (pasar a `NeighborLoader` [15,10] si escalás), log por época a `reports/training_log.csv`.

**Detalles que separan amateur de profesional:** normalizar features con estadísticas del train set solamente (evitar leakage); el grafo es dirigido — aplicar `ToUndirected` o aristas inversas explícitas y documentar la decisión; guardar el modelo (`models/graphsage_best.pt`) y el grafo procesado (`data/processed/graph.pt`); test de consistencia en `tests/`.

**Prompt tipo (usá plan mode primero — Shift+Tab):**
> "Proponé un plan para implementar src/models/graphsage.py y src/train.py según el documento. No escribas código hasta que apruebe el plan."

---

### FASE F — Análisis comparativo e insights de modelo (1-2 sesiones)

1. **Tabla final:** LogReg vs. XGBoost vs. GraphSAGE, mismas métricas, mismo test set.
2. **Curvas PR superpuestas** — la figura principal de todo el proyecto.
3. **Análisis de errores:** tomar 5-10 falsos negativos del GNN y examinar su vecindario. ¿Nodos periféricos de anillos? ¿Aislados? Este análisis cualitativo alimenta la sección de limitaciones del PDF.
4. **Ablation mínimo:** GraphSAGE con features reales vs. features constantes (solo topología). Responde cuánto aporta la estructura del grafo por sí sola — un insight muy vendedor si da bien.
5. **Actualizar `insights.md`** con 3-4 insights de modelo en el mismo formato Hallazgo/Implicancia/Acción (ej.: "el GNN detecta el 78% de las cuentas de anillo que XGBoost no ve, porque la señal es estructural y no de monto").

**Resultado esperable:** con anillos cíclicos sintéticos, el GNN debería ganar con claridad en recall de nodos de anillo. Si no pasa, investigá — homofilia baja o features tabulares que ya capturan el grado son las causas típicas, y el hallazgo también vale para el informe.

6. **Exportar para el dashboard** (`src/export_dashboard.py` → `dashboard/public/data/`):
   - `kpis.json` — métricas resumen
   - `pr_curves.json` — puntos de las curvas PR de los 3 modelos
   - `score_distribution.json` — histograma de scores fraude vs. legítimo
   - `rings.json` — top 10 anillos: nodos, aristas, scores, montos
   - `top_accounts.json` — top 200 cuentas por score de riesgo con sus features

---

### FASE G — Dashboard en Vercel (2-3 sesiones)

El dashboard es la pieza que convierte el proyecto en algo que un cliente **puede tocar**. Sitio estático Next.js que consume los JSONs — sin backend, deploy gratuito.

**Setup:**

```cmd
cd fraud-gnn
npx create-next-app@latest dashboard --typescript --tailwind --app
cd dashboard
npm install recharts cytoscape react-cytoscapejs
```

**Páginas** (la skill `dashboard-fraude` guía a Claude Code):

1. **`/` Overview** — KPIs grandes arriba (cuentas analizadas, % fraude, PR-AUC del GNN, recall@p90), curva PR comparativa de los 3 modelos, distribución de scores, y 3-4 insights destacados en cards.
2. **`/anillos` Explorador de anillos** — la página estrella: Cytoscape.js mostrando cada anillo de lavado, nodos coloreados por score del modelo (gradiente gris→rojo), click en nodo muestra sus features. Selector para navegar los top 10 anillos.
3. **`/cuentas` Ranking de riesgo** — tabla ordenable/filtrable de las top 200 cuentas, con score, grado, monto total y flag de si pertenece a un anillo. Es la vista "cola de trabajo del analista".
4. **`/metodologia`** — media página explicando el modelo en lenguaje de analista + disclaimer de datos sintéticos.

**Deploy en Vercel:**

```cmd
cd dashboard
npm run build        # verificar que buildea sin errores ANTES de deployar
npx vercel           # login con GitHub, deploy de preview
npx vercel --prod    # deploy a producción
```

Alternativa aún más simple: pusheá el repo a GitHub y conectalo desde vercel.com (auto-deploy en cada push). Como los datos son JSONs estáticos versionados en el repo, no hay secretos ni variables de entorno que configurar.

**Prompt para Claude Code:**
> "Usando la skill dashboard-fraude, creá la página de overview consumiendo public/data/kpis.json y pr_curves.json. Mobile-friendly, dark navy theme. Corré npm run dev y verificá que renderiza sin errores de consola."

**Criterio de salida:** URL pública de Vercel funcionando, navegable desde el celular.

---

### FASE H — Informe PDF institucional (1-2 sesiones)

El cierre: un PDF que BRS podría poner sobre la mesa de su directorio. La skill `informe-gc` define pipeline y estética; acá va el contenido.

**Estructura del documento (12-18 páginas):**

1. **Portada** — "Detección de Redes de Lavado mediante Inteligencia de Grafos / Preparado para Banco Regional del Sur / Germán Cárdenas / Julio 2026"
2. **Disclaimer** — confidencialidad + aclaración explícita de que el estudio usa datos sintéticos como prueba de concepto, y que la fase siguiente calibraría con datos reales del cliente
3. **Resumen ejecutivo (1 página)** — el problema en números, qué se hizo, los 3 resultados principales, la recomendación. Un director tiene que poder leer SOLO esta página y decidir si sigue
4. **Contexto** — costo del fraude/AML, límites de los sistemas de reglas (el ~90% de falsos positivos de BRS), por qué el lavado estructurado es un problema de *red* y no de *transacción*
5. **Datos y metodología** — dataset, esquema, features, modelos evaluados, protocolo de validación (accesible; lo denso va al anexo)
6. **Resultados** — tabla comparativa, curva PR, visualización de un anillo real detectado, y la traducción operativa: "con este modelo, los 6 analistas de BRS pasarían de revisar ~X alertas/día con 90% de ruido a ~Y alertas/día con 90% de precisión"
7. **Insights y recomendaciones** — los 8-12 insights de `insights.md`, cada uno en su callout box gold
8. **Roadmap de implementación** — fase piloto con datos reales (8 semanas), integración con el case management existente, capacitación de analistas, y monitoreo del modelo. Incluí un Gantt simple
9. **Anexo técnico** — hiperparámetros, ablations, curvas de entrenamiento, limitaciones metodológicas

**Prompt:**
> "Usando la skill informe-gc, generá reports/informe_final.pdf a partir de reports/informe_final.md e insights.md, incorporando las figuras de reports/figures/. Verificá el render abriendo el PDF: portada, headers/footers, paginación, que ninguna figura quede cortada entre páginas."

**Criterio de salida:** PDF que le mandarías a un cliente real sin vergüenza. Test ácido: mostráselo a alguien que no sepa de ML y preguntale qué entendió del resumen ejecutivo.

---

## 7. Tips para Claude Code en cmd (Windows)

- **Una fase por sesión.** Al cerrar cada sesión: *"actualizá la sección Estado actual del CLAUDE.md con lo hecho, lo pendiente y las decisiones tomadas"*.
- **Plan mode (Shift+Tab) para las fases E, G y H** — revisá el plan antes de que escriba una línea de código.
- **Exigí ejecución:** nunca aceptes código sin correr. "Corré el script y mostrame el output" — Claude Code ejecuta en tu cmd y se auto-corrige.
- **Paths:** en config.yaml usá forward slashes relativos (`data/raw`); Python los resuelve bien en Windows.
- **Notebooks:** alternativa cómoda — scripts `.py` con celdas `# %%` (VS Code los trata como notebooks) y conversión final con `jupytext`.
- **Commits por fase**, mensajes descriptivos, convención `feat:`/`fix:`/`chore:`/`docs:`.
- **Contexto largo:** si una sesión se pone pesada, `/compact` antes de seguir; el CLAUDE.md actualizado hace que un `/clear` no duela.
- **Node/Vercel:** verificá `node --version` (necesitás 18+) antes de la Fase G; `npm run build` local siempre antes de deployar.

---

## 8. Checklist de progreso

- [ ] A — Repo + venv + CLAUDE.md + 4 skills creadas
- [ ] B — Dataset generado + `docs/data_schema.md`
- [ ] C — EDA completo + `insights.md` con 6-10 insights formato Hallazgo/Implicancia/Acción
- [ ] D — Baselines con métricas y splits guardados
- [ ] E — GraphSAGE entrenado (`graphsage_best.pt`)
- [ ] F — Tabla comparativa + análisis de errores + ablation + JSONs exportados
- [ ] G — Dashboard deployado en Vercel (URL pública)
- [ ] H — `informe_final.pdf` con calidad de directorio
- [ ] Bonus — README del repo con screenshots del dashboard y link al PDF

---

## 9. Reutilización futura (fases 2-4 del roadmap original)

| Asset de este proyecto | Dónde se reutiliza |
|---|---|
| CSVs de gen-fraud-graph | Fase 2: carga a Neo4j (`LOAD CSV`) para el dashboard investigativo avanzado |
| GraphSAGE entrenado | Fase 2: scoring en vivo; Fase 4: demo comercial |
| `evaluate.py` + skill metricas-fraude | Fase 3: benchmark de node2vec, GAT, reglas heurísticas sobre el mismo harness |
| Dashboard Vercel | Fase 4: demo pública en el pitch "Fraud Detection as a Service" |
| Informe PDF + skill informe-gc | Fase 4: base del brochure comercial AML de Germán Cárdenas |
| Las 4 skills de Claude Code | Cualquier proyecto futuro de fraude/datos — se copian tal cual |

---

*Primer comando de la primera sesión: crear la carpeta, el venv, pegar este documento en el repo como `docs/proyecto.md`, y pedirle a Claude Code que ejecute la Fase A.*
