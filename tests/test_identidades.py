"""Tests de generación de identidades AR (CUIL) y features de nodo."""
import re as _re

import pandas as pd

from src.enrich_personas import _cuil
from src.features import build_node_features


def test_cuil_format():
    c = _cuil(20, 12345678)
    assert _re.match(r"^\d{2}-\d{8}-\d$", c), c


def test_cuil_deterministic():
    assert _cuil(27, 40000000) == _cuil(27, 40000000)


def test_build_node_features_columns_and_no_nan():
    acc = pd.DataFrame({
        "account_id": ["A", "B", "C"], "balance": [100.0, 200.0, 300.0],
        "risk_score": [0.1, 0.2, 0.3], "account_type": ["personal", "business", "merchant"],
        "opened_days_ago": [100, 200, 300], "is_fraud": [0, 1, 0],
    })
    txn = pd.DataFrame({
        "src": ["A", "A", "B"], "dst": ["B", "C", "C"], "amount": [100.0, 50.0, 200.0],
        "timestamp": [1000, 2000, 3000], "is_fraud": [0, 1, 0],
    })
    feats = build_node_features(acc, txn)
    assert len(feats) == 3
    for c in ["degree_in", "degree_out", "total_received", "total_sent", "in_out_symmetry"]:
        assert c in feats.columns
    assert not feats[["degree_in", "degree_out", "total_received"]].isna().any().any()
