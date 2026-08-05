import { describe, it, expect } from "vitest";
import { computeTriage } from "@/lib/triage";
import { makeCase } from "./_fixtures";

describe("computeTriage", () => {
  it("caso benigno → prioridad 0 / Baja", () => {
    const t = computeTriage(makeCase());
    expect(t.score).toBe(0);
    expect(t.level).toBe("Baja");
  });

  it("caso de alta señal → Crítica y score alto", () => {
    const t = computeTriage(makeCase({
      gnn_score: 1, rule_score: 100, is_pep: true, risk_score: 0.05,
      rules_fired: [{ id: "R08" } as any],
      screening: { hit_directo: { estado: "confirmado", lista: "REPET" } as any, exposicion_indirecta: [] },
    }));
    expect(t.score).toBeGreaterThanOrEqual(80);
    expect(t.level).toBe("Crítica");
  });

  it("el score nunca supera 100 y la suma de componentes cuadra", () => {
    const t = computeTriage(makeCase({
      gnn_score: 1, rule_score: 100, is_pep: true,
      screening: { hit_directo: { estado: "confirmado", lista: "OFAC" } as any, exposicion_indirecta: [] },
    }));
    expect(t.score).toBeLessThanOrEqual(100);
    const sum = t.components.reduce((a, c) => a + c.points, 0);
    expect(t.score).toBe(Math.min(100, sum));
  });
});
