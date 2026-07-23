interface KPICardProps {
  label: string;
  value: string;
  sub?: string;
  color?: string;
  dim?: boolean;
}

export default function KPICard({ label, value, sub, color = "#0A1F44", dim }: KPICardProps) {
  const accent = dim ? "#64748B" : color;
  return (
    <div
      className="rounded-xl flex flex-col overflow-hidden"
      style={{
        backgroundColor: "#FFFFFF",
        border: "1px solid #E2E8F0",
        boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
      }}
    >
      <div className="h-1 w-full" style={{ backgroundColor: accent }} />
      <div className="p-5 flex flex-col gap-1.5 flex-1">
        <p
          className="text-[11px] font-semibold uppercase tracking-widest"
          style={{ color: "#64748B" }}
        >
          {label}
        </p>
        <p
          className="text-3xl font-bold leading-none tracking-tight"
          style={{ color: accent }}
        >
          {value}
        </p>
        {sub && (
          <p className="text-xs leading-relaxed" style={{ color: "#64748B" }}>
            {sub}
          </p>
        )}
      </div>
    </div>
  );
}
