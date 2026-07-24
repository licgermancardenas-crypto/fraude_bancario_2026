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
Compliance (casos/entidades/SAR), informe PDF institucional, API FastAPI (api/) con
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

## Pendientes
- Setear NEXT_PUBLIC_API_URL=https://phantom-rcs9.onrender.com en las env vars del
  proyecto Vercel del dashboard (Settings → Environment Variables) para que
  /app/en-vivo funcione en el deploy de producción, no solo en local.
- Verificar visualmente la landing en un navegador real contra
  docs/phantom-landing.html (no se pudo verificar con Claude in Chrome en esta
  sesión — la extensión no estaba conectada). La fidelidad se validó a mano,
  valor por valor de CSS, pero falta el chequeo pixel-a-pixel.
