import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
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
        sans:    ["Inter", "sans-serif"],
        display: ["'Space Grotesk'", "sans-serif"],
        mono:    ["'JetBrains Mono'", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
