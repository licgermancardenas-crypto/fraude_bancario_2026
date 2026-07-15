"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/",            label: "Overview"    },
  { href: "/anillos",     label: "Anillos"     },
  { href: "/origen",      label: "Origen"      },
  { href: "/cuentas",     label: "Cuentas"     },
  { href: "/metodologia", label: "Metodología" },
];

export default function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-50 border-b border-white/8"
         style={{ backgroundColor: "#050f1f" }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">

        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-7 h-7 rounded"
               style={{ backgroundColor: "#C9A227" }}>
            <span className="text-[10px] font-black text-[#050f1f] tracking-tight">BRS</span>
          </div>
          <div className="hidden sm:block">
            <p className="text-white text-sm font-semibold leading-none">Detección de Lavado</p>
            <p className="text-white/35 text-[10px] leading-none mt-0.5 tracking-wider">GNN · Germán Cárdenas</p>
          </div>
        </div>

        <div className="flex items-center">
          {links.map(({ href, label }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link key={href} href={href}
                className={`relative px-3 py-1.5 text-sm transition-colors ${
                  active ? "text-white font-medium" : "text-white/45 hover:text-white/80"
                }`}>
                {label}
                {active && (
                  <span className="absolute bottom-0 left-3 right-3 h-0.5 rounded-full"
                        style={{ backgroundColor: "#C9A227" }} />
                )}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
