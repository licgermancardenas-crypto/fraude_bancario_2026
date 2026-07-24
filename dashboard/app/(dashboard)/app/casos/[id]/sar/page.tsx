"use client";
import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { Case, SARDraft } from "@/lib/types";

const PATRON_LABELS: Record<string, string> = {
  anillo_lavado:           "Operaciones de lavado de activos mediante anillo de transferencias circulares (layering)",
  estructuracion:          "Estructuración de operaciones (pitufeo) para evadir controles de operaciones en efectivo",
  agregacion_fondos:       "Agregación de fondos de múltiples fuentes de origen dudoso (placement/layering)",
  transacciones_inusuales: "Operaciones que no guardan relación con el perfil transaccional habitual del cliente",
};

function buildSARDraft(c: Case): SARDraft {
  const amounts = c.recent_transactions.map(t => t.amount);
  const total = amounts.reduce((a, b) => a + b, 0);
  const dates = c.recent_transactions.map(t => t.timestamp).sort();
  const persona = c.persona || {};
  const empresa = c.empresa;

  return {
    case_id:              c.case_id,
    fecha_reporte:        new Date().toISOString().slice(0, 10),
    sujeto_obligado:      "Banco Regional del Sur S.A.",
    cuit_sujeto:          "30-66540234-3",
    oficial_cumplimiento: "Lic. María González",
    reportado_nombre:     empresa?.razon_social || persona?.nombre_completo || c.account_id,
    reportado_cuil:       empresa?.cuit_empresa || persona?.cuil || "",
    reportado_tipo:       empresa ? "Persona Jurídica" : "Persona Física",
    cuentas_involucradas: [c.account_id, ...c.neighbors.filter(n => n.is_fraud).map(n => n.account_id)],
    monto_total:          Math.round(total),
    fecha_desde:          dates[0]?.toString() || c.alert_date,
    fecha_hasta:          dates[dates.length-1]?.toString() || c.alert_date,
    patron_detectado:     PATRON_LABELS[c.pattern] || c.pattern,
    descripcion:          buildDescripcion(c),
    estado_sar:           "borrador",
  };
}

function buildDescripcion(c: Case): string {
  const persona = c.persona || {};
  const nombre  = c.empresa?.razon_social || persona?.nombre_completo || c.account_id;
  const tipo    = c.empresa ? "persona jurídica" : "persona física";
  const amounts = c.recent_transactions.map(t => t.amount);
  const total   = amounts.reduce((a, b) => a + b, 0);
  const nTxns   = c.recent_transactions.length;
  const nNeigh  = c.neighbors.filter(n => n.is_fraud).length;

  return (
    `El sistema de detección de fraude basado en Graph Neural Networks (Phantom AI) flagueó la cuenta ${c.account_id} ` +
    `perteneciente a ${nombre} (${tipo}) con un score de riesgo de ${c.gnn_score.toFixed(4)} sobre 1.0, ` +
    `superando el umbral operativo de 0.90 establecido por el área de Compliance. ` +
    `\n\nSe identificaron ${nTxns} transacciones por un monto total de $${total.toLocaleString("es-AR")} ` +
    `y ${nNeigh} cuentas vinculadas con perfil de fraude confirmado. ` +
    `El patrón detectado es consistente con operaciones de ${PATRON_LABELS[c.pattern]?.toLowerCase() || c.pattern}. ` +
    `\n\n` +
    (c.empresa?.is_shell ? `Se detectó vinculación con empresa de fachada: ${c.empresa.razon_social} (${c.empresa.pais_constitucion}), ` +
    `sector ${c.empresa.sector}, CUIT ${c.empresa.cuit_empresa}. ` : "") +
    (c.is_pep ? `El titular ha sido identificado como Persona Expuesta Políticamente (PEP), ` +
    `lo que incrementa el perfil de riesgo según normativa UIF. ` : "") +
    `\n\nEn cumplimiento del artículo 21 de la Ley 25.246 y la Resolución UIF N° 30/2017, ` +
    `se procede a reportar la presente operación como sospechosa.`
  );
}

function getStoredSAR(caseId: string): Partial<SARDraft> {
  if (typeof window === "undefined") return {};
  try { return JSON.parse(localStorage.getItem(`phantom_sar_${caseId}`) || "{}"); } catch { return {}; }
}
function saveStoredSAR(caseId: string, draft: SARDraft) {
  localStorage.setItem(`phantom_sar_${caseId}`, JSON.stringify(draft));
}

export default function SARPage() {
  const params = useParams();
  const caseId = params.id as string;

  const [draft, setDraft]   = useState<SARDraft | null>(null);
  const [saved, setSaved]   = useState(false);
  const printRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/data/cases.json")
      .then(r => r.json())
      .then((cases: Case[]) => {
        const c = cases.find(x => x.case_id === caseId);
        if (!c) return;
        const stored = getStoredSAR(caseId);
        const base   = buildSARDraft(c);
        setDraft({ ...base, ...stored });
      });
  }, [caseId]);

  const update = (field: keyof SARDraft, value: string) => {
    setDraft(prev => prev ? { ...prev, [field]: value } : prev);
    setSaved(false);
  };

  const handleSave = () => {
    if (!draft) return;
    saveStoredSAR(caseId, draft);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handlePrint = () => window.print();

  if (!draft) return (
    <div className="flex items-center justify-center h-64 text-[#5A6478]">Generando borrador…</div>
  );

  const estadoColors = {
    borrador: { bg: "rgba(245,158,11,0.15)", text: "#F59E0B" },
    revision: { bg: "rgba(46,107,255,0.15)", text: "#7AA2FF" },
    enviado:  { bg: "rgba(34,197,94,0.15)",  text: "#22C55E" },
  };
  const ec = estadoColors[draft.estado_sar];

  return (
    <div className="space-y-5 max-w-4xl mx-auto print:max-w-none">
      {/* Header — hidden on print */}
      <div className="flex items-center justify-between print:hidden">
        <div className="flex items-center gap-2 text-sm text-[#5A6478]">
          <Link href="/app/casos" className="hover:text-[#EDEAE6]">Casos</Link>
          <span>/</span>
          <Link href={`/app/casos/${caseId}`} className="hover:text-[#EDEAE6]">{caseId}</Link>
          <span>/</span>
          <span className="text-[#EDEAE6] font-medium">Borrador SAR</span>
        </div>
        <div className="flex gap-2">
          <button onClick={handleSave}
                  className="px-3 min-h-[44px] text-xs font-medium rounded-lg border border-[#1E2430] text-[#5A6478] hover:bg-[#12161F] transition-colors">
            {saved ? "✓ Guardado" : "Guardar borrador"}
          </button>
          <button
            onClick={() => { if(draft) { const d={...draft,estado_sar:"revision" as const}; setDraft(d); saveStoredSAR(caseId,d); }}}
            className="px-3 min-h-[44px] text-xs font-medium rounded-lg border border-[#2E6BFF]/40 text-[#7AA2FF] bg-[#2E6BFF]/10 hover:bg-[#2E6BFF]/20 transition-colors">
            Enviar a revisión
          </button>
          <button onClick={handlePrint}
                  className="px-3 min-h-[44px] text-xs font-medium rounded-lg text-white transition-colors"
                  style={{ backgroundColor: "#2E6BFF" }}>
            Imprimir / PDF
          </button>
        </div>
      </div>

      {/* SAR Document */}
      <div ref={printRef} className="bg-[#0E1219] rounded-xl border border-[#1E2430] overflow-hidden print:rounded-none print:border-none">
        {/* Document header */}
        <div className="p-6 border-b border-[#1E2430] print:border-[#1E2430]" style={{ backgroundColor: "#0A1226" }}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white/60 text-xs uppercase tracking-widest">Phantom AI · Compliance</p>
              <h1 className="text-white text-xl font-bold mt-1">
                Reporte de Operación Sospechosa (ROS)
              </h1>
              <p className="text-white/60 text-xs mt-1">UIF — Unidad de Información Financiera · Argentina</p>
            </div>
            <div className="text-right">
              <span className="text-xs font-medium px-2.5 py-1 rounded-full"
                    style={{ backgroundColor: ec.bg, color: ec.text }}>
                {draft.estado_sar.charAt(0).toUpperCase() + draft.estado_sar.slice(1)}
              </span>
              <p className="text-white/50 text-xs mt-2">{draft.case_id}</p>
            </div>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Section 1: Sujeto obligado */}
          <Section title="1. Sujeto Obligado">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Denominación" value={draft.sujeto_obligado}
                     onChange={v => update("sujeto_obligado", v)} />
              <Field label="CUIT" value={draft.cuit_sujeto}
                     onChange={v => update("cuit_sujeto", v)} />
              <Field label="Oficial de Cumplimiento" value={draft.oficial_cumplimiento}
                     onChange={v => update("oficial_cumplimiento", v)} />
              <Field label="Fecha de reporte" value={draft.fecha_reporte}
                     onChange={v => update("fecha_reporte", v)} />
            </div>
          </Section>

          {/* Section 2: Sujeto reportado */}
          <Section title="2. Sujeto Reportado">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Nombre / Razón social" value={draft.reportado_nombre}
                     onChange={v => update("reportado_nombre", v)} />
              <Field label="CUIL / CUIT" value={draft.reportado_cuil}
                     onChange={v => update("reportado_cuil", v)} />
              <Field label="Tipo de persona" value={draft.reportado_tipo}
                     onChange={v => update("reportado_tipo", v)} />
              <div>
                <label className="text-xs font-semibold text-[#5A6478] uppercase tracking-wider block mb-1.5">
                  Cuentas involucradas
                </label>
                <p className="text-sm font-mono text-[#EDEAE6] bg-[#12161F] rounded-lg px-3 py-2 leading-relaxed">
                  {draft.cuentas_involucradas.join(" · ")}
                </p>
              </div>
            </div>
          </Section>

          {/* Section 3: Operaciones */}
          <Section title="3. Operaciones Sospechosas">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Field label="Monto total (ARS)" value={String(draft.monto_total)}
                     onChange={v => update("monto_total" as any, v)} />
              <Field label="Fecha desde" value={draft.fecha_desde}
                     onChange={v => update("fecha_desde", v)} />
              <Field label="Fecha hasta" value={draft.fecha_hasta}
                     onChange={v => update("fecha_hasta", v)} />
            </div>
            <div className="mt-4">
              <label className="text-xs font-semibold text-[#5A6478] uppercase tracking-wider block mb-1.5">
                Patrón tipificado
              </label>
              <p className="text-sm text-[#EDEAE6] bg-[#12161F] rounded-lg px-3 py-2 leading-relaxed">
                {draft.patron_detectado}
              </p>
            </div>
          </Section>

          {/* Section 4: Descripción */}
          <Section title="4. Descripción de la Operatoria">
            <textarea
              value={draft.descripcion}
              onChange={e => update("descripcion", e.target.value)}
              rows={10}
              className="w-full text-sm text-[#EDEAE6] bg-[#12161F] rounded-lg px-3 py-2.5 border border-[#1E2430] outline-none focus:ring-2 focus:ring-[#2E6BFF] leading-relaxed resize-none print:border-none print:bg-[#0E1219]"
            />
          </Section>

          {/* Footer */}
          <div className="border-t border-[#1E2430] pt-4 flex justify-between items-end text-xs text-[#5A6478]">
            <div>
              <p>Generado por: <span className="font-semibold text-[#5A6478]">Phantom AI — Motor de detección GNN</span></p>
              <p className="mt-0.5">Datos 100% sintéticos — engagement simulado Banco Regional del Sur (BRS)</p>
            </div>
            <p>Score modelo: <span className="font-mono font-bold text-[#5A6478]">{draft.case_id}</span></p>
          </div>
        </div>
      </div>

      {/* Print styles */}
      <style>{`
        @media print {
          body * { visibility: hidden; }
          .print\\:max-w-none, .print\\:max-w-none * { visibility: visible; }
          .print\\:hidden { display: none !important; }
        }
      `}</style>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-bold text-[#EDEAE6] border-b border-[#1E2430] pb-2">{title}</h3>
      {children}
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="text-xs font-semibold text-[#5A6478] uppercase tracking-wider block mb-1.5">{label}</label>
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full text-sm text-[#EDEAE6] bg-[#12161F] rounded-lg px-3 py-2 border border-[#1E2430] outline-none focus:ring-2 focus:ring-[#2E6BFF] print:border-none print:bg-[#0E1219]"
      />
    </div>
  );
}
