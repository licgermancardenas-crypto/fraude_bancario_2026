import { PhantomMark } from "@/brand-kit/react/PhantomMark";
import Navbar from "@/components/marketing/Navbar";
import HeroDashMockup from "@/components/HeroDashMockup";

const card = { backgroundColor: "#0E1219", border: "1px solid #1E2430" } as const;
const eyebrow = {
  fontFamily: "var(--font-mono)",
  fontSize: 11,
  letterSpacing: "0.4em",
  textTransform: "uppercase" as const,
  color: "#7AA2FF",
};
const display = { fontFamily: "var(--font-display)" } as const;

const PROBLEM_STATS = [
  { value: "90%", label: "de las alertas de un sistema de reglas típico son falsos positivos. Los analistas pierden el día revisando ruido." },
  { value: "48", suffix: "hs", label: "es la ventana promedio de un anillo de lavado. Para cuando una regla por umbral lo detecta, el dinero ya salió." },
  { value: "14x", label: "más probabilidad de que una arista sea fraude→fraude que por azar. La señal está en la red, no en la transacción." },
  { value: "0%", label: "de los perpetradores de colocación aparecen en alertas por umbral: inyectan montos chicos, tienen baja centralidad." },
];

const PILLARS = [
  {
    title: "Graph Neural Network",
    tag: "ESTRATIFICACIÓN",
    desc: "Un modelo GraphSAGE analiza cada cuenta en el contexto de su vecindario transaccional. No mira la cuenta sola — mira con quién transacciona, y con quién transaccionan esos, hasta descubrir la firma de un anillo de lavado.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="#7AA2FF" strokeWidth={1.5}>
        <circle cx="12" cy="12" r="3" /><path d="M12 2v4m0 12v4M2 12h4m12 0h4" />
        <circle cx="12" cy="12" r="9" strokeDasharray="4 3" />
      </svg>
    ),
  },
  {
    title: "Backward Tracing",
    tag: "COLOCACIÓN",
    desc: "El GNN detecta las mulas. El backward tracing remonta el grafo dirigido hasta encontrar el origen: quién inyectó el dinero. Revela a los perpetradores que ningún clasificador de conectividad ve.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="#7AA2FF" strokeWidth={1.5}>
        <path d="M21 12H9m0 0l4-4m-4 4l4 4" /><path d="M3 12h2" /><circle cx="6" cy="12" r="1.5" />
      </svg>
    ),
  },
  {
    title: "Detección de pitufeo",
    tag: "STRUCTURING",
    desc: "Features AML explícitas — clustering de montos bajo el umbral, fan-in temporal, velocidad de consolidación — capturan la firma del pitufeo que la topología de red sola no distingue.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="#7AA2FF" strokeWidth={1.5}>
        <rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" /><path d="M14 17.5h7M17.5 14v7" />
      </svg>
    ),
  },
];

const FEATURES = [
  { title: "Scoring masivo de cuentas", desc: "Clasifica cada cuenta del banco por probabilidad de pertenecer a una red ilícita. Cola de trabajo priorizada: los analistas empiezan por lo que importa." },
  { title: "Visualización de anillos", desc: "Los anillos de lavado se ven como lo que son: ciclos en el grafo. Cada nodo coloreado por score, expandible con un clic. Investigación visual, no tabulada." },
  { title: "Screening de listas y PEPs", desc: "Cruce contra sancionados, PEPs y jurisdicciones de riesgo — con un diferencial: no solo alertás al que está en la lista, sino al que está a 1-2 saltos en la red." },
  { title: "Narrativa pre-redactada para ROS", desc: "Cada alerta con su texto listo para el Reporte de Operación Sospechosa: “cuenta X recibió 14 depósitos de 11 originantes en 48hs, 92% bajo el umbral”." },
  { title: "Evaluación transductiva e inductiva", desc: "El modelo se evalúa en ambos modos: con información de red completa y simulando cuentas nuevas que nunca vio. Las métricas que reportamos son las de producción." },
  { title: "Datos 100% del cliente", desc: "No somos un SaaS con datos compartidos. Phantom se despliega sobre la infraestructura del banco: sus datos nunca salen de su perímetro." },
];

const TRUST_STATS = [
  { value: "0.", accent: "94", suffix: "", label: "PR-AUC EN CUENTAS NUEVAS" },
  { value: "", accent: "78", suffix: "%", label: "RECALL EN NODOS DE ANILLO QUE XGBOOST NO VE" },
  { value: "", accent: "10", suffix: "x", label: "REDUCCIÓN DE FALSOS POSITIVOS VS. REGLAS" },
];

function SectionDivider() {
  return (
    <div
      className="absolute top-0 left-0 right-0 h-px"
      style={{ background: "linear-gradient(90deg, transparent, #1E2430, transparent)" }}
    />
  );
}

export default function PhantomLandingPage() {
  return (
    <>
      <Navbar />

      {/* HERO */}
      <section className="relative overflow-hidden" style={{ minHeight: "100vh", display: "flex", alignItems: "center", padding: "140px 0 100px" }}>
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse at 20% 50%, rgba(46,107,255,0.06) 0%, transparent 50%), radial-gradient(ellipse at 80% 20%, rgba(46,107,255,0.03) 0%, transparent 40%)",
          }}
        />
        <div
          className="absolute bottom-0 left-0 right-0"
          style={{ height: 200, background: "linear-gradient(transparent, #07090F)" }}
        />
        <div className="relative z-[2] max-w-[1200px] mx-auto px-8 grid grid-cols-1 mkt:grid-cols-2 gap-20 items-center">
          <div>
            <div style={{ ...eyebrow, marginBottom: 20 }}>Financial Crime Intelligence</div>
            <h1
              className="tracking-tight"
              style={{ ...display, fontWeight: 600, fontSize: "clamp(40px,5.5vw,72px)", letterSpacing: "-2px", lineHeight: 1.05, color: "#EDEAE6", marginBottom: 28 }}
            >
              Las redes no se esconden.
              <span className="block" style={{ color: "#7AA2FF" }}>Se revelan.</span>
            </h1>
            <p className="text-lg" style={{ color: "#5A6478", maxWidth: 480, marginBottom: 40, lineHeight: 1.7 }}>
              Phantom detecta anillos de lavado, redes de mulas y esquemas de pitufeo que los sistemas de reglas no ven — analizando la estructura de la red, no solo la transacción.
            </p>
            <div className="flex gap-4 flex-wrap">
              <a
                href="#cta"
                className="inline-flex items-center gap-2 px-6 py-2.5 rounded-md text-sm font-medium"
                style={{ ...display, backgroundColor: "#2E6BFF", color: "#fff" }}
              >
                Solicitar demo →
              </a>
              <a
                href="#como"
                className="inline-flex items-center gap-2 px-6 py-2.5 rounded-md text-sm font-medium"
                style={{ ...display, backgroundColor: "transparent", color: "#EDEAE6", border: "1px solid #1E2430" }}
              >
                Cómo funciona
              </a>
            </div>
          </div>
          <div className="order-first mkt:order-none">
            <HeroDashMockup />
          </div>
        </div>
      </section>

      {/* PROBLEM */}
      <section id="producto" className="relative" style={{ padding: "140px 0" }}>
        <SectionDivider />
        <div className="max-w-[1200px] mx-auto px-8 grid grid-cols-1 mkt:grid-cols-2 gap-20 items-start">
          <div>
            <div style={{ ...eyebrow, marginBottom: 16 }}>El problema</div>
            <h2 style={{ ...display, fontWeight: 600, fontSize: "clamp(28px,3.5vw,44px)", letterSpacing: "-1px", lineHeight: 1.15, color: "#EDEAE6" }}>
              Los sistemas de reglas detectan transacciones sospechosas.
              <br />
              <span style={{ color: "#7AA2FF" }}>No detectan redes.</span>
            </h2>
            <p style={{ fontSize: 16, color: "#5A6478", marginTop: 20, lineHeight: 1.7 }}>
              Un esquema de lavado estructurado mueve plata en montos chicos, a través de decenas de cuentas, en ventanas cortas. Cada transacción individual parece normal. Lo que delata el esquema es la{" "}
              <strong style={{ color: "#EDEAE6" }}>estructura de la red</strong> — y eso es invisible para un sistema que mira una transacción a la vez.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-5" style={{ marginTop: 40 }}>
            {PROBLEM_STATS.map(s => (
              <div key={s.label} className="rounded-[10px] p-6" style={card}>
                <div style={{ ...display, fontWeight: 600, fontSize: 36, color: "#EDEAE6" }}>
                  {s.suffix ? (
                    <>
                      {s.value}
                      <span style={{ color: "#7AA2FF" }}>{s.suffix}</span>
                    </>
                  ) : (
                    <span style={{ color: "#7AA2FF" }}>{s.value}</span>
                  )}
                </div>
                <div style={{ fontSize: 14, color: "#5A6478", marginTop: 8, lineHeight: 1.5 }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="como" className="relative" style={{ padding: "140px 0" }}>
        <SectionDivider />
        <div className="max-w-[1200px] mx-auto px-8">
          <div className="text-center" style={{ marginBottom: 72 }}>
            <div style={eyebrow}>Cómo funciona</div>
            <h2 style={{ ...display, fontWeight: 600, fontSize: "clamp(28px,3.5vw,44px)", letterSpacing: "-1px", marginTop: 16, color: "#EDEAE6" }}>
              De millones de transacciones
              <br />
              a inteligencia accionable
            </h2>
            <p style={{ fontSize: 18, color: "#5A6478", maxWidth: 600, margin: "20px auto 0" }}>
              Tres capas que se complementan: lo que una no ve, la siguiente lo revela.
            </p>
          </div>
          <div className="grid grid-cols-1 mkt:grid-cols-3 gap-6">
            {PILLARS.map(p => (
              <div key={p.title} className="group relative overflow-hidden rounded-xl p-8" style={{ ...card, transition: "border-color .3s" }}>
                <div
                  className="w-12 h-12 rounded-[10px] flex items-center justify-center"
                  style={{ backgroundColor: "#12161F", border: "1px solid #1E2430", marginBottom: 20 }}
                >
                  <div className="w-6 h-6">{p.icon}</div>
                </div>
                <h3 style={{ ...display, fontWeight: 500, fontSize: 18, color: "#EDEAE6", marginBottom: 12 }}>{p.title}</h3>
                <p style={{ fontSize: 14, color: "#5A6478", lineHeight: 1.7 }}>{p.desc}</p>
                <span
                  className="inline-block mt-4 rounded-full px-3 py-1"
                  style={{ fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: 2, color: "#7AA2FF", backgroundColor: "rgba(46,107,255,0.08)" }}
                >
                  {p.tag}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section id="features" className="relative" style={{ padding: "140px 0" }}>
        <SectionDivider />
        <div className="max-w-[1200px] mx-auto px-8">
          <div style={{ ...eyebrow, marginBottom: 16 }}>Capacidades</div>
          <h2 style={{ ...display, fontWeight: 600, fontSize: "clamp(28px,3.5vw,44px)", letterSpacing: "-1px", color: "#EDEAE6" }}>
            Todo lo que un equipo de compliance necesita
          </h2>
          <div className="grid grid-cols-1 mkt:grid-cols-2 gap-5" style={{ marginTop: 56 }}>
            {FEATURES.map(f => (
              <div key={f.title} className="flex rounded-[10px] p-7" style={{ ...card, gap: 18 }}>
                <div className="rounded-full flex-shrink-0" style={{ width: 8, height: 8, backgroundColor: "#2E6BFF", marginTop: 7 }} />
                <div>
                  <h4 style={{ ...display, fontWeight: 500, fontSize: 16, color: "#EDEAE6", marginBottom: 6 }}>{f.title}</h4>
                  <p style={{ fontSize: 13, color: "#5A6478", lineHeight: 1.6 }}>{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* TRUST / METRICS */}
      <section className="relative text-center" style={{ padding: "100px 0" }}>
        <SectionDivider />
        <div className="max-w-[1200px] mx-auto px-8">
          <div style={eyebrow}>Resultados medidos</div>
          <h2 style={{ ...display, fontWeight: 600, fontSize: "clamp(28px,3.5vw,44px)", letterSpacing: "-1px", marginTop: 16, color: "#EDEAE6" }}>
            Métricas operativas, no de laboratorio
          </h2>
          <div className="flex flex-col mkt:flex-row justify-center gap-10 mkt:gap-20" style={{ marginTop: 48 }}>
            {TRUST_STATS.map(s => (
              <div key={s.label} className="flex flex-col items-center">
                <div style={{ ...display, fontWeight: 600, fontSize: 48, color: "#EDEAE6" }}>
                  {s.value}
                  <span style={{ color: "#7AA2FF" }}>{s.accent}</span>
                  {s.suffix}
                </div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: 2, color: "#6B7486", marginTop: 8 }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section id="cta" className="relative" style={{ padding: "120px 0" }}>
        <div className="max-w-[1200px] mx-auto px-8">
          <div
            className="relative overflow-hidden rounded-[20px] text-center"
            style={{ backgroundColor: "#0A1226", border: "1px solid #1E2430", padding: "80px 60px" }}
          >
            <div
              className="absolute inset-0"
              style={{ background: "radial-gradient(ellipse at 50% 0%, rgba(46,107,255,0.08) 0%, transparent 60%)" }}
            />
            <div className="relative z-[2] flex justify-center" style={{ marginBottom: 24 }}>
              <PhantomMark size={56} />
            </div>
            <h2
              className="relative z-[2]"
              style={{ ...display, fontWeight: 600, fontSize: "clamp(28px,4vw,48px)", letterSpacing: "-1px", marginBottom: 16, color: "#EDEAE6" }}
            >
              ¿Querés ver qué hay <span style={{ color: "#7AA2FF" }}>detrás</span> de tus transacciones?
            </h2>
            <p className="relative z-[2]" style={{ fontSize: 18, color: "#5A6478", maxWidth: 560, margin: "0 auto 36px" }}>
              Armamos una prueba de concepto con datos sintéticos sobre la estructura transaccional de tu institución. Sin comprometer datos reales hasta que haya contrato.
            </p>
            <div className="relative z-[2] flex justify-center gap-4 flex-wrap">
              <a
                href="mailto:german@phantom.ai"
                className="inline-flex items-center gap-2 px-6 py-2.5 rounded-md text-sm font-medium"
                style={{ ...display, backgroundColor: "#2E6BFF", color: "#fff" }}
              >
                Solicitar demo →
              </a>
              <a
                href="#"
                className="inline-flex items-center gap-2 px-6 py-2.5 rounded-md text-sm font-medium"
                style={{ ...display, backgroundColor: "transparent", color: "#EDEAE6", border: "1px solid #1E2430" }}
              >
                Descargar one-pager
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer style={{ borderTop: "1px solid #1E2430", padding: "48px 0" }}>
        <div className="max-w-[1200px] mx-auto px-8 flex flex-col mkt:flex-row items-center justify-between gap-6 text-center mkt:text-left">
          <div className="flex items-center gap-2.5">
            <PhantomMark size={22} />
            <span style={{ ...display, fontWeight: 600, fontSize: 15, color: "#EDEAE6" }}>Phantom AI</span>
          </div>
          <div className="flex gap-7 text-[13px]" style={{ color: "#5A6478" }}>
            <a href="#" style={{ color: "#7AA2FF" }}>Producto</a>
            <a href="#" style={{ color: "#7AA2FF" }}>Metodología</a>
            <a href="#" style={{ color: "#7AA2FF" }}>Contacto</a>
          </div>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "#6B7486", letterSpacing: 1 }}>
            © 2026 GERMÁN CÁRDENAS
          </span>
        </div>
      </footer>
    </>
  );
}
