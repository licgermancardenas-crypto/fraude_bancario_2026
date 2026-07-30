"""
Deterministic AML rules engine.

Runs alongside the GNN as an explainable, regulator-facing layer: a catalogue
of named scenarios, each with a regulatory citation and a severity, evaluated
per account from the transactional/behavioural features. Rules and the GNN are
complementary — rules flag the obvious, auditable red flags (large amounts,
pass-through conduits, dormant reactivation) while the GNN catches the subtle
network-only structures a rule cannot express.

Output per account: the list of fired rules and a 0-100 `rule_score`
(capped sum of severity points). This is intentionally NOT the GNN score —
the dashboard shows both so an analyst sees the rule-based and the model-based
view side by side.

Thresholds live in config.yaml (`rules:`), calibrated on the legitimate
population of the synthetic dataset.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ── rule catalogue ────────────────────────────────────────────────────────────
# Each rule: id, nombre, descripcion (analyst-facing), cita (regulatory),
# severidad. The predicate is attached in `evaluate` (vectorised over the
# feature frame) so the catalogue stays declarative and serialisable.

RULES: list[dict] = [
    {
        "id": "R01",
        "nombre": "Cuenta de paso / tránsito rápido",
        "descripcion": "Los fondos entran y salen por montos casi idénticos sin "
                       "retención de saldo: comportamiento de cuenta conducto.",
        "cita": "GAFI — cuentas de tránsito (pass-through)",
        "severidad": "alta",
    },
    {
        "id": "R02",
        "nombre": "Transferencia de alto monto atípica",
        "descripcion": "Operación individual muy por encima del perfil transaccional "
                       "habitual de la cartera minorista.",
        "cita": "UIF Res. 30/2017 — umbral de operación",
        "severidad": "media",
    },
    {
        "id": "R03",
        "nombre": "Reenvío inmediato de fondos",
        "descripcion": "Alta proporción de ingresos reenviados en menos de 24 h, "
                       "señal típica de cuenta mula.",
        "cita": "GAFI — money mules / rapid movement of funds",
        "severidad": "alta",
    },
    {
        "id": "R04",
        "nombre": "Reactivación de cuenta durmiente",
        "descripcion": "Cuenta antigua sin actividad reciente que registra de golpe "
                       "ingresos de alto monto concentrados.",
        "cita": "GAFI — dormant account reactivation",
        "severidad": "alta",
    },
    {
        "id": "R05",
        "nombre": "Concentración de fondos (fan-in)",
        "descripcion": "Recepción de fondos desde numerosas fuentes distintas en el "
                       "período, patrón de agregación previa a la salida.",
        "cita": "GAFI — placement / agregación de fondos",
        "severidad": "media",
    },
    {
        "id": "R06",
        "nombre": "Dispersión a múltiples destinos",
        "descripcion": "Envío fragmentado a numerosos destinatarios con montos "
                       "promedio bajos, consistente con estructuración.",
        "cita": "UIF Res. 30/2017 — estructuración (pitufeo)",
        "severidad": "media",
    },
    {
        "id": "R07",
        "nombre": "Volumen agregado elevado en el período",
        "descripcion": "El flujo total (entradas + salidas) supera ampliamente el "
                       "perfil de una cuenta minorista habitual.",
        "cita": "Monitoreo de umbral acumulado",
        "severidad": "media",
    },
    # R08 (exposición a listas de sanciones) se evalúa en la capa de export,
    # donde está disponible el resultado del screening por caso.
    {
        "id": "R08",
        "nombre": "Exposición a listas de sanciones",
        "descripcion": "Coincidencia directa en listas (ONU/OFAC/REPET) o exposición "
                       "a un salto de una cuenta listada.",
        "cita": "Ley 25.246 — sujetos obligados / listas de designación",
        "severidad": "alta",
    },
]

RULES_BY_ID: dict[str, dict] = {r["id"]: r for r in RULES}

# Reglas evaluadas por este módulo (R08 la agrega la capa de export).
_TRANSACTIONAL_RULE_IDS = ["R01", "R02", "R03", "R04", "R05", "R06", "R07"]


def _default_thresholds() -> dict:
    return {
        "high_amount": 15000, "conduit_symmetry": 0.15, "conduit_retention": 1.0,
        "conduit_min_flow": 5000, "rapid_out_ratio": 0.50, "rapid_symmetry": 0.25,
        "dormant_days": 1095, "dormant_active_days": 10, "dormant_min_amount": 12000,
        "fanin_degree": 12, "fanin_min_flow": 10000, "fanout_degree": 12,
        "fanout_avg_max": 4000, "fanout_min_total": 15000, "agg_volume": 50000,
        "severity_points": {"alta": 40, "media": 25, "baja": 15},
    }


def _rule_masks(feats: pd.DataFrame, t: dict) -> dict[str, pd.Series]:
    """Vectorised boolean mask per transactional rule, indexed like `feats`."""
    f = feats
    return {
        "R01": (
            (f["in_out_symmetry"] <= t["conduit_symmetry"])
            & (f["balance_retention"] <= t["conduit_retention"])
            & (f["total_received"] >= t["conduit_min_flow"])
        ),
        "R02": (
            (f["max_sent"] >= t["high_amount"]) | (f["max_received"] >= t["high_amount"])
        ),
        "R03": (
            (f["rapid_out_ratio"] >= t["rapid_out_ratio"])
            & (f["in_out_symmetry"] <= t["rapid_symmetry"])
            & (f["total_received"] >= t["conduit_min_flow"])
        ),
        "R04": (
            (f["opened_days_ago"] >= t["dormant_days"])
            & (f["active_days"] <= t["dormant_active_days"])
            & (f["max_received"] >= t["dormant_min_amount"])
        ),
        "R05": (
            (f["degree_in"] >= t["fanin_degree"])
            & (f["unique_senders"] >= t["fanin_degree"])
            & (f["total_received"] >= t["fanin_min_flow"])
        ),
        "R06": (
            (f["degree_out"] >= t["fanout_degree"])
            & (f["unique_receivers"] >= t["fanout_degree"])
            & (f["avg_sent"] <= t["fanout_avg_max"])
            & (f["total_sent"] >= t["fanout_min_total"])
        ),
        "R07": (
            (f["total_received"] + f["total_sent"]) >= t["agg_volume"]
        ),
    }


def evaluate(feats: pd.DataFrame, cfg: dict | None = None) -> dict[str, dict]:
    """
    Evaluate the transactional rules (R01-R07) over a feature frame.

    Returns {account_id: {"rules_fired": [rule_id, ...], "rule_score": int}}
    for accounts that fire at least one rule. R08 is layered in by the caller.
    """
    t = _default_thresholds()
    if cfg and isinstance(cfg.get("rules"), dict):
        t = {**t, **cfg["rules"]}
    pts = t["severity_points"]

    if "account_id" in feats.columns:
        feats = feats.set_index("account_id")

    masks = _rule_masks(feats, t)
    fired_df = pd.DataFrame(masks)  # columns = rule ids, index = account_id

    out: dict[str, dict] = {}
    any_fired = fired_df.any(axis=1)
    for acc_id in fired_df.index[any_fired]:
        ids = [rid for rid in _TRANSACTIONAL_RULE_IDS if bool(fired_df.at[acc_id, rid])]
        score = min(100, sum(pts[RULES_BY_ID[rid]["severidad"]] for rid in ids))
        out[acc_id] = {"rules_fired": ids, "rule_score": int(score)}
    return out


def score_from_ids(rule_ids: list[str], cfg: dict | None = None) -> int:
    """Compute the capped 0-100 rule_score from a list of fired rule ids."""
    pts = _default_thresholds()["severity_points"]
    if cfg and isinstance(cfg.get("rules"), dict) and "severity_points" in cfg["rules"]:
        pts = cfg["rules"]["severity_points"]
    return int(min(100, sum(pts[RULES_BY_ID[r]["severidad"]] for r in rule_ids if r in RULES_BY_ID)))


def catalogue() -> list[dict]:
    """Serialisable rule catalogue (for the dashboard rules reference)."""
    return [dict(r) for r in RULES]
