export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://phantom-rcs9.onrender.com";

export interface HealthResponse {
  status: string;
  timestamp: string;
  started_at: string;
  accounts_indexed: number;
  cases_indexed: number;
  placement_indexed: number;
  numpy_scores_loaded: boolean;
}

export interface ScoreResult {
  account_id: string;
  found: boolean;
  gnn_score: number | null;
  risk_level: string;
  placement_score_norm?: number | null;
  in_ring?: boolean;
}

export interface ScoreResponse {
  model: string;
  model_version: string;
  scored_at: string;
  requested: number;
  found: number;
  not_found: number;
  results: ScoreResult[];
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const res = await fetch(`${API_URL}/health`, { signal });
  if (!res.ok) throw new Error(`API respondió ${res.status}`);
  return res.json();
}

export async function scoreAccounts(accountIds: string[]): Promise<ScoreResponse> {
  const res = await fetch(`${API_URL}/accounts/score`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ account_ids: accountIds, model_version: "graphsage-v1" }),
  });
  if (!res.ok) throw new Error(`API respondió ${res.status}`);
  return res.json();
}
