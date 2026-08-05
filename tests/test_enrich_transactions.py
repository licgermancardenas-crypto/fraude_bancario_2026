"""Tests del enriquecimiento transaccional — la invariante clave: NO altera la
estructura base (por eso el grafo/modelo quedan intactos)."""
import pandas as pd

from src.generate import enrich_transactions

BASE = ["transaction_id", "src", "dst", "amount", "timestamp", "transaction_type", "is_fraud"]


def _data():
    acc = pd.DataFrame({"account_id": ["A", "B", "C"], "account_type": ["personal", "business", "merchant"]})
    txn = pd.DataFrame({
        "transaction_id": ["T1", "T2", "T3", "T4"],
        "src": ["A", "B", "C", "A"], "dst": ["B", "C", "A", "C"],
        "amount": [100.0, 60000.0, 2500.0, 500.0], "timestamp": [1, 2, 3, 4],
        "transaction_type": ["transfer", "payment", "withdrawal", "payment"],
        "is_fraud": [0, 1, 0, 0],
    })
    return acc, txn


def test_base_columns_unchanged():
    acc, txn = _data()
    out = enrich_transactions(txn.copy(), acc)
    pd.testing.assert_frame_equal(out[BASE].reset_index(drop=True), txn[BASE].reset_index(drop=True))


def test_new_columns_and_domains():
    acc, txn = _data()
    out = enrich_transactions(txn, acc)
    for c in ["canal", "canal_codigo", "cbu_dst", "glosa", "estado", "comision", "impuesto", "moneda", "referencia"]:
        assert c in out.columns
    assert (out["moneda"] == "ARS").all()
    assert set(out["estado"]).issubset({"liquidada", "pendiente", "reversada"})
    assert out["cbu_dst"].astype(str).str.len().eq(22).all()
    assert (out["comision"] >= 0).all() and (out["impuesto"] >= 0).all()


def test_deterministic():
    acc, txn = _data()
    a = enrich_transactions(txn, acc, seed=42)
    b = enrich_transactions(txn, acc, seed=42)
    pd.testing.assert_frame_equal(a, b)
