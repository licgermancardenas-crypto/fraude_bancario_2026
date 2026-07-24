import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      screens: {
        // breakpoint del layout de la landing (docs/phantom-landing.html
        // usa @media(max-width:900px) para colapsar a 1 columna)
        mkt: "900px",
      },
      colors: {
        phantom: {
          void:     "#07090F",
          graphite: "#0E1219",
          panel:    "#12161F",
          line:     "#1E2430",
          steel:    "#5A6478",
          steelDim: "#6B7486",
          bone:     "#EDEAE6",
          pulse:    "#2E6BFF",
          pulseHi:  "#7AA2FF",
          navy:     "#0A1226",
        },
        fraud: "#EF4444",
        legit: "#5A6478",
      },
      fontFamily: {
        // var(--font-*, fallback) — el fallback solo se usa si la variable no
        // está definida (rutas del dashboard, que cargan las fuentes por
        // @import en globals.css). La landing (app/(marketing)) define estas
        // variables vía next/font/google en su layout.
        sans:    ["var(--font-body, 'Inter')", "sans-serif"],
        display: ["var(--font-display, 'Space Grotesk')", "sans-serif"],
        mono:    ["var(--font-mono, 'JetBrains Mono')", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
