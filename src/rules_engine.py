"""
Deterministic AML rules engine — motor AGREGADO.

Corre junto al GNN como capa explicable y defendible ante el regulador: un
catálogo de escenarios con nombre, cita normativa y severidad, evaluados por
cuenta a partir de las features transaccionales y de comportamiento.

Este módulo evalúa los escenarios **agregados** (R01-R07, más R08 que se agrega
en la capa de export desde el screening de listas): miran totales, grados,
promedios y ratios calculados sobre todo el período. Los escenarios de **ventana
temporal** (R09-R13) viven en `rules_temporal`, que razona sobre la secuencia de
operaciones en el stream y no sobre agregados — lo que el agregado no puede ver
por construcción. El CATÁLOGO de los dos motores vive acá, en `RULES`, con el
campo `motor` indicando quién evalúa cada escenario.

Output por cuenta: la lista de escenarios disparados y un `rule_score` 0-100
(suma de puntos por severidad, con tope). Deliberadamente NO es el score del
GNN — el dashboard muestra los dos para que el analista vea la lectura por
reglas y la del modelo lado a lado.

Umbrales en config.yaml (`rules:`), calibrados sobre la población legítima del
dataset sintético.
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
        "motor": "agregado",
    },
    {
        "id": "R02",
        "nombre": "Transferencia de alto monto atípica",
        "descripcion": "Operación individual muy por encima del perfil transaccional "
                       "habitual de la cartera minorista.",
        "cita": "UIF Res. 30/2017 — umbral de operación",
        "severidad": "media",
        "motor": "agregado",
    },
    {
        "id": "R03",
        "nombre": "Reenvío inmediato de fondos",
        "descripcion": "Alta proporción de ingresos reenviados en menos de 24 h, "
                       "señal típica de cuenta mula.",
        "cita": "GAFI — money mules / rapid movement of funds",
        "severidad": "alta",
        "motor": "agregado",
    },
    {
        "id": "R04",
        "nombre": "Reactivación de cuenta durmiente",
        "descripcion": "Cuenta antigua sin actividad reciente que registra de golpe "
                       "ingresos de alto monto concentrados.",
        "cita": "GAFI — dormant account reactivation",
        "severidad": "alta",
        "motor": "agregado",
    },
    {
        "id": "R05",
        "nombre": "Concentración de fondos (fan-in)",
        "descripcion": "Recepción de fondos desde numerosas fuentes distintas en el "
                       "período, patrón de agregación previa a la salida.",
        "cita": "GAFI — placement / agregación de fondos",
        "severidad": "media",
        "motor": "agregado",
    },
    {
        "id": "R06",
        "nombre": "Dispersión a múltiples destinos",
        "descripcion": "Envío fragmentado a numerosos destinatarios con montos "
                       "promedio bajos, consistente con estructuración.",
        "cita": "UIF Res. 30/2017 — estructuración (pitufeo)",
        "severidad": "media",
        "motor": "agregado",
    },
    {
        "id": "R07",
        "nombre": "Volumen agregado elevado en el período",
        "descripcion": "El flujo total (entradas + salidas) supera ampliamente el "
                       "perfil de una cuenta minorista habitual.",
        "cita": "Monitoreo de umbral acumulado",
        "severidad": "media",
        "motor": "agregado",
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
        "motor": "agregado",
    },
    # ── escenarios de ventana temporal ────────────────────────────────────────
    # Se evalúan en `rules_temporal` sobre el stream de transacciones, no sobre
    # las features agregadas: dependen de la secuencia y del intervalo entre
    # operaciones, que el agregado por definición no conserva. Devuelven además
    # las operaciones concretas que los dispararon (evidencia citable en el ROS).
    {
        "id": "R09",
        "nombre": "Dispersión en ráfaga (pitufeo)",
        "descripcion": "Salidas a múltiples destinatarios distintos concentradas en "
                       "una ventana de horas: fraccionamiento deliberado de un monto "
                       "único para diluirlo por debajo del control por operación.",
        "cita": "UIF Res. 30/2017 — fraccionamiento / estructuración (pitufeo)",
        "severidad": "alta",
        "motor": "temporal",
    },
    {
        "id": "R10",
        "nombre": "Agregación en ráfaga",
        "descripcion": "Ingresos desde múltiples remitentes distintos concentrados en "
                       "pocos días, consistente con una cuenta recolectora que junta "
                       "los tramos de una estructuración previa.",
        "cita": "GAFI — cuentas recolectoras / smurfing",
        "severidad": "media",
        "motor": "temporal",
    },
    {
        "id": "R11",
        "nombre": "Operación circular (U-turn)",
        "descripcion": "Los fondos salen de la cuenta y regresan por un monto "
                       "equivalente a través de otra contraparte: retorno con "
                       "apariencia de origen lícito, típico de la fase de integración.",
        "cita": "GAFI — integración / operaciones circulares (round-tripping)",
        "severidad": "alta",
        "motor": "temporal",
    },
    {
        "id": "R12",
        "nombre": "Tránsito emparejado entrada-salida",
        "descripcion": "Un ingreso y su reenvío por casi el mismo monto a otra "
                       "contraparte dentro de la misma ventana corta: el par concreto "
                       "que evidencia que la cuenta operó como conducto.",
        "cita": "GAFI — cuentas de tránsito / movimiento inmediato de fondos",
        "severidad": "alta",
        "motor": "temporal",
    },
    {
        "id": "R13",
        "nombre": "Desvío del perfil transaccional",
        "descripcion": "El volumen del día pico supera en varios órdenes la mediana "
                       "diaria histórica de la propia cuenta: cambio abrupto de "
                       "comportamiento respecto del perfil declarado.",
        "cita": "UIF Res. 30/2017 — conocimiento del cliente / perfil transaccional",
        "severidad": "media",
        "motor": "temporal",
    },
]

RULES_BY_ID: dict[str, dict] = {r["id"]: r for r in RULES}

# Reglas evaluadas por este módulo (R08 la agrega la capa de export).
_TRANSACTIONAL_RULE_IDS = ["R01", "R02", "R03", "R04", "R05", "R06", "R07"]


def _default_thresholds() -> dict:
    # Montos en PESOS (escala monetaria de config.yaml::monetary.scale). Deben
    # coincidir con config.yaml::rules — test_defaults_match_config lo verifica.
    return {
        "high_amount": {"personal": 1_500_000, "business": 5_000_000, "merchant": 5_000_000},
        "conduit_symmetry": 0.15, "conduit_retention": 1.0,
        "conduit_min_flow": 500_000, "rapid_out_ratio": 0.50, "rapid_symmetry": 0.25,
        "dormant_days": 1095, "dormant_active_days": 10, "dormant_min_amount": 1_200_000,
        "fanin_min_flow": 1_000_000, "fanout_avg_max": 400_000, "fanout_min_total": 1_500_000,
        # segmentado por tipo de cuenta (KYC segmentation)
        "fanin_degree":  {"personal": 12, "business": 40, "merchant": 70},
        "fanout_degree": {"personal": 12, "business": 45, "merchant": 40},
        "agg_volume":    {"personal": 5_000_000, "business": 50_000_000, "merchant": 50_000_000},
        "severity_points": {"alta": 40, "media": 25, "baja": 15},
    }


def _by_type(feats: pd.DataFrame, mapping) -> pd.Series:
    """Per-account threshold from a {account_type: value} mapping (falls back to
    personal). Accepts a scalar for backward compatibility."""
    if not isinstance(mapping, dict):
        return pd.Series(float(mapping), index=feats.index)
    default = mapping.get("personal", next(iter(mapping.values())))
    atype = feats["account_type"] if "account_type" in feats.columns else None
    if atype is None:
        return pd.Series(float(default), index=feats.index)
    return atype.map(lambda x: mapping.get(x, default)).astype(float)


def _rule_masks(feats: pd.DataFrame, t: dict) -> dict[str, pd.Series]:
    """Vectorised boolean mask per transactional rule, indexed like `feats`."""
    f = feats
    # segmented thresholds by account type (KYC segmentation) for R05/R06/R07
    fanin_thr  = _by_type(f, t["fanin_degree"])
    fanout_thr = _by_type(f, t["fanout_degree"])
    agg_thr    = _by_type(f, t["agg_volume"])
    high_thr   = _by_type(f, t["high_amount"])
    return {
        "R01": (
            (f["in_out_symmetry"] <= t["conduit_symmetry"])
            & (f["balance_retention"] <= t["conduit_retention"])
            & (f["total_received"] >= t["conduit_min_flow"])
        ),
        "R02": (
            (f["max_sent"] >= high_thr) | (f["max_received"] >= high_thr)
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
            (f["degree_in"] >= fanin_thr)
            & (f["unique_senders"] >= fanin_thr)
            & (f["total_received"] >= t["fanin_min_flow"])
        ),
        "R06": (
            (f["degree_out"] >= fanout_thr)
            & (f["unique_receivers"] >= fanout_thr)
            & (f["avg_sent"] <= t["fanout_avg_max"])
            & (f["total_sent"] >= t["fanout_min_total"])
        ),
        "R07": (
            (f["total_received"] + f["total_sent"]) >= agg_thr
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
