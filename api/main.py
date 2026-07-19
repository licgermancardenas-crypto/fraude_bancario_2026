"""
Phantom AI — Scoring API
FastAPI service that exposes pre-computed GNN scores, case management data,
and fraud intelligence for integration with core banking systems.

Run:
    uvicorn api.main:app --reload --port 8000
Docs:
    http://localhost:8000/docs
"""

from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .loader import store, _risk_level

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Phantom AI — Fraud Detection API",
    description=(
        "REST API para el sistema de detección de redes de lavado mediante "
        "Graph Neural Networks. Expone scores GNN, placement scores, cola de alertas "
        "y trazabilidad de perpetradores sobre datos sintéticos de BRS."
    ),
    version="1.0.0",
    contact={"name": "Germán Cárdenas", "email": "yellowy.c76@gmail.com"},
    license_info={"name": "Datos 100% sintéticos — uso demostrativo"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class ScoreRequest(BaseModel):
    account_ids: list[str]
    model_version: str = "graphsage-v1"

    model_config = {
        "json_schema_extra": {
            "example": {
                "account_ids": ["ACC0000009", "ACC0000050", "ACC0000210"],
                "model_version": "graphsage-v1",
            }
        }
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root():
    return {
        "service": "Phantom AI — Fraud Detection API",
        "version": "1.0.0",
        "model": "GraphSAGE (SAGEConv 18→64→64)",
        "dataset": "Sintético BRS — 75K cuentas · 400K transacciones",
        "docs": "/docs",
        "endpoints": [
            "/health", "/stats",
            "/accounts", "/accounts/{id}", "/accounts/score",
            "/cases", "/cases/{id}",
            "/rings", "/perpetrators", "/placement",
            "/models/performance",
        ],
    }


@app.get("/health", tags=["Info"])
def health():
    now = datetime.now(timezone.utc).isoformat()
    return {
        "status": "ok",
        "timestamp": now,
        "started_at": store.started_at,
        "accounts_indexed": len(store.account_idx),
        "cases_indexed": len(store.case_idx),
        "placement_indexed": len(store.placement_idx),
        "numpy_scores_loaded": store.scores_gnn is not None,
    }


@app.get("/stats", tags=["Info"])
def stats():
    kpis = store.kpis
    bi   = store.business_impact if isinstance(store.business_impact, dict) else {}
    return {
        "dataset": {
            "n_accounts": kpis.get("n_accounts", 75_000),
            "n_fraud": kpis.get("n_fraud"),
            "pct_fraud": kpis.get("pct_fraud"),
            "client": kpis.get("client"),
        },
        "model_performance": {
            "model": kpis.get("model"),
            "pr_auc": kpis.get("pr_auc_gnn"),
            "recall_at_p90": kpis.get("recall_at_p90"),
        },
        "alert_queue": {
            "total_cases": len(store.cases),
            "open": sum(1 for c in store.cases if c.get("status") == "abierto"),
            "in_review": sum(1 for c in store.cases if c.get("status") == "en_revision"),
            "escalated": sum(1 for c in store.cases if c.get("status") == "escalado"),
            "dismissed": sum(1 for c in store.cases if c.get("status") == "desestimado"),
        },
        "business_impact": bi,
    }


# ── Accounts ──────────────────────────────────────────────────────────────────

@app.get("/accounts", tags=["Accounts"])
def list_accounts(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    min_score: Annotated[float, Query(ge=0.0, le=1.0)] = 0.0,
    in_ring: bool | None = None,
    account_type: Literal["personal", "business", "merchant"] | None = None,
    risk_level: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] | None = None,
):
    """
    Paginated list of high-risk accounts (top 200 by GNN score).
    Supports filtering by minimum score, ring membership, account type, and risk level.
    """
    accounts = store.top_accounts

    if min_score > 0:
        accounts = [a for a in accounts if a["gnn_score"] >= min_score]
    if in_ring is not None:
        accounts = [a for a in accounts if bool(a.get("in_ring")) == in_ring]
    if account_type:
        accounts = [a for a in accounts if a.get("account_type") == account_type]
    if risk_level:
        accounts = [a for a in accounts if _risk_level(a["gnn_score"]) == risk_level]

    total = len(accounts)
    page  = accounts[offset: offset + limit]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "accounts": [
            {**a, "risk_level": _risk_level(a["gnn_score"])} for a in page
        ],
    }


@app.get("/accounts/{account_id}", tags=["Accounts"])
def get_account(account_id: str):
    """
    Full account detail: GNN score, placement score, persona, empresa,
    neighbors with risk scores, and recent transactions.
    """
    account = store.get_account(account_id)
    if not account:
        raise HTTPException(
            status_code=404,
            detail=f"Account '{account_id}' not found in indexed dataset (top-200 + 80 cases)."
        )
    return account


@app.post("/accounts/score", tags=["Accounts"])
def score_accounts(body: ScoreRequest):
    """
    Score one or more accounts by ID.
    Returns GNN score, risk level, and placement score for each.
    Scores are pre-computed from the trained GraphSAGE model.
    """
    if len(body.account_ids) > 100:
        raise HTTPException(status_code=422, detail="Maximum 100 accounts per request.")

    results = store.score_accounts(body.account_ids)
    found   = sum(1 for r in results if r["found"])

    return {
        "model": "GraphSAGE (SAGEConv 18→64→64)",
        "model_version": body.model_version,
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "requested": len(body.account_ids),
        "found": found,
        "not_found": len(body.account_ids) - found,
        "results": results,
    }


# ── Cases ─────────────────────────────────────────────────────────────────────

@app.get("/cases", tags=["Cases"])
def list_cases(
    limit: Annotated[int, Query(ge=1, le=80)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: Literal["abierto", "en_revision", "escalado", "desestimado"] | None = None,
    pattern: Literal["anillo_lavado", "estructuracion", "agregacion_fondos"] | None = None,
    min_score: Annotated[float, Query(ge=0.0, le=1.0)] = 0.0,
    is_pep: bool | None = None,
):
    """
    Alert queue — filterable by status, typology, minimum GNN score, and PEP flag.
    """
    cases = store.cases

    if status:
        cases = [c for c in cases if c.get("status") == status]
    if pattern:
        cases = [c for c in cases if c.get("pattern") == pattern]
    if min_score > 0:
        cases = [c for c in cases if c["gnn_score"] >= min_score]
    if is_pep is not None:
        cases = [c for c in cases if bool(c.get("is_pep")) == is_pep]

    total = len(cases)
    page  = cases[offset: offset + limit]

    # Return lightweight version (no neighbors/transactions in list)
    slim = []
    for c in page:
        slim.append({
            k: v for k, v in c.items()
            if k not in ("neighbors", "recent_transactions")
        } | {"risk_level": _risk_level(c["gnn_score"])})

    return {"total": total, "limit": limit, "offset": offset, "cases": slim}


@app.get("/cases/{case_id}", tags=["Cases"])
def get_case(case_id: str):
    """
    Full case detail including persona, empresa, risk neighbors, and recent transactions.
    """
    case = store.case_idx.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return {**case, "risk_level": _risk_level(case["gnn_score"])}


# ── Rings ─────────────────────────────────────────────────────────────────────

@app.get("/rings", tags=["Fraud Intelligence"])
def list_rings():
    """
    Detected cyclic laundering rings. Each ring includes member accounts,
    total amount cycled, number of hops, and timestamps.
    """
    rings = store.rings if isinstance(store.rings, list) else []
    return {
        "total_rings": len(rings),
        "rings": rings,
    }


# ── Perpetrators ──────────────────────────────────────────────────────────────

@app.get("/perpetrators", tags=["Fraud Intelligence"])
def perpetrators():
    """
    Origin accounts identified via backward tracing from detected mule accounts.
    Includes accounts NOT detected by the GNN (score ≈ 0%) but identified
    as injection sources through directed graph traversal.
    """
    trace = store.origin_trace
    return {
        "summary": trace.get("summary", {}),
        "perpetrators": trace.get("perpetrators", []),
        "note": (
            "Accounts with gnn_score ≈ 0 that appear here were not flagged by the "
            "GNN classifier but were identified as fund injection sources via backward "
            "tracing on the directed transaction graph."
        ),
    }


# ── Placement ─────────────────────────────────────────────────────────────────

@app.get("/placement", tags=["Fraud Intelligence"])
def placement(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    only_new: bool = False,
):
    """
    Placement score ranking — inverse risk propagation that surfaces
    origin accounts even when the GNN score is low.
    Accounts with high placement_score_norm but low gnn_score are prime
    candidates for placement / colocación investigation.
    """
    candidates = store.placement.get("candidates", [])

    if only_new:
        candidates = [c for c in candidates if not c.get("detected_by_gnn")]

    return {
        "total": len(candidates),
        "n_flagged": store.placement.get("n_flagged"),
        "n_new_discoveries": store.placement.get("n_new_discoveries"),
        "known_perpetrators": store.placement.get("known_perpetrators"),
        "candidates": candidates[:limit],
        "method": (
            "placement(u) = Σ gnn[v]×amount(u→v) "
            "+ 0.3×Σ gnn[w]×amount(v→w)×amount(u→v)/total_out(v)"
        ),
    }


# ── Model Performance ─────────────────────────────────────────────────────────

@app.get("/models/performance", tags=["Model"])
def model_performance():
    """
    Comparative model performance: PR-AUC, ROC-AUC, Recall@P90, and
    business impact translation for all evaluated models.
    """
    return {
        "dataset": {
            "n_accounts": 75_000,
            "n_fraud": 1_147,
            "pct_fraud": 1.53,
            "scale_factor": 0.5,
        },
        "models": [
            {
                "model": "Logistic Regression",
                "type": "tabular_linear",
                "pr_auc": 0.675,
                "roc_auc": 0.986,
                "recall_at_p90": 0.0,
                "f1_optimal": 0.680,
                "pct_fraud_missed": 27.6,
                "daily_alerts_brs": 30,
            },
            {
                "model": "XGBoost",
                "type": "tabular_nonlinear",
                "pr_auc": 0.927,
                "roc_auc": 0.998,
                "recall_at_p90": 0.804,
                "f1_optimal": 0.858,
                "pct_fraud_missed": 20.2,
                "daily_alerts_brs": 23,
            },
            {
                "model": "GAT",
                "type": "graph_attention",
                "pr_auc": 0.973,
                "roc_auc": 0.999,
                "recall_at_p90": 0.933,
                "f1_optimal": 0.938,
                "pct_fraud_missed": 8.0,
                "daily_alerts_brs": 25,
            },
            {
                "model": "GraphSAGE",
                "type": "graph_inductive",
                "pr_auc": 0.977,
                "roc_auc": 0.9995,
                "recall_at_p90": 0.951,
                "f1_optimal": 0.950,
                "pct_fraud_missed": 6.7,
                "daily_alerts_brs": 25,
                "recommended": True,
            },
        ],
        "pr_curves": store.pr_curves,
        "temporal_eval": store.temporal_eval,
        "homophily": {
            "lift_fraud_fraud": 14.3,
            "cohen_d_credit_score": 0.055,
            "interpretation": (
                "Fraud accounts are 14.3× more likely to be connected to other fraud "
                "accounts than chance. Credit score has near-zero discriminative power "
                "(Cohen d=0.055): AML is a network problem, not a profile problem."
            ),
        },
    }
