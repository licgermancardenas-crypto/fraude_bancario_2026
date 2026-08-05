import { describe, it, expect } from "vitest";
import { casesByPattern } from "@/lib/caseAggregates";
import { makeCase } from "./_fixtures";

describe("casesByPattern", () => {
  it("cuenta casos por tipología y omite las de count 0", () => {
    const cases = [
      makeCase({ pattern: "round_tripping" }),
      makeCase({ pattern: "round_tripping" }),
      makeCase({ pattern: "shell_layering" }),
    ];
    const res = casesByPattern(cases);
    const rt = res.find(r => r.pattern === "round_tripping");
    const sl = res.find(r => r.pattern === "shell_layering");
    expect(rt?.count).toBe(2);
    expect(sl?.count).toBe(1);
    expect(res.every(r => r.count > 0)).toBe(true);
  });
});
