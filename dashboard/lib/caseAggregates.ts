import type { Case, CasePattern } from "@/lib/types";
import { PATTERN_LABELS, PATTERN_COLORS } from "@/lib/patterns";

const MONTH_LABELS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

export interface PatternCount {
  pattern: CasePattern;
  label: string;
  color: string;
  count: number;
}

export function casesByPattern(cases: Case[]): PatternCount[] {
  const counts = new Map<CasePattern, number>();
  for (const c of cases) counts.set(c.pattern, (counts.get(c.pattern) ?? 0) + 1);
  return (Object.keys(PATTERN_LABELS) as CasePattern[])
    .map(pattern => ({
      pattern,
      label: PATTERN_LABELS[pattern],
      color: PATTERN_COLORS[pattern],
      count: counts.get(pattern) ?? 0,
    }))
    .filter(p => p.count > 0);
}

export interface MonthCount {
  key: string;   // YYYY-MM
  label: string; // "ene 26"
  count: number;
}

export function casesByMonth(cases: Case[]): MonthCount[] {
  const counts = new Map<string, number>();
  for (const c of cases) {
    const d = new Date(`${c.alert_date}T00:00:00`);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, count]) => {
      const [year, month] = key.split("-");
      const label = `${MONTH_LABELS[Number(month) - 1]} ${year.slice(2)}`;
      return { key, label, count };
    });
}
