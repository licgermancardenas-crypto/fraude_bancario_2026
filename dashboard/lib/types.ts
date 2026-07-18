export interface KPIs {
  n_accounts: number;
  n_fraud: number;
  pct_fraud: number;
  pr_auc_gnn: number;
  recall_at_p90: number;
  model: string;
  dataset: string;
  client: string;
}

export interface PRCurve {
  model: string;
  pr_auc: number;
  precision: number[];
  recall: number[];
}

export interface ScoreDistribution {
  bin_centers: number[];
  fraud: number[];
  legit: number[];
}

export interface Persona {
  nombre?: string;
  apellido?: string;
  nombre_completo?: string;
  dni?: number;
  cuil?: string;
  fecha_nacimiento?: string;
  edad?: number;
  genero?: string;
  nacionalidad?: string;
  provincia?: string;
  municipio?: string;
  direccion?: string;
  codigo_postal?: string;
  condicion_afip?: string;
  categoria_mono?: string | null;
  actividad_economica?: string;
  ocupacion?: string;
  tipo_cuenta?: string;
  antiguedad_meses?: number;
  sucursal?: string;
  telefono?: string;
  email?: string;
}

export interface RingNode {
  id: string;
  gnn_score: number;
  is_fraud: number;
  balance: number;
  risk_score: number;
  account_type: string;
  nombre_completo?: string;
  ocupacion?: string;
  municipio?: string;
}

export interface RingEdge {
  src: string;
  dst: string;
  amount: number;
}

export interface Ring {
  ring_id: number;
  n_nodes: number;
  total_amount: number;
  avg_score: number;
  nodes: RingNode[];
  edges: RingEdge[];
}

export interface Account extends Persona {
  account_id: string;
  gnn_score: number;
  is_fraud: number;
  balance: number;
  risk_score: number;
  account_type: string;
  degree_in: number;
  degree_out: number;
  total_sent: number;
  total_received: number;
  in_ring: boolean;
}

export interface Empresa {
  empresa_id: string;
  razon_social: string;
  cuit_empresa: string;
  sector: string;
  pais_constitucion: string;
  is_shell: boolean;
}

export type EntityNodeType = "cuenta" | "persona" | "empresa";

export interface EntityNode {
  id: string;
  type: EntityNodeType;
  label: string;
  gnn_score?: number;
  is_fraud?: number;
  is_pep?: boolean;
  is_shell?: boolean;
  balance?: number;
  risk_score?: number;
  account_type?: string;
  nombre_completo?: string;
  ocupacion?: string;
  municipio?: string;
  cuil?: string;
  razon_social?: string;
  cuit_empresa?: string;
  sector?: string;
  pais_constitucion?: string;
}

export interface EntityEdge {
  src: string;
  dst: string;
  type: "es_titular" | "es_director" | "transaccion";
  porcentaje?: number;
  cargo?: string;
  vigente?: boolean;
  amount?: number;
}

export interface EntityGraph {
  nodes: EntityNode[];
  edges: EntityEdge[];
}

export type CaseStatus = "abierto" | "en_revision" | "escalado" | "desestimado" | "sar_enviado";
export type CasePattern = "anillo_lavado" | "estructuracion" | "agregacion_fondos" | "transacciones_inusuales";

export interface CaseTransaction {
  src: string;
  dst: string;
  amount: number;
  timestamp: number;
  direction: "entrada" | "salida";
  is_fraud: number;
}

export interface CaseNeighbor {
  account_id: string;
  gnn_score: number;
  is_fraud: number;
  direction: "entrada" | "salida";
  amount: number;
}

export interface CaseNote {
  author: string;
  text: string;
  timestamp: string;
}

export interface Case {
  case_id: string;
  account_id: string;
  gnn_score: number;
  is_fraud: number;
  alert_date: string;
  status: CaseStatus;
  pattern: CasePattern;
  is_pep: boolean;
  balance: number;
  risk_score: number;
  account_type: string;
  persona: Persona;
  empresa: Empresa | null;
  neighbors: CaseNeighbor[];
  recent_transactions: CaseTransaction[];
}

export interface SARDraft {
  case_id: string;
  fecha_reporte: string;
  sujeto_obligado: string;
  cuit_sujeto: string;
  oficial_cumplimiento: string;
  reportado_nombre: string;
  reportado_cuil: string;
  reportado_tipo: string;
  cuentas_involucradas: string[];
  monto_total: number;
  fecha_desde: string;
  fecha_hasta: string;
  patron_detectado: string;
  descripcion: string;
  estado_sar: "borrador" | "revision" | "enviado";
}
