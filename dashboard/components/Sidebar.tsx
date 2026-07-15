"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { navGroups } from "@/lib/nav";

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="hidden sm:flex w-56 flex-shrink-0 flex-col"
      style={{
        backgroundColor: "#FFFFFF",
        borderRight: "1px solid #E2E8F0",
        minHeight: "100vh",
        position: "sticky",
        top: 0,
        alignSelf: "flex-start",
        height: "100vh",
        overflowY: "auto",
      }}
    >
      {/* Logo */}
      <div className="p-5" style={{ borderBottom: "1px solid #E2E8F0" }}>
        <div className="flex items-center gap-3">
          <div
            className="flex items-center justify-center w-9 h-9 rounded-xl flex-shrink-0"
            style={{ background: "linear-gradient(135deg, #1E3A8A, #2563EB)" }}
          >
            <span className="text-[11px] font-black text-white tracking-tight">BRS</span>
          </div>
          <div>
            <p className="text-sm font-bold leading-tight" style={{ color: "#0F172A" }}>
              Detección AML
            </p>
            <p className="text-[10px] mt-0.5" style={{ color: "#94A3B8" }}>
              GNN · Banco Regional
            </p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 pt-4 space-y-6">
        {navGroups.map(group => (
          <div key={group.label}>
            <p
              className="px-3 mb-1.5 text-[10px] font-bold uppercase tracking-widest"
              style={{ color: "#CBD5E1" }}
            >
              {group.label}
            </p>
            <div className="space-y-0.5">
              {group.items.map(({ href, label, Icon }) => {
                const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
                return (
                  <Link
                    key={href}
                    href={href}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150"
                    style={{
                      backgroundColor: active ? "#EFF6FF" : "transparent",
                      color: active ? "#2563EB" : "#64748B",
                    }}
                  >
                    <span style={{ color: active ? "#2563EB" : "#94A3B8" }}>
                      <Icon />
                    </span>
                    {label}
                    {active && (
                      <span
                        className="ml-auto w-1.5 h-1.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: "#2563EB" }}
                      />
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4" style={{ borderTop: "1px solid #E2E8F0" }}>
        <p className="text-xs font-semibold" style={{ color: "#0F172A" }}>
          Germán Cárdenas
        </p>
        <p className="text-[10px] mt-0.5" style={{ color: "#94A3B8" }}>
          Data & Analytics · 2026
        </p>
        <p className="text-[9px] mt-2 leading-relaxed" style={{ color: "#CBD5E1" }}>
          Datos 100% sintéticos —<br />engagement simulado para BRS
        </p>
      </div>
    </aside>
  );
}
