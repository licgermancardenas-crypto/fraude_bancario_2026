"use client";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { navItemsFlat, type NavItem } from "@/lib/nav";

const MAX_VISIBLE = 4;

function MoreIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="5" cy="12" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="19" cy="12" r="1.5" />
    </svg>
  );
}

function TabLink({ href, label, Icon, active, onClick }: NavItem & { active: boolean; onClick?: () => void }) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className="flex-1 flex flex-col items-center gap-1 py-2.5"
      style={{ color: active ? "#0A1F44" : "#64748B" }}
    >
      <Icon />
      <span className="text-[10px] font-medium leading-none">{label}</span>
    </Link>
  );
}

export default function MobileNav() {
  const pathname = usePathname();
  const [showMore, setShowMore] = useState(false);

  const overflowing = navItemsFlat.length > MAX_VISIBLE;
  const visible  = overflowing ? navItemsFlat.slice(0, MAX_VISIBLE - 1) : navItemsFlat;
  const overflow = overflowing ? navItemsFlat.slice(MAX_VISIBLE - 1) : [];
  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));
  const overflowActive = overflow.some(item => isActive(item.href));

  return (
    <>
      {showMore && (
        <div
          className="sm:hidden fixed inset-0 z-40"
          style={{ backgroundColor: "rgba(15,23,42,0.35)" }}
          onClick={() => setShowMore(false)}
        />
      )}

      {showMore && (
        <div
          className="sm:hidden fixed bottom-16 left-3 right-3 z-50 rounded-xl overflow-hidden"
          style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", boxShadow: "0 -4px 16px rgba(0,0,0,0.12)" }}
        >
          {overflow.map(({ href, label, Icon }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setShowMore(false)}
              className="flex items-center gap-3 px-4 py-3 text-sm font-medium"
              style={{
                color: isActive(href) ? "#0A1F44" : "#0F172A",
                borderBottom: "1px solid #F1F5F9",
              }}
            >
              <Icon />
              {label}
            </Link>
          ))}
        </div>
      )}

      <nav
        className="sm:hidden fixed bottom-0 inset-x-0 z-50 flex"
        style={{
          backgroundColor: "#FFFFFF",
          borderTop: "1px solid #E2E8F0",
          boxShadow: "0 -2px 8px rgba(0,0,0,0.06)",
          paddingBottom: "env(safe-area-inset-bottom)",
        }}
      >
        {visible.map(item => (
          <TabLink key={item.href} {...item} active={isActive(item.href)} />
        ))}
        {overflowing && (
          <button
            onClick={() => setShowMore(s => !s)}
            className="flex-1 flex flex-col items-center gap-1 py-2.5"
            style={{ color: showMore || overflowActive ? "#0A1F44" : "#64748B" }}
          >
            <MoreIcon />
            <span className="text-[10px] font-medium leading-none">Más</span>
          </button>
        )}
      </nav>
    </>
  );
}
