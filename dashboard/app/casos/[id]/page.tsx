"use client";
import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { Case, CaseStatus, CaseNote } from "@/lib/types";
import PageHeader from "@/components/PageHeader";


const STATUS_LABELS: Record<CaseStatus, string> = {
  abierto:      "Abierto",
  en_revision:  "En revisión",
  escalado:     "Escalado",
  desestimado:  "Desestimado",
  sar_enviado:  "SAR enviado",
};
const STATUS_COLORS: Record<CaseStatus, { bg: string; text: string; border: string }> = {
  abierto:     { bg: "rgba(46,107,255,0.15)", text: "#7AA2FF", border: "rgba(46,107,255,0.3)" },
  en_revision: { bg: "rgba(245,158,11,0.15)", text: "#F59E0B", border: "rgba(245,158,11,0.3)" },
  escalado:    { bg: "rgba(239,68,68,0.15)",  text: "#EF4444", border: "rgba(239,68,68,0.3)" },
  desestimado: { bg: "rgba(90,100,120,0.15)", text: "#8A93A6", border: "#1E2430" },
  sar_enviado: { bg: "rgba(34,197,94,0.15)",  text: "#22C55E", border: "rgba(34,197,94,0.3)" },
};
const PATTERN_DESC: Record<string, string> = {
  anillo_lavado:           "El modelo detectó un ciclo de transferencias entre múltiples cuentas consistente con un anillo de lavado de activos (layering).",
  estructuracion:          "Se detectaron múltiples transacciones de bajo monto desde esta cuenta, patrón consistente con estructuración (pitufeo) para evadir controles.",
  agregacion_fondos:       "Esta cuenta recibe fondos de múltiples fuentes con alta frecuencia, patrón consistente con agregación de fondos ilegales (placement).",
  transacciones_inusuales: "El perfil de transacciones de esta cuenta difiere significativamente de su comportamiento histórico esperado.",
};

function getStoredStatuses(): Record<string, CaseStatus> {
  if (typeof window === "undefined") return {};
  try { return JSON.parse(localStorage.getItem("phantom_case_statuses") || "{}"); } catch { return {}; }
}
function setStoredStatus(caseId: string, status: CaseStatus) {
  const all = getStoredStatuses();
  all[caseId] = status;
  localStorage.setItem("phantom_case_statuses", JSON.stringify(all));
}
function getStoredNotes(caseId: string): CaseNote[] {
  if (typeof window === "undefined") return [];
  try { return JSON.parse(localStorage.getItem(`phantom_notes_${caseId}`) || "[]"); } catch { return []; }
}
function addStoredNote(caseId: string, note: CaseNote) {
  const notes = getStoredNotes(caseId);
  notes.push(note);
  localStorage.setItem(`phantom_notes_${caseId}`, JSON.stringify(notes));
}

export default function CaseDetailPage() {
  const params = useParams();
  const caseId = params.id as string;

  const [caseData, setCaseData] = useState<Case | null>(null);
  const [status, setStatus]     = useState<CaseStatus>("abierto");
  const [notes, setNotes]       = useState<CaseNote[]>([]);
  const [noteText, setNoteText] = useState("");
  const [activeTab, setActiveTab] = useState<"resumen" | "grafo" | "transacciones" | "notas">("resumen");
  const cyRef = useRef<HTMLDivElement>(null);
  const cyInst = useRef<any>(null);

  useEffect(() => {
    fetch("/data/cases.json")
      .then(r => r.json())
      .then((cases: Case[]) => {
        const c = cases.find(x => x.case_id === caseId);
        if (c) {
          setCaseData(c);
          const stored = getStoredStatuses();
          setStatus(stored[c.case_id] ?? c.status);
          setNotes(getStoredNotes(c.case_id));
        }
      });
  }, [caseId]);

  // Build subgraph in Cytoscape
  useEffect(() => {
    if (!caseData || activeTab !== "grafo" || !cyRef.current) return;

    import("cytoscape").then(({ default: cytoscape }) => {
      if (cyInst.current) cyInst.current.destroy();

      const center = caseData.account_id;
      const nodes = [
        {
          data: {
            id: center, label: (caseData.persona?.nombre_completo || center).split(" ").slice(0,2).join(" "),
            score: caseData.gnn_score, is_fraud: caseData.is_fraud, isCenter: true
          }
        },
        ...caseData.neighbors.map(n => ({
          data: {
            id: n.account_id, label: n.account_id.slice(-6),
            score: n.gnn_score, is_fraud: n.is_fraud, isCenter: false
          }
        })),
      ];
      const edges = caseData.neighbors.map((n, i) => ({
        data: {
          id: `e${i}`,
          source: n.direction === "entrada" ? n.account_id : center,
          target: n.direction === "entrada" ? center : n.account_id,
          amount: n.amount,
        }
      }));

      cyInst.current = cytoscape({
        container: cyRef.current,
        elements: [...nodes, ...edges],
        style: [
          { selector: "node", style: {
            "width": 36, "height": 36, "label": "data(label)",
            "font-size": 10, "text-valign": "bottom", "text-margin-y": 4,
            "color": "#5A6478", "background-color": "#5A6478",
          }},
          { selector: "node[isCenter=true]", style: {
            "background-color": "#0A1226", "border-width": 3, "border-color": "#2E6BFF",
            "width": 48, "height": 48, "font-size": 11, "font-weight": "bold",
          }},
          { selector: "node[is_fraud=1]", style: { "background-color": "#EF4444" }},
          { selector: "edge", style: {
            "width": 2, "line-color": "#5A6478",
            "target-arrow-color": "#5A6478", "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "label": "data(amount)", "font-size": 8, "color": "#5A6478",
            "text-rotation": "autorotate",
          }},
        ],
        layout: { name: "concentric", concentric: (n: any) => n.data("isCenter") ? 10 : 1, levelWidth: () => 1 },
      });
    });

    return () => { if (cyInst.current) cyInst.current.destroy(); };
  }, [caseData, activeTab]);

  const handleStatusChange = (newStatus: CaseStatus) => {
    setStatus(newStatus);
    setStoredStatus(caseId, newStatus);
  };

  const handleAddNote = () => {
    if (!noteText.trim()) return;
    const note: CaseNote = {
      author: "Analista AML",
      text: noteText.trim(),
      timestamp: new Date().toISOString(),
    };
    addStoredNote(caseId, note);
    setNotes(prev => [...prev, note]);
    setNoteText("");
  };

  if (!caseData) {
    return (
      <div className="flex items-center justify-center h-64 text-[#5A6478]">Cargando caso…</div>
    );
  }

  const sc = STATUS_COLORS[status];

  return (
    <div className="space-y-5">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-[#5A6478]">
        <Link href="/casos" className="hover:text-[#EDEAE6]">Cola de alertas</Link>
        <span>/</span>
        <span className="text-[#EDEAE6] font-medium">{caseId}</span>
      </div>

      {/* Header */}
      <div className="bg-[#0E1219] rounded-xl border border-[#1E2430] p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-xl font-bold text-[#EDEAE6]">{caseData.persona?.nombre_completo || caseData.account_id}</h1>
              <span className="text-xs font-medium px-2.5 py-1 rounded-full border"
                    style={{ backgroundColor: sc.bg, color: sc.text, borderColor: sc.border }}>
                {STATUS_LABELS[status]}
              </span>
              {caseData.is_pep && (
                <span className="text-xs font-medium px-2.5 py-1 rounded-full" style={{background:"rgba(245,158,11,0.15)",color:"#F59E0B"}}>PEP</span>
              )}
            </div>
            <p className="text-sm text-[#5A6478] mt-1">{caseData.account_id} · Alerta {caseData.alert_date}</p>
          </div>

          {/* Action buttons */}
          <div className="flex gap-2 flex-wrap">
            {status === "abierto" && (
              <button onClick={() => handleStatusChange("en_revision")}
                      className="px-3 min-h-[44px] text-xs font-medium rounded-lg border border-[#F59E0B]/40 text-[#F59E0B] bg-[#F59E0B]/10 hover:bg-[#F59E0B]/20 transition-colors">
                Tomar caso
              </button>
            )}
            {(status === "abierto" || status === "en_revision") && (
              <>
                <button onClick={() => handleStatusChange("desestimado")}
                        className="px-3 min-h-[44px] text-xs font-medium rounded-lg border border-[#1E2430] text-[#5A6478] bg-[#12161F] hover:bg-[#12161F] transition-colors">
                  Desestimar
                </button>
                <Link href={`/casos/${caseId}/sar`}
                      onClick={() => handleStatusChange("escalado")}
                      className="px-3 min-h-[44px] text-xs font-medium rounded-lg bg-[#EF4444] text-white hover:bg-[#DC2626] transition-colors">
                  Escalar → SAR
                </Link>
              </>
            )}
            {status === "escalado" && (
              <Link href={`/casos/${caseId}/sar`}
                    className="px-3 min-h-[44px] text-xs font-medium rounded-lg bg-[#EF4444] text-white hover:bg-[#DC2626] transition-colors">
                Ver borrador SAR
              </Link>
            )}
          </div>
        </div>

        {/* Score bar */}
        <div className="mt-4 flex items-center gap-3">
          <span className="text-xs text-[#5A6478] w-24">Score GNN</span>
          <div className="flex-1 h-2 rounded-full bg-[#12161F] overflow-hidden">
            <div className="h-full rounded-full transition-all" style={{
              width: `${caseData.gnn_score * 100}%`,
              backgroundColor: caseData.gnn_score > 0.7 ? "#EF4444" : caseData.gnn_score > 0.4 ? "#F59E0B" : "#22C55E"
            }}/>
          </div>
          <span className="font-mono text-sm font-bold text-[#EDEAE6]">{caseData.gnn_score.toFixed(4)}</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-[#12161F] p-1 rounded-xl w-fit">
        {(["resumen","grafo","transacciones","notas"] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
                  className="px-4 min-h-[44px] rounded-lg text-sm font-medium transition-colors capitalize"
                  style={{
                    backgroundColor: activeTab === tab ? "rgba(46,107,255,0.15)" : "transparent",
                    color: activeTab === tab ? "#7AA2FF" : "#5A6478",
                  }}>
            {tab === "notas" ? `Notas (${notes.length})` : tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "resumen" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Pattern */}
          <div className="bg-[#0E1219] rounded-xl border border-[#1E2430] p-4 space-y-3">
            <h3 className="text-sm font-bold text-[#EDEAE6]">Patrón detectado</h3>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full" style={{background:"rgba(239,68,68,0.15)",color:"#EF4444"}}>
                {caseData.pattern.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
              </span>
            </div>
            <p className="text-sm text-[#5A6478] leading-relaxed">{PATTERN_DESC[caseData.pattern]}</p>
          </div>

          {/* Entity info */}
          <div className="bg-[#0E1219] rounded-xl border border-[#1E2430] p-4 space-y-3">
            <h3 className="text-sm font-bold text-[#EDEAE6]">Información del titular</h3>
            <div className="space-y-2 text-sm">
              {[
                { label: "CUIL",       val: caseData.persona?.cuil },
                { label: "Ocupación",  val: caseData.persona?.ocupacion },
                { label: "Provincia",  val: caseData.persona?.provincia },
                { label: "Municipio",  val: caseData.persona?.municipio },
                { label: "Condición AFIP", val: caseData.persona?.condicion_afip },
                { label: "Sucursal",   val: caseData.persona?.sucursal },
                { label: "Balance",    val: caseData.balance ? `$${caseData.balance.toLocaleString("es-AR")}` : null },
                { label: "Tipo cuenta",val: caseData.account_type },
              ].filter(r => r.val).map(r => (
                <div key={r.label} className="flex justify-between gap-2">
                  <span className="text-[#5A6478]">{r.label}</span>
                  <span className="text-[#EDEAE6] font-medium text-right">{r.val}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Empresa */}
          {caseData.empresa && (
            <div className="bg-[#0E1219] rounded-xl border border-[#1E2430] p-4 space-y-3">
              <h3 className="text-sm font-bold text-[#EDEAE6]">Empresa vinculada</h3>
              {caseData.empresa.is_shell && (
                <span className="text-xs font-medium px-2.5 py-1 rounded-full inline-flex items-center gap-1.5"
                      style={{background:"rgba(239,68,68,0.15)",color:"#EF4444"}}>
                  <span className="w-1.5 h-1.5 rounded-full bg-red-500"/>
                  Empresa de fachada (shell)
                </span>
              )}
              <div className="space-y-2 text-sm">
                {[
                  { label: "Razón social",  val: caseData.empresa.razon_social },
                  { label: "CUIT",          val: caseData.empresa.cuit_empresa },
                  { label: "Sector",        val: caseData.empresa.sector },
                  { label: "País",          val: caseData.empresa.pais_constitucion },
                ].map(r => (
                  <div key={r.label} className="flex justify-between gap-2">
                    <span className="text-[#5A6478]">{r.label}</span>
                    <span className="text-[#EDEAE6] font-medium text-right">{r.val}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Neighbors */}
          <div className="bg-[#0E1219] rounded-xl border border-[#1E2430] p-4 space-y-3">
            <h3 className="text-sm font-bold text-[#EDEAE6]">Cuentas vinculadas</h3>
            <div className="space-y-2">
              {caseData.neighbors.map(n => (
                <div key={n.account_id} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${n.direction === "entrada" ? "bg-[#EF4444]" : "bg-[#5A6478]"}`}/>
                    <span className="font-mono text-xs text-[#5A6478]">{n.account_id}</span>
                    <span className="text-[10px] text-[#5A6478]">{n.direction}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    {n.is_fraud === 1 && <span className="text-[10px] text-red-500 font-semibold">FRAUDE</span>}
                    <span className="font-mono text-xs text-[#EDEAE6]">{n.gnn_score.toFixed(3)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === "grafo" && (
        <div className="bg-[#0E1219] rounded-xl border border-[#1E2430] overflow-hidden">
          <div className="p-3 border-b border-[#1E2430] text-xs text-[#5A6478]">
            Subgrafo de vecinos directos — nodo central en azul, fraude en rojo
          </div>
          <div ref={cyRef} style={{ width: "100%", height: 420 }} />
        </div>
      )}

      {activeTab === "transacciones" && (
        <div className="bg-[#0E1219] rounded-xl border border-[#1E2430] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ backgroundColor: "#12161F", borderBottom: "1px solid #1E2430" }}>
                  {["Origen", "Destino", "Monto", "Dirección", "Timestamp"].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-[#5A6478] uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {caseData.recent_transactions.map((t, i) => (
                  <tr key={i} style={{ borderBottom: i < caseData.recent_transactions.length-1 ? "1px solid #1E2430" : undefined }}
                      className={t.is_fraud ? "bg-[#EF4444]/10" : ""}>
                    <td className="px-4 py-2.5 font-mono text-xs text-[#5A6478]">{t.src}</td>
                    <td className="px-4 py-2.5 font-mono text-xs text-[#5A6478]">{t.dst}</td>
                    <td className="px-4 py-2.5 text-xs font-semibold text-[#EDEAE6]">${t.amount.toLocaleString("es-AR")}</td>
                    <td className="px-4 py-2.5">
                      <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${t.direction === "entrada" ? "bg-[#EF4444]/15 text-[#EF4444]" : "bg-[#2E6BFF]/15 text-[#7AA2FF]"}`}>
                        {t.direction}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-[#5A6478] font-mono">{t.timestamp}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === "notas" && (
        <div className="space-y-4">
          <div className="space-y-3">
            {notes.length === 0 && (
              <div className="bg-[#0E1219] rounded-xl border border-[#1E2430] p-8 text-center text-[#5A6478] text-sm">
                Sin notas aún. Agregá observaciones del caso aquí.
              </div>
            )}
            {notes.map((n, i) => (
              <div key={i} className="bg-[#0E1219] rounded-xl border border-[#1E2430] p-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs font-semibold text-[#EDEAE6]">{n.author}</span>
                  <span className="text-xs text-[#5A6478]">{new Date(n.timestamp).toLocaleString("es-AR")}</span>
                </div>
                <p className="text-sm text-[#5A6478] leading-relaxed">{n.text}</p>
              </div>
            ))}
          </div>
          <div className="bg-[#0E1219] rounded-xl border border-[#1E2430] p-4 space-y-3">
            <h4 className="text-sm font-semibold text-[#EDEAE6]">Agregar nota</h4>
            <textarea
              value={noteText}
              onChange={e => setNoteText(e.target.value)}
              rows={3}
              placeholder="Observaciones, hallazgos, fuentes consultadas…"
              className="w-full border border-[#1E2430] rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#2E6BFF] resize-none"
            />
            <button onClick={handleAddNote}
                    disabled={!noteText.trim()}
                    className="px-4 min-h-[44px] text-sm font-medium rounded-lg text-white transition-colors disabled:opacity-40"
                    style={{ backgroundColor: "#2E6BFF" }}>
              Guardar nota
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
