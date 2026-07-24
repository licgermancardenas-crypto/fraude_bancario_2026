"use client";
import { useEffect, useState } from "react";
import { PhantomMark } from "@/brand-kit/react/PhantomMark";

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 60);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav
      className="fixed top-0 inset-x-0 z-[100] py-5 transition-[background] duration-300"
      style={
        scrolled
          ? { backgroundColor: "rgba(7,9,15,0.92)", backdropFilter: "blur(20px)", borderBottom: "1px solid #1E2430" }
          : undefined
      }
    >
      <div className="max-w-[1200px] mx-auto px-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <PhantomMark size={28} />
          <span className="text-lg font-semibold tracking-tight" style={{ fontFamily: "var(--font-display)", color: "#EDEAE6" }}>
            Phantom
          </span>
        </div>
        <div className="flex items-center gap-8">
          <a href="#producto" className="hidden mkt:inline text-sm" style={{ color: "#5A6478" }}>Producto</a>
          <a href="#como" className="hidden mkt:inline text-sm" style={{ color: "#5A6478" }}>Cómo funciona</a>
          <a href="#features" className="hidden mkt:inline text-sm" style={{ color: "#5A6478" }}>Capacidades</a>
          <a
            href="#cta"
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-md text-sm font-medium transition-transform"
            style={{ fontFamily: "var(--font-display)", backgroundColor: "#2E6BFF", color: "#fff" }}
          >
            Solicitar demo
          </a>
        </div>
      </div>
    </nav>
  );
}
