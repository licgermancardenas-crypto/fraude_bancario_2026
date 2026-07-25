import type { CaseStatus } from "@/lib/types";

const KEY = "phantom_case_statuses";

export function getStoredStatuses(): Record<string, CaseStatus> {
  if (typeof window === "undefined") return {};
  try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch { return {}; }
}

export function setStoredStatus(caseId: string, status: CaseStatus) {
  const all = getStoredStatuses();
  all[caseId] = status;
  localStorage.setItem(KEY, JSON.stringify(all));
}
