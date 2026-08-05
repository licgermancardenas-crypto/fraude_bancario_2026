import type { Case } from "@/lib/types";

/** Construye un Case mínimo válido para tests (campos no usados quedan vacíos). */
export function makeCase(over: Partial<Case> = {}): Case {
  const base = {
    case_id: "CASO-00001", account_id: "ACC0000001", gnn_score: 0, is_fraud: 0,
    alert_date: "2026-03-01", status: "abierto", pattern: "round_tripping",
    is_pep: false, balance: 1000, risk_score: 0.05, account_type: "personal",
    analista_asignado: "Lic. Tester", dias_plazo_ros: 150, vencimiento_ros: "2026-12-01",
    screening: { hit_directo: null, exposicion_indirecta: [] },
    rule_score: 0, rules_fired: [], persona: { nombre_completo: "Test User" },
    empresa: null, neighbors: [], recent_transactions: [],
  };
  return { ...base, ...over } as unknown as Case;
}
