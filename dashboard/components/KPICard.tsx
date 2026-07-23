interface KPICardProps {
  label: string;
  value: string;
  sub?: string;
  color?: string;
  dim?: boolean;
}

export default function KPICard({ label, value, sub, color = "#EDEAE6", dim }: KPICardProps) {
  const accent = dim ? "#5A6478" : color;
  return (
    <div
      className="rounded-xl flex flex-col overflow-hidden"
      style={{
        backgroundColor: "#12161F",
        border: "1px solid #1E2430",
      }}
    >
      <div className="h-1 w-full" style={{ backgroundColor: accent }} />
      <div className="p-5 flex flex-col gap-1.5 flex-1">
        <p
          className="text-[11px] font-semibold uppercase tracking-widest"
          style={{ color: "#5A6478", fontFamily: "'JetBrains Mono', monospace" }}
        >
          {label}
        </p>
        <p
          className="text-3xl font-bold leading-none tracking-tight"
          style={{ color: accent, fontFamily: "'JetBrains Mono', monospace" }}
        >
          {value}
        </p>
        {sub && (
          <p className="text-xs leading-relaxed" style={{ color: "#6B7486" }}>
            {sub}
          </p>
        )}
      </div>
    </div>
  );
}
