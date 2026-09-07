"""
Genera dashboard/public/data/transactions_sample.json — una muestra de
transacciones para el Transaction Explorer.

Es una MUESTRA (2.600 de 11,2M) para que el explorador sea navegable en el
browser. Se elige PRIMERO y se materializa después: `load_transactions(rows=...)`
trae sólo esas filas del almacén columnar en vez de levantar el libro entero.

Los campos transaccionales se dividen en dos: canal, MCC, estado, comisión e
impuesto están ALMACENADOS (los emite src/generate.py); transaction_id, CBU,
alias, rubro, glosa, moneda y referencia son DERIVADOS y los reconstruye
`txn_store.hydrate()` sobre la muestra — el almacén no los guarda porque a 11,2M
filas cada uno costaría ~700 MB de strings. La derivación es determinística, así
que el valor es el mismo que si estuviera en disco.
"""
import json

import numpy as np
import pandas as pd

from src.export_dashboard import load_config

from src import txn_store

TIPO_MAP = {"transfer": "Transferencia", "payment": "Pago", "withdrawal": "Extracción"}


def build(config_path="config/config.yaml"):
    cfg = load_config(config_path)
    data_dir = cfg["paths"]["dashboard_data_dir"]
    raw = cfg["data"]["raw_dir"]

    accounts = pd.read_csv(f"{raw}/accounts.csv")
    acc = accounts.set_index("account_id")
    per = pd.read_csv(f"{raw}/personas.csv").set_index("account_id")
    name = per["nombre_completo"].to_dict()
    atype = acc["account_type"].to_dict()

    # La muestra se define sobre la columna is_fraud sola (11 MB) y recién
    # después se traen esas filas completas del almacén.
    flags = txn_store.load_transactions(raw, columns=["is_fraud"])["is_fraud"]
    fraud_rows = pd.Series(np.flatnonzero(flags.to_numpy() == 1))
    legit_rows = pd.Series(np.flatnonzero(flags.to_numpy() == 0))
    sel = np.concatenate([
        fraud_rows.sample(min(1600, len(fraud_rows)), random_state=42).to_numpy(),
        legit_rows.sample(min(1000, len(legit_rows)), random_state=42).to_numpy(),
    ])

    sample = txn_store.load_transactions(raw, rows=sel, with_row_id=True)
    sample = txn_store.hydrate(sample, accounts, row_ids=sel)
    sample = sample.sort_values("timestamp", ascending=False)

    def s(v, default=""):
        return default if pd.isna(v) else v

    rows = []
    for t in sample.itertuples():
        rows.append({
            "id": t.transaction_id,
            "ts": int(t.timestamp),
            "src": t.src, "dst": t.dst,
            "src_name": name.get(t.src, ""), "dst_name": name.get(t.dst, ""),
            "src_type": atype.get(t.src, ""), "dst_type": atype.get(t.dst, ""),
            "amount": round(float(t.amount), 2),
            "tipo": TIPO_MAP.get(t.transaction_type, t.transaction_type),
            "canal": s(getattr(t, "canal", "")),
            "canal_codigo": s(getattr(t, "canal_codigo", "")),
            "cbu_dst": str(s(getattr(t, "cbu_dst", ""))),
            "alias_dst": s(getattr(t, "alias_dst", "")),
            "mcc": str(s(getattr(t, "mcc", ""))),
            "rubro": s(getattr(t, "rubro", "")),
            "glosa": s(getattr(t, "glosa", "")),
            "concepto": s(getattr(t, "glosa", "")),
            "estado": s(getattr(t, "estado", "liquidada")),
            "comision": round(float(s(getattr(t, "comision", 0), 0)), 2),
            "impuesto": round(float(s(getattr(t, "impuesto", 0), 0)), 2),
            "moneda": s(getattr(t, "moneda", "ARS"), "ARS"),
            "referencia": s(getattr(t, "referencia", "")),
            "is_fraud": int(t.is_fraud),
        })

    out = f"{data_dir}/transactions_sample.json"
    json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, default=txn_store.json_default)
    from pathlib import Path
    kb = Path(out).stat().st_size / 1024
    print(f"  → {out}  ({kb:.1f} KB, {len(rows)} transacciones · {int(sample.is_fraud.sum())} fraude)")


if __name__ == "__main__":
    build()
