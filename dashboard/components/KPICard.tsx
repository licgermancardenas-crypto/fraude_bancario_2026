interface KPICardProps {
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
}

export default function KPICard({ label, value, sub, accent }: KPICardProps) {
  return (
    <div className="rounded-xl p-5 border border-white/10 flex flex-col gap-1"
         style={{ backgroundColor: "#122855" }}>
      <p className="text-xs font-medium uppercase tracking-wider text-white/50">{label}</p>
      <p className={`text-3xl font-bold ${accent ? "text-[#C9A227]" : "text-white"}`}>{value}</p>
      {sub && <p className="text-xs text-white/40 mt-1">{sub}</p>}
    </div>
  );
}
