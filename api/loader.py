"""
Data loader — loads all pre-computed data at startup and provides O(1) lookups.
Sources: dashboard/public/data/*.json  +  data/processed/scores_*.npy
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

DATA_DIR = Path(__file__).parent.parent / "dashboard" / "public" / "data"
PROC_DIR = Path(__file__).parent.parent / "data" / "processed"


def _risk_level(score: float) -> str:
    if score >= 0.9:
        return "CRITICAL"
    if score >= 0.7:
        return "HIGH"
    if score >= 0.4:
        return "MEDIUM"
    return "LOW"


class DataStore:
    """Single instance loaded once at API startup."""

    def __init__(self):
        self.started_at = datetime.utcnow().isoformat() + "Z"
        self._load()

    def _load(self):
        # ── JSON exports ──────────────────────────────────────────────────────
        self.kpis: dict             = self._j("kpis.json")
        self.top_accounts: list     = self._j("top_accounts.json")
        self.cases: list            = self._j("cases.json")
        self.rings: list            = self._j("rings.json")
        self.origin_trace: dict     = self._j("origin_trace.json")
        self.placement: dict        = self._j("placement_candidates.json")
        self.pr_curves: dict        = self._j("pr_curves.json")
        self.score_dist: dict       = self._j("score_distribution.json")
        self.business_impact: dict  = self._j("business_impact.json")
        self.explanations: dict     = self._j("explanations.json")
        self.temporal_eval: dict    = self._j("temporal_eval.json")

        # ── Numpy scores (full graph) ─────────────────────────────────────────
        self.scores_gnn   = self._np("scores_graphsage.npy")
        self.scores_xgb   = self._np("scores_xgboost.npy")

        # ── Indexes ───────────────────────────────────────────────────────────
        # account_id → account dict (from top_accounts)
        self.account_idx: dict[str, dict] = {
            a["account_id"]: a for a in self.top_accounts
        }
        # account_id → case dict (richer: has persona, empresa, neighbors, txns)
        self.case_by_account: dict[str, dict] = {
            c["account_id"]: c for c in self.cases
        }
        # case_id → case dict
        self.case_idx: dict[str, dict] = {
            c["case_id"]: c for c in self.cases
        }
        # placement index
        self.placement_idx: dict[str, dict] = {
            p["account_id"]: p for p in self.placement.get("candidates", [])
        }

    def _j(self, fname: str) -> Any:
        path = DATA_DIR / fname
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _np(self, fname: str):
        path = PROC_DIR / fname
        if not path.exists():
            return None
        return np.load(path)

    # ── Public helpers ────────────────────────────────────────────────────────

    def get_account(self, account_id: str) -> dict | None:
        """Return enriched account dict, preferring case data (has persona)."""
        case = self.case_by_account.get(account_id)
        if case:
            acct = self.account_idx.get(account_id, {})
            return {
                "account_id": account_id,
                "gnn_score": case["gnn_score"],
                "risk_level": _risk_level(case["gnn_score"]),
                "is_fraud_label": bool(case.get("is_fraud")),
                "in_ring": bool(acct.get("in_ring", False)),
                "account_type": case.get("account_type"),
                "balance": case.get("balance"),
                "risk_score": case.get("risk_score"),
                "degree_in": acct.get("degree_in"),
                "degree_out": acct.get("degree_out"),
                "total_sent": acct.get("total_sent"),
                "total_received": acct.get("total_received"),
                "alert_date": case.get("alert_date"),
                "pattern": case.get("pattern"),
                "is_pep": case.get("is_pep", False),
                "persona": case.get("persona"),
                "empresa": case.get("empresa"),
                "neighbors": case.get("neighbors", []),
                "recent_transactions": case.get("recent_transactions", []),
                "placement": self.placement_idx.get(account_id),
            }
        acct = self.account_idx.get(account_id)
        if acct:
            return {
                **acct,
                "risk_level": _risk_level(acct["gnn_score"]),
                "is_fraud_label": bool(acct.get("is_fraud")),
                "placement": self.placement_idx.get(account_id),
            }
        return None

    def score_accounts(self, account_ids: list[str]) -> list[dict]:
        results = []
        for aid in account_ids:
            acct = self.account_idx.get(aid)
            plac = self.placement_idx.get(aid)
            if acct:
                results.append({
                    "account_id": aid,
                    "gnn_score": acct["gnn_score"],
                    "risk_level": _risk_level(acct["gnn_score"]),
                    "placement_score_norm": plac["placement_score_norm"] if plac else None,
                    "in_ring": bool(acct.get("in_ring", False)),
                    "found": True,
                })
            else:
                results.append({"account_id": aid, "found": False,
                                 "gnn_score": None, "risk_level": "UNKNOWN"})
        return results


store = DataStore()
