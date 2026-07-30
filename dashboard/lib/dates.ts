import type { CaseStatus } from "@/lib/types";

export const RESOLVED_STATUSES: CaseStatus[] = ["desestimado", "sar_enviado"];

export function daysUntil(dateStr: string): number {
  const ms = new Date(`${dateStr}T00:00:00`).getTime() - Date.now();
  return Math.ceil(ms / (1000 * 60 * 60 * 24));
}

export function rosUrgency(days: number): { bg: string; text: string; label: string } {
  if (days < 0) return { bg: "rgba(239,68,68,0.15)", text: "#EF4444", label: `Vencido hace ${Math.abs(days)}d` };
  if (days <= 15) return { bg: "rgba(239,68,68,0.15)", text: "#EF4444", label: `${days}d restantes` };
  if (days <= 45) return { bg: "rgba(245,158,11,0.15)", text: "#F59E0B", label: `${days}d restantes` };
  return { bg: "rgba(34,197,94,0.15)", text: "#22C55E", label: `${days}d restantes` };
}
