"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import SessionSwitcher from "@/components/SessionSwitcher";
import { getSession, setSessionRole, can, type Session, type Role } from "@/lib/session";
import { appendAudit } from "@/lib/auditLog";
import {
  ACTIVIDADES, assessOnboarding, getOnboardings, addOnboarding,
  type OnbInput, type OnbRecord,
} from "@/lib/onboarding";

const PANEL = "#0E1219", LINE = "#1E2430", BONE = "#EDEAE6", MUTED = "#5A6478";
const NIVEL_STYLE: Record<string, { bg: string; text: string }> = {
  Alto: { bg: "rgba(239,68,68,0.15)", text: "#EF4444" },
  Medio: { bg: "rgba(245,158,11,0.15)", text: "#F59E0B" },
  Bajo: { bg: "rgba(34,197,94,0.15)", text: "#22C55E" },
};
const NIVEL_COLOR: Record<string, string> = { alto: "#EF4444", medio: "#F59E0B", bajo: "#22C55E" };
const DECISIONES = ["Aprobar alta", "Aprobar con Debida Diligencia Reforzada (EDD)", "Rechazar la solicitud"];
const inp = "w-full rounded-lg border px-2 py-2 text-sm outline-none";
const inpStyle = { borderColor: LINE, background: "#12161F", color: BONE };

function Section({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl p-4" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
      <h3 className="text-sm font-bold mb-3" style={{ color: BONE }}>
        <span className="mr-2 inline-flex h-5 w-5 items-center justify-center rounded-full text-[11px]" style={{ background: "rgba(46,107,255,0.15)", color: "#7AA2FF" }}>{n}</span>
        {title}
      </h3>
      {children}
    </div>
  );
}

export default function OnboardingPage() {
  const [session, setSession] = useState<Session>({ role: "analista", nombre: "" });
  const [recent, setRecent] = useState<OnbRecord[]>([]);
  const [f, setF] = useState<OnbInput>({ nombre: "", dni: "", tipoPersona: "Persona física", actividad: ACTIVIDADES[0], accountType: "personal", pep: false });
  const [decision, setDecision] = useState(DECISIONES[0]);
  const [done, setDone] = useState<OnbRecord | null>(null);

  useEffect(() => { setSession(getSession()); setRecent(getOnboardings()); }, []);
  const changeRole = (role: Role) => { setSessionRole(role); setSession(getSession()); };

  const assess = useMemo(() => assessOnboarding(f), [f]);
  // sugerir decisión según el riesgo evaluado
  useEffect(() => { setDecision(assess.edd ? DECISIONES[1] : DECISIONES[0]); }, [assess.edd]);

  const allowed = can(session.role, "cliente.alta");
  const canSubmit = allowed && f.nombre.trim() && f.dni.trim();

  const confirm = () => {
    if (!canSubmit) return;
    const rec: OnbRecord = {
      ...f, id: "ONB-" + Date.now().toString(36).toUpperCase(),
      fecha: new Date().toISOString(), nivel: assess.nivel, edd: assess.edd,
      decision, analista: session.nombre,
    };
    addOnboarding(rec);
    setRecent(getOnboardings());
    appendAudit({ actor: session.nombre, role: session.role, action: "cliente.alta", target: rec.id, detail: `${decision} · riesgo ${assess.nivel}` });
    setDone(rec);
    setF({ nombre: "", dni: "", tipoPersona: "Persona física", actividad: ACTIVIDADES[0], accountType: "personal", pep: false });
  };

  const nv = NIVEL_STYLE[assess.nivel];

  return (
    <div className="space-y-4">
      <div className="text-xs" style={{ color: MUTED }}>
        <Link href="/app/clientes" className="hover:text-[#EDEAE6]">Legajos de clientes</Link> / Alta (onboarding)
      </div>
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <PageHeader eyebrow="KYC / CDD" title="Alta de Cliente (Onboarding)"
          description="Proceso de debida diligencia de entrada: se capturan los datos, se evalúa el riesgo por factores, se corre screening y se decide aprobar, aprobar con EDD o rechazar." />
        <SessionSwitcher role={session.role} nombre={session.nombre} onChange={changeRole} />
      </div>

      {done && (
        <div className="rounded-xl p-4" style={{ background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.3)" }}>
          <p className="text-sm" style={{ color: "#22C55E" }}>
            ✓ Solicitud <b>{done.id}</b> registrada — {done.decision} · riesgo {done.nivel}{done.edd ? " · EDD requerida" : ""}. Asentada en el registro de auditoría.
          </p>
        </div>
      )}

      {!allowed && (
        <div className="rounded-xl p-4 text-sm" style={{ background: PANEL, border: `1px solid ${LINE}`, color: "#F59E0B" }}>
          Tu rol ({session.role}) no tiene permiso para dar de alta clientes. Cambiá a Analista u Oficial de Cumplimiento.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Section n={1} title="Datos del cliente">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <div className="text-[10px] uppercase tracking-wide mb-1" style={{ color: MUTED }}>Nombre / razón social</div>
              <input value={f.nombre} onChange={e => setF({ ...f, nombre: e.target.value })} className={inp} style={inpStyle} placeholder="Ej. Juan Pérez" />
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wide mb-1" style={{ color: MUTED }}>DNI / CUIT</div>
              <input value={f.dni} onChange={e => setF({ ...f, dni: e.target.value })} className={inp} style={inpStyle} placeholder="Ej. 30123456" />
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wide mb-1" style={{ color: MUTED }}>Tipo</div>
              <select value={f.tipoPersona} onChange={e => setF({ ...f, tipoPersona: e.target.value })} className={inp} style={inpStyle}>
                <option>Persona física</option><option>Persona jurídica</option>
              </select>
            </div>
            <div className="col-span-2">
              <div className="text-[10px] uppercase tracking-wide mb-1" style={{ color: MUTED }}>Actividad económica</div>
              <select value={f.actividad} onChange={e => setF({ ...f, actividad: e.target.value })} className={inp} style={inpStyle}>
                {ACTIVIDADES.map(a => <option key={a} value={a}>{a}</option>)}
              </select>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wide mb-1" style={{ color: MUTED }}>Tipo de cuenta</div>
              <select value={f.accountType} onChange={e => setF({ ...f, accountType: e.target.value })} className={inp} style={inpStyle}>
                <option value="personal">Personal</option><option value="business">Empresa</option><option value="merchant">Comercio</option>
              </select>
            </div>
            <label className="flex items-end gap-2 text-xs cursor-pointer pb-2" style={{ color: f.pep ? "#A78BFA" : MUTED }}>
              <input type="checkbox" checked={f.pep} onChange={e => setF({ ...f, pep: e.target.checked })} /> Persona Expuesta Políticamente (PEP)
            </label>
          </div>
        </Section>

        <Section n={2} title="Evaluación de riesgo y screening">
          <div className="flex items-center gap-3 mb-3">
            <span className="rounded-full px-3 py-1 text-xs font-bold" style={{ background: nv.bg, color: nv.text, border: `1px solid ${nv.text}66` }}>Riesgo CDD: {assess.nivel}</span>
            {assess.edd && <span className="rounded-full px-3 py-1 text-xs font-bold" style={{ background: "rgba(239,68,68,0.15)", color: "#EF4444" }}>EDD requerida</span>}
            <span className="text-[11px]" style={{ color: assess.screeningHit ? "#EF4444" : "#22C55E" }}>
              {assess.screeningHit ? "🔴 Screening: coincidencia" : "✓ Screening: sin coincidencias"}
            </span>
          </div>
          <div className="space-y-1.5">
            {assess.factores.length === 0
              ? <p className="text-xs" style={{ color: MUTED }}>Sin factores de riesgo elevado — perfil estándar.</p>
              : assess.factores.map((x, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: NIVEL_COLOR[x.nivel], flexShrink: 0 }} />
                  <span style={{ color: BONE }}>{x.factor}</span>
                  <span className="ml-auto text-[10px] uppercase" style={{ color: NIVEL_COLOR[x.nivel] }}>{x.nivel}</span>
                </div>
              ))}
          </div>
        </Section>
      </div>

      <Section n={3} title="Decisión de alta">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[240px]">
            <div className="text-[10px] uppercase tracking-wide mb-1" style={{ color: MUTED }}>Decisión</div>
            <select value={decision} onChange={e => setDecision(e.target.value)} className={inp} style={inpStyle}>
              {DECISIONES.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <button onClick={confirm} disabled={!canSubmit}
            className="rounded-lg px-4 py-2 text-sm font-semibold text-white transition-colors disabled:opacity-40"
            style={{ background: "#2E6BFF" }}>
            Registrar alta
          </button>
        </div>
        <p className="text-[11px] mt-2" style={{ color: MUTED }}>
          La decisión sugerida ({assess.edd ? "aprobar con EDD" : "aprobar"}) surge del riesgo evaluado; el oficial puede modificarla. Toda alta queda asentada en auditoría.
        </p>
      </Section>

      {recent.length > 0 && (
        <div className="rounded-xl p-4" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
          <h3 className="text-sm font-bold mb-2" style={{ color: BONE }}>Altas recientes ({recent.length})</h3>
          <div className="space-y-1.5">
            {recent.slice(0, 8).map(r => (
              <div key={r.id} className="flex items-center justify-between text-[11px]" style={{ color: MUTED }}>
                <span><b style={{ color: BONE }}>{r.nombre}</b> · {r.id} · {r.decision}</span>
                <span>riesgo {r.nivel} · {new Date(r.fecha).toLocaleDateString("es-AR")}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
