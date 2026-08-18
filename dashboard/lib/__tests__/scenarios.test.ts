import { describe, it, expect } from "vitest";
import {
  calibrationImpact, currentPoint, pointAt, canApprove, pendingFor,
  type Calibration, type CalibrationProposal,
} from "@/lib/scenarios";

const cal: Calibration = {
  parametro: "fanin_degree",
  label: "Grado de entrada mínimo",
  unidad: "contrapartes",
  segmentado: true,
  valor_actual: "12 / 40 / 70",
  direccion: "menos_alertas",
  puntos: [
    { factor: 0.5, valor: "6 / 20 / 35", disparos: 3402, tp: 683, fp: 2719, precision: 0.201, recall: 0.319, tasa_fp: 0.037, lift: 7 },
    { factor: 1.0, valor: "12 / 40 / 70", disparos: 291, tp: 93, fp: 198, precision: 0.32, recall: 0.043, tasa_fp: 0.003, lift: 11.2 },
    { factor: 1.5, valor: "18 / 60 / 105", disparos: 29, tp: 28, fp: 1, precision: 0.966, recall: 0.013, tasa_fp: 0.0, lift: 33.9 },
  ],
};

const proposal = (over: Partial<CalibrationProposal> = {}): CalibrationProposal => ({
  id: "PROP-1", scenario_id: "R05", scenario_nombre: "Concentración de fondos",
  parametro: "Grado de entrada mínimo", factor: 1.5,
  valor_actual: "12 / 40 / 70", valor_propuesto: "18 / 60 / 105",
  justificacion: "Exceso de falsos positivos", proponente: "Lic. Tomás Ferreyra",
  rol: "analista", fecha: "2026-08-18T10:00:00Z", estado: "pendiente",
  impacto: { dAlertas: -262, dPrecision: 0.646, dRecall: -0.03, perdidaCobertura: 65 },
  ...over,
});

describe("currentPoint / pointAt", () => {
  it("el punto vigente es el de factor 1", () => {
    expect(currentPoint(cal).valor).toBe("12 / 40 / 70");
  });
  it("un factor inexistente cae al punto vigente", () => {
    expect(pointAt(cal, 99).factor).toBe(1.0);
  });
});

describe("calibrationImpact", () => {
  it("apretar el umbral baja alertas y sube precisión, pero cuesta cobertura", () => {
    const i = calibrationImpact(cal, 1.5);
    expect(i.dAlertas).toBe(-262);
    expect(i.dPrecision).toBeCloseTo(0.646, 3);
    expect(i.dFalsosPositivos).toBe(-197);
    expect(i.perdidaCobertura).toBe(65); // 93 - 28 fraudes que se dejan de ver
  });

  it("aflojar el umbral gana cobertura a costa de falsos positivos", () => {
    const i = calibrationImpact(cal, 0.5);
    expect(i.dAlertas).toBe(3111);
    expect(i.perdidaCobertura).toBe(-590); // negativo = se detecta MÁS fraude
    expect(i.dFalsosPositivos).toBe(2521);
  });

  it("el punto vigente no mueve nada", () => {
    const i = calibrationImpact(cal, 1.0);
    expect(i.dAlertas).toBe(0);
    expect(i.perdidaCobertura).toBe(0);
  });
});

describe("canApprove · control de cuatro ojos", () => {
  it("nadie aprueba su propia propuesta, aunque tenga el permiso", () => {
    expect(canApprove(proposal(), "Lic. Tomás Ferreyra", true)).toBe(false);
  });
  it("un segundo par de ojos con permiso sí aprueba", () => {
    expect(canApprove(proposal(), "Lic. María González", true)).toBe(true);
  });
  it("sin permiso no se aprueba", () => {
    expect(canApprove(proposal(), "Cra. Paula Ríos", false)).toBe(false);
  });
  it("una propuesta ya resuelta no se vuelve a aprobar", () => {
    expect(canApprove(proposal({ estado: "aprobada" }), "Lic. María González", true)).toBe(false);
  });
});

describe("pendingFor", () => {
  const list = [proposal({ id: "P1", estado: "aprobada" }), proposal({ id: "P2" })];
  it("devuelve sólo la propuesta pendiente del escenario", () => {
    expect(pendingFor(list, "R05")?.id).toBe("P2");
  });
  it("devuelve undefined para un escenario sin propuestas", () => {
    expect(pendingFor(list, "R01")).toBeUndefined();
  });
});
