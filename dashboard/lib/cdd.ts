/** Tipos y helpers del legajo del cliente (Customer 360 / CDD). */
export type RiesgoNivel = "Alto" | "Medio" | "Bajo";

export interface CddFactor { factor: string; nivel: "alto" | "medio" | "bajo"; }
export interface CddDoc { tipo: string; estado: string; }

export interface KycProfile {
  account_id: string;
  persona: Record<string, string>;
  cuentas: { account_id: string; tipo: string; account_type: string; balance: number; gnn_score: number; is_fraud: number }[];
  pep: boolean;
  pep_info: { categoria: string; cargo: string; pais: string } | null;
  screening: {
    hit_directo: { lista: string; estado: string; nombre: string; score_match: number } | null;
    exposicion_indirecta: { account_id: string; lista: string; estado: string; direction: string }[];
  };
  cdd: {
    riesgo_nivel: RiesgoNivel;
    riesgo_score: number;
    factores: CddFactor[];
    kyc_onboarding: string;
    fecha_alta: string;
    ultima_revision: string;
    proxima_revision: string;
    revision_vencida: boolean;
    edd_requerida: boolean;
    edd_motivos: string[];
    verificacion_identidad: string;
    documentos: CddDoc[];
  };
  alertas: { ref: string; fecha: string; patron: string; score: number; estado: string }[];
}

export const RIESGO_STYLE: Record<RiesgoNivel, { bg: string; text: string }> = {
  Alto:  { bg: "rgba(239,68,68,0.15)",  text: "#EF4444" },
  Medio: { bg: "rgba(245,158,11,0.15)", text: "#F59E0B" },
  Bajo:  { bg: "rgba(34,197,94,0.15)",  text: "#22C55E" },
};

export function docEstadoColor(estado: string): string {
  if (estado.startsWith("Verificado")) return "#22C55E";
  if (estado.startsWith("Requerida")) return "#EF4444";
  return "#F59E0B"; // Pendiente
}
