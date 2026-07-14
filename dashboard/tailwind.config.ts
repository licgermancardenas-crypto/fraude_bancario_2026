import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy:  { DEFAULT: "#0A1F44", light: "#122855", dark: "#061530" },
        gold:  { DEFAULT: "#C9A227", light: "#E0B840", dark: "#A8861F" },
        fraud: "#C0392B",
        legit: "#BDC3C7",
      },
      fontFamily: { sans: ["Inter", "sans-serif"] },
    },
  },
  plugins: [],
};
export default config;
