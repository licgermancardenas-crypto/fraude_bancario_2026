"""Tests de la capa de gestión de escenarios (backtest de calibración)."""
import numpy as np
import pandas as pd
import pytest

from src.export_scenarios import (
    CALIBRATION_FACTORS, PRIMARY_PARAM, _calibration_curve, _fmt, _metrics, _scale,
)


def test_scale_escalar_y_segmentado():
    assert _scale(12, 1.5, entero=True) == 18
    assert _scale(0.15, 2.0, entero=False) == 0.3
    assert _scale({"personal": 12, "business": 40}, 1.5, entero=True) == {
        "personal": 18, "business": 60,
    }


def test_fmt_segmentado_respeta_el_orden_de_segmentos():
    assert _fmt({"merchant": 70, "personal": 12, "business": 40}, entero=True) == "12 / 40 / 70"
    assert _fmt(15000, entero=True) == "15.000"
    assert _fmt(0.15, entero=False) == "0.15"


def test_metrics_precision_recall_y_lift():
    y = np.array([1, 1, 1, 0, 0, 0, 0, 0, 0, 0])  # tasa base 0.3
    mask = np.array([1, 1, 0, 1, 0, 0, 0, 0, 0, 0], dtype=bool)
    m = _metrics(mask, y)
    assert m["disparos"] == 3 and m["tp"] == 2 and m["fp"] == 1
    assert m["precision"] == pytest.approx(2 / 3, abs=1e-4)
    assert m["recall"] == pytest.approx(2 / 3, abs=1e-4)
    assert m["tasa_fp"] == pytest.approx(1 / 7, abs=1e-4)
    assert m["lift"] == pytest.approx((2 / 3) / 0.3, abs=0.01)


def test_metrics_sin_disparos_no_divide_por_cero():
    y = np.array([1, 0, 0, 0])
    m = _metrics(np.zeros(4, dtype=bool), y)
    assert m == {"disparos": 0, "tp": 0, "fp": 0, "precision": 0.0,
                 "recall": 0.0, "tasa_fp": 0.0, "lift": 0.0}


def _feats(n=200) -> pd.DataFrame:
    """Frame mínimo con las columnas que consumen las máscaras del motor."""
    rng = np.random.default_rng(42)
    return pd.DataFrame(index=pd.Index([f"ACC{i:05d}" for i in range(n)], name="account_id"), data={
        "account_type": ["personal"] * n,
        "is_fraud": rng.integers(0, 2, n),
        "degree_in": rng.integers(0, 40, n),
        "degree_out": rng.integers(0, 40, n),
        "unique_senders": rng.integers(0, 40, n),
        "unique_receivers": rng.integers(0, 40, n),
        "total_received": rng.uniform(0, 100_000, n),
        "total_sent": rng.uniform(0, 100_000, n),
        "avg_sent": rng.uniform(0, 8_000, n),
        "max_sent": rng.uniform(0, 60_000, n),
        "max_received": rng.uniform(0, 60_000, n),
        "in_out_symmetry": rng.uniform(0, 1, n),
        "balance_retention": rng.uniform(0, 3, n),
        "rapid_out_ratio": rng.uniform(0, 1, n),
        "opened_days_ago": rng.integers(0, 3000, n),
        "active_days": rng.integers(0, 200, n),
    })


def _stream(feats: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Stream mínimo alineado con `_feats`, con un caso de cada familia temporal:
    una ráfaga de dispersión, una de agregación, un circuito y un tránsito.
    Alcanza para que la curva de calibración de los escenarios temporales tenga
    puntos que medir en ambos sentidos del umbral.
    """
    ids = list(feats.index)
    t0, filas = 1_700_000_000, []
    filas += [(ids[0], ids[10 + i], 4_000, i * 3_600) for i in range(5)]            # R09
    filas += [(ids[20 + i], ids[1], 4_000, i * 3_600) for i in range(5)]            # R10
    filas += [(ids[2], ids[30], 120_000, 0), (ids[31], ids[2], 118_000, 5 * 86_400)]  # R11
    filas += [(ids[40], ids[3], 30_000, 0), (ids[3], ids[41], 28_000, 6 * 3_600)]     # R12
    txn = pd.DataFrame([
        {"transaction_id": f"TXN{i:05d}", "src": s, "dst": d, "amount": float(a),
         "timestamp": t0 + off, "transaction_type": "transfer"}
        for i, (s, d, a, off) in enumerate(filas)
    ])
    acc = pd.DataFrame({"account_id": ids, "account_type": "personal"})
    return txn, acc


@pytest.mark.parametrize("rid", sorted(PRIMARY_PARAM))
def test_curva_de_calibracion_cubre_todos_los_factores(rid):
    from src.export_scenarios import _thresholds

    feats = _feats()
    y = feats["is_fraud"].to_numpy()
    txn, acc = _stream(feats)
    cal = _calibration_curve(rid, feats, y, _thresholds({}), txn, acc, {})

    assert cal is not None
    assert [p["factor"] for p in cal["puntos"]] == CALIBRATION_FACTORS
    assert cal["direccion"] in {"menos_alertas", "mas_alertas"}
    # El punto vigente (1x) siempre existe: es el ancla del simulador what-if.
    assert any(p["factor"] == 1.0 for p in cal["puntos"])


def test_curva_es_monotona_en_volumen_de_alertas():
    """Subir un umbral '>=' sólo puede cerrar la canilla, nunca abrirla."""
    from src.export_scenarios import _thresholds

    feats = _feats()
    y = feats["is_fraud"].to_numpy()
    cal = _calibration_curve("R05", feats, y, _thresholds({}))
    disparos = [p["disparos"] for p in cal["puntos"]]

    assert cal["direccion"] == "menos_alertas"
    assert disparos == sorted(disparos, reverse=True)


def test_r08_no_es_calibrable():
    """El escenario de sanciones no tiene umbral numérico que mover."""
    assert "R08" not in PRIMARY_PARAM
    assert _calibration_curve("R08", _feats(), np.zeros(200), {}) is None


def test_calibracion_temporal_requiere_el_stream():
    """Sin transacciones no se puede backtestear un escenario de ventana."""
    from src.export_scenarios import _thresholds

    feats = _feats()
    y = feats["is_fraud"].to_numpy()
    assert _calibration_curve("R12", feats, y, _thresholds({})) is None
