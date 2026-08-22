"""
Escenarios ALD de ventana temporal — motor sobre el stream de transacciones.

El motor de `rules_engine` (R01-R08) evalúa **features agregadas de cuenta**:
totales, grados, promedios y ratios calculados sobre todo el período. Eso lo
hace barato pero estructuralmente ciego a la dimensión que define media
tipología ALD: *cuándo* pasaron las cosas y *en qué secuencia*.

Un motor de monitoreo transaccional real no razona sobre agregados: razona
sobre secuencias dentro de ventanas móviles. "Diez transferencias a diez
destinatarios distintos" es operatoria normal en un año y es pitufeo en
cuarenta y ocho horas — el agregado no distingue los dos casos, la ventana sí.

Este módulo agrega los escenarios que necesitan el stream (R09-R13) y, a
diferencia del motor agregado, devuelve **evidencia**: las transacciones
concretas que dispararon cada escenario. Un ROS se sostiene con las
operaciones citadas, no con el nombre de una regla.

Umbrales en config.yaml (`rules_temporal:`), calibrados sobre este dataset;
segmentados por `account_type` donde el comportamiento comercial legítimo
(nómina, cobros de comercio) genera el mismo patrón por motivos lícitos.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from .rules_engine import RULES_BY_ID, _default_thresholds as _agg_thresholds

DAY = 86_400
HOUR = 3_600

# Escenarios evaluados por este módulo. El catálogo (nombre, cita, severidad)
# vive en `rules_engine.RULES`; acá va sólo el orden de evaluación.
TEMPORAL_RULE_IDS = ["R09", "R10", "R11", "R12", "R13"]

# Tipos de operación que cuentan como movimiento de fondos dirigido. Las
# extracciones quedan fuera de los escenarios de dispersión: en este dataset
# el efectivo es siempre operatoria legítima (ver nota en el README).
_FLOW_TYPES = ("transfer", "payment")


def _default_thresholds() -> dict:
    # Montos en PESOS (config.yaml::monetary.scale). Deben coincidir con
    # config.yaml::rules_temporal — test_defaults_match_config lo verifica.
    return {
        # R09 — dispersión en ráfaga (pitufeo)
        "burst_out_window_h": 48,
        "burst_out_min_counterparties": 4,
        "burst_out_min_total": {"personal": 800_000, "business": 8_000_000, "merchant": 8_000_000},
        # R10 — agregación en ráfaga
        "burst_in_window_h": 72,
        "burst_in_min_counterparties": 4,
        "burst_in_min_total": {"personal": 800_000, "business": 8_000_000, "merchant": 16_000_000},
        # R11 — operación circular (U-turn)
        "uturn_window_days": 30,
        "uturn_tolerance": 0.15,
        "uturn_min_amount": 5_000_000,
        # R12 — tránsito emparejado
        "passthrough_window_h": 72,
        "passthrough_min_ratio": 0.80,
        "passthrough_min_amount": 500_000,
        # R13 — desvío contra la baseline propia
        "velocity_multiple": 20,
        "velocity_min_active_days": 4,
        "velocity_min_peak": 3_000_000,
    }


def _thresholds(cfg: dict | None) -> dict:
    t = _default_thresholds()
    if cfg and isinstance(cfg.get("rules_temporal"), dict):
        t = {**t, **cfg["rules_temporal"]}
    return t


def _by_type(mapping, account_type: str) -> float:
    """Umbral para un tipo de cuenta (cae a `personal`). Acepta escalar."""
    if not isinstance(mapping, dict):
        return float(mapping)
    default = mapping.get("personal", next(iter(mapping.values())))
    return float(mapping.get(account_type, default))


# ── escenarios ────────────────────────────────────────────────────────────────

def _burst(txns: pd.DataFrame, actor: str, counterparty: str, atype: pd.Series,
           window_s: int, min_cp: int, min_total_by_type) -> dict[str, dict]:
    """
    Ráfaga: dentro de una ventana móvil, ≥`min_cp` contrapartes DISTINTAS
    sumando ≥ umbral. Dos punteros con un contador de contrapartes vivas, así
    que recorre el stream una sola vez por cuenta.

    Devuelve {cuenta: evidencia} para la primera ventana que dispara.
    """
    d = txns.sort_values([actor, "timestamp"], kind="mergesort")
    act = d[actor].to_numpy()
    cps = d[counterparty].to_numpy()
    amt = d["amount"].to_numpy(dtype=float)
    ts = d["timestamp"].to_numpy(dtype=np.int64)
    tid = d["transaction_id"].to_numpy()

    hits: dict[str, dict] = {}
    i, n = 0, len(d)
    while i < n:
        j = i
        while j < n and act[j] == act[i]:
            j += 1
        cuenta = act[i]
        umbral = _by_type(min_total_by_type, atype.get(cuenta, "personal"))
        lo = i
        vivos: dict = defaultdict(int)
        total = 0.0
        for r in range(i, j):
            vivos[cps[r]] += 1
            total += amt[r]
            while ts[r] - ts[lo] > window_s:
                vivos[cps[lo]] -= 1
                if vivos[cps[lo]] == 0:
                    del vivos[cps[lo]]
                total -= amt[lo]
                lo += 1
            if len(vivos) >= min_cp and total >= umbral:
                hits[cuenta] = {
                    "operaciones": [str(x) for x in tid[lo:r + 1]],
                    "contrapartes": int(len(vivos)),
                    "monto_total": round(float(total), 2),
                    "ventana_horas": int(window_s // HOUR),
                    "desde": int(ts[lo]),
                    "hasta": int(ts[r]),
                    "umbral_aplicado": umbral,
                }
                break
        i = j
    return hits


def _paired(ledger: dict, window_s: int, lo_ratio: float, hi_ratio: float,
            first_out: bool, min_amount: float) -> dict[str, dict]:
    """
    Par emparejado por monto dentro de una ventana: una operación de referencia
    y, poco después, su contraparte en el sentido opuesto por un monto similar
    con OTRA contraparte.

    `first_out=True`  → salida y retorno posterior (U-turn / operación circular).
    `first_out=False` → entrada y reenvío posterior (tránsito / cuenta conducto).
    """
    A, CP, AM, TS, D, TID = (ledger[k] for k in ("acc", "cp", "amount", "ts", "dir", "tid"))
    ref_dir = -1 if first_out else 1

    hits: dict[str, dict] = {}
    i, n = 0, len(A)
    while i < n:
        j = i
        while j < n and A[j] == A[i]:
            j += 1
        for r in range(i, j):
            if D[r] != ref_dir or AM[r] < min_amount:
                continue
            x = AM[r]
            for s in range(r + 1, j):
                if TS[s] - TS[r] > window_s:
                    break
                if D[s] == ref_dir or CP[s] == CP[r]:
                    continue
                if lo_ratio * x <= AM[s] <= hi_ratio * x:
                    hits[A[i]] = {
                        "operaciones": [str(TID[r]), str(TID[s])],
                        "monto_referencia": round(float(x), 2),
                        "monto_contrapartida": round(float(AM[s]), 2),
                        "cobertura": round(float(AM[s] / x), 4),
                        "horas_transcurridas": round((TS[s] - TS[r]) / HOUR, 1),
                        "contraparte_origen": str(CP[r]),
                        "contraparte_destino": str(CP[s]),
                    }
                    break
            if A[i] in hits:
                break
        i = j
    return hits


def _velocity(txns: pd.DataFrame, multiple: float, min_active_days: int,
              min_peak: float) -> dict[str, dict]:
    """
    Desvío contra la baseline propia: el volumen diario de salida en su día pico
    supera `multiple` veces la mediana diaria histórica de la misma cuenta.

    A diferencia de R02/R07, que comparan contra un umbral fijo de la cartera,
    acá el punto de comparación es el comportamiento previo del propio cliente
    — el desvío del perfil que exige la debida diligencia continua.
    """
    d = txns[["src", "amount", "timestamp"]].copy()
    d["dia"] = d["timestamp"] // DAY
    diario = d.groupby(["src", "dia"], sort=False)["amount"].sum().rename("volumen").reset_index()

    g = diario.groupby("src")["volumen"]
    stat = pd.DataFrame({"pico": g.max(), "mediana": g.median(), "dias": g.count()})
    disparan = stat[
        (stat["dias"] >= min_active_days)
        & (stat["pico"] >= multiple * stat["mediana"])
        & (stat["pico"] >= min_peak)
    ]
    if disparan.empty:
        return {}

    # día pico de cada cuenta que dispara, para citar sus operaciones
    picos = (diario[diario["src"].isin(disparan.index)]
             .sort_values("volumen")
             .drop_duplicates("src", keep="last")
             .set_index("src"))
    ops = (txns[txns["src"].isin(disparan.index)]
           .assign(dia=lambda x: x["timestamp"] // DAY)
           .merge(picos["dia"].rename("dia_pico"), left_on="src", right_index=True)
           .query("dia == dia_pico")
           .groupby("src")["transaction_id"].apply(list))

    return {
        acc: {
            "operaciones": [str(x) for x in ops.get(acc, [])],
            "volumen_pico": round(float(row["pico"]), 2),
            "mediana_diaria": round(float(row["mediana"]), 2),
            "multiplo": round(float(row["pico"] / row["mediana"]), 1) if row["mediana"] else None,
            "dias_activos": int(row["dias"]),
            "dia_pico": int(picos.at[acc, "dia"] * DAY),
        }
        for acc, row in disparan.iterrows()
    }


# ── API ───────────────────────────────────────────────────────────────────────

def _build_ledger(txns: pd.DataFrame) -> dict:
    """Extracto por cuenta: una fila por lado de cada operación, ordenado."""
    envia = txns.rename(columns={"src": "acc", "dst": "cp"}).assign(dir=-1)
    recibe = txns.rename(columns={"dst": "acc", "src": "cp"}).assign(dir=1)
    cols = ["acc", "cp", "amount", "timestamp", "dir", "transaction_id"]
    led = pd.concat([envia[cols], recibe[cols]], ignore_index=True)
    led = led.sort_values(["acc", "timestamp"], kind="mergesort")
    return {
        "acc": led["acc"].to_numpy(), "cp": led["cp"].to_numpy(),
        "amount": led["amount"].to_numpy(dtype=float),
        "ts": led["timestamp"].to_numpy(dtype=np.int64),
        "dir": led["dir"].to_numpy(dtype=np.int8),
        "tid": led["transaction_id"].to_numpy(),
    }


def evaluate_rules(txns: pd.DataFrame, accounts: pd.DataFrame,
                   cfg: dict | None = None,
                   only: list[str] | None = None) -> dict[str, dict[str, dict]]:
    """
    Evalúa los escenarios temporales y devuelve {rule_id: {cuenta: evidencia}}.

    `only` restringe qué escenarios se corren — lo usa la curva de calibración,
    que re-evalúa un solo escenario una decena de veces con el umbral escalado y
    no puede pagar el costo de los otros cuatro en cada punto.
    """
    t = _thresholds(cfg)
    pedidos = [r for r in TEMPORAL_RULE_IDS if only is None or r in only]
    atype = accounts.set_index("account_id")["account_type"] if "account_type" in accounts.columns \
        else pd.Series("personal", index=accounts["account_id"])

    # Las vistas caras se construyen sólo si algún escenario pedido las usa.
    flujo = txns[txns["transaction_type"].isin(_FLOW_TYPES)] \
        if {"R09", "R13"} & set(pedidos) else None
    ledger = _build_ledger(txns) if {"R11", "R12"} & set(pedidos) else None

    corredores = {
        "R09": lambda: _burst(flujo, "src", "dst", atype,
                              int(t["burst_out_window_h"]) * HOUR,
                              int(t["burst_out_min_counterparties"]), t["burst_out_min_total"]),
        "R10": lambda: _burst(txns, "dst", "src", atype,
                              int(t["burst_in_window_h"]) * HOUR,
                              int(t["burst_in_min_counterparties"]), t["burst_in_min_total"]),
        "R11": lambda: _paired(ledger, int(t["uturn_window_days"]) * DAY,
                               1 - float(t["uturn_tolerance"]), 1 + float(t["uturn_tolerance"]),
                               True, float(t["uturn_min_amount"])),
        "R12": lambda: _paired(ledger, int(t["passthrough_window_h"]) * HOUR,
                               float(t["passthrough_min_ratio"]), 1.0,
                               False, float(t["passthrough_min_amount"])),
        "R13": lambda: _velocity(flujo, float(t["velocity_multiple"]),
                                 int(t["velocity_min_active_days"]), float(t["velocity_min_peak"])),
    }
    return {rid: corredores[rid]() for rid in pedidos}


def evaluate(txns: pd.DataFrame, accounts: pd.DataFrame,
             cfg: dict | None = None) -> dict[str, dict]:
    """
    Evalúa los escenarios temporales (R09-R13) sobre el stream de transacciones.

    Devuelve, para cada cuenta que dispara al menos un escenario:
        {"rules_fired": [id, ...],
         "rule_score": int,          # 0-100, mismos puntos por severidad
         "evidence": {id: {...}}}    # operaciones citadas por escenario
    """
    por_regla = evaluate_rules(txns, accounts, cfg)

    pts = _agg_thresholds()["severity_points"]
    if cfg and isinstance(cfg.get("rules"), dict) and "severity_points" in cfg["rules"]:
        pts = cfg["rules"]["severity_points"]

    out: dict[str, dict] = {}
    for rid in TEMPORAL_RULE_IDS:
        for cuenta, evidencia in por_regla.get(rid, {}).items():
            entry = out.setdefault(cuenta, {"rules_fired": [], "evidence": {}})
            entry["rules_fired"].append(rid)
            entry["evidence"][rid] = evidencia
    for entry in out.values():
        entry["rule_score"] = int(min(100, sum(
            pts[RULES_BY_ID[rid]["severidad"]] for rid in entry["rules_fired"]
        )))
    return out
