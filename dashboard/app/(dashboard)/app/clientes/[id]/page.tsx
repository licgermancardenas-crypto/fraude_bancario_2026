"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { type KycProfile, RIESGO_STYLE, docEstadoColor } from "@/lib/cdd";
import { PATTERN_LABELS } from "@/lib/patterns";

const PANEL = "#0E1219", LINE = "#1E2430", BONE = "#EDEAE6", MUTED = "#5A6478";
const money = (n: number) => "$ " + Math.round(n).toLocaleString("es-AR");
const fdate = (s: string) => { try { return new Date(s + "T00:00:00").toLocaleDateString("es-AR"); } catch { return s; } };
const NIVEL_COLOR: Record<string, string> = { alto: "#EF4444", medio: "#F59E0B", bajo: "#22C55E" };

function Card({ title, children, right }: { title: string; children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div className="rounded-xl p-4" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold" style={{ color: BONE }}>{title}</h3>
        {right}
      </div>
      {children}
    </div>
  );
}
function Field({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide" style={{ color: MUTED }}>{k}</div>
      <div className="text-xs" style={{ color: BONE }}>{v || "—"}</div>
    </div>
  );
}

export default function ClientePage() {
  const id = useParams().id as string;
  const [profiles, setProfiles] = useState<Record<string, KycProfile> | null>(null);

  useEffect(() => { fetch("/data/kyc_profiles.json").then(r => r.json()).then(setProfiles); }, []);

  if (!profiles) return <div className="flex items-center justify-center h-64 text-[#5A6478]">Cargando legajo…</div>;
  const p = profiles[id];
  if (!p) return (
    <div className="space-y-4">
      <Link href="/app/clientes" className="text-xs text-[#7AA2FF]">← Legajos</Link>
      <div className="rounded-xl p-8 text-center text-sm" style={{ background: PANEL, border: `1px solid ${LINE}`, color: MUTED }}>
        No hay legajo CDD para {id}. Los legajos cubren la cartera de mayor riesgo y una muestra de clientes.
      </div>
    </div>
  );

  const per = p.persona;
  const cdd = p.cdd;
  const rs = RIESGO_STYLE[cdd.riesgo_nivel];

  return (
    <div className="space-y-4">
      <div className="text-xs text-[#5A6478]">
        <Link href="/app/clientes" className="hover:text-[#EDEAE6]">Legajos de clientes</Link> / {per.nombre_completo || id}
      </div>

      {/* Header */}
      <div className="rounded-xl p-5" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold" style={{ color: BONE }}>{per.nombre_completo || p.account_id}</h1>
            <p className="text-sm mt-1" style={{ color: MUTED }}>
              DNI {per.dni} · CUIL {per.cuil} · {per.ocupacion} · {per.municipio}, {per.provincia}
            </p>
          </div>
          <div className="flex flex-wrap gap-2 justify-end">
            <span className="rounded-full px-3 py-1 text-xs font-bold" style={{ background: rs.bg, color: rs.text, border: `1px solid ${rs.text}66` }}>
              Riesgo CDD: {cdd.riesgo_nivel}
            </span>
            {cdd.edd_requerida && <span className="rounded-full px-3 py-1 text-xs font-bold" style={{ background: "rgba(239,68,68,0.15)", color: "#EF4444", border: "1px solid rgba(239,68,68,0.4)" }}>EDD requerida</span>}
            {cdd.revision_vencida && <span className="rounded-full px-3 py-1 text-xs font-bold" style={{ background: "rgba(245,158,11,0.15)", color: "#F59E0B", border: "1px solid rgba(245,158,11,0.4)" }}>Revisión vencida</span>}
            {p.pep && <span className="rounded-full px-3 py-1 text-xs font-bold" style={{ background: "rgba(167,139,250,0.15)", color: "#A78BFA", border: "1px solid rgba(167,139,250,0.4)" }}>PEP</span>}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Riesgo CDD */}
        <Card title="Calificación de riesgo (CDD)"
          right={<span className="text-[11px]" style={{ color: MUTED }}>KYC onboarding: <b style={{ color: BONE }}>{cdd.kyc_onboarding}</b></span>}>
          <div className="space-y-2">
            {cdd.factores.length === 0 && <p className="text-xs" style={{ color: MUTED }}>Sin factores de riesgo elevado.</p>}
            {cdd.factores.map((f, i) => (
              <div key={i} className="flex items-center gap-2">
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: NIVEL_COLOR[f.nivel], flexShrink: 0 }} />
                <span className="text-xs" style={{ color: BONE }}>{f.factor}</span>
                <span className="ml-auto text-[10px] uppercase" style={{ color: NIVEL_COLOR[f.nivel] }}>{f.nivel}</span>
              </div>
            ))}
          </div>
          {cdd.edd_requerida && (
            <div className="mt-3 rounded-lg p-2.5 text-[11px]" style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)", color: "#F87171" }}>
              <b>Debida Diligencia Reforzada (EDD)</b> — disparada por: {cdd.edd_motivos.join(" · ")}.
            </div>
          )}
        </Card>

        {/* Revisión periódica */}
        <Card title="Revisión periódica (KYC continuo)">
          <div className="grid grid-cols-3 gap-3">
            <Field k="Alta del cliente" v={fdate(cdd.fecha_alta)} />
            <Field k="Última revisión" v={fdate(cdd.ultima_revision)} />
            <div>
              <div className="text-[10px] uppercase tracking-wide" style={{ color: MUTED }}>Próxima revisión</div>
              <div className="text-xs font-semibold" style={{ color: cdd.revision_vencida ? "#EF4444" : "#22C55E" }}>
                {fdate(cdd.proxima_revision)} {cdd.revision_vencida && "⚠"}
              </div>
            </div>
          </div>
          <p className="text-[11px] mt-3" style={{ color: MUTED }}>
            {cdd.revision_vencida
              ? "La revisión periódica está vencida — riesgo de incumplimiento de KYC continuo."
              : `Cadencia según riesgo ${cdd.riesgo_nivel.toLowerCase()}: revisión ${cdd.riesgo_nivel === "Alto" ? "semestral" : cdd.riesgo_nivel === "Medio" ? "anual" : "bienal"}.`}
          </p>
        </Card>

        {/* Cuentas */}
        <Card title="Cuentas del cliente">
          <div className="space-y-2">
            {p.cuentas.map(c => (
              <div key={c.account_id} className="flex items-center justify-between rounded-lg p-2.5" style={{ background: "#12161F", border: `1px solid ${LINE}` }}>
                <div>
                  <p className="text-xs font-mono" style={{ color: BONE }}>{c.account_id}</p>
                  <p className="text-[10px]" style={{ color: MUTED }}>{c.tipo} · {c.account_type}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs" style={{ color: BONE }}>{money(c.balance)}</p>
                  <p className="text-[10px]" style={{ color: c.gnn_score > 0.7 ? "#EF4444" : MUTED }}>score GNN {c.gnn_score.toFixed(2)}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Screening & PEP */}
        <Card title="Screening y PEP">
          {p.screening.hit_directo ? (
            <div className="rounded-lg p-2.5 text-[11px] mb-2" style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", color: "#F87171" }}>
              🔴 Coincidencia directa en <b>{p.screening.hit_directo.lista}</b> — "{p.screening.hit_directo.nombre}" ({p.screening.hit_directo.estado}, score {p.screening.hit_directo.score_match})
            </div>
          ) : p.screening.exposicion_indirecta.length > 0 ? (
            <p className="text-[11px] mb-2" style={{ color: "#F59E0B" }}>⚠ Exposición indirecta ({p.screening.exposicion_indirecta.length}) a cuenta(s) en lista de sanciones.</p>
          ) : (
            <p className="text-[11px] mb-2" style={{ color: MUTED }}>Sin coincidencias en listas de sanciones.</p>
          )}
          {p.pep && p.pep_info ? (
            <p className="text-[11px]" style={{ color: "#A78BFA" }}>PEP: {p.pep_info.cargo} · {p.pep_info.categoria} · {p.pep_info.pais}</p>
          ) : (
            <p className="text-[11px]" style={{ color: MUTED }}>No figura como Persona Expuesta Políticamente.</p>
          )}
        </Card>
      </div>

      {/* Documentación / CDD checklist */}
      <Card title="Documentación y debida diligencia"
        right={<span className="text-[11px]" style={{ color: cdd.verificacion_identidad === "Verificada" ? "#22C55E" : "#F59E0B" }}>Identidad: {cdd.verificacion_identidad}</span>}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {cdd.documentos.map((d, i) => (
            <div key={i} className="flex items-center justify-between rounded-lg p-2.5" style={{ background: "#12161F", border: `1px solid ${LINE}` }}>
              <span className="text-xs" style={{ color: BONE }}>{d.tipo}</span>
              <span className="text-[11px] font-semibold" style={{ color: docEstadoColor(d.estado) }}>{d.estado}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Historial de alertas */}
      <Card title={`Historial de alertas (${p.alertas.length})`}>
        {p.alertas.length === 0 ? (
          <p className="text-xs" style={{ color: MUTED }}>Sin alertas registradas para este cliente.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: `1px solid ${LINE}` }}>
                  {["Referencia", "Fecha", "Patrón", "Score", "Estado"].map(h => (
                    <th key={h} className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider" style={{ color: MUTED }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {p.alertas.map((a, i) => {
                  const isCase = a.ref.startsWith("CASO-");
                  return (
                    <tr key={i} style={{ borderBottom: i < p.alertas.length - 1 ? `1px solid ${LINE}` : undefined }}>
                      <td className="px-3 py-2 text-xs font-mono" style={{ color: isCase ? "#7AA2FF" : MUTED }}>
                        {isCase ? <Link href={`/app/casos/${a.ref}`}>{a.ref} →</Link> : a.ref}
                      </td>
                      <td className="px-3 py-2 text-xs" style={{ color: BONE }}>{fdate(a.fecha)}</td>
                      <td className="px-3 py-2 text-xs" style={{ color: MUTED }}>{PATTERN_LABELS[a.patron as keyof typeof PATTERN_LABELS] ?? a.patron}</td>
                      <td className="px-3 py-2 text-xs" style={{ color: BONE }}>{a.score.toFixed(2)}</td>
                      <td className="px-3 py-2 text-[11px]" style={{ color: a.estado.includes("investigación") ? "#F59E0B" : a.estado.includes("ROS") ? "#EF4444" : MUTED }}>{a.estado}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Identidad completa */}
      <Card title="Identidad y perfil (KYC)">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-6 gap-y-3">
          {[
            ["Nombre", per.nombre_completo], ["DNI", per.dni], ["CUIL", per.cuil],
            ["Fecha nac.", per.fecha_nacimiento], ["Edad", per.edad], ["Género", per.genero],
            ["Nacionalidad", per.nacionalidad], ["Domicilio", per.direccion], ["Localidad", `${per.municipio}, ${per.provincia}`],
            ["CP", per.codigo_postal], ["Condición AFIP", per.condicion_afip], ["Cat. monotributo", per.categoria_mono],
            ["Actividad económica", per.actividad_economica], ["Ocupación", per.ocupacion], ["Tipo de cuenta", per.tipo_cuenta],
            ["Antigüedad", `${per.antiguedad_meses} meses`], ["Sucursal", per.sucursal], ["Teléfono", per.telefono], ["Email", per.email],
          ].map(([k, v]) => <Field key={k} k={k as string} v={v as string} />)}
        </div>
      </Card>
    </div>
  );
}
