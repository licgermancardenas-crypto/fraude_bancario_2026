import { PhantomMark } from "@/brand-kit/react/PhantomMark";

const BARS = [40, 55, 35, 82, 48, 42, 58, 90, 38, 52, 44, 60];
const HIGHLIGHTED = new Set([3, 7]);

export default function HeroDashMockup() {
  return (
    <div className="relative">
      <div
        className="rounded-2xl overflow-hidden"
        style={{ backgroundColor: "#0E1219", border: "1px solid #1E2430", boxShadow: "0 40px 120px rgba(0,0,0,0.5)" }}
      >
        {/* top bar */}
        <div className="flex items-center gap-2 px-4 py-3" style={{ borderBottom: "1px solid #1E2430" }}>
          <PhantomMark size={20} />
          <span className="text-sm font-semibold" style={{ fontFamily: "var(--font-display)", color: "#EDEAE6" }}>
            Phantom
          </span>
          <div className="ml-auto flex gap-3.5 text-[9px] tracking-[1.5px]" style={{ fontFamily: "var(--font-mono)" }}>
            <span style={{ color: "#7AA2FF" }}>OVERVIEW</span>
            <span style={{ color: "#5A6478" }}>ANILLOS</span>
            <span style={{ color: "#5A6478" }}>ORIGEN</span>
            <span style={{ color: "#5A6478" }}>CASOS</span>
          </div>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-3 gap-2.5 p-4">
          {[
            { v: "0.94", l: "PR-AUC INDUCTIVO", accent: true },
            { v: "20", l: "REDES DETECTADAS", accent: false },
            { v: "$4.9M", l: "MONTO EN RIESGO", accent: false },
          ].map(kpi => (
            <div key={kpi.l} className="rounded-lg p-3.5" style={{ backgroundColor: "#12161F", border: "1px solid #1E2430" }}>
              <div
                className="text-2xl font-semibold"
                style={{ fontFamily: "var(--font-display)", color: kpi.accent ? "#7AA2FF" : "#EDEAE6" }}
              >
                {kpi.v}
              </div>
              <div className="text-[8px] tracking-[1.5px] mt-1" style={{ fontFamily: "var(--font-mono)", color: "#6B7486" }}>
                {kpi.l}
              </div>
            </div>
          ))}
        </div>

        {/* bar chart */}
        <div className="flex items-end gap-[5px] px-4 pb-4" style={{ height: 100 }}>
          {BARS.map((h, i) => (
            <div
              key={i}
              className="flex-1 rounded-t-[3px]"
              style={{ height: `${h}%`, backgroundColor: HIGHLIGHTED.has(i) ? "#2E6BFF" : "#1E2430" }}
            />
          ))}
        </div>
      </div>

      {/* floating card */}
      <div
        className="hidden mkt:block absolute rounded-[10px] p-3.5"
        style={{
          top: -40,
          right: -60,
          width: 180,
          height: 110,
          backgroundColor: "#12161F",
          border: "1px solid #1E2430",
          boxShadow: "0 20px 60px rgba(0,0,0,0.4)",
          transform: "rotate(3deg)",
        }}
      >
        <div className="text-[8px] tracking-[1.5px]" style={{ fontFamily: "var(--font-mono)", color: "#6B7486" }}>
          RED DETECTADA
        </div>
        <div className="text-[28px] font-semibold mt-1.5" style={{ fontFamily: "var(--font-display)", color: "#7AA2FF" }}>
          Ring #07
        </div>
        <div className="text-[11px] mt-1" style={{ color: "#5A6478" }}>
          7 nodos · $493K · 48hs
        </div>
      </div>
    </div>
  );
}
