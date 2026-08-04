"""
Análisis de equidad (fairness) del score GNN — genera dashboard/public/data/fairness.json.

Un validador de modelos exige verificar que el modelo no genere impacto dispar
sobre grupos sensibles (género, edad, región). Se aplica la regla de los 4/5
(four-fifths rule): si la tasa de marcado del grupo menos favorecido es < 80% de
la del más favorecido, hay indicio de impacto adverso a investigar.

Nota: sobre datos sintéticos, la ausencia de sesgo es esperable (los atributos no
se usaron para generar el fraude). El valor es demostrar el CONTROL, que sobre
datos reales es obligatorio.
"""
import json

import numpy as np
import pandas as pd

from src.export_dashboard import load_all, load_config


def _bin_edad(e):
    try:
        e = int(e)
    except (ValueError, TypeError):
        return "s/d"
    return "18–30" if e <= 30 else "31–45" if e <= 45 else "46–60" if e <= 60 else "60+"


REGION = {
    "CABA": "Centro", "Buenos Aires": "Centro", "Córdoba": "Centro", "Santa Fe": "Centro",
    "Entre Ríos": "Litoral", "Corrientes": "Litoral", "Misiones": "Litoral", "Chaco": "NEA", "Formosa": "NEA",
    "Mendoza": "Cuyo", "San Juan": "Cuyo", "San Luis": "Cuyo",
    "Tucumán": "NOA", "Salta": "NOA", "Jujuy": "NOA", "Santiago del Estero": "NOA", "Catamarca": "NOA", "La Rioja": "NOA",
    "Neuquén": "Patagonia", "Río Negro": "Patagonia", "Chubut": "Patagonia",
    "Santa Cruz": "Patagonia", "Tierra del Fuego": "Patagonia", "La Pampa": "Patagonia",
}


def _groups(df, col, threshold, min_n=200):
    overall = float((df["score"] >= threshold).mean())
    rows = []
    for g, sub in df.groupby(col):
        if len(sub) < min_n:
            continue
        rate = float((sub["score"] >= threshold).mean())
        rows.append({
            "grupo": str(g),
            "n": int(len(sub)),
            "flagged_rate": round(rate, 4),
            "mean_score": round(float(sub["score"].mean()), 4),
        })
    if not rows:
        return None
    rates = [r["flagged_rate"] for r in rows]
    mx = max(rates) or 1e-9
    for r in rows:
        r["disparate_impact"] = round(r["flagged_rate"] / mx, 3)
    min_ratio = round((min(rates) or 0) / mx, 3)
    return {
        "grupos": sorted(rows, key=lambda x: -x["flagged_rate"]),
        "min_ratio": min_ratio,
        "four_fifths_ok": min_ratio >= 0.80,
        "overall_flagged_rate": round(overall, 4),
    }


def build(config_path="config/config.yaml"):
    cfg = load_config(config_path)
    data_dir = cfg["paths"]["dashboard_data_dir"]
    raw = cfg["data"]["raw_dir"]

    acc, txn, data, scores_all, *_ = load_all(cfg)
    node_ids = data.node_ids
    id2score = {nid: float(scores_all[i]) for i, nid in enumerate(node_ids)}

    personas = pd.read_csv(f"{raw}/personas.csv")
    personas["score"] = personas["account_id"].map(id2score)
    personas = personas.dropna(subset=["score"]).copy()
    personas["grupo_etario"] = personas["edad"].map(_bin_edad)
    personas["region"] = personas["provincia"].map(lambda p: REGION.get(p, "Otra"))

    # umbral operativo (percentil 97 ~ tasa base de fraude); marca la cola de alertas
    threshold = float(np.quantile(personas["score"], 0.97))

    attributes = []
    for name, col in [("Género", "genero"), ("Grupo etario", "grupo_etario"), ("Región", "region")]:
        res = _groups(personas, col, threshold)
        if res:
            attributes.append({"name": name, "attr": col, **res})

    all_ok = all(a["four_fifths_ok"] for a in attributes)
    veredicto = (
        "Sin impacto dispar detectado: todos los grupos cumplen la regla de los 4/5."
        if all_ok else
        "Atención: algún grupo no cumple la regla de los 4/5 — requiere revisión."
    )

    out = {
        "threshold": round(threshold, 4),
        "n_evaluadas": int(len(personas)),
        "attributes": attributes,
        "four_fifths_ok_global": all_ok,
        "veredicto": veredicto,
        "_nota": "Equidad medida sobre datos sintéticos (atributos no usados para generar el "
                 "fraude). Demuestra el control; sobre datos reales la evaluación es obligatoria "
                 "y debe incluir proxies indirectos.",
    }
    with open(f"{data_dir}/fairness.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"  → {data_dir}/fairness.json  (umbral={threshold:.4f}, 4/5 global={all_ok})")


if __name__ == "__main__":
    build()
