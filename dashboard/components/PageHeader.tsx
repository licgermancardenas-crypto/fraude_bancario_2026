interface PageHeaderProps {
  title: string;
  eyebrow?: string;
  description?: string;
  subtitle?: string;
}

export default function PageHeader({ eyebrow, title, description, subtitle }: PageHeaderProps) {
  const body = description ?? subtitle;
  return (
    <div
      className="rounded-2xl px-7 py-6 mb-6"
      style={{
        background: "linear-gradient(135deg, #0A1226 0%, #07090F 100%)",
        border: "1px solid #1E2430",
      }}
    >
      {eyebrow && (
        <p
          className="text-[11px] font-bold uppercase tracking-widest mb-1.5"
          style={{ color: "#7AA2FF", fontFamily: "'JetBrains Mono', monospace" }}
        >
          {eyebrow}
        </p>
      )}
      <h1
        className="text-2xl font-semibold tracking-tight"
        style={{ color: "#EDEAE6", fontFamily: "'Space Grotesk', sans-serif" }}
      >
        {title}
      </h1>
      {body && (
        <p className="mt-1.5 text-sm max-w-2xl leading-relaxed" style={{ color: "rgba(237,234,230,0.7)" }}>
          {body}
        </p>
      )}
    </div>
  );
}
