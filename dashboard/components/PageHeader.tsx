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
        background: "linear-gradient(135deg, #0A1F44 0%, #122855 100%)",
        boxShadow: "0 4px 24px rgba(10,31,68,0.25)",
      }}
    >
      {eyebrow && (
        <p
          className="text-[11px] font-bold uppercase tracking-widest mb-1.5"
          style={{ color: "#E0B840" }}
        >
          {eyebrow}
        </p>
      )}
      <h1 className="text-2xl font-bold tracking-tight" style={{ color: "#FFFFFF" }}>
        {title}
      </h1>
      {body && (
        <p className="mt-1.5 text-sm max-w-2xl leading-relaxed" style={{ color: "#CBD5E1" }}>
          {body}
        </p>
      )}
    </div>
  );
}
