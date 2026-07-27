import type { CasePattern } from "@/lib/types";

export const PATTERN_LABELS: Record<CasePattern, string> = {
  anillo_lavado:           "Anillo de lavado",
  estructuracion:          "Estructuración",
  agregacion_fondos:       "Agregación de fondos",
  transacciones_inusuales: "Transacciones inusuales",
};

/** Reutiliza acentos ya establecidos en el resto del dashboard; evita
 *  #2E6BFF/#7AA2FF, reservados como acento primario de marca/modelo. */
export const PATTERN_COLORS: Record<CasePattern, string> = {
  anillo_lavado:           "#EF4444",
  estructuracion:          "#F59E0B",
  agregacion_fondos:       "#A78BFA",
  transacciones_inusuales: "#34D399",
};
