interface Props {
  label: string;
  value: number;     // 0..1
  sub?: string;       // e.g. "71 / 80"
  color?: string;
}

export default function ProgressBar({ label, value, sub, color = "#2E6BFF" }: Props) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1">
        <p className="text-xs font-medium" style={{ color: "#EDEAE6" }}>{label}</p>
        <p className="text-xs font-mono" style={{ color: "#5A6478" }}>{sub ?? `${pct}%`}</p>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: "#1E2430" }}>
        <div
          className="h-full rounded-full"
          style={{ width: `${pct}%`, backgroundColor: color, transition: "width 0.6s ease" }}
        />
      </div>
    </div>
  );
}
