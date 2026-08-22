"""Tests del motor de reglas AML (lógica pura, determinista)."""
import pandas as pd

from src import rules_engine as re


def _feats(**over):
    base = dict(
        in_out_symmetry=0.9, balance_retention=5.0, total_received=1000.0, total_sent=1000.0,
        max_sent=100.0, max_received=100.0, rapid_out_ratio=0.0, active_days=200,
        opened_days_ago=100, degree_in=1, unique_senders=1, degree_out=1, unique_receivers=1,
        avg_sent=100.0, account_type="personal",
    )
    base.update(over)
    return pd.DataFrame([base], index=["ACC0000001"])


def test_catalogue_structure():
    cat = re.catalogue()
    # El catálogo cubre los dos motores: agregado (R01-R08) y temporal (R09-R13).
    assert len(cat) == 13
    for r in cat:
        assert {"id", "nombre", "descripcion", "cita", "severidad", "motor"} <= set(r)
        assert r["severidad"] in {"alta", "media", "baja"}
        assert r["motor"] in {"agregado", "temporal"}
    assert sum(1 for r in cat if r["motor"] == "agregado") == 8
    assert sum(1 for r in cat if r["motor"] == "temporal") == 5


def test_aggregate_engine_ignores_temporal_rules():
    """`rules_engine.evaluate` no debe disparar escenarios que no evalúa."""
    res = re.evaluate(_feats(in_out_symmetry=0.0, balance_retention=0.0, total_received=99_999.0))
    for entry in res.values():
        assert all(rid in re._TRANSACTIONAL_RULE_IDS for rid in entry["rules_fired"])


def test_score_from_ids_caps_and_severity():
    assert re.score_from_ids([]) == 0
    assert re.score_from_ids(["R08"]) == 40          # severidad alta
    assert re.score_from_ids(["R08", "R08"]) == 80
    assert re.score_from_ids(["R08", "R08", "R08"]) == 100   # tope 100
    assert re.score_from_ids(["ZZZ"]) == 0           # id desconocido se ignora


def test_evaluate_benign_fires_nothing():
    # una cuenta sin reglas disparadas no queda flagueada (no aparece en el output)
    out = re.evaluate(_feats())
    assert "ACC0000001" not in out or out["ACC0000001"]["rules_fired"] == []


def test_evaluate_high_amount_triggers_r02():
    out = re.evaluate(_feats(max_sent=20000.0))["ACC0000001"]
    assert "R02" in out["rules_fired"]
    # el score debe ser consistente con score_from_ids sobre las reglas disparadas
    assert out["rule_score"] == re.score_from_ids(out["rules_fired"])
    assert out["rule_score"] > 0
