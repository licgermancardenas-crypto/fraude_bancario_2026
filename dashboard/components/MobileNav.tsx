"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { navItemsFlat } from "@/lib/nav";

export default function MobileNav() {
  const pathname = usePathname();

  return (
    <nav
      className="sm:hidden fixed bottom-0 inset-x-0 z-50 flex"
      style={{
        backgroundColor: "#FFFFFF",
        borderTop: "1px solid #E2E8F0",
        boxShadow: "0 -2px 8px rgba(0,0,0,0.06)",
        paddingBottom: "env(safe-area-inset-bottom)",
      }}
    >
      {navItemsFlat.map(({ href, label, Icon }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            className="flex-1 flex flex-col items-center gap-1 py-2.5"
            style={{ color: active ? "#2563EB" : "#94A3B8" }}
          >
            <Icon />
            <span className="text-[10px] font-medium leading-none">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
