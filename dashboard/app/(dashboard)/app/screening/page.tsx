"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import SessionSwitcher from "@/components/SessionSwitcher";
import { getSession, setSessionRole, can, type Session, type Role } from "@/lib/session";
import { appendAudit } from "@/lib/auditLog";
import {
  type ScreeningEstado, type ScreeningDisposition, LISTA_STYLE, ESTADO_STYLE,
  MOTIVOS_CONFIRMAR, MOTIVOS_DESCARTAR, getDispositions, setDisposition,
  getLastRescreen, setRescreenNow,
} from "@/lib/screeningQueue";

const PANEL = "#0E1219", LINE = "#1E2430", BONE = "#EDEAE6", MUTED = "#5A6478";
const fdate = (s: string) => { try { return new Date(s.length > 10 ? s : s + "T00:00:00").toLocaleDateString("es-AR"); } catch { return s; } };
const PAGE = 30;

interface Hit {
  id: string; fecha: string; account_id: string; entidad: string; account_type: string;
  is_pep: boolean; lista: string; nombre_coincidencia: string; motivo: string;
  score_match: number; estado: ScreeningEstado; caso_ref: string | null; analista: string;
}
interface Summary { total: number; pendientes: number; confirmados: number; descartados: number; por_lista: Record<string, number>; ultimo_screening: string; }

export default function ScreeningPage() {
  const [data, setData] = useState<{ summary: Summary; hits: Hit[] } | null>(null);
  const [disp, setDisp] = useState<Record<string, ScreeningDisposition>>({});
  const [session, setSession] = useState<Session>({ role: "analista", nombre: "" });
  const [rescreen, setRescreen] = useState<string | null>(null);
  const [sel, setSel] = useState<Hit | null>(null);
  const [motivo, setMotivo] = useState("");
  const [fLista, setFLista] = useState("all");
  const [fEstado, setFEstado] = useState("all");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(0);

  useEffect(() => {
    fetch("/data/screening_hits.json").then(r => r.json()).then(setData);
    setDisp(getDispositions()); setSession(getSession()); setRescreen(getLastRescreen());
  }, []);

  const changeRole = (role: Role) => { setSessionRole(role); setSession(getSession()); };
  const effEstado = (h: Hit): ScreeningEstado => disp[h.id]?.estado ?? h.estado;

  const rows = useMemo(() => {
    if (!data) return [];
    const ql = q.trim().toLowerCase();
    return data.hits
      .filter(h => fLista === "all" || h.lista === fLista)
      .filter(h => fEstado === "all" || effEstado(h) === fEstado)
      .filter(h => !ql || h.entidad.toLowerCase().includes(ql) || h.account_id.toLowerCase().includes(ql) || h.nombre_coincidencia.toLowerCase().includes(ql))
      .sort((a, b) => (effEstado(a) === "pendiente" ? -1 : 0) - (effEstado(b) === "pendiente" ? -1 : 0) || b.score_match - a.score_match);
  }, [data, disp, fLista, fEstado, q]);

  useEffect(() => setPage(0), [fLista, fEstado, q]);
  if (!data) return <div className="flex items-center justify-center h-64 text-[#5A6478]">Cargando screening…</div>;

  const counts = data.hits.reduce((a, h) => { const e = effEstado(h); a[e] = (a[e] ?? 0) + 1; return a; }, {} as Record<string, number>);
  const pageRows = rows.slice(page * PAGE, page * PAGE + PAGE);
  const pages = Math.ceil(rows.length / PAGE);

  const dispose = (estado: ScreeningEstado) => {
    if (!sel || !can(session.role, "screening.disponer")) return;
    const d: ScreeningDisposition = { estado, motivo, revisor: session.nombre, fecha: new Date().toISOString() };
    setDisposition(sel.id, d);
    setDisp(getDispositions());
    appendAudit({ actor: session.nombre, role: session.role, action: `screening.${estado}`, target: sel.account_id, detail: `${sel.lista} · ${motivo}` });
    setSel(null); setMotivo("");
  };
  const doRescreen = () => setRescreen(setRescreenNow());

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <PageHeader eyebrow="Sanciones y listas" title="Screening — Workbench"
          description="Cola de coincidencias contra listas de sanciones (ONU / OFAC / REPET, ficticias). El analista dispone cada hit: confirmar (verdadero positivo) o descartar (homónimo / baja confianza). El screening es continuo." />
        <SessionSwitcher role={session.role} nombre={session.nombre} onChange={changeRole} />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {[
          { label: "Coincidencias", value: data.summary.total, color: BONE },
          { label: "Pendientes de revisión", value: counts.pendiente ?? 0, color: "#F59E0B" },
          { label: "Confirmadas", value: counts.confirmado ?? 0, color: "#EF4444" },
          { label: "Descartadas (FP)", value: counts.descartado ?? 0, color: "#5A6478" },
          { label: "Tasa de descarte", value: `${Math.round(((counts.descartado ?? 0) / data.summary.total) * 100)}%`, color: "#5A6478" },
        ].map(k => (
          <div key={k.label} className="rounded-xl p-4" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
            <div className="text-2xl font-bold" style={{ color: k.color }}>{k.value}</div>
            <div className="text-[11px] mt-1" style={{ color: MUTED }}>{k.label}</div>
          </div>
        ))}
      </div>

      {/* Rescreening + filtros */}
      <div className="rounded-xl p-4 flex flex-wrap gap-2 items-center" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
        <div className="flex items-center gap-2 mr-2">
          <button onClick={doRescreen} className="rounded-lg px-3 min-h-[40px] text-sm font-medium" style={{ background: "rgba(46,107,255,0.12)", color: "#7AA2FF", border: "1px solid rgba(46,107,255,0.35)" }}>↻ Re-ejecutar screening</button>
          <span className="text-[11px]" style={{ color: MUTED }}>último: {rescreen ? new Date(rescreen).toLocaleString("es-AR") : fdate(data.summary.ultimo_screening)}</span>
        </div>
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="Buscar entidad, cuenta o nombre en lista…" className="flex-1 min-w-[200px] rounded-lg border border-[#1E2430] bg-[#12161F] px-3 min-h-[40px] text-sm outline-none" style={{ color: BONE }} />
        <select value={fLista} onChange={e => setFLista(e.target.value)} className="rounded-lg border border-[#1E2430] bg-[#12161F] px-2 min-h-[40px] text-sm outline-none" style={{ color: BONE }}>
          <option value="all">Toda lista</option>{Object.keys(data.summary.por_lista).map(l => <option key={l} value={l}>{l}</option>)}
        </select>
        <select value={fEstado} onChange={e => setFEstado(e.target.value)} className="rounded-lg border border-[#1E2430] bg-[#12161F] px-2 min-h-[40px] text-sm outline-none" style={{ color: BONE }}>
          <option value="all">Todo estado</option>
          {(["pendiente", "confirmado", "descartado"] as ScreeningEstado[]).map(e => <option key={e} value={e}>{ESTADO_STYLE[e].label}</option>)}
        </select>
        <span className="text-xs ml-auto" style={{ color: MUTED }}>{rows.length} coincidencias</span>
      </div>

      {/* Panel de disposición */}
      {sel && (
        <div className="rounded-xl p-4" style={{ background: "#07090F", border: "1px solid #1E2430" }}>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-bold" style={{ color: BONE }}>Disponer coincidencia — {sel.id}</h3>
            <button onClick={() => setSel(null)} className="text-[11px]" style={{ color: MUTED }}>cerrar ✕</button>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-2 text-xs mb-3">
            <div><div className="text-[9px] uppercase" style={{ color: MUTED }}>Entidad</div><div style={{ color: BONE }}>{sel.entidad}</div></div>
            <div><div className="text-[9px] uppercase" style={{ color: MUTED }}>Cuenta</div><div className="font-mono" style={{ color: BONE }}>{sel.account_id}</div></div>
            <div><div className="text-[9px] uppercase" style={{ color: MUTED }}>Lista</div><div style={{ color: LISTA_STYLE[sel.lista]?.text }}>{sel.lista}</div></div>
            <div><div className="text-[9px] uppercase" style={{ color: MUTED }}>Score match</div><div style={{ color: BONE }}>{Math.round(sel.score_match * 100)}%</div></div>
            <div className="col-span-2"><div className="text-[9px] uppercase" style={{ color: MUTED }}>Coincidencia en lista</div><div style={{ color: BONE }}>{sel.nombre_coincidencia}</div></div>
            <div className="col-span-2"><div className="text-[9px] uppercase" style={{ color: MUTED }}>Motivo de la designación</div><div style={{ color: BONE }}>{sel.motivo}</div></div>
          </div>
          {can(session.role, "screening.disponer") ? (
            <div className="space-y-2">
              <select value={motivo} onChange={e => setMotivo(e.target.value)} className="w-full rounded-md border px-2 py-2 text-xs outline-none" style={{ borderColor: LINE, background: "#12161F", color: BONE }}>
                <option value="">— elegí un motivo —</option>
                <optgroup label="Descartar (falso positivo)">{MOTIVOS_DESCARTAR.map(m => <option key={m} value={m}>{m}</option>)}</optgroup>
                <optgroup label="Confirmar (verdadero positivo)">{MOTIVOS_CONFIRMAR.map(m => <option key={m} value={m}>{m}</option>)}</optgroup>
              </select>
              <div className="flex gap-2">
                <button onClick={() => dispose("descartado")} disabled={!motivo} className="rounded-md px-3 py-2 text-xs font-semibold disabled:opacity-40" style={{ background: "rgba(90,100,120,0.2)", color: BONE, border: `1px solid ${LINE}` }}>Descartar (FP)</button>
                <button onClick={() => dispose("confirmado")} disabled={!motivo} className="rounded-md px-3 py-2 text-xs font-semibold text-white disabled:opacity-40" style={{ background: "#EF4444" }}>Confirmar coincidencia</button>
                {sel.caso_ref && <Link href={`/app/casos/${sel.caso_ref}`} className="ml-auto rounded-md border px-3 py-2 text-xs" style={{ borderColor: LINE, color: "#7AA2FF" }}>Ver caso {sel.caso_ref} →</Link>}
              </div>
            </div>
          ) : <p className="text-[11px]" style={{ color: "#F59E0B" }}>Rol sin permiso para disponer (auditoría es sólo lectura).</p>}
        </div>
      )}

      {pages > 1 && (
        <div className="flex items-center justify-end gap-2 text-xs" style={{ color: MUTED }}>
          <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} className="px-2 py-1 rounded disabled:opacity-40" style={{ border: `1px solid ${LINE}` }}>←</button>
          <span>{page + 1} / {pages}</span>
          <button onClick={() => setPage(p => Math.min(pages - 1, p + 1))} disabled={page >= pages - 1} className="px-2 py-1 rounded disabled:opacity-40" style={{ border: `1px solid ${LINE}` }}>→</button>
        </div>
      )}

      <div className="rounded-xl overflow-hidden" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: "#12161F", borderBottom: `1px solid ${LINE}` }}>
                {["Fecha", "Entidad", "Lista", "Coincidencia", "Match", "Estado", ""].map(h => (
                  <th key={h} className="px-3 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider" style={{ color: MUTED }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pageRows.map((h, i) => {
                const est = ESTADO_STYLE[effEstado(h)];
                const ls = LISTA_STYLE[h.lista] ?? { bg: LINE, text: MUTED };
                return (
                  <tr key={h.id} onClick={() => { setSel(h); setMotivo(""); }} className="cursor-pointer hover:bg-[#12161F]" style={{ borderBottom: i < pageRows.length - 1 ? `1px solid ${LINE}` : undefined }}>
                    <td className="px-3 py-2 text-[11px] whitespace-nowrap" style={{ color: "#8A93A6" }}>{fdate(h.fecha)}</td>
                    <td className="px-3 py-2">
                      <p className="text-xs" style={{ color: BONE }}>{h.entidad} {h.is_pep && <span className="text-[9px]" style={{ color: "#A78BFA" }}>PEP</span>}</p>
                      <p className="text-[10px] font-mono" style={{ color: MUTED }}>{h.account_id}</p>
                    </td>
                    <td className="px-3 py-2"><span className="rounded-full px-2 py-0.5 text-[10px] font-bold" style={{ background: ls.bg, color: ls.text }}>{h.lista}</span></td>
                    <td className="px-3 py-2 text-[11px]" style={{ color: BONE }}>{h.nombre_coincidencia}</td>
                    <td className="px-3 py-2 text-xs font-semibold" style={{ color: h.score_match >= 0.9 ? "#EF4444" : h.score_match >= 0.8 ? "#F59E0B" : MUTED }}>{Math.round(h.score_match * 100)}%</td>
                    <td className="px-3 py-2"><span className="rounded-full px-2 py-0.5 text-[10px] font-semibold whitespace-nowrap" style={{ background: `${est.color}22`, color: est.color }}>{est.label}</span></td>
                    <td className="px-3 py-2 text-[11px] whitespace-nowrap" style={{ color: "#7AA2FF" }}>disponer →</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
