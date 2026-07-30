import type { Case, CasePattern } from "@/lib/types";
import { kycTier, isBlindSpot } from "@/lib/kyc";
import { screeningSummary } from "@/lib/screening";

export const PATTERN_DESC: Record<CasePattern, string> = {
  anillo_lavado:           "El modelo detectó un ciclo de transferencias entre múltiples cuentas consistente con un anillo de lavado de activos (layering).",
  estructuracion:          "Se detectaron múltiples transacciones de bajo monto desde esta cuenta, patrón consistente con estructuración (pitufeo) para evadir controles.",
  agregacion_fondos:       "Esta cuenta recibe fondos de múltiples fuentes con alta frecuencia, patrón consistente con agregación de fondos ilegales (placement).",
  cuenta_paso:             "La cuenta recibe y transfiere fondos por montos casi idénticos en cuestión de horas, manteniendo un saldo cercano a cero: comportamiento de cuenta de paso (conducto).",
  shell_layering:          "Los fondos atraviesan cuentas de empresas (posibles sociedades pantalla) que fragmentan y redistribuyen el dinero simulando pagos comerciales (layering).",
  cuenta_durmiente:        "Una cuenta sin actividad durante un período prolongado registra de golpe ingresos y egresos de alto monto concentrados en pocos días (reactivación de cuenta durmiente).",
  red_mulas:               "Un nodo reparte fondos en montos pequeños a numerosas cuentas recién abiertas que reenvían el dinero a un punto de retiro: patrón de red de mulas reclutadas.",
  round_tripping:          "El dinero sale de la cuenta, circula por intermediarios y regresa al origen con apariencia de ingreso legítimo (round-tripping / integración).",
  transacciones_inusuales: "El perfil de transacciones de esta cuenta difiere significativamente de su comportamiento histórico esperado.",
};

export type DetectionReasonKind =
  | "score" | "pattern" | "network" | "kyc_blindspot" | "screening_directo"
  | "screening_indirecto" | "pep" | "shell" | "activity";

export interface DetectionReason {
  kind: DetectionReasonKind;
  color: string;
  title: string;
  detail: string;
}

const COLOR = {
  red:    "#EF4444",
  amber:  "#F59E0B",
  violet: "#A78BFA",
  blue:   "#7AA2FF",
  green:  "#22C55E",
};

/**
 * Arma la lista de razones concretas por las que Phantom AI marcó este caso,
 * a partir de datos reales ya calculados para la cuenta (no texto genérico
 * por patrón — cada razón cita cifras y cuentas específicas de este caso).
 */
export function buildDetectionInsight(c: Case): DetectionReason[] {
  const reasons: DetectionReason[] = [];

  // 1. Score de comportamiento en red — siempre presente.
  const scorePct = (c.gnn_score * 100).toFixed(1);
  reasons.push({
    kind: "score",
    color: c.gnn_score >= 0.9 ? COLOR.red : c.gnn_score >= 0.7 ? COLOR.amber : COLOR.blue,
    title: `Score de comportamiento en red: ${scorePct}%`,
    detail: c.gnn_score >= 0.9
      ? "Extremadamente alto — muy por encima del umbral operativo de 90% que usa el equipo de compliance para priorizar la cola."
      : c.gnn_score >= 0.7
      ? "Alto — supera el umbral operativo de riesgo."
      : "Moderado, pero suficiente para generar una alerta dado el resto de las señales del caso.",
  });

  // 2. Patrón detectado.
  reasons.push({
    kind: "pattern",
    color: COLOR.red,
    title: `Patrón: ${c.pattern.replace(/_/g, " ")}`,
    detail: PATTERN_DESC[c.pattern],
  });

  // 3. Vecinos de alto riesgo / fraude confirmado.
  const riesgosos = c.neighbors.filter(n => n.is_fraud === 1 || n.gnn_score >= 0.7);
  if (riesgosos.length > 0) {
    const top = riesgosos.slice(0, 3).map(n => `${n.account_id} (${(n.gnn_score * 100).toFixed(0)}%)`);
    reasons.push({
      kind: "network",
      color: COLOR.red,
      title: `Conectada a ${riesgosos.length} cuenta${riesgosos.length > 1 ? "s" : ""} de alto riesgo`,
      detail: `Transaccionó directamente con ${top.join(", ")}${riesgosos.length > 3 ? ` y ${riesgosos.length - 3} más` : ""} — no es el monto lo que la delata, es con quién opera.`,
    });
  }

  // 4. Punto ciego del onboarding: KYC no la habría marcado, el GNN sí.
  if (isBlindSpot(c.risk_score, c.gnn_score)) {
    reasons.push({
      kind: "kyc_blindspot",
      color: COLOR.violet,
      title: `Punto ciego del onboarding — rating KYC ${kycTier(c.risk_score)}`,
      detail: "El perfil declarado al momento de abrir la cuenta no tenía nada de alarmante. Solo la estructura de sus conexiones en la red revela el riesgo.",
    });
  }

  // 5. Screening de sanciones.
  const scr = screeningSummary(c.screening);
  if (scr.kind === "direct") {
    reasons.push({
      kind: "screening_directo",
      color: scr.status === "confirmado" ? COLOR.red : scr.status === "pendiente" ? COLOR.amber : COLOR.blue,
      title: `Coincidencia en lista ${scr.lista}`,
      detail: scr.status === "confirmado"
        ? "El match fue confirmado por un Oficial de Cumplimiento — no es un falso positivo."
        : scr.status === "pendiente"
        ? "Match pendiente de revisión — todavía no se descartó como falso positivo."
        : "Match descartado tras revisión (falso positivo), pero quedó registrado en el historial de screening.",
    });
  } else if (scr.kind === "indirect") {
    reasons.push({
      kind: "screening_indirecto",
      color: COLOR.violet,
      title: "Exposición indirecta a una cuenta sancionada",
      detail: "La cuenta en sí no figura en ninguna lista, pero transaccionó directamente con una que sí — un salto de distancia.",
    });
  }

  // 6. PEP.
  if (c.is_pep) {
    reasons.push({
      kind: "pep",
      color: COLOR.amber,
      title: "Titular es Persona Expuesta Políticamente (PEP)",
      detail: "Eleva el perfil de riesgo según normativa UIF, independientemente del resto de las señales.",
    });
  }

  // 7. Empresa de fachada vinculada.
  if (c.empresa?.is_shell) {
    reasons.push({
      kind: "shell",
      color: COLOR.red,
      title: "Vinculada a una empresa de fachada",
      detail: `${c.empresa.razon_social} (${c.empresa.pais_constitucion}, sector ${c.empresa.sector}) — sin actividad económica real aparente.`,
    });
  }

  // 8. Volumen/actividad transaccional concreta.
  if (c.recent_transactions.length > 0) {
    const total = c.recent_transactions.reduce((a, t) => a + t.amount, 0);
    reasons.push({
      kind: "activity",
      color: COLOR.blue,
      title: `${c.recent_transactions.length} transacciones por $${Math.round(total).toLocaleString("es-AR")}`,
      detail: "Volumen y frecuencia analizados en la ventana de detección — ver el detalle en la pestaña Transacciones.",
    });
  }

  return reasons;
}
