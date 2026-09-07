"""
Tests del enriquecimiento transaccional.

La invariante clave sigue siendo la misma —el enriquecimiento NO altera la
estructura base, y por eso el grafo y el modelo quedan intactos— pero el
contrato ahora está partido en dos:

  - `generate.enrich_transactions` ASIGNA lo que no es derivable (canal, MCC,
    estado, comisión, impuesto) y lo devuelve como categóricas de códigos;
  - `txn_store.hydrate` DERIVA la capa de presentación (código de canal, CBU,
    alias, rubro, glosa, moneda, referencia) sobre el subconjunto que se vaya a
    mostrar.

La partición existe porque a ~11M de filas cada columna de texto costaba
cientos de MB, y las derivables sólo hacen falta para las pocas miles de filas
que llegan al dashboard.
"""
import numpy as np
import pandas as pd

from src import txn_store
from src.generate import enrich_transactions

BASE = ["src", "dst", "amount", "timestamp", "transaction_type", "is_fraud"]


def _data():
    acc = pd.DataFrame({
        "account_id": ["A", "B", "C"],
        "account_type": ["personal", "business", "merchant"],
    })
    # src/dst van como índice posicional sobre `acc`: el generador nunca
    # materializa los account_id fila por fila.
    txn = pd.DataFrame({
        "src": np.array([0, 1, 2, 0], dtype=np.int32),
        "dst": np.array([1, 2, 0, 2], dtype=np.int32),
        "amount": np.array([100.0, 60000.0, 2500.0, 500.0], dtype=np.float32),
        "timestamp": np.array([1, 2, 3, 4], dtype=np.int32),
        "transaction_type": pd.Categorical(
            ["transfer", "payment", "withdrawal", "payment"]),
        "is_fraud": np.array([0, 1, 0, 0], dtype=np.int8),
    })
    return acc, txn


def test_base_columns_unchanged():
    acc, txn = _data()
    out = enrich_transactions(txn.copy(), acc)
    pd.testing.assert_frame_equal(
        out[BASE].reset_index(drop=True), txn[BASE].reset_index(drop=True)
    )


def test_new_columns_and_domains():
    acc, txn = _data()
    out = enrich_transactions(txn, acc)
    for c in ["canal", "mcc", "estado", "comision", "impuesto"]:
        assert c in out.columns
    assert set(out["estado"].astype(str)).issubset({"liquidada", "pendiente", "reversada"})
    assert set(out["canal"].astype(str)).issubset(set(txn_store.CANAL_COD))
    assert (out["comision"] >= 0).all() and (out["impuesto"] >= 0).all()
    # el MCC sólo tiene sentido en pagos a comercio o empresa
    es_pago = out["transaction_type"].astype(str) == "payment"
    assert (out.loc[~es_pago, "mcc"].astype(str) == "").all()


def test_deterministic():
    acc, txn = _data()
    a = enrich_transactions(txn, acc, seed=42)
    b = enrich_transactions(txn, acc, seed=42)
    pd.testing.assert_frame_equal(a, b)


def test_hydrate_deriva_la_capa_de_presentacion():
    acc, txn = _data()
    enriched = enrich_transactions(txn, acc)
    # hydrate espera los account_id, como los devuelve txn_store.load_transactions
    enriched["src"] = pd.Categorical.from_codes(enriched["src"], acc["account_id"])
    enriched["dst"] = pd.Categorical.from_codes(enriched["dst"], acc["account_id"])
    out = txn_store.hydrate(enriched, acc, seed=42)

    for c in ["transaction_id", "canal_codigo", "cbu_dst", "alias_dst",
              "rubro", "glosa", "moneda", "referencia"]:
        assert c in out.columns
    assert (out["moneda"] == "ARS").all()
    assert out["cbu_dst"].astype(str).str.len().eq(22).all()
    assert out["transaction_id"].tolist() == [f"TXN{i:09d}" for i in range(len(out))]
    # el CBU es estable por cuenta: la misma cuenta destino da el mismo número
    por_cuenta = out.groupby(out["dst"].astype(str), observed=True)["cbu_dst"].nunique()
    assert (por_cuenta == 1).all()


def test_hydrate_es_determinista():
    acc, txn = _data()
    enriched = enrich_transactions(txn, acc)
    enriched["src"] = pd.Categorical.from_codes(enriched["src"], acc["account_id"])
    enriched["dst"] = pd.Categorical.from_codes(enriched["dst"], acc["account_id"])
    a = txn_store.hydrate(enriched, acc, seed=42)
    b = txn_store.hydrate(enriched, acc, seed=42)
    pd.testing.assert_frame_equal(a, b)
