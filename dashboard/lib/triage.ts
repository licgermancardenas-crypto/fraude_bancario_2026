/**
 * Score de triage compuesto — una única prioridad de investigación (0-100) que
 * combina las señales sueltas que ya calcula la plataforma: señal de red (GNN),
 * reglas AML deterministas, screening de sanciones, PEP y rating KYC. Replica
 * lo que hace un motor de priorización de casos real (Actimize/SAS): en vez de
 * mostrar 5 números aislados, un score con su desglose ("por qué está arriba
 * en la cola"). Es capa de presentación: no cambia el modelo ni el dataset.
 */
import type { Case } from "@/lib/types";
import { kycTier, isBlindSpot } from "@/lib/kyc";

export type TriageLevel = "Crítica" | "Alta" | "Media" | "Baja";

export interface TriageComponent {
  key: string;
  label: string;
  points: number;
  max: number;
  detail: string;
  color: string;
}

export interface Triage {
  score: number;
  level: TriageLevel;
  color: string;
  components: TriageComponent[];
}

const COL = {
  gnn: "#2E6BFF",
  rules: "#F59E0B",
  screening: "#EF4444",
  pep: "#A78BFA",
  kyc: "#2DD4BF",
};

function screeningPoints(c: Case): { pts: number; detail: string } {
  const s = c.screening;
  if (s.hit_directo) {
    const st = s.hit_directo.estado;
    const pts = st === "confirmado" ? 15 : st === "pendiente" ? 11 : 4;
    return { pts, detail: `Hit directo ${s.hit_directo.lista} (${st})` };
  }
  const ind = s.exposicion_indirecta;
  if (ind.length > 0) {
    const conf = ind.some(h => h.estado === "confirmado");
    const pend = ind.some(h => h.estado === "pendiente");
    const pts = conf ? 12 : pend ? 9 : 5;
    return { pts, detail: `Exposición indirecta a lista (${ind.length})` };
  }
  return { pts: 0, detail: "Sin coincidencias" };
}

function kycPoints(c: Case): { pts: number; detail: string } {
  if (isBlindSpot(c.risk_score, c.gnn_score))
    return { pts: 10, detail: "Punto ciego del onboarding" };
  const tier = kycTier(c.risk_score);
  const pts = tier === "Alto" ? 6 : tier === "Medio" ? 3 : 0;
  return { pts, detail: `Rating ${tier}` };
}

function levelOf(score: number): { level: TriageLevel; color: string } {
  if (score >= 80) return { level: "Crítica", color: "#EF4444" };
  if (score >= 60) return { level: "Alta", color: "#F59E0B" };
  if (score >= 40) return { level: "Media", color: "#7AA2FF" };
  return { level: "Baja", color: "#5A6478" };
}

export function computeTriage(c: Case): Triage {
  const gnnPts = Math.round(c.gnn_score * 45);
  const rulePts = Math.round((c.rule_score / 100) * 25);
  const scr = screeningPoints(c);
  const pepPts = c.is_pep ? 5 : 0;
  const kyc = kycPoints(c);

  const components: TriageComponent[] = [
    { key: "gnn", label: "Señal de red (GNN)", points: gnnPts, max: 45,
      detail: `Score ${(c.gnn_score * 100).toFixed(0)}%`, color: COL.gnn },
    { key: "rules", label: "Reglas AML", points: rulePts, max: 25,
      detail: `${c.rule_score}/100 · ${(c.rules_fired ?? []).length} disparadas`, color: COL.rules },
    { key: "screening", label: "Screening sanciones", points: scr.pts, max: 15,
      detail: scr.detail, color: COL.screening },
    { key: "pep", label: "Persona Expuesta (PEP)", points: pepPts, max: 5,
      detail: c.is_pep ? "Cliente marcado como PEP" : "No", color: COL.pep },
    { key: "kyc", label: "Rating KYC", points: kyc.pts, max: 10,
      detail: kyc.detail, color: COL.kyc },
  ];

  const score = Math.min(100, components.reduce((a, x) => a + x.points, 0));
  const { level, color } = levelOf(score);
  return { score, level, color, components };
}
