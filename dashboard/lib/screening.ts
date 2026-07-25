import type { Screening, ScreeningStatus } from "@/lib/types";

export const SCREENING_STATUS_STYLE: Record<ScreeningStatus, { bg: string; text: string; label: string }> = {
  confirmado: { bg: "rgba(239,68,68,0.15)",  text: "#EF4444", label: "Confirmado" },
  pendiente:  { bg: "rgba(245,158,11,0.15)", text: "#F59E0B", label: "Pendiente de revisión" },
  descartado: { bg: "rgba(90,100,120,0.15)", text: "#8A93A6", label: "Descartado (falso positivo)" },
};

export type ScreeningSummary =
  | { kind: "none" }
  | { kind: "direct"; status: ScreeningStatus; lista: string }
  | { kind: "indirect" };

export function screeningSummary(s: Screening): ScreeningSummary {
  if (s.hit_directo) return { kind: "direct", status: s.hit_directo.estado, lista: s.hit_directo.lista };
  if (s.exposicion_indirecta.length > 0) return { kind: "indirect" };
  return { kind: "none" };
}
