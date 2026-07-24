# Phantom AI — Brand Kit

Identidad visual de Phantom AI (producto ficticio, engagement simulado para
"Banco Regional del Sur"). Fuente de verdad para colores, tipografía e isotipo
en el dashboard y en la landing de marketing.

## Isotipo

Tres barras paralelas ascendentes: dos en `bone` (#EDEAE6) y una tercera, más
alta, en `pulse` (#2E6BFF) — la señal que se destaca sobre el ruido.

- SVG fuente: [`svg/phantom-mark.svg`](svg/phantom-mark.svg) — `viewBox="20 16 186 190"`.
- Componente React: [`react/PhantomMark.tsx`](react/PhantomMark.tsx) — exporta
  `PhantomMark` (isotipo solo) y `PhantomLockup` (isotipo + wordmark, para
  navbars/headers).
- **No alterar las coordenadas de los polygons** — es la geometría final aprobada.
- Import: `@/brand-kit/react/PhantomMark`.

```tsx
import { PhantomMark, PhantomLockup } from "@/brand-kit/react/PhantomMark";

<PhantomMark size={28} />                 // default: 2 barras bone + 1 pulse
<PhantomMark variant="mono" />            // todo en bone, sin dependencia de color
<PhantomMark variant="onLight" />         // para fondos claros
<PhantomLockup markSize={36} />           // isotipo + "Phantom" + eyebrow
```

## Color

Paleta dark. Ver [`tokens/tokens.css`](tokens/tokens.css) y
[`tokens/tokens.json`](tokens/tokens.json) — ambos deben mantenerse en sync.
El dashboard ya expone estos mismos valores como `theme.extend.colors.phantom.*`
en `tailwind.config.ts` (nombres: `void`, `graphite`, `panel`, `line`, `steel`,
`steelDim`, `bone`, `pulse`, `pulseHi`, `navy` — `graphite`/`pulseHi` son los
nombres Tailwind de `--graph`/`--phi`).

| Token | Hex | Uso |
|---|---|---|
| `void` | `#07090F` | Fondo base de la página |
| `graph` | `#0E1219` | Fondo de cards secundarias, sidebar |
| `panel` | `#12161F` | Fondo de cards primarias, KPIs |
| `line` | `#1E2430` | Bordes |
| `steel` | `#5A6478` | Texto secundario / body |
| `dim` | `#6B7486` | Texto terciario / labels mono |
| `bone` | `#EDEAE6` | Texto principal, titulares |
| `pulse` | `#2E6BFF` | Acento primario — CTAs, barra activa |
| `phi` | `#7AA2FF` | Acento secundario — eyebrows, links, hover |
| `navy` | `#0A1226` | Fondo de bloques destacados (CTA box) |

No confundir con la paleta del informe PDF institucional (navy #0A1F44 /
gold #C9A227, marca personal de Germán Cárdenas) — son sistemas visuales
distintos para audiencias distintas.

## Tipografía

Tres familias, cada una con un rol fijo:

| Variable CSS | Familia | Uso |
|---|---|---|
| `--font-display` | Space Grotesk (500/600) | Titulares, KPIs, wordmark |
| `--font-body` | Inter (300/400/500) | Texto de párrafo |
| `--font-mono` | JetBrains Mono (300/400) | Eyebrows, labels, tags, timestamps |

En la landing de marketing (`app/(marketing)/`) se cargan self-hosted vía
`next/font/google` y se exponen como variables CSS en el `<html>`/`<body>`
del layout — sin depender de una request externa a Google Fonts en runtime.
El dashboard (`app/(dashboard)/`) sigue cargándolas por `@import` en
`globals.css` (no se tocó ese pipeline al construir la landing).

## Reglas

- El isotipo va siempre en su combinación de color aprobada — no se recolorea
  la barra `pulse` a otro tono.
- Fondo oscuro por defecto (`void`/`graph`); no hay versión light del sistema.
- `phi` (#7AA2FF) es el color de interacción — hover states, links, eyebrows.
  `pulse` (#2E6BFF) es el color de intención — botones primarios, barra activa.
