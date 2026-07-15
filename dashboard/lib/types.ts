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
  points: Array<{ precision: number; recall: number }>;
}

export interface ScoreDistribution {
  bin_centers: number[];
  fraud: number[];
  legit: number[];
}

export interface RingNode {
  id: string;
  gnn_score: number;
  is_fraud: number;
  balance: number;
  risk_score: number;
  account_type: string;
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

export interface Account {
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
