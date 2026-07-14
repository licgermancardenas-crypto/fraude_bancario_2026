import type { Metadata } from "next";
import "./globals.css";
import NavBar from "@/components/NavBar";

export const metadata: Metadata = {
  title: "Fraude BRS — Dashboard de Detección de Lavado",
  description: "Sistema de detección de redes de lavado mediante Graph Neural Networks — Germán Cárdenas",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-screen flex flex-col" style={{ backgroundColor: "#0A1F44" }}>
        <NavBar />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        <footer className="border-t border-white/10 py-5 text-center text-xs text-white/40">
          <span className="text-[#C9A227] font-semibold">GERMÁN CÁRDENAS</span>
          {" · "}Data &amp; Analytics
          {" · "}Datos 100% sintéticos — engagement simulado para Banco Regional del Sur
        </footer>
      </body>
    </html>
  );
}
