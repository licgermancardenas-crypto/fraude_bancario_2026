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
