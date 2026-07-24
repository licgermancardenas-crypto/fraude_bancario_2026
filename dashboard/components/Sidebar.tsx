"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { navGroups } from "@/lib/nav";
import { PhantomMark } from "@/brand-kit/react/PhantomMark";

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="hidden sm:flex w-56 flex-shrink-0 flex-col"
      style={{
        backgroundColor: "#0E1219",
        borderRight: "1px solid #1E2430",
        minHeight: "100vh",
        position: "sticky",
        top: 0,
        alignSelf: "flex-start",
        height: "100vh",
        overflowY: "auto",
      }}
    >
      {/* Logo */}
      <div className="p-5" style={{ borderBottom: "1px solid #1E2430" }}>
        <div className="flex items-center gap-3">
          <PhantomMark size={30} />
          <div>
            <p
              className="text-sm font-semibold leading-tight"
              style={{ color: "#EDEAE6", fontFamily: "'Space Grotesk', sans-serif" }}
            >
              Phantom AI
            </p>
            <p className="text-[10px] mt-0.5" style={{ color: "#5A6478" }}>
              GNN · Detección de Fraude
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
              style={{ color: "#5A6478" }}
            >
              {group.label}
            </p>
            <div className="space-y-0.5">
              {group.items.map(({ href, label, Icon }) => {
                const active = href === "/app" ? pathname === "/app" : pathname.startsWith(href);
                return (
                  <Link
                    key={href}
                    href={href}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150"
                    style={{
                      backgroundColor: active ? "rgba(46,107,255,0.12)" : "transparent",
                      color: active ? "#7AA2FF" : "#5A6478",
                      fontWeight: active ? 700 : 500,
                    }}
                  >
                    <span style={{ color: active ? "#7AA2FF" : "#5A6478" }}>
                      <Icon />
                    </span>
                    {label}
                    {active && (
                      <span
                        className="ml-auto w-1.5 h-1.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: "#2E6BFF" }}
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
      <div className="p-4" style={{ borderTop: "1px solid #1E2430" }}>
        <p className="text-xs font-semibold" style={{ color: "#EDEAE6" }}>
          Germán Cárdenas
        </p>
        <p className="text-[10px] mt-0.5" style={{ color: "#5A6478" }}>
          Data & Analytics · 2026
        </p>
        <p className="text-[9px] mt-2 leading-relaxed" style={{ color: "#5A6478" }}>
          Datos 100% sintéticos —<br />engagement simulado para BRS
        </p>
      </div>
    </aside>
  );
}
