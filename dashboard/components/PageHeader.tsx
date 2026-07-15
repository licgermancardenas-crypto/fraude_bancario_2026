interface PageHeaderProps {
  eyebrow: string;
  title: string;
  description?: string;
}

export default function PageHeader({ eyebrow, title, description }: PageHeaderProps) {
  return (
    <div className="pb-2 border-b border-white/8 mb-8">
      <p className="text-[11px] font-bold uppercase tracking-widest mb-2"
         style={{ color: "#C9A227" }}>
        {eyebrow}
      </p>
      <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">{title}</h1>
      {description && (
        <p className="mt-2 text-sm text-white/45 max-w-2xl leading-relaxed">{description}</p>
      )}
    </div>
  );
}
