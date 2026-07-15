interface KPICardProps {
  label: string;
  value: string;
  sub?: string;
  color?: string;
  dim?: boolean;
}

export default function KPICard({ label, value, sub, color = "#C9A227", dim }: KPICardProps) {
  return (
    <div className="rounded-xl border border-white/8 flex flex-col overflow-hidden"
         style={{ backgroundColor: "#0d1e38" }}>
      <div className="h-0.5 w-full" style={{ backgroundColor: dim ? "#ffffff18" : color }} />
      <div className="p-5 flex flex-col gap-1.5 flex-1">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-white/40">{label}</p>
        <p className="text-3xl font-bold leading-none tracking-tight"
           style={{ color: dim ? "rgba(255,255,255,0.55)" : color }}>
          {value}
        </p>
        {sub && <p className="text-xs text-white/35 leading-relaxed">{sub}</p>}
      </div>
    </div>
  );
}
