import { describe, it, expect } from "vitest";
import { relatedCases } from "@/lib/relatedCases";
import { makeCase } from "./_fixtures";

describe("relatedCases", () => {
  it("vincula casos que comparten una contraparte", () => {
    const a = makeCase({ case_id: "CASO-1", account_id: "ACC_A", neighbors: [{ account_id: "ACC_X" } as any] });
    const b = makeCase({ case_id: "CASO-2", account_id: "ACC_B", neighbors: [{ account_id: "ACC_X" } as any] });
    const c = makeCase({ case_id: "CASO-3", account_id: "ACC_C", neighbors: [{ account_id: "ACC_Z" } as any] });
    const rel = relatedCases(a, [a, b, c]);
    const ids = rel.map(r => r.case.case_id);
    expect(ids).toContain("CASO-2");
    expect(ids).not.toContain("CASO-3");
    expect(rel.find(r => r.case.case_id === "CASO-2")!.sharedAccount).toBe("ACC_X");
  });

  it("no se vincula consigo mismo", () => {
    const a = makeCase({ case_id: "CASO-1", account_id: "ACC_A", neighbors: [{ account_id: "ACC_X" } as any] });
    expect(relatedCases(a, [a]).length).toBe(0);
  });
});
