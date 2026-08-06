/**
 * Revisión periódica de CDD (KYC continuo) como TAREA, no como estado. Registra
 * quién revisó, cuándo, qué verificó (checklist), la decisión y recalcula la
 * próxima revisión según la cadencia por riesgo. Persistencia en localStorage
 * (en producción sería server-side con trazabilidad inmutable).
 */
export interface CddReview {
  decision: string;
  nota?: string;
  revisor: string;
  fecha: string;            // ISO
  proxima_revision: string; // YYYY-MM-DD recalculada
  checklist: string[];
}

export const DECISIONES = [
  "Mantener la calificación de riesgo",
  "Recalificar el riesgo (ver nota)",
  "Escalar a Debida Diligencia Reforzada (EDD)",
  "Cerrar la relación comercial",
];

export const CHECKLIST = [
  "Identidad verificada / documentación vigente",
  "Screening de sanciones re-ejecutado",
  "Origen de fondos consistente con el perfil",
  "Actividad real consistente con la declarada",
  "Sin operatoria inusual en el período",
];

/** Meses de cadencia entre revisiones según el nivel de riesgo. */
export function cadenceMonths(nivel: string): number {
  return nivel === "Alto" ? 6 : nivel === "Medio" ? 12 : 24;
}

export function nextReviewDate(nivel: string, from = new Date()): string {
  const d = new Date(from);
  d.setMonth(d.getMonth() + cadenceMonths(nivel));
  return d.toISOString().slice(0, 10);
}

const KEY = "phantom_cdd_reviews";

export function getReviews(): Record<string, CddReview[]> {
  if (typeof window === "undefined") return {};
  try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch { return {}; }
}

export function getReviewsFor(accountId: string): CddReview[] {
  return getReviews()[accountId] ?? [];
}

export function addReview(accountId: string, review: CddReview) {
  const all = getReviews();
  all[accountId] = [review, ...(all[accountId] ?? [])];
  localStorage.setItem(KEY, JSON.stringify(all));
}
