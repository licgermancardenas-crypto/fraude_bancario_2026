/**
 * Onboarding / alta de cliente (CDD de entrada). Al dar de alta un cliente se
 * evalúa su riesgo por factores, se corre screening y se decide: aprobar,
 * aprobar con Debida Diligencia Reforzada (EDD) o rechazar. Espejo client-side
 * de la lógica de src/kyc_profiles.py.
 */
export const ACTIVIDADES = [
  "Empleado/a en relación de dependencia",
  "Comercio minorista",
  "Servicios profesionales independientes",
  "Jubilado/a / clase pasiva",
  "Construcción",
  "Servicios de importación y exportación",
  "Servicios de restaurante y catering",
  "Comercio al por mayor de alimentos y bebidas",
  "Actividades inmobiliarias por cuenta propia",
  "Cambio de moneda / servicios financieros",
];

export const HIGH_RISK_ACT = new Set([
  "Servicios de importación y exportación",
  "Servicios de restaurante y catering",
  "Comercio al por mayor de alimentos y bebidas",
  "Actividades inmobiliarias por cuenta propia",
  "Cambio de moneda / servicios financieros",
]);

export interface OnbInput {
  nombre: string; dni: string; tipoPersona: string;
  actividad: string; accountType: string; pep: boolean;
}
export interface OnbFactor { factor: string; nivel: "alto" | "medio" | "bajo"; }
export interface OnbAssessment { nivel: "Alto" | "Medio" | "Bajo"; puntos: number; factores: OnbFactor[]; edd: boolean; screeningHit: boolean; }

/** Screening determinístico por DNI (~5% coincidencia; ilustrativo). */
export function screeningResult(dni: string): boolean {
  const n = parseInt(dni.replace(/\D/g, "") || "0", 10);
  return n > 0 && n % 19 === 0;
}

export function assessOnboarding(i: OnbInput): OnbAssessment {
  const factores: OnbFactor[] = [];
  let pts = 0;
  const screeningHit = screeningResult(i.dni);
  if (i.pep) { factores.push({ factor: "Persona Expuesta Políticamente (PEP)", nivel: "alto" }); pts += 3; }
  if (screeningHit) { factores.push({ factor: "Coincidencia en lista de sanciones", nivel: "alto" }); pts += 3; }
  if (HIGH_RISK_ACT.has(i.actividad)) { factores.push({ factor: `Actividad de alto riesgo: ${i.actividad}`, nivel: "medio" }); pts += 1; }
  if (i.accountType !== "personal") { factores.push({ factor: "Actividad intensiva en efectivo", nivel: "bajo" }); pts += 0.5; }
  const nivel = pts >= 3 ? "Alto" : pts >= 1 ? "Medio" : "Bajo";
  const edd = nivel === "Alto" || i.pep || screeningHit;
  return { nivel, puntos: pts, factores, edd, screeningHit };
}

export interface OnbRecord extends OnbInput {
  id: string; fecha: string; nivel: string; edd: boolean; decision: string; analista: string;
}

const KEY = "phantom_onboardings";

export function getOnboardings(): OnbRecord[] {
  if (typeof window === "undefined") return [];
  try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; }
}
export function addOnboarding(rec: OnbRecord) {
  localStorage.setItem(KEY, JSON.stringify([rec, ...getOnboardings()].slice(0, 50)));
}
