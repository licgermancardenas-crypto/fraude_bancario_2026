import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "Fraude BRS — Dashboard de Detección de Lavado",
  description: "Sistema de detección de redes de lavado mediante Graph Neural Networks — Germán Cárdenas",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="flex min-h-screen" style={{ backgroundColor: "#EEF2FF", color: "#0F172A" }}>
        <Sidebar />
        <div className="flex-1 min-w-0 flex flex-col">
          <main className="flex-1 p-6 lg:p-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
