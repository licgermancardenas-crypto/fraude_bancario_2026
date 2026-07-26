/** Ícono "i" con tooltip en hover/focus — explica un término técnico en una frase de negocio. */
export default function InfoTooltip({ text }: { text: string }) {
  return (
    <span className="relative inline-flex group ml-1 align-middle">
      <span
        className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full text-[9px] font-bold cursor-help select-none"
        style={{ backgroundColor: "#1E2430", color: "#8A93A6" }}
        tabIndex={0}
      >
        i
      </span>
      <span
        role="tooltip"
        className="pointer-events-none absolute z-50 hidden group-hover:block group-focus-within:block bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 rounded-lg px-3 py-2 text-[11px] leading-relaxed font-normal normal-case tracking-normal"
        style={{
          backgroundColor: "#0A1226",
          border: "1px solid #1E2430",
          color: "#EDEAE6",
          boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
        }}
      >
        {text}
      </span>
    </span>
  );
}
