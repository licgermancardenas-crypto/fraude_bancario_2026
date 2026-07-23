import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import MobileNav from "@/components/MobileNav";
import { PhantomMark } from "@/components/PhantomMark";

export const metadata: Metadata = {
  title: "Phantom AI — Detección de Fraude con GNN",
  description: "Phantom AI: detección de redes de lavado mediante Graph Neural Networks — Germán Cárdenas",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="flex min-h-screen" style={{ backgroundColor: "#07090F", color: "#EDEAE6" }}>
        <Sidebar />
        <div
          className="sm:hidden flex items-center gap-2 px-4 h-12 fixed top-0 inset-x-0 z-40"
          style={{ backgroundColor: "#0E1219", borderBottom: "1px solid #1E2430" }}
        >
          <PhantomMark size={22} />
          <p className="text-sm font-bold" style={{ color: "#EDEAE6", fontFamily: "'Space Grotesk', sans-serif" }}>Phantom AI</p>
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
