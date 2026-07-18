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
        background: "linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%)",
        boxShadow: "0 4px 24px rgba(37,99,235,0.25)",
      }}
    >
      {eyebrow && (
        <p
          className="text-[11px] font-bold uppercase tracking-widest mb-1.5"
          style={{ color: "#93C5FD" }}
        >
          {eyebrow}
        </p>
      )}
      <h1 className="text-2xl font-bold tracking-tight" style={{ color: "#FFFFFF" }}>
        {title}
      </h1>
      {body && (
        <p className="mt-1.5 text-sm max-w-2xl leading-relaxed" style={{ color: "#BFDBFE" }}>
          {body}
        </p>
      )}
    </div>
  );
}
