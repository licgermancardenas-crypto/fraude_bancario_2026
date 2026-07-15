"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

function HomeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12l9-9 9 9" /><path d="M5 10v10h5v-5h4v5h5V10" />
    </svg>
  );
}
function GraphIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="5" cy="12" r="2" /><circle cx="19" cy="5" r="2" /><circle cx="19" cy="19" r="2" />
      <line x1="7" y1="12" x2="17" y2="5.5" /><line x1="7" y1="12" x2="17" y2="18.5" />
    </svg>
  );
}
function TargetIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" />
      <line x1="12" y1="2" x2="12" y2="4" /><line x1="12" y1="20" x2="12" y2="22" />
      <line x1="2" y1="12" x2="4" y2="12" /><line x1="20" y1="12" x2="22" y2="12" />
    </svg>
  );
}
function TableIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <line x1="3" y1="9" x2="21" y2="9" /><line x1="3" y1="15" x2="21" y2="15" />
      <line x1="9" y1="3" x2="9" y2="21" />
    </svg>
  );
}
function BookIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 016.5 17H20" /><path d="M4 4.5A2.5 2.5 0 016.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15z" />
    </svg>
  );
}

const navGroups = [
  {
    label: "Sistema",
    items: [
      { href: "/",        label: "Inicio",      Icon: HomeIcon },
      { href: "/anillos", label: "Anillos",      Icon: GraphIcon },
      { href: "/origen",  label: "Origen",       Icon: TargetIcon },
    ],
  },
  {
    label: "Análisis",
    items: [
      { href: "/cuentas",     label: "Cuentas",     Icon: TableIcon },
      { href: "/metodologia", label: "Metodología", Icon: BookIcon },
    ],
  },
];

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
