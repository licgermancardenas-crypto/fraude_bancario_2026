# Proyecto: Detección de fraude con GNNs — Germán Cárdenas

## Contexto
Engagement simulado para "Banco Regional del Sur (BRS)": detección de anillos
de lavado en grafo transaccional sintético (gen-fraud-graph, Santander AI Lab).
Entregables finales: dashboard en Vercel + informe PDF institucional.

## Stack
- Python 3.13 en Linux, venv en ./venv
- PyTorch + PyTorch Geometric (CPU-only, sin GPU)
- pandas, scikit-learn, xgboost, networkx, matplotlib
- Dashboard: Next.js 14 + Tailwind + Recharts + Cytoscape.js, deploy en Vercel
- API: FastAPI (api/), deploy en Render (free tier) — servicio separado, no conectado al dashboard
- PDF: HTML/CSS → Playwright/Chromium (pipeline HTML → PDF)

## Convenciones
- Código y docstrings en inglés; textos de negocio e informes en español
- Lógica en src/, notebooks solo para narrativa
- Config centralizada en config/config.yaml — nada hardcodeado
- Métricas obligatorias: PR-AUC, recall@precision=0.90, F1. NUNCA accuracy sola
  (fraude ≈ 1-3% de los nodos; el desbalance domina todo)
- Seed=42 en todo. Splits guardados en data/processed/ y compartidos
  entre baselines y GNN (comparación justa)
- Estética dashboard: rebrand "Phantom AI" — paleta dark (void #07090F, panel #12161F, line #1E2430, bone #EDEAE6, pulse #2E6BFF/#7AA2FF), tipografía Inter+Space Grotesk+JetBrains Mono. PDF institucional sigue en navy (#0A1F44) y gold (#C9A227), marca personal GC — paletas distintas, no confundir.

## Skills disponibles (.claude/skills/)
- eda-grafo: análisis exploratorio estándar de grafos transaccionales
- metricas-fraude: evaluación con métricas operativas bancarias
- informe-gc: generación de PDFs institucionales navy/gold
- dashboard-fraude: convenciones del dashboard Next.js

## Comandos frecuentes
- source venv/bin/activate
- python -m src.generate --scale 0.01
- python -m src.build_graph
- python -m src.train
- python -m src.evaluate
- python -m src.export_dashboard
- cd dashboard && npm run dev
- uvicorn api.main:app --reload

## Arquitectura de rutas (dashboard/app/)
Dos route groups paralelos, cada uno con su propio root layout (Next.js App
Router soporta múltiples root layouts vía grupos entre paréntesis — no hay
`app/layout.tsx` compartido):
- `app/(marketing)/` → landing pública en `/` (Space Grotesk/Inter/JetBrains
  Mono self-hosted vía next/font/google, CSS vars --font-display/--font-body/
  --font-mono). Sin Sidebar/MobileNav.
- `app/(dashboard)/app/` → la herramienta real, TODA bajo prefijo `/app/*`
  (antes vivía en `/`, `/anillos`, `/casos`, etc. — se movió completa para
  liberar `/` para la landing). Layout con Sidebar/MobileNav sin cambios.
`lib/nav.tsx`, `components/Sidebar.tsx` y `components/MobileNav.tsx` ya
reflejan los hrefs con prefijo `/app`. Si se agrega una página nueva al
dashboard, va en `app/(dashboard)/app/<ruta>/page.tsx`, no en `app/<ruta>/`.

## brand-kit/
`dashboard/brand-kit/` es la fuente de verdad de identidad visual (antes solo
existía `components/PhantomMark.tsx`, ahora movido a `brand-kit/react/`):
- `BRAND.md` — reglas de marca, tabla de tokens, uso del isotipo
- `tokens/tokens.css` + `tokens/tokens.json` — mismos valores que
  `tailwind.config.ts` (`theme.extend.colors.phantom.*`), deben mantenerse en sync
- `react/PhantomMark.tsx` — componente canónico (`PhantomMark`, `PhantomLockup`),
  importar como `@/brand-kit/react/PhantomMark`
- `svg/phantom-mark.svg` — SVG fuente, no alterar los polygons

## Estado actual
[2026-07-24] Las 8 fases del roadmap original (A-H) están completas, más extensiones:
5 modelos entrenados (mejor: GraphSAGE, PR-AUC 0.977), explicabilidad (GNNExplainer),
backward tracing de perpetradores, placement scoring, dashboard de 9 páginas + módulo
Compliance (casos/entidades/ROS), informe PDF institucional, API FastAPI (api/) con
11 endpoints deployada en Render (confirmada viva en https://phantom-rcs9.onrender.com),
y landing de marketing en `/` (`app/(marketing)/`, réplica fiel de
`docs/phantom-landing.html`).
La API dejó de ser un servicio 100% aislado: la página `/app/en-vivo`
(dashboard/app/(dashboard)/app/en-vivo/, componente dashboard/components/LiveApiConsole.tsx)
llama en runtime a GET /health y POST /accounts/score contra la API real. El resto del
dashboard sigue leyendo los JSONs estáticos de dashboard/public/data/ — decisión
deliberada para no exponer la demo principal a los cold-starts de Render free tier
(~30-50s tras 15min de inactividad, medido en vivo). URL de la API configurable vía
NEXT_PUBLIC_API_URL (dashboard/.env.local, no versionado; ver dashboard/.env.example).
README.md es la fuente de verdad del estado del proyecto; actualizar esta sección junto
con el README cuando cambie algo relevante.

## Realismo del módulo Compliance (completo — 4/4)
Plan de 4 mejoras para que la cola de casos suene a plataforma AML real de un
banco, no a demo. Las 4 completas:
1. ✅ **Asignación de analista + plazo regulatorio.** `src/export_dashboard.py`
   (`export_cases`) asigna `analista_asignado` (pool de 5 analistas ficticios,
   determinístico vía `rng`) y calcula `vencimiento_ros` = `alert_date` + 150
   días (Ley 25.246 art. 21 inc. b — plazo UIF para reportar ROS). Nuevos
   campos en `Case` (lib/types.ts), helper compartido `lib/dates.ts`
   (`daysUntil`, `rosUrgency`), badge de vencimiento en `/app/casos` (lista +
   filtro por analista) y en el detalle de caso.
2. ✅ **Rating KYC (estático) separado del score GNN (dinámico).** `risk_score`
   ya existía en el dataset (src/generate.py, Beta(2,8)) pero no se mostraba
   como concepto propio — se comprobó que fraude/legit tienen medias casi
   idénticas (0.1999 vs 0.1992), coherente con el Cohen d=0.055 ya reportado
   en /app/metodologia. `lib/kyc.ts` categoriza en tiers Bajo/Medio/Alto
   (cortes en percentiles ~33/~78) con paleta propia (grises/violeta,
   deliberadamente distinta del rojo/ámbar/verde del score GNN para no
   confundir los dos sistemas). Se muestra en `/app/casos` (lista + detalle),
   `/app/cuentas` y `/app/anillos` + `RingGraph`. En el detalle de caso hay un
   callout "Punto ciego del onboarding" cuando KYC no es Alto pero el GNN
   score es alto (`isBlindSpot()`) — dispara en 64/80 casos actuales.
3. ✅ **Screening de sanciones/listas (ONU, OFAC, REPET).** Nuevo
   `src/generate_entities.py::generate_sanctions_hits()` — watchlist 100%
   ficticia (9 entradas inventadas, ninguna corresponde a una designación
   real) en 3 listas; ~0.3% de las cuentas matchean (5x más si es fraude,
   2x más si es PEP — igual que el sesgo ya usado para PEP), con
   `score_match` difuso y estado `pendiente/confirmado/descartado` (la
   mayoría queda "descartado" tras revisión — mismo ~90% de falsos
   positivos que ya se menciona en la landing). Se guarda en
   `data/raw/sanctions_hits.csv` (gitignored, como el resto de data/raw/).
   `export_cases()` arma el objeto `screening` por caso: `hit_directo` sobre
   la cuenta + `exposicion_indirecta` sobre sus `neighbors` (1 salto) — es
   la capacidad que la landing ya promete ("no solo alertás al que está en
   la lista, sino al que está a 1-2 saltos"). Card dedicada en el detalle
   de caso + columna/badge + KPI "Screening pendiente" en `/app/casos`.
4. ✅ **Cuatro ojos — revisor + aprobador antes de enviar el ROS.** Solo
   frontend, no requirió cambios en el pipeline Python. `SARDraft` (lib/types.ts
   — nombre interno, no renombrado; ver nota de terminología abajo) suma
   `analista_caso` (snapshot de `case.analista_asignado`) y `audit:
   SARAuditEvent[]` (trazabilidad: quién, qué acción, cuándo, comentario
   opcional). En `/app/casos/[id]/ros`, cuando `estado_sar === "revision"`
   aparece el panel "Aprobación — control de cuatro ojos": el Oficial de
   Cumplimiento firma con su nombre y puede Aprobar (→ `enviado`, y
   además actualiza el estado del caso a `sar_enviado` vía
   `lib/caseStatus.ts`, que antes nunca se alcanzaba desde la UI) o
   Rechazar (→ vuelve a `borrador`). Control anti-autoaprobación: el botón
   Aprobar se deshabilita si la firma coincide con `analista_caso`. Una vez
   `enviado`, el formulario queda bloqueado (`disabled`) y se agrega una
   Sección 5 "Trazabilidad" al documento con el historial completo de
   eventos. De paso se extrajo `getStoredStatuses`/`setStoredStatus`
   (duplicados en 2 archivos) a `lib/caseStatus.ts` — ahora también los usa
   la página del ROS.

## Terminología: ROS, no SAR
El documento regulatorio argentino se llama **ROS** (Reporte de Operación
Sospechosa, Ley 25.246 / UIF) — "SAR" (Suspicious Activity Report) es el
término de EEUU/FinCEN, no corresponde acá. [2026-07-25] Se corrigió una
mezcla real: botones, la ruta (`/app/casos/[id]/sar` → `/app/casos/[id]/ros`)
y el label de estado ("SAR enviado" → "ROS enviado") decían SAR mientras el
documento en sí ya decía "Reporte de Operación Sospechosa (ROS)" correctamente.
**Los identificadores internos de TypeScript quedaron sin renombrar a propósito**
(`SARDraft`, `SARAuditEvent`, `buildSARDraft`, `estado_sar`, el status literal
`"sar_enviado"` en `CaseStatus`) — es deuda cosmética conocida, no un olvido:
no son visibles para el usuario y renombrarlos no traía beneficio para el
alcance acotado de este fix. Si se vuelve a tocar `lib/types.ts` o
`casos/[id]/ros/page.tsx` a fondo, considerar renombrarlos a `ROSDraft` etc.
para que el código interno también diga ROS.

## Auditoría de terminología [2026-07-25]
Se corrieron 7 hallazgos (agente Explore). Los 2 críticos (SAR/ROS, bug de
label "Score modelo") están arriba. De los 5 medios:
- ✅ **Tooltips en jerga técnica** — nuevo `components/InfoTooltip.tsx`
  (ícono "i", hover/focus, CSS puro sin JS) + prop `tooltip?` en
  `KPICard`. Aplicado en `/app` (home) a PR-AUC, Recall @ Precisión 90%,
  Lift y Cohen d.
- ✅ **Jerga sin anclaje en `/app/origen`** — "backward tracing" aparecía
  suelto en el legend y el insight box aunque el header ya lo explica en
  criollo ("traza hacia atrás..."). Se agregó el mismo anclaje en español
  ("rastreo hacia atrás (backward tracing)") en las 3 apariciones sueltas.
- ✅ **"Shells" vs "Empresa de fachada (shell)"** — `/app/entidades` decía
  "Shells"/"Solo shells"/"Shell" a secas; ahora dice "Fachadas"/"Solo
  fachadas"/"Fachada", consistente con el detalle de caso.
- ✅ **"AML" → "ALD" en el dashboard** (2026-07-25, pasada aparte). Las 5
  apariciones fuera de la landing: `casos/page.tsx` (subtítulo "Gestión de
  casos ALD"), `casos/[id]/page.tsx` (autor de nota hardcodeado "Analista
  ALD"), `metodologia/page.tsx` (x2), `page.tsx` home (insight Cohen d).
  La landing sigue diciendo "AML" — es la única inconsistencia
  remanente a propósito entre landing y dashboard (decisión explícita
  del usuario, no vale la pena tocar el copy aprobado por una sigla).
- ✅ **STRUCTURING → ESTRUCTURACIÓN en la landing** (2026-07-25, tercera
  pasada — el usuario pidió tocar esto después de todo, revirtiendo la
  decisión inicial de no desviarse del HTML de referencia). Cambiado en
  `docs/phantom-landing.html` Y en `app/(marketing)/page.tsx` a la vez
  para que el HTML de referencia y la landing en vivo no queden
  desincronizados. Coincide con "Estructuración" que ya se usa en
  `casos/page.tsx` (PATTERN_LABELS) para el mismo concepto. Los títulos
  de pilar en inglés ("Graph Neural Network", "Backward Tracing") NO se
  tocaron — son nombres técnicos/de producto, consistentes con "GNN" sin
  traducir en todo el resto del proyecto; solo el tag de categoría (la
  única palabra suelta en mayúsculas) estaba realmente fuera de lugar.

Si se regenera `cases.json` desde cero, usar `export_cases()` (o `export_all()`
completo) — **ojo:** `export_all()` hoy rompe en `export_pr_curves` por un
mismatch de longitudes preexistente (scores_by_model vs y_test, ~22501 vs
11251) que no tiene que ver con este cambio; para tocar solo casos, llamar
`load_all(cfg)` + `export_cases(...)` directo, como se hizo acá. Si se
regenera la capa de entidades, correr `generate_entities()` (agrega
`sanctions_hits.csv`; reproduce empresas/titularidades/directores/pep_flags
idénticos porque el seed y el orden de generación no cambiaron).

## Pendientes
- Setear NEXT_PUBLIC_API_URL=https://phantom-rcs9.onrender.com en las env vars del
  proyecto Vercel del dashboard (Settings → Environment Variables) para que
  /app/en-vivo funcione en el deploy de producción, no solo en local.
- Verificar visualmente la landing en un navegador real contra
  docs/phantom-landing.html (no se pudo verificar con Claude in Chrome en esta
  sesión — la extensión no estaba conectada). La fidelidad se validó a mano,
  valor por valor de CSS, pero falta el chequeo pixel-a-pixel.
- Investigar el mismatch de longitudes en export_pr_curves (ver arriba) —
  probablemente un .npy de scores desactualizado en data/processed/.
- La mayoría de los scripts en src/ (analysis.py, build_graph.py, train*.py,
  evaluate*.py, explain.py, trace_origin.py, detect_placement.py,
  generate_report.py, eda.py, enrich_personas.py, business_impact.py,
  detect_communities.py) tienen prints con "→" que crashean con
  UnicodeEncodeError en la consola cp1252 default de Windows (ya se
  encontró y arregló en export_dashboard.py y generate_entities.py). No
  bloquea nada hoy porque el crash pasa DESPUÉS de guardar los archivos,
  pero conviene limpiarlo si se automatiza el pipeline en Windows.
