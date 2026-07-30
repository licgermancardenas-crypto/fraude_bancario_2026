import React from "react";

/**
 * Phantom AI — isotype (three parallel bars, ascending signal).
 * Source of truth: brand-kit/svg/phantom-mark.svg
 * Do not alter the polygon coordinates — they are the approved final geometry.
 *
 * Usage:
 *   <PhantomMark />                          // default: two bone bars + one pulse bar
 *   <PhantomMark variant="mono" />            // all bars in bone (no color dependency)
 *   <PhantomMark variant="onLight" />          // for light backgrounds
 *   <PhantomMark size={32} />                 // controls rendered pixel size (square)
 *   <PhantomMark className="opacity-80" />    // pass-through Tailwind/utility classes
 */
type PhantomMarkProps = {
  size?: number;
  variant?: "default" | "mono" | "onLight";
  className?: string;
};

const PALETTES: Record<string, [string, string, string]> = {
  default: ["#EDEAE6", "#EDEAE6", "#2E6BFF"],
  mono: ["#EDEAE6", "#EDEAE6", "#EDEAE6"],
  onLight: ["#12161F", "#12161F", "#2E6BFF"],
};

export function PhantomMark({
  size = 40,
  variant = "default",
  className,
}: PhantomMarkProps) {
  const [c1, c2, c3] = PALETTES[variant];
  return (
    <svg
      width={size}
      height={size}
      viewBox="20 16 186 190"
      fill="none"
      role="img"
      aria-label="Phantom"
      className={className}
    >
      <polygon points="66,36 98,36 72,186 40,186" fill={c1} />
      <polygon points="110,36 142,36 116,186 84,186" fill={c2} />
      <polygon points="154,36 186,36 171.09,122 139.09,122" fill={c3} />
    </svg>
  );
}

/**
 * Horizontal lockup: mark + wordmark. Use in headers/navbars.
 * Requires Space Grotesk loaded (next/font or @font-face) — falls back to
 * system-ui otherwise, so layout never breaks if the font hasn't loaded yet.
 */
export function PhantomLockup({
  markSize = 36,
  className,
}: {
  markSize?: number;
  className?: string;
}) {
  return (
    <div className={`flex items-center gap-3 ${className ?? ""}`}>
      <PhantomMark size={markSize} />
      <div className="flex flex-col leading-none">
        <span
          style={{ fontFamily: "'Space Grotesk', system-ui, sans-serif" }}
          className="text-2xl font-semibold tracking-tight text-[#EDEAE6]"
        >
          Phantom
        </span>
        <span
          style={{ fontFamily: "'Space Grotesk', system-ui, sans-serif" }}
          className="text-[10px] tracking-[0.3em] text-[#6B7486]"
        >
          FINANCIAL CRIME INTELLIGENCE
        </span>
      </div>
    </div>
  );
}

export default PhantomMark;
