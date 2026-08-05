import { describe, it, expect } from "vitest";
import { daysUntil, rosUrgency } from "@/lib/dates";

describe("daysUntil", () => {
  it("positivo para fechas futuras, negativo para pasadas", () => {
    const future = new Date(Date.now() + 10 * 86400_000).toISOString().slice(0, 10);
    const past = new Date(Date.now() - 10 * 86400_000).toISOString().slice(0, 10);
    expect(daysUntil(future)).toBeGreaterThan(0);
    expect(daysUntil(past)).toBeLessThan(0);
  });
});

describe("rosUrgency", () => {
  it("vencido → rojo con etiqueta de vencimiento", () => {
    const u = rosUrgency(-5);
    expect(u.text).toBe("#EF4444");
    expect(u.label.toLowerCase()).toContain("vencido");
  });
  it("con holgura → verde", () => {
    expect(rosUrgency(100).text).toBe("#22C55E");
  });
});
