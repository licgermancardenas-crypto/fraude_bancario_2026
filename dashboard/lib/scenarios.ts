/**
 * Gestión de escenarios ALD — tipos, lectura del backtest y flujo de cambio
 * de umbrales con control de cuatro ojos.
 *
 * En una plataforma ALD real, cambiar el umbral de un escenario NO es editar un
 * número: es un cambio de control que exige justificación, evidencia del impacto
 * (backtest), aprobación de un segundo par de ojos y registro de auditoría. Este
 * módulo modela ese circuito: el analista propone un factor de calibración sobre
 * la curva backtesteada, el oficial de cumplimiento aprueba o rechaza, y nadie
 * aprueba su propia propuesta.
 *
 * NOTA: las propuestas viven en localStorage y NO se aplican al motor (que corre
 * en el pipeline Python con los umbrales de config.yaml). Es la demostración del
 * proceso de gobierno de escenarios, no su enforcement productivo.
 */

export interface ScenarioMetrics {
  disparos: number;
  tp: number;
  fp: number;
  precision: number;
  recall: number;
  tasa_fp: number;
  lift: number;
}

export interface CalibrationPoint extends ScenarioMetrics {
  factor: number;
  valor: string;
}

export interface Calibration {
  parametro: string;
  label: string;
  unidad: string;
  segmentado: boolean;
  valor_actual: string;
  direccion: "menos_alertas" | "mas_alertas";
  puntos: CalibrationPoint[];
}

export interface ScenarioThreshold {
  clave: string;
  label: string;
  valor: number | Record<string, number>;
  segmentado: boolean;
}

export type Severidad = "alta" | "media" | "baja";

export interface Scenario {
  id: string;
  nombre: string;
  descripcion: string;
  cita: string;
  severidad: Severidad;
  estado: string;
  calibrable: boolean;
  fuente: string;
  puntos_severidad: number;
  umbrales: ScenarioThreshold[];
  metricas: ScenarioMetrics;
  por_tipo: Record<string, ScenarioMetrics>;
  aporte_exclusivo: number;
  calibracion: Calibration | null;
}

export interface Complementarity {
  corte_gnn: number;
  fraude_total: number;
  ambos: number;
  solo_reglas: number;
  solo_gnn: number;
  ninguno: number;
  nota: string;
}

export interface ScenariosData {
  generated_at: string;
  poblacion: { cuentas: number; fraude: number; legitimas: number; tasa_base: number };
  resumen: ScenarioMetrics & { escenarios: number; activos: number };
  complementariedad: Complementarity;
  factores_calibracion: number[];
  escenarios: Scenario[];
}

export const SEVERITY_STYLE: Record<Severidad, { label: string; color: string; bg: string }> = {
  alta: { label: "Alta", color: "#EF4444", bg: "rgba(239,68,68,0.14)" },
  media: { label: "Media", color: "#F59E0B", bg: "rgba(245,158,11,0.14)" },
  baja: { label: "Baja", color: "#7AA2FF", bg: "rgba(46,107,255,0.14)" },
};

/** Punto de la curva correspondiente al umbral vigente (factor 1). */
export function currentPoint(cal: Calibration): CalibrationPoint {
  return cal.puntos.find(p => p.factor === 1) ?? cal.puntos[0];
}

export function pointAt(cal: Calibration, factor: number): CalibrationPoint {
  return cal.puntos.find(p => p.factor === factor) ?? currentPoint(cal);
}

export interface CalibrationImpact {
  desde: CalibrationPoint;
  hasta: CalibrationPoint;
  dAlertas: number;
  dPrecision: number;
  dRecall: number;
  dFalsosPositivos: number;
  /** Fraudes que se dejarían de detectar (positivo = pérdida de cobertura). */
  perdidaCobertura: number;
}

/** Impacto backtesteado de mover el umbral del punto vigente al factor elegido. */
export function calibrationImpact(cal: Calibration, factor: number): CalibrationImpact {
  const desde = currentPoint(cal);
  const hasta = pointAt(cal, factor);
  return {
    desde,
    hasta,
    dAlertas: hasta.disparos - desde.disparos,
    dPrecision: hasta.precision - desde.precision,
    dRecall: hasta.recall - desde.recall,
    dFalsosPositivos: hasta.fp - desde.fp,
    perdidaCobertura: desde.tp - hasta.tp,
  };
}

// ── propuestas de recalibración (cuatro ojos) ────────────────────────────────

export type ProposalEstado = "pendiente" | "aprobada" | "rechazada";

export interface CalibrationProposal {
  id: string;
  scenario_id: string;
  scenario_nombre: string;
  parametro: string;
  factor: number;
  valor_actual: string;
  valor_propuesto: string;
  justificacion: string;
  proponente: string;
  rol: string;
  fecha: string;
  estado: ProposalEstado;
  aprobador?: string;
  fecha_decision?: string;
  comentario?: string;
  impacto: { dAlertas: number; dPrecision: number; dRecall: number; perdidaCobertura: number };
}

const KEY = "phantom_scenario_proposals";

export function getProposals(): CalibrationProposal[] {
  if (typeof window === "undefined") return [];
  try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; }
}

function write(list: CalibrationProposal[]) {
  localStorage.setItem(KEY, JSON.stringify(list));
}

export function saveProposal(p: CalibrationProposal): CalibrationProposal[] {
  const list = [p, ...getProposals()];
  write(list);
  return list;
}

export function decideProposal(
  id: string, estado: Exclude<ProposalEstado, "pendiente">, aprobador: string, comentario: string,
): CalibrationProposal[] {
  const list = getProposals().map(p =>
    p.id === id ? { ...p, estado, aprobador, comentario, fecha_decision: new Date().toISOString() } : p,
  );
  write(list);
  return list;
}

/**
 * Control anti-autoaprobación: quien propuso el cambio no puede aprobarlo,
 * aunque su rol tenga el permiso. Es la esencia del control de cuatro ojos.
 */
export function canApprove(p: CalibrationProposal, aprobador: string, tienePermiso: boolean): boolean {
  return tienePermiso && p.estado === "pendiente" && p.proponente !== aprobador;
}

/** Propuesta pendiente de un escenario, si la hay (sólo una a la vez). */
export function pendingFor(list: CalibrationProposal[], scenarioId: string): CalibrationProposal | undefined {
  return list.find(p => p.scenario_id === scenarioId && p.estado === "pendiente");
}

export const MOTIVOS_CALIBRACION = [
  "Exceso de falsos positivos: la cola supera la capacidad del equipo",
  "Recomendación de la revisión periódica de escenarios",
  "Hallazgo de auditoría interna",
  "Cambio en el perfil transaccional de la cartera",
  "Alineación con el apetito de riesgo aprobado por el Directorio",
];
