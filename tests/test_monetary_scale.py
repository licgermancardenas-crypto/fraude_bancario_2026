"""
La escala monetaria vive en config.yaml (monetary.scale) y los umbrales de ambos
motores de reglas están expresados en esa misma escala. Estos tests existen para
que datos y umbrales no puedan volver a desincronizarse en silencio: los defaults
hardcodeados de rules_engine/rules_temporal duplican el config por conveniencia,
y un cambio en uno solo de los dos lados rompería las reglas sin ruido.
"""
import pandas as pd
import pytest
import yaml

from src.generate import MONETARY_COLS_ACC, MONETARY_COLS_TXN, rescale_amounts
from src.rules_engine import _default_thresholds as agg_defaults
from src.rules_temporal import _default_thresholds as tmp_defaults


@pytest.fixture(scope="module")
def cfg():
    with open("config/config.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_monetary_section_present(cfg):
    m = cfg["monetary"]
    assert m["currency"] == "ARS"
    assert m["scale"] >= 1
    assert m["smvm"] > 0
    assert m["uif_efectivo_smvm"] == 40      # Res. UIF 78/2025


def test_defaults_match_config_aggregated(cfg):
    """Los defaults de rules_engine deben ser idénticos al config."""
    defaults, conf = agg_defaults(), cfg["rules"]
    for key, value in conf.items():
        assert key in defaults, f"config define {key} pero el default no lo tiene"
        assert defaults[key] == value, f"{key}: default={defaults[key]} config={value}"


def test_defaults_match_config_temporal(cfg):
    """Ídem para los escenarios de ventana temporal."""
    defaults, conf = tmp_defaults(), cfg["rules_temporal"]
    for key, value in conf.items():
        assert key in defaults, f"config define {key} pero el default no lo tiene"
        assert defaults[key] == value, f"{key}: default={defaults[key]} config={value}"


def test_thresholds_are_plausible_in_smvm(cfg):
    """
    Anclaje declarado: la transferencia individual atípica de una persona física
    debe caer en el orden de unos pocos SMVM. Si alguien mueve la escala sin
    mover los umbrales (o al revés), este test lo delata.
    """
    smvm = cfg["monetary"]["smvm"]
    personal = cfg["rules"]["high_amount"]["personal"]
    assert 2 <= personal / smvm <= 8, f"high_amount.personal = {personal/smvm:.1f} SMVM"


def _sample():
    txn = pd.DataFrame({
        "src": ["A", "B"], "dst": ["B", "C"],
        "amount": [100.0, 250.5], "comision": [1.0, 0.0], "impuesto": [0.6, 1.5],
        "timestamp": [1, 2], "transaction_type": ["transfer", "payment"],
        "is_fraud": [0, 1], "mcc": [5411.0, 5812.0],
    })
    acc = pd.DataFrame({
        "account_id": ["A", "B", "C"], "balance": [10.0, 20.0, 30.0],
        "risk_score": [0.1, 0.2, 0.3], "account_type": ["personal"] * 3,
        "opened_days_ago": [100, 200, 300], "is_fraud": [0, 1, 0],
    })
    return txn, acc


def test_rescale_only_touches_monetary_columns():
    """El grafo y las etiquetas tienen que sobrevivir intactos al reescalado."""
    txn, acc = _sample()
    txn2, acc2 = rescale_amounts(txn, acc, 100)
    for col in txn.columns:
        if col not in MONETARY_COLS_TXN:
            assert txn[col].equals(txn2[col]), col
    for col in acc.columns:
        if col not in MONETARY_COLS_ACC:
            assert acc[col].equals(acc2[col]), col


def test_rescale_is_linear():
    txn, acc = _sample()
    txn2, acc2 = rescale_amounts(txn, acc, 100)
    assert txn2["amount"].tolist() == [10000.0, 25050.0]
    assert txn2["impuesto"].tolist() == [60.0, 150.0]
    assert acc2["balance"].tolist() == [1000.0, 2000.0, 3000.0]


def test_rescale_identity_is_a_noop():
    txn, acc = _sample()
    txn2, acc2 = rescale_amounts(txn, acc, 1)
    assert txn2["amount"].equals(txn["amount"])
    assert acc2["balance"].equals(acc["balance"])


def test_rescale_preserves_ratios():
    """
    La razón entre dos montos es lo que miran las reglas de simetría/tránsito
    (passthrough_min_ratio, conduit_symmetry): debe ser invariante a la escala.
    """
    txn, acc = _sample()
    before = txn["amount"].iloc[1] / txn["amount"].iloc[0]
    txn2, _ = rescale_amounts(txn, acc, 100)
    after = txn2["amount"].iloc[1] / txn2["amount"].iloc[0]
    assert before == pytest.approx(after)
