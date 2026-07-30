import type { Metadata } from "next";
import { Space_Grotesk, Inter, JetBrains_Mono } from "next/font/google";
import "../globals.css";
import "@/brand-kit/tokens/tokens.css";
import "./marketing.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-display",
});
const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500"],
  variable: "--font-body",
});
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["300", "400"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Phantom AI — Financial Crime Intelligence",
  description:
    "Phantom detecta anillos de lavado, redes de mulas y esquemas de pitufeo que los sistemas de reglas no ven — analizando la estructura de la red, no solo la transacción.",
};

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${spaceGrotesk.variable} ${inter.variable} ${jetbrainsMono.variable}`}>
      <body
        style={{
          backgroundColor: "#07090F",
          color: "#EDEAE6",
          fontFamily: "var(--font-body, 'Inter'), system-ui, sans-serif",
          fontWeight: 300,
          lineHeight: 1.7,
          overflowX: "hidden",
        }}
      >
        {children}
      </body>
    </html>
  );
}
