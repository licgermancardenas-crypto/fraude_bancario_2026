"use client";

import type { Case } from "@/lib/types";
import { computeTriage } from "@/lib/triage";

const PANEL = "#12161F", LINE = "#1E2430", BONE = "#EDEAE6", MUTED = "#5A6478", VOID = "#07090F";

export default function TriageWaterfall({ caseData }: { caseData: Case }) {
  const t = computeTriage(caseData);

  return (
    <div className="rounded-lg p-4" style={{ background: PANEL, border: `1px solid ${LINE}` }}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold" style={{ color: BONE }}>Prioridad de investigación</h3>
            <span className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide"
              style={{ background: `${t.color}22`, color: t.color, border: `1px solid ${t.color}` }}>
              {t.level}
            </span>
          </div>
          <p className="mt-0.5 text-[11px]" style={{ color: MUTED }}>
            score compuesto — combina red, reglas, sanciones, PEP y KYC
          </p>
        </div>
        <div className="text-right leading-none">
          <span className="text-3xl font-bold" style={{ color: t.color }}>{t.score}</span>
          <span className="text-sm" style={{ color: MUTED }}>/100</span>
        </div>
      </div>

      {/* composición apilada */}
      <div className="mt-3 flex h-3 w-full overflow-hidden rounded-full" style={{ background: VOID }}>
        {t.components.filter(c => c.points > 0).map(c => (
          <div key={c.key} title={`${c.label}: +${c.points}`}
            style={{ width: `${c.points}%`, background: c.color }} />
        ))}
      </div>

      {/* desglose por componente */}
      <div className="mt-4 space-y-2.5">
        {t.components.map(c => (
          <div key={c.key} className="flex items-center gap-3">
            <span style={{ width: 9, height: 9, borderRadius: "50%", background: c.color, opacity: c.points ? 1 : 0.3, flexShrink: 0 }} />
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-2">
                <span className="truncate text-xs font-semibold" style={{ color: c.points ? BONE : MUTED }}>{c.label}</span>
                <span className="text-xs font-bold tabular-nums" style={{ color: c.points ? c.color : MUTED }}>
                  {c.points > 0 ? `+${c.points}` : "0"}
                </span>
              </div>
              <div className="mt-1 flex items-center gap-2">
                <div className="h-1.5 flex-1 overflow-hidden rounded-full" style={{ background: VOID }}>
                  <div className="h-full rounded-full" style={{ width: `${(c.points / c.max) * 100}%`, background: c.color }} />
                </div>
                <span className="w-32 shrink-0 truncate text-[10px]" style={{ color: MUTED }}>{c.detail}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
