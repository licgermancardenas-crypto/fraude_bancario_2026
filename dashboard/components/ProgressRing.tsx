interface Props {
  value: number; // 0..1
  label: string;
  size?: number;
  strokeWidth?: number;
  color?: string;
}

export default function ProgressRing({ value, label, size = 88, strokeWidth = 8, color = "#2E6BFF" }: Props) {
  const r = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - Math.max(0, Math.min(1, value)));

  return (
    <div className="flex flex-col items-center gap-1.5" style={{ width: size }}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#1E2430" strokeWidth={strokeWidth} />
          <circle
            cx={size / 2} cy={size / 2} r={r} fill="none"
            stroke={color} strokeWidth={strokeWidth} strokeLinecap="round"
            strokeDasharray={circumference} strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 0.6s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-bold" style={{ color: "#EDEAE6", fontFamily: "'JetBrains Mono', monospace", fontSize: size * 0.22 }}>
            {Math.round(value * 100)}%
          </span>
        </div>
      </div>
      <p className="text-[10px] font-semibold uppercase tracking-widest text-center leading-tight" style={{ color: "#5A6478" }}>
        {label}
      </p>
    </div>
  );
}
