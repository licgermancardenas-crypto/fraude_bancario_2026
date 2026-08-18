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
    return pd.DataFrame({
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


@pytest.mark.parametrize("rid", sorted(PRIMARY_PARAM))
def test_curva_de_calibracion_cubre_todos_los_factores(rid):
    from src.export_scenarios import _thresholds

    feats = _feats()
    y = feats["is_fraud"].to_numpy()
    cal = _calibration_curve(rid, feats, y, _thresholds({}))

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
