"use client";
import { useEffect, useRef, useState } from "react";
import { API_URL, fetchHealth, scoreAccounts, type HealthResponse, type ScoreResponse } from "@/lib/api";

type HealthState = "checking" | "online" | "waking" | "offline";

const EXAMPLES = ["ACC0000009", "ACC0000210", "ACC0001046"];

function ScoreBar({ score }: { score: number }) {
  const color = score > 0.7 ? "#EF4444" : score > 0.3 ? "#D97706" : "#22C55E";
  const bg    = score > 0.7 ? "rgba(239,68,68,0.15)" : score > 0.3 ? "rgba(217,119,6,0.15)" : "rgba(34,197,94,0.15)";
  return (
    <div className="flex items-center gap-2 min-w-[110px]">
      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: bg }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${score * 100}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs font-mono font-semibold w-11 text-right" style={{ color }}>
        {(score * 100).toFixed(1)}%
      </span>
    </div>
  );
}

function HealthBadge({ state, health }: { state: HealthState; health: HealthResponse | null }) {
  const map: Record<HealthState, { color: string; bg: string; label: string }> = {
    checking: { color: "#5A6478", bg: "rgba(90,100,120,0.15)",  label: "Consultando…" },
    waking:   { color: "#F59E0B", bg: "rgba(245,158,11,0.12)", label: "Despertando servicio (Render free tier)…" },
    online:   { color: "#22C55E", bg: "rgba(34,197,94,0.12)",  label: "API en vivo" },
    offline:  { color: "#EF4444", bg: "rgba(239,68,68,0.12)",  label: "API no disponible" },
  };
  const s = map[state];
  return (
    <div className="flex items-center gap-2 rounded-lg px-3 py-2" style={{ backgroundColor: s.bg, border: `1px solid ${s.color}33` }}>
      <span
        className="w-2 h-2 rounded-full flex-shrink-0"
        style={{ backgroundColor: s.color, boxShadow: state === "online" ? `0 0 6px ${s.color}` : undefined }}
      />
      <span className="text-xs font-semibold" style={{ color: s.color }}>{s.label}</span>
      {health && state === "online" && (
        <span className="text-[11px] font-mono" style={{ color: "#5A6478" }}>
          · {health.accounts_indexed} cuentas · {health.cases_indexed} casos indexados
        </span>
      )}
    </div>
  );
}

export default function LiveApiConsole() {
  const [health, setHealth]         = useState<HealthResponse | null>(null);
  const [healthState, setHealthState] = useState<HealthState>("checking");
  const [input, setInput]           = useState(EXAMPLES.join(", "));
  const [result, setResult]         = useState<ScoreResponse | null>(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState<string | null>(null);
  const wakingTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 60_000);
    fetchHealth(controller.signal)
      .then(h => { setHealth(h); setHealthState("online"); })
      .catch(() => setHealthState("offline"))
      .finally(() => clearTimeout(timeout));
    return () => controller.abort();
  }, []);

  async function handleScore() {
    const ids = input.split(",").map(s => s.trim()).filter(Boolean).slice(0, 20);
    if (ids.length === 0) return;

    setLoading(true);
    setError(null);
    setResult(null);
    // Render free tier duerme tras inactividad — si tarda, avisamos que se está despertando
    wakingTimer.current = setTimeout(() => setHealthState(s => s === "online" ? s : "waking"), 4_000);

    try {
      const res = await scoreAccounts(ids);
      setResult(res);
      setHealthState("online");
    } catch {
      setError("No se pudo contactar la API. Puede estar reiniciándose (Render free tier) — probá de nuevo en unos segundos.");
      setHealthState("offline");
    } finally {
      if (wakingTimer.current) clearTimeout(wakingTimer.current);
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <HealthBadge state={healthState} health={health} />
        <a
          href={`${API_URL}/docs`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs font-mono underline"
          style={{ color: "#7AA2FF" }}
        >
          {API_URL}/docs ↗
        </a>
      </div>

      <div className="rounded-xl p-5 space-y-3" style={{ backgroundColor: "#12161F", border: "1px solid #1E2430" }}>
        <label className="text-xs font-semibold uppercase tracking-wider" style={{ color: "#5A6478" }}>
          POST /accounts/score — account_ids separados por coma
        </label>
        <div className="flex gap-2 flex-col sm:flex-row">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="ACC0000009, ACC0000210, ACC0001046"
            className="flex-1 rounded-lg px-4 py-2.5 min-h-[44px] text-sm font-mono outline-none"
            style={{ backgroundColor: "#0E1219", border: "1px solid #1E2430", color: "#EDEAE6" }}
            onFocus={e => (e.target.style.borderColor = "#2E6BFF")}
            onBlur={e  => (e.target.style.borderColor = "#1E2430")}
            onKeyDown={e => e.key === "Enter" && handleScore()}
          />
          <button
            onClick={handleScore}
            disabled={loading}
            className="rounded-lg px-5 py-2.5 min-h-[44px] text-sm font-semibold whitespace-nowrap transition-opacity"
            style={{ backgroundColor: "#2E6BFF", color: "#07090F", opacity: loading ? 0.6 : 1 }}
          >
            {loading ? "Consultando…" : "Scorear cuentas"}
          </button>
        </div>
        {healthState === "waking" && (
          <p className="text-xs" style={{ color: "#F59E0B" }}>
            El servicio en Render duerme tras 15 min de inactividad — el primer request puede tardar 30-50s en despertarlo.
          </p>
        )}
        {error && <p className="text-xs" style={{ color: "#EF4444" }}>{error}</p>}
      </div>

      {result && (
        <div className="rounded-xl p-5 space-y-3" style={{ backgroundColor: "#12161F", border: "1px solid #1E2430" }}>
          <div className="flex items-center justify-between text-xs" style={{ color: "#5A6478" }}>
            <span>
              {result.found}/{result.requested} encontradas · modelo {result.model} · {new Date(result.scored_at).toLocaleTimeString("es-AR")}
            </span>
          </div>
          <div className="space-y-2">
            {result.results.map(r => (
              <div key={r.account_id} className="flex items-center gap-3 rounded-lg px-3 py-2"
                   style={{ backgroundColor: "#0E1219", border: "1px solid #1E2430" }}>
                <span className="text-xs font-mono w-28 flex-shrink-0" style={{ color: "#EDEAE6" }}>{r.account_id}</span>
                {r.found ? (
                  <>
                    <ScoreBar score={r.gnn_score ?? 0} />
                    {r.in_ring && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded whitespace-nowrap"
                            style={{ backgroundColor: "rgba(239,68,68,0.15)", color: "#EF4444" }}>
                        en anillo
                      </span>
                    )}
                    {r.placement_score_norm != null && r.placement_score_norm > 0.3 && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded whitespace-nowrap"
                            style={{ backgroundColor: "rgba(124,58,237,0.15)", color: "#A78BFA" }}>
                        placement {(r.placement_score_norm * 100).toFixed(0)}%
                      </span>
                    )}
                  </>
                ) : (
                  <span className="text-xs italic" style={{ color: "#5A6478" }}>no indexada (fuera del top-200 + 80 casos)</span>
                )}
              </div>
            ))}
          </div>
          <details className="text-xs">
            <summary className="cursor-pointer font-semibold" style={{ color: "#7AA2FF" }}>Ver respuesta JSON cruda</summary>
            <pre className="mt-2 rounded-lg p-3 overflow-x-auto" style={{ backgroundColor: "#0E1219", color: "#8A93A6", border: "1px solid #1E2430" }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}
