import { describe, it, expect } from "vitest";
import { kycTier, isBlindSpot } from "@/lib/kyc";

describe("kycTier", () => {
  it("clasifica en tramos", () => {
    expect(kycTier(0.05)).toBe("Bajo");
    expect(kycTier(0.20)).toBe("Medio");
    expect(kycTier(0.50)).toBe("Alto");
  });
});

describe("isBlindSpot", () => {
  it("detecta punto ciego: KYC no-Alto pero GNN alto", () => {
    expect(isBlindSpot(0.05, 0.9)).toBe(true);
  });
  it("no es punto ciego si el KYC ya es Alto", () => {
    expect(isBlindSpot(0.5, 0.9)).toBe(false);
  });
  it("no es punto ciego si el GNN es bajo", () => {
    expect(isBlindSpot(0.05, 0.2)).toBe(false);
  });
});
