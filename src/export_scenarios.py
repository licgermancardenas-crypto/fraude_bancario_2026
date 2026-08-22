"""
Genera dashboard/public/data/scenarios.json — la capa de GESTIÓN DE ESCENARIOS
del motor de reglas ALD.

Un catálogo de reglas sin administración es una caja negra: el oficial de
cumplimiento no puede ver qué rinde cada escenario ni justificar ante el
regulador por qué un umbral vale lo que vale. Este módulo produce, para cada
escenario del catálogo (`src/rules_engine.RULES`):

  1. sus umbrales vigentes (incluidos los segmentados por tipo de cuenta),
  2. su performance medida contra la etiqueta del dataset — disparos, precisión,
     recall, tasa de falsos positivos, lift sobre la tasa base,
  3. su desempeño desagregado por segmento KYC,
  4. cuánto aporta en exclusiva (cuentas que sólo ese escenario marca), y
  5. una CURVA DE CALIBRACIÓN: el mismo escenario re-evaluado con su umbral
     principal escalado por un factor, de 0,5× a 2×. Es el backtest que
     alimenta el simulador what-if del dashboard: mover el umbral y ver de
     antemano cuántas alertas y cuánta precisión/recall se ganan o se pierden.

Además calcula la COMPLEMENTARIEDAD reglas ↔ GNN: qué fraudes ve cada capa que
la otra no ve. Es el argumento central para mantener las dos.

NOTA sobre la medición: la precisión y el recall se calculan contra la etiqueta
`is_fraud` del dataset sintético, que es perfecta. En producción no existe esa
etiqueta y la performance de un escenario se mide contra las disposiciones de
los analistas (alertas confirmadas / desestimadas), con meses de rezago. Los
números de acá son ilustrativos del MÉTODO de calibración, no un pronóstico de
la tasa de falsos positivos real.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src import rules_engine, rules_temporal
from src.features import build_node_features

# Factores aplicados al umbral principal de cada escenario para el backtest.
CALIBRATION_FACTORS = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0]

# Umbral principal de cada escenario: el parámetro que un oficial de
# cumplimiento realmente movería para abrir o cerrar la canilla de alertas.
# `entero` fuerza el redondeo (grados de un nodo), `unidad` es para la UI.
PRIMARY_PARAM: dict[str, dict] = {
    "R01": {"clave": "conduit_symmetry", "label": "Simetría entrada/salida máxima",
            "unidad": "ratio", "entero": False},
    "R02": {"clave": "high_amount", "label": "Monto de operación individual",
            "unidad": "ARS", "entero": True},
    "R03": {"clave": "rapid_out_ratio", "label": "Fracción reenviada en menos de 24 h",
            "unidad": "ratio", "entero": False},
    "R04": {"clave": "dormant_min_amount", "label": "Monto de la ráfaga de reactivación",
            "unidad": "ARS", "entero": True},
    "R05": {"clave": "fanin_degree", "label": "Grado de entrada mínimo",
            "unidad": "contrapartes", "entero": True},
    "R06": {"clave": "fanout_degree", "label": "Grado de salida mínimo",
            "unidad": "contrapartes", "entero": True},
    "R07": {"clave": "agg_volume", "label": "Volumen agregado del período",
            "unidad": "ARS", "entero": True},
    # R08 se evalúa contra las listas de sanciones: no tiene umbral numérico
    # que calibrar (una coincidencia se confirma o se descarta a mano).
    "R09": {"clave": "burst_out_min_total", "label": "Monto total de la ráfaga",
            "unidad": "ARS", "entero": True},
    "R10": {"clave": "burst_in_min_total", "label": "Monto total agregado en la ventana",
            "unidad": "ARS", "entero": True},
    "R11": {"clave": "uturn_min_amount", "label": "Monto mínimo del circuito",
            "unidad": "ARS", "entero": True},
    "R12": {"clave": "passthrough_min_amount", "label": "Monto mínimo del ingreso",
            "unidad": "ARS", "entero": True},
    "R13": {"clave": "velocity_multiple", "label": "Múltiplo sobre la mediana diaria",
            "unidad": "×", "entero": False},
}

# Escenarios cuyo umbral principal vive en `rules_temporal:` y no en `rules:`.
TEMPORAL_IDS = set(rules_temporal.TEMPORAL_RULE_IDS)

# Todos los umbrales, con etiqueta para la ficha del escenario.
THRESHOLD_LABELS: dict[str, str] = {
    "high_amount": "Monto de operación individual",
    "conduit_symmetry": "Simetría entrada/salida máxima",
    "conduit_retention": "Retención de saldo máxima",
    "conduit_min_flow": "Flujo recibido mínimo",
    "rapid_out_ratio": "Fracción reenviada en menos de 24 h",
    "rapid_symmetry": "Simetría entrada/salida máxima",
    "dormant_days": "Antigüedad mínima de la cuenta (días)",
    "dormant_active_days": "Días activos máximos",
    "dormant_min_amount": "Monto de la ráfaga de reactivación",
    "fanin_min_flow": "Flujo recibido mínimo",
    "fanin_degree": "Grado de entrada mínimo",
    "fanout_degree": "Grado de salida mínimo",
    "fanout_avg_max": "Monto promedio máximo por envío",
    "fanout_min_total": "Total distribuido mínimo",
    "agg_volume": "Volumen agregado del período",
    # escenarios de ventana temporal
    "burst_out_window_h": "Ventana de la ráfaga (horas)",
    "burst_out_min_counterparties": "Destinatarios distintos mínimos",
    "burst_out_min_total": "Monto total de la ráfaga",
    "burst_in_window_h": "Ventana de la ráfaga (horas)",
    "burst_in_min_counterparties": "Remitentes distintos mínimos",
    "burst_in_min_total": "Monto total agregado en la ventana",
    "uturn_window_days": "Plazo máximo del retorno (días)",
    "uturn_tolerance": "Tolerancia de monto del retorno",
    "uturn_min_amount": "Monto mínimo del circuito",
    "passthrough_window_h": "Ventana entrada-salida (horas)",
    "passthrough_min_ratio": "Cobertura mínima de la salida",
    "passthrough_min_amount": "Monto mínimo del ingreso",
    "velocity_multiple": "Múltiplo sobre la mediana diaria",
    "velocity_min_active_days": "Días activos mínimos (baseline)",
    "velocity_min_peak": "Volumen mínimo del día pico",
}

# Umbrales que consume cada escenario (para mostrar su ficha completa).
RULE_THRESHOLDS: dict[str, list[str]] = {
    "R01": ["conduit_symmetry", "conduit_retention", "conduit_min_flow"],
    "R02": ["high_amount"],
    "R03": ["rapid_out_ratio", "rapid_symmetry", "conduit_min_flow"],
    "R04": ["dormant_days", "dormant_active_days", "dormant_min_amount"],
    "R05": ["fanin_degree", "fanin_min_flow"],
    "R06": ["fanout_degree", "fanout_avg_max", "fanout_min_total"],
    "R07": ["agg_volume"],
    "R08": [],
    "R09": ["burst_out_window_h", "burst_out_min_counterparties", "burst_out_min_total"],
    "R10": ["burst_in_window_h", "burst_in_min_counterparties", "burst_in_min_total"],
    "R11": ["uturn_window_days", "uturn_tolerance", "uturn_min_amount"],
    "R12": ["passthrough_window_h", "passthrough_min_ratio", "passthrough_min_amount"],
    "R13": ["velocity_multiple", "velocity_min_active_days", "velocity_min_peak"],
}

SEGMENTS = ["personal", "business", "merchant"]


# ── helpers ───────────────────────────────────────────────────────────────────

def load_config(path: str = "config/config.yaml") -> dict:
    """Config propia: importarla de export_dashboard arrastraría torch, que no
    hace falta para el backtest (sólo para la complementariedad, cargada aparte)."""
    with open(path) as f:
        return yaml.safe_load(f)


def _thresholds(cfg: dict) -> dict:
    """Umbrales vigentes = defaults del motor pisados por config.yaml."""
    t = rules_engine._default_thresholds()
    if cfg and isinstance(cfg.get("rules"), dict):
        t = {**t, **cfg["rules"]}
    tt = rules_temporal._default_thresholds()
    if cfg and isinstance(cfg.get("rules_temporal"), dict):
        tt = {**tt, **cfg["rules_temporal"]}
    # Un único diccionario de umbrales: los escenarios no comparten claves entre
    # motores, así que la ficha y la calibración pueden tratarlos igual.
    return {**t, **tt}


def _split_cfg(t: dict, cfg: dict | None) -> dict:
    """Reconstruye el cfg que espera cada motor a partir de los umbrales planos."""
    agg = set(rules_engine._default_thresholds())
    tmp = set(rules_temporal._default_thresholds())
    return {
        **(cfg or {}),
        "rules": {k: v for k, v in t.items() if k in agg},
        "rules_temporal": {k: v for k, v in t.items() if k in tmp},
    }


def _temporal_mask(rid: str, txn: pd.DataFrame, acc: pd.DataFrame,
                   index: pd.Index, t: dict, cfg: dict) -> np.ndarray:
    """Corre un escenario temporal aislado y lo alinea con el índice de cuentas."""
    hits = rules_temporal.evaluate_rules(txn, acc, _split_cfg(t, cfg), only=[rid])
    return index.isin(list(hits.get(rid, {})))


def _scale(value, factor: float, entero: bool):
    """Escala un umbral (escalar o segmentado por tipo de cuenta)."""
    if isinstance(value, dict):
        return {k: (int(round(v * factor)) if entero else round(v * factor, 4))
                for k, v in value.items()}
    return int(round(value * factor)) if entero else round(value * factor, 4)


def _fmt(value, entero: bool) -> str:
    """Representación legible de un umbral, segmentado o no."""
    def one(v):
        return f"{int(v):,}".replace(",", ".") if entero else f"{v:g}"
    if isinstance(value, dict):
        return " / ".join(one(value[s]) for s in SEGMENTS if s in value)
    return one(value)


def _metrics(mask: np.ndarray, y: np.ndarray) -> dict:
    """Métricas operativas de un escenario contra la etiqueta del dataset."""
    fired = int(mask.sum())
    tp = int((mask & (y == 1)).sum())
    fp = fired - tp
    n_fraud = int((y == 1).sum())
    n_legit = int((y == 0).sum())
    base = n_fraud / len(y) if len(y) else 0.0
    precision = tp / fired if fired else 0.0
    return {
        "disparos": fired,
        "tp": tp,
        "fp": fp,
        "precision": round(precision, 4),
        "recall": round(tp / n_fraud, 4) if n_fraud else 0.0,
        "tasa_fp": round(fp / n_legit, 4) if n_legit else 0.0,
        "lift": round(precision / base, 2) if base and fired else 0.0,
    }


# ── construcción ──────────────────────────────────────────────────────────────

def _calibration_curve(rid: str, feats: pd.DataFrame, y: np.ndarray, t: dict,
                       txn: pd.DataFrame | None = None, acc: pd.DataFrame | None = None,
                       cfg: dict | None = None) -> dict | None:
    """
    Re-evalúa el escenario con su umbral principal escalado (backtest what-if).

    Los escenarios temporales se re-corren sobre el stream en cada punto de la
    curva — más caro que re-aplicar una máscara vectorizada, pero es la única
    forma honesta de medirlos: su disparo depende de la secuencia, no de un
    agregado que se pueda recalcular con una comparación.
    """
    spec = PRIMARY_PARAM.get(rid)
    if spec is None:
        return None
    clave, entero = spec["clave"], spec["entero"]
    actual = t[clave]
    es_temporal = rid in TEMPORAL_IDS
    if es_temporal and (txn is None or acc is None):
        # Sin el stream no hay nada que backtestear: estos escenarios no se
        # pueden recalcular desde las features agregadas.
        return None

    puntos = []
    for factor in CALIBRATION_FACTORS:
        probe = {**t, clave: _scale(actual, factor, entero)}
        if es_temporal:
            mask = _temporal_mask(rid, txn, acc, feats.index, probe, cfg)
        else:
            mask = rules_engine._rule_masks(feats, probe)[rid].to_numpy()
        puntos.append({
            "factor": factor,
            "valor": _fmt(probe[clave], entero),
            **_metrics(mask, y),
        })

    # Dirección real (medida, no supuesta): ¿subir el umbral abre o cierra la canilla?
    direccion = "menos_alertas" if puntos[-1]["disparos"] <= puntos[0]["disparos"] else "mas_alertas"

    return {
        "parametro": clave,
        "label": spec["label"],
        "unidad": spec["unidad"],
        "segmentado": isinstance(actual, dict),
        "valor_actual": _fmt(actual, entero),
        "direccion": direccion,
        "puntos": puntos,
    }


def _r08_mask(feats: pd.DataFrame, raw: str) -> np.ndarray:
    """R08 no sale de las features: son las cuentas con coincidencia en listas."""
    path = Path(raw) / "sanctions_hits.csv"
    if not path.exists():
        return np.zeros(len(feats), dtype=bool)
    hits = set(pd.read_csv(path)["account_id"])
    return feats.index.isin(hits)


def build(config_path: str = "config/config.yaml") -> dict:
    cfg = load_config(config_path)
    raw = cfg["data"]["raw_dir"]
    out_dir = cfg["paths"]["dashboard_data_dir"]

    acc = pd.read_csv(f"{raw}/accounts.csv")
    txn = pd.read_csv(f"{raw}/transactions.csv")
    feats = build_node_features(acc, txn).set_index("account_id")
    y = feats["is_fraud"].to_numpy().astype(int)
    t = _thresholds(cfg)

    masks = {rid: m.to_numpy() for rid, m in rules_engine._rule_masks(feats, t).items()}
    masks["R08"] = _r08_mask(feats, raw)

    # Escenarios de ventana temporal: una sola pasada sobre el stream para los cinco.
    temporal_hits = rules_temporal.evaluate_rules(txn, acc, _split_cfg(t, cfg))
    for rid, hits in temporal_hits.items():
        masks[rid] = feats.index.isin(list(hits))

    # Cuántos escenarios dispara cada cuenta (para medir el aporte exclusivo).
    stack = np.vstack([masks[r["id"]] for r in rules_engine.RULES])
    n_fired_per_account = stack.sum(axis=0)

    atype = feats["account_type"].to_numpy()

    escenarios = []
    for rule in rules_engine.RULES:
        rid = rule["id"]
        mask = masks[rid]
        exclusivo = int((mask & (n_fired_per_account == 1)).sum())

        por_tipo = {}
        for seg in SEGMENTS:
            sel = atype == seg
            if sel.any():
                por_tipo[seg] = _metrics(mask[sel], y[sel])

        umbrales = [{
            "clave": k,
            "label": THRESHOLD_LABELS.get(k, k),
            "valor": t[k],
            "segmentado": isinstance(t[k], dict),
        } for k in RULE_THRESHOLDS.get(rid, [])]

        escenarios.append({
            **rule,
            "estado": "activo",
            "calibrable": rid in PRIMARY_PARAM,
            "fuente": ("stream de transacciones (ventana móvil)" if rid in TEMPORAL_IDS
                       else "features transaccionales" if rid in PRIMARY_PARAM
                       else "listas de sanciones"),
            "cita_evidencia": rid in TEMPORAL_IDS,
            "puntos_severidad": t["severity_points"][rule["severidad"]],
            "umbrales": umbrales,
            "metricas": _metrics(mask, y),
            "por_tipo": por_tipo,
            "aporte_exclusivo": exclusivo,
            "calibracion": _calibration_curve(rid, feats, y, t, txn, acc, cfg),
        })

    # ── motor completo + complementariedad con el GNN ─────────────────────────
    any_mask = stack.any(axis=0)

    def _motor_mask(motor: str) -> np.ndarray:
        ids = [r["id"] for r in rules_engine.RULES if r["motor"] == motor]
        return np.vstack([masks[i] for i in ids]).any(axis=0)

    agg_mask, tmp_mask = _motor_mask("agregado"), _motor_mask("temporal")
    n_agg = sum(1 for r in rules_engine.RULES if r["motor"] == "agregado")
    resumen = {
        "escenarios": len(rules_engine.RULES),
        "activos": len(rules_engine.RULES),
        **_metrics(any_mask, y),
        "por_motor": {
            "agregado": {"escenarios": n_agg, **_metrics(agg_mask, y)},
            "temporal": {"escenarios": len(rules_engine.RULES) - n_agg,
                         **_metrics(tmp_mask, y)},
        },
        # Cuánto fraude ve el motor temporal que el agregado no ve, y al revés:
        # la comparación interna que justifica sostener las dos familias.
        "cruce_motores": {
            "solo_agregado": int((agg_mask & ~tmp_mask & (y == 1)).sum()),
            "solo_temporal": int((~agg_mask & tmp_mask & (y == 1)).sum()),
            "ambos": int((agg_mask & tmp_mask & (y == 1)).sum()),
        },
    }

    complementariedad = _complementarity(feats, y, any_mask, cfg)

    poblacion = {
        "cuentas": int(len(feats)),
        "fraude": int((y == 1).sum()),
        "legitimas": int((y == 0).sum()),
        "tasa_base": round(float((y == 1).mean()), 4),
    }

    obj = {
        "generated_at": date.today().isoformat(),
        "poblacion": poblacion,
        "resumen": resumen,
        "complementariedad": complementariedad,
        "factores_calibracion": CALIBRATION_FACTORS,
        "escenarios": escenarios,
    }

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    with open(f"{out_dir}/scenarios.json", "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    kb = Path(f"{out_dir}/scenarios.json").stat().st_size / 1024
    print(f"  -> {out_dir}/scenarios.json  ({kb:.1f} KB · {len(escenarios)} escenarios · "
          f"{resumen['disparos']} cuentas marcadas · precisión {resumen['precision']:.0%})")
    return obj


def _complementarity(feats: pd.DataFrame, y: np.ndarray, any_mask: np.ndarray,
                     cfg: dict, gnn_cut: float = 0.5) -> dict:
    """
    Reparto de los fraudes entre las dos capas de detección. Responde la pregunta
    que hace el regulador: si ya tenés un modelo, ¿para qué querés reglas?
    """
    try:
        import torch
        import torch.nn.functional as F

        from src.models.graphsage import GraphSAGE
    except Exception as exc:  # pragma: no cover - entorno sin torch
        print(f"  (complementariedad omitida: {exc})")
        return {}

    processed = cfg["data"]["processed_dir"]
    graph_path = Path(processed) / "graph.pt"
    ckpt_path = Path("models/graphsage_best.pt")
    if not (graph_path.exists() and ckpt_path.exists()):
        print("  (complementariedad omitida: falta graph.pt o el checkpoint)")
        return {}

    data = torch.load(graph_path, weights_only=False)
    ckpt = torch.load(ckpt_path, weights_only=False)
    model = GraphSAGE(data.num_node_features, **{
        k: ckpt["config"][k] for k in ["hidden_channels", "num_layers", "dropout"]
    })
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    with torch.no_grad():
        scores = F.softmax(model(data.x, data.edge_index), dim=1)[:, 1].numpy()

    # Alinear los scores (indexados por nodo del grafo) con el frame de features.
    id2score = {nid: float(scores[i]) for i, nid in enumerate(data.node_ids)}
    gnn = feats.index.map(lambda a: id2score.get(a, 0.0)).to_numpy()

    gnn_mask = gnn >= gnn_cut
    is_fraud = y == 1
    return {
        "corte_gnn": gnn_cut,
        "fraude_total": int(is_fraud.sum()),
        "ambos": int((is_fraud & any_mask & gnn_mask).sum()),
        "solo_reglas": int((is_fraud & any_mask & ~gnn_mask).sum()),
        "solo_gnn": int((is_fraud & ~any_mask & gnn_mask).sum()),
        "ninguno": int((is_fraud & ~any_mask & ~gnn_mask).sum()),
        "nota": (
            "El score del GNN se calcula sobre el grafo completo, que incluye los "
            "nodos de entrenamiento: la cobertura del modelo acá está sobreestimada "
            "respecto de su performance out-of-sample (ver Gobernanza para las "
            "métricas de test). La lectura válida es relativa — qué aporta cada capa "
            "sobre la otra — no el valor absoluto."
        ),
    }


if __name__ == "__main__":
    build()
