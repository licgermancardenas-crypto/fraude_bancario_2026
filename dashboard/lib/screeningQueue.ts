/**
 * Workbench de screening de sanciones. El analista dispone cada coincidencia:
 * confirmarla (verdadero positivo → reportar/bloquear) o descartarla (homónimo /
 * baja confianza). Persistencia en localStorage. El screening real es continuo:
 * se re-ejecuta periódicamente contra las listas actualizadas.
 */
export type ScreeningEstado = "pendiente" | "confirmado" | "descartado";

export interface ScreeningDisposition {
  estado: ScreeningEstado;
  motivo: string;
  revisor: string;
  fecha: string;
}

export const MOTIVOS_DESCARTAR = [
  "Homónimo — no es la persona/entidad designada",
  "Datos identificatorios no coinciden (fecha nac. / documento)",
  "Coincidencia de baja confianza tras revisión manual",
  "Verificado contra la fuente oficial de la lista",
];
export const MOTIVOS_CONFIRMAR = [
  "Coincidencia verificada con la designación",
  "Amerita reporte a la UIF y bloqueo de fondos",
];

export const LISTA_STYLE: Record<string, { bg: string; text: string }> = {
  ONU: { bg: "rgba(239,68,68,0.15)", text: "#EF4444" },
  OFAC: { bg: "rgba(245,158,11,0.15)", text: "#F59E0B" },
  REPET: { bg: "rgba(167,139,250,0.15)", text: "#A78BFA" },
};
export const ESTADO_STYLE: Record<ScreeningEstado, { label: string; color: string }> = {
  pendiente: { label: "Pendiente", color: "#F59E0B" },
  confirmado: { label: "Confirmada", color: "#EF4444" },
  descartado: { label: "Descartada (FP)", color: "#5A6478" },
};

const KEY = "phantom_screening_dispositions";
const RESCREEN_KEY = "phantom_screening_last";

export function getDispositions(): Record<string, ScreeningDisposition> {
  if (typeof window === "undefined") return {};
  try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch { return {}; }
}
export function setDisposition(hitId: string, d: ScreeningDisposition) {
  const all = getDispositions();
  all[hitId] = d;
  localStorage.setItem(KEY, JSON.stringify(all));
}

export function getLastRescreen(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(RESCREEN_KEY);
}
export function setRescreenNow(): string {
  const now = new Date().toISOString();
  localStorage.setItem(RESCREEN_KEY, now);
  return now;
}
