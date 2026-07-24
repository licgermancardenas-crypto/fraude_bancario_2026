import PageHeader from "@/components/PageHeader";
import LiveApiConsole from "@/components/LiveApiConsole";

export default function EnVivoPage() {
  return (
    <div className="space-y-6 max-w-3xl">
      <PageHeader
        eyebrow="Integración en tiempo real"
        title="API en Vivo"
        description="El resto del dashboard lee JSONs pre-computados para garantizar velocidad y disponibilidad. Esta consola llama en vivo a la API FastAPI deployada en Render — el mismo servicio que un core bancario real consumiría vía REST."
      />
      <LiveApiConsole />
      <div
        className="rounded-xl px-5 py-4 text-xs leading-relaxed"
        style={{ backgroundColor: "rgba(46,107,255,0.08)", border: "1px solid rgba(46,107,255,0.25)" }}
      >
        <span className="font-semibold" style={{ color: "#7AA2FF" }}>Nota técnica — </span>
        <span style={{ color: "rgba(237,234,230,0.75)" }}>
          La API (Render free tier) se duerme tras 15 minutos sin tráfico y tarda 30-50s en el primer
          request tras despertar. En producción esto se resuelve con un plan pago o un servicio siempre activo.
        </span>
      </div>
    </div>
  );
}
