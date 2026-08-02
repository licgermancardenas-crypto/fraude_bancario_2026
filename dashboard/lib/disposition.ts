/**
 * Disposición del caso — el registro de *por qué* se cerró un caso. En una
 * plataforma AML real, desestimar una alerta sin reportarla exige justificar el
 * motivo (el regulador audita los falsos positivos). Guardamos motivo + nota +
 * analista + fecha en localStorage, análogo a lib/caseStatus.
 */
import type { CaseStatus } from "@/lib/types";

export interface Disposition {
  estado: CaseStatus;        // el estado de resolución (desestimado / sar_enviado)
  motivo: string;
  nota?: string;
  analista: string;
  timestamp: string;         // ISO
}

/** Motivos típicos para desestimar una alerta sin elevar a ROS. */
export const MOTIVOS_DESESTIMAR = [
  "Operatoria consistente con el perfil del cliente",
  "Screening de sanciones descartado tras revisión",
  "Fondos de origen lícito debidamente acreditado",
  "Falso positivo del modelo — sin indicios de lavado",
  "Caso duplicado / ya cubierto por otro reporte",
  "Sin mérito suficiente para un ROS",
];

const KEY = "phantom_case_dispositions";

export function getStoredDispositions(): Record<string, Disposition> {
  if (typeof window === "undefined") return {};
  try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch { return {}; }
}

export function getDisposition(caseId: string): Disposition | null {
  return getStoredDispositions()[caseId] ?? null;
}

export function setDisposition(caseId: string, disp: Disposition) {
  const all = getStoredDispositions();
  all[caseId] = disp;
  localStorage.setItem(KEY, JSON.stringify(all));
}

export function clearDisposition(caseId: string) {
  const all = getStoredDispositions();
  delete all[caseId];
  localStorage.setItem(KEY, JSON.stringify(all));
}
