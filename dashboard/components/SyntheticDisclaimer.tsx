/**
 * Banner de divulgación — deja explícito que es una prueba de concepto sobre
 * datos sintéticos, no validada para producción. Honestidad estadística visible:
 * lo que un validador de modelos espera ver arriba de todo, no escondido al pie.
 */
export default function SyntheticDisclaimer({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className="rounded-lg flex items-start gap-2"
      style={{
        background: "rgba(245,158,11,0.08)",
        border: "1px solid rgba(245,158,11,0.3)",
        padding: compact ? "8px 12px" : "12px 14px",
      }}
    >
      <span style={{ fontSize: compact ? 14 : 16, lineHeight: 1 }}>⚠</span>
      <p className="text-[11px] leading-relaxed" style={{ color: "#F59E0B" }}>
        <b>Prueba de concepto — datos 100% sintéticos.</b> No validado para producción ni
        aprobado por ninguna autoridad. Las métricas reflejan el dataset sintético (etiquetas
        perfectas) y <b>no</b> representan performance sobre datos reales
        {compact ? "." : ", donde la tasa de falsos positivos de un sistema de monitoreo transaccional es del 90–98%."}
      </p>
    </div>
  );
}
