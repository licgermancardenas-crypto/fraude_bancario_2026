import Link from "next/link";

const links = [
  { href: "/",            label: "Overview"   },
  { href: "/anillos",     label: "Anillos"    },
  { href: "/origen",      label: "Origen"     },
  { href: "/cuentas",     label: "Cuentas"    },
  { href: "/metodologia", label: "Metodología"},
];

export default function NavBar() {
  return (
    <nav className="border-b border-white/10 sticky top-0 z-50"
         style={{ backgroundColor: "#061530" }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold tracking-widest uppercase"
                style={{ color: "#C9A227" }}>BRS</span>
          <span className="text-white font-semibold text-sm hidden sm:block">
            Detección de Lavado · GNN
          </span>
        </div>
        <div className="flex items-center gap-1">
          {links.map(({ href, label }) => (
            <Link key={href} href={href}
              className="px-3 py-1.5 rounded text-sm text-white/70 hover:text-white hover:bg-white/10 transition-colors">
              {label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
