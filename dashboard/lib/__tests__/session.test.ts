import { describe, it, expect } from "vitest";
import { can, roleLabel } from "@/lib/session";

describe("RBAC · can()", () => {
  it("el analista opera pero no aprueba ROS (cuatro ojos)", () => {
    expect(can("analista", "caso.desestimar")).toBe(true);
    expect(can("analista", "ros.enviar_revision")).toBe(true);
    expect(can("analista", "ros.aprobar")).toBe(false);
  });
  it("el oficial de cumplimiento sí aprueba ROS", () => {
    expect(can("oficial", "ros.aprobar")).toBe(true);
  });
  it("auditoría es sólo lectura", () => {
    expect(can("auditor", "auditoria.ver")).toBe(true);
    expect(can("auditor", "caso.tomar")).toBe(false);
    expect(can("auditor", "ros.aprobar")).toBe(false);
  });
});

describe("roleLabel", () => {
  it("devuelve etiquetas legibles", () => {
    expect(roleLabel("oficial")).toMatch(/Cumplimiento/);
  });
});
