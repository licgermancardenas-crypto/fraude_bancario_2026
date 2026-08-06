"""
Genera dashboard/public/data/screening_hits.json — la cola de coincidencias de
screening de sanciones (workbench). Cada coincidencia de una cuenta contra las
listas (ONU / OFAC / REPET, ficticias) con su score de matching difuso, motivo y
estado, enriquecida con la entidad y el enlace a caso si escaló.
"""
import json
import random
from datetime import date, timedelta

import pandas as pd

from src.export_dashboard import load_config

ANALISTAS = ["Lic. Valentina Ibarra", "Lic. Tomás Ferreyra", "Lic. Camila Suárez",
             "Lic. Nicolás Paredes", "Lic. Agustina Domínguez"]


def build(config_path="config/config.yaml"):
    cfg = load_config(config_path)
    data_dir = cfg["paths"]["dashboard_data_dir"]
    raw = cfg["data"]["raw_dir"]

    sanc = pd.read_csv(f"{raw}/sanctions_hits.csv")
    personas = pd.read_csv(f"{raw}/personas.csv").set_index("account_id")
    acc = pd.read_csv(f"{raw}/accounts.csv").set_index("account_id")
    name = personas["nombre_completo"].to_dict()
    atype = acc["account_type"].to_dict()
    pep = set(pd.read_csv(f"{raw}/pep_flags.csv")["account_id"])
    cases = json.load(open(f"{data_dir}/cases.json", encoding="utf-8"))
    case_of = {c["account_id"]: c["case_id"] for c in cases}

    rng = random.Random(42)
    base = date(2026, 2, 1)
    hits = []
    for i, r in enumerate(sanc.itertuples()):
        aid = r.account_id
        dt = base + timedelta(days=rng.randint(0, 185))
        hits.append({
            "id": f"SCR-{i + 1:05d}",
            "fecha": dt.isoformat(),
            "account_id": aid,
            "entidad": name.get(aid, aid),
            "account_type": atype.get(aid, ""),
            "is_pep": aid in pep,
            "lista": r.lista,
            "nombre_coincidencia": r.nombre_coincidencia,
            "motivo": r.motivo,
            "score_match": round(float(r.score_match), 2),
            "estado": r.estado,
            "caso_ref": case_of.get(aid),
            "analista": ANALISTAS[rng.randrange(len(ANALISTAS))],
        })

    by_estado, by_lista = {}, {}
    for h in hits:
        by_estado[h["estado"]] = by_estado.get(h["estado"], 0) + 1
        by_lista[h["lista"]] = by_lista.get(h["lista"], 0) + 1

    summary = {
        "total": len(hits),
        "pendientes": by_estado.get("pendiente", 0),
        "confirmados": by_estado.get("confirmado", 0),
        "descartados": by_estado.get("descartado", 0),
        "por_lista": by_lista,
        "ultimo_screening": date(2026, 8, 1).isoformat(),
    }

    json.dump({"summary": summary, "hits": hits},
              open(f"{data_dir}/screening_hits.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(f"  → screening_hits.json  ({len(hits)} coincidencias · "
          f"{summary['pendientes']} pendientes · {summary['confirmados']} confirmadas)")


if __name__ == "__main__":
    build()
