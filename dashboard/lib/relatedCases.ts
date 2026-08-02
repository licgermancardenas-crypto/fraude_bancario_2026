/**
 * Casos vinculados — otros casos que comparten una contraparte con el actual.
 * Es lo que hace un investigador AML real: agrupar alertas que tocan la misma
 * cuenta (mula, perpetrador, sociedad pantalla) para ver la red completa en
 * lugar de casos aislados. Se calcula client-side sobre cases.json.
 */
import type { Case } from "@/lib/types";

export interface RelatedCase {
  case: Case;
  sharedAccount: string;
}

/** Cuentas con las que interactúa un caso (vecinos + cadena de trazabilidad). */
function counterparties(c: Case): Set<string> {
  const s = new Set<string>();
  for (const n of c.neighbors ?? []) s.add(n.account_id);
  const tr = c.traceability;
  if (tr) {
    for (const h of tr.upstream ?? []) { s.add(h.from); s.add(h.to); }
    for (const h of tr.downstream ?? []) s.add(h.to);
  }
  s.delete(c.account_id);
  return s;
}

export function relatedCases(current: Case, all: Case[], limit = 8): RelatedCase[] {
  const mine = counterparties(current);
  mine.add(current.account_id); // casos que tienen a ESTA cuenta como contraparte
  const out: RelatedCase[] = [];
  for (const other of all) {
    if (other.case_id === current.case_id) continue;
    const theirs = counterparties(other);
    theirs.add(other.account_id);
    const shared = Array.from(mine).find(a => theirs.has(a)) ?? null;
    if (shared) out.push({ case: other, sharedAccount: shared });
    if (out.length >= limit) break;
  }
  return out;
}
