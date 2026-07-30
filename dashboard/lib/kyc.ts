/**
 * Rating KYC — perfil de riesgo estático asignado en el onboarding (alta de
 * cuenta), a partir de variables declarativas del cliente. Es el mismo campo
 * `risk_score` del dataset (ver src/generate.py), que la evaluación cuantitativa
 * (Cohen d=0.055, ver /app/metodologia) mostró que casi no distingue fraude de
 * legítimo — a diferencia del score GNN, que sí lo hace por estructura de red.
 * Mostrar ambos números lado a lado es el punto: el rating KYC es estático y
 * ciego a la red; el score GNN es dinámico y se recalcula con cada transacción.
 */
export type KycTier = "Bajo" | "Medio" | "Alto";

export function kycTier(riskScore: number): KycTier {
  if (riskScore < 0.13) return "Bajo";
  if (riskScore < 0.30) return "Medio";
  return "Alto";
}

export const KYC_TIER_STYLE: Record<KycTier, { bg: string; text: string }> = {
  Bajo:  { bg: "rgba(90,100,120,0.15)", text: "#8A93A6" },
  Medio: { bg: "rgba(124,58,237,0.15)", text: "#A78BFA" },
  Alto:  { bg: "rgba(124,58,237,0.28)", text: "#C4B5FD" },
};

/** El caso interesante: onboarding lo vio "tranquilo" pero el comportamiento en red dice lo contrario. */
export function isBlindSpot(riskScore: number, gnnScore: number): boolean {
  return kycTier(riskScore) !== "Alto" && gnnScore >= 0.7;
}
