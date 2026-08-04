"""
Genera dashboard/public/data/transactions_sample.json — una muestra de
transacciones enriquecida para el Transaction Explorer (tabla con filtros
avanzados y exportación). Incluye todas/la mayoría de las transacciones
fraudulentas más una muestra de legítimas, con nombres de contraparte, canal,
concepto, tipos de cuenta y moneda.

Es una MUESTRA (no las 544K) para que el explorador sea navegable en el browser.
"""
import json
import random

import pandas as pd

from src.export_dashboard import _txn_meta, load_config

TIPO_MAP = {"transfer": "Transferencia", "payment": "Pago", "withdrawal": "Extracción"}


def build(config_path="config/config.yaml"):
    cfg = load_config(config_path)
    data_dir = cfg["paths"]["dashboard_data_dir"]
    raw = cfg["data"]["raw_dir"]

    txn = pd.read_csv(f"{raw}/transactions.csv")
    acc = pd.read_csv(f"{raw}/accounts.csv").set_index("account_id")
    per = pd.read_csv(f"{raw}/personas.csv").set_index("account_id")
    name = per["nombre_completo"].to_dict()
    atype = acc["account_type"].to_dict()

    fraud = txn[txn.is_fraud == 1]
    legit = txn[txn.is_fraud == 0]
    fr = fraud.sample(min(2500, len(fraud)), random_state=42)
    lg = legit.sample(min(1500, len(legit)), random_state=42)
    sample = pd.concat([fr, lg]).sort_values("timestamp", ascending=False)

    rows = []
    for t in sample.itertuples():
        meta = _txn_meta(t.src, t.dst, t.amount, atype.get(t.dst))
        rows.append({
            "id": t.transaction_id,
            "ts": int(t.timestamp),
            "src": t.src, "dst": t.dst,
            "src_name": name.get(t.src, ""), "dst_name": name.get(t.dst, ""),
            "src_type": atype.get(t.src, ""), "dst_type": atype.get(t.dst, ""),
            "amount": round(float(t.amount), 2),
            "tipo": TIPO_MAP.get(t.transaction_type, t.transaction_type),
            "canal": meta["canal"], "concepto": meta["concepto"], "moneda": "ARS",
            "is_fraud": int(t.is_fraud),
        })

    out = f"{data_dir}/transactions_sample.json"
    json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    from pathlib import Path
    kb = Path(out).stat().st_size / 1024
    print(f"  → {out}  ({kb:.1f} KB, {len(rows)} transacciones · {int(sample.is_fraud.sum())} fraude)")


if __name__ == "__main__":
    build()
