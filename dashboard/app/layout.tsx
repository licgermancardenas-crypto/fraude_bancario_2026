import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import MobileNav from "@/components/MobileNav";

export const metadata: Metadata = {
  title: "Phantom AI — Detección de Fraude con GNN",
  description: "Phantom AI: detección de redes de lavado mediante Graph Neural Networks — Germán Cárdenas",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="flex min-h-screen" style={{ backgroundColor: "#EEF2FF", color: "#0F172A" }}>
        <Sidebar />
        <div
          className="sm:hidden flex items-center gap-2 px-4 h-12 fixed top-0 inset-x-0 z-40"
          style={{ backgroundColor: "#FFFFFF", borderBottom: "1px solid #E2E8F0" }}
        >
          <div
            className="flex items-center justify-center w-7 h-7 rounded-lg flex-shrink-0"
            style={{ background: "linear-gradient(135deg, #0A1F44, #1E3A8A)" }}
          >
            <span className="text-[9px] font-black text-white tracking-tight">PH</span>
          </div>
          <p className="text-sm font-bold" style={{ color: "#0F172A" }}>Phantom AI</p>
        </div>
        <div className="flex-1 min-w-0 flex flex-col">
          <main className="flex-1 px-6 lg:px-8 pt-16 pb-20 sm:pt-8 sm:pb-8">
            {children}
          </main>
        </div>
        <MobileNav />
      </body>
    </html>
  );
}
