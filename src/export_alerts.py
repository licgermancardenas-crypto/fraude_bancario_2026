"""
Genera dashboard/public/data/alerts.json + el resumen del embudo.

Modela la REALIDAD operativa de un sistema de monitoreo transaccional: se
generan muchas más alertas que casos, y la enorme mayoría son FALSOS POSITIVOS
(cuentas legítimas que disparan una regla o tienen un score moderado). El
analista tría: la mayoría se cierra como falso positivo (auto o tras revisión)
y sólo una fracción escala a caso / ROS.

La población de FP no se inventa: son cuentas legítimas que efectivamente
disparan el motor de reglas AML o tienen score GNN moderado.
"""
import json
import random
from datetime import date, timedelta

import pandas as pd

from src.export_dashboard import load_all, load_config
from src.features import build_node_features
from src import rules_engine


def build(config_path="config/config.yaml"):
    cfg = load_config(config_path)
    data_dir = cfg["paths"]["dashboard_data_dir"]
    raw = cfg["data"]["raw_dir"]

    acc, txn, data, scores_all, *_ = load_all(cfg)
    node_ids = data.node_ids
    id2score = {nid: float(scores_all[i]) for i, nid in enumerate(node_ids)}

    feats = build_node_features(acc, txn)
    rules_by = rules_engine.evaluate(feats, cfg)

    personas = pd.read_csv(f"{raw}/personas.csv").set_index("account_id")
    name = personas["nombre_completo"].to_dict()
    atype = acc.set_index("account_id")["account_type"].to_dict()
    isfraud = acc.set_index("account_id")["is_fraud"].to_dict()
    pep = set(pd.read_csv(f"{raw}/pep_flags.csv")["account_id"])
    sanc = set(pd.read_csv(f"{raw}/sanctions_hits.csv")["account_id"])
    cases = json.load(open(f"{data_dir}/cases.json", encoding="utf-8"))
    case_of = {c["account_id"]: c["case_id"] for c in cases}

    ANALISTAS = ["Lic. Valentina Ibarra", "Lic. Tomás Ferreyra", "Lic. Camila Suárez",
                 "Lic. Nicolás Paredes", "Lic. Agustina Domínguez"]

    # ── población de alertas ─────────────────────────────────────────────────
    # Un TM real está DOMINADO por falsos positivos: cuentas legítimas que
    # disparan una regla o tienen score moderado. Componemos la cola con esa
    # realidad: los 80 casos (fraude escalado) + poco fraude extra + MUCHA
    # legítima ruidosa → tasa de FP ~90%, como en producción.
    flagged = set()
    for aid, r in rules_by.items():
        if r["rule_score"] > 0:
            flagged.add(aid)
    for aid, sc in id2score.items():
        if sc >= 0.20:
            flagged.add(aid)
    flagged |= sanc

    rng = random.Random(42)
    case_ids = set(case_of)
    legit_pool = [a for a in flagged if isfraud.get(a, 0) == 0 and a not in case_ids]
    fraud_pool = [a for a in flagged if isfraud.get(a, 0) == 1 and a not in case_ids]
    legit_sample = rng.sample(legit_pool, min(1400, len(legit_pool)))
    fraud_extra = rng.sample(fraud_pool, min(40, len(fraud_pool)))
    alert_ids = list(case_ids) + fraud_extra + legit_sample

    base = date(2026, 2, 1)
    alerts = []
    for i, aid in enumerate(sorted(alert_ids)):
        gnn = id2score.get(aid, 0.0)
        r = rules_by.get(aid, {"rules_fired": [], "rule_score": 0})
        rs = r["rule_score"]
        fired = r["rules_fired"]
        is_sanc = aid in sanc
        is_pep = aid in pep
        fraud = int(isfraud.get(aid, 0))

        # disparador dominante
        if is_sanc:
            disparador, detalle = "Screening de sanciones", "Coincidencia en lista (ONU/OFAC/REPET)"
        elif rs >= 40 and fired:
            top = rules_engine.RULES_BY_ID.get(fired[0], {})
            disparador, detalle = "Regla AML", f"{fired[0]} — {top.get('nombre', '')}"
        elif gnn >= 0.5:
            disparador, detalle = "Modelo GNN", "Comportamiento de red de alto riesgo"
        elif fired:
            top = rules_engine.RULES_BY_ID.get(fired[0], {})
            disparador, detalle = "Regla AML", f"{fired[0]} — {top.get('nombre', '')}"
        else:
            disparador, detalle = "Modelo GNN", "Score de comportamiento moderado"

        prioridad = min(100, round(gnn * 50 + rs * 0.30 + (15 if is_sanc else 0) + (5 if is_pep else 0)))

        # estado / disposición (embudo de triage)
        if aid in case_of:
            estado, disp = "escalada", "Escalada a caso / ROS"
        elif fraud and prioridad >= 45:
            estado, disp = "en_revision", "En investigación"
        elif prioridad < 22:
            estado, disp = "auto_cerrada", "Falso positivo (cierre automático)"
        else:
            estado, disp = ("en_revision", "Pendiente de revisión") if rng.random() < 0.18 \
                else ("cerrada_fp", "Falso positivo (revisada)")

        dt = base + timedelta(days=rng.randint(0, 185))
        alerts.append({
            "alert_id": f"ALR-{i + 1:06d}",
            "fecha": dt.isoformat(),
            "account_id": aid,
            "entidad": name.get(aid, aid),
            "account_type": atype.get(aid, ""),
            "disparador": disparador, "detalle": detalle,
            "score_gnn": round(gnn, 3), "rule_score": rs, "prioridad": prioridad,
            "estado": estado, "disposicion": disp,
            "is_fraud": fraud, "caso_ref": case_of.get(aid),
            "analista": ANALISTAS[rng.randrange(len(ANALISTAS))],
        })

    # ── resumen del embudo ────────────────────────────────────────────────────
    n = len(alerts)
    by_estado = {}
    for a in alerts:
        by_estado[a["estado"]] = by_estado.get(a["estado"], 0) + 1
    resueltas = [a for a in alerts if a["estado"] in ("auto_cerrada", "cerrada_fp")]
    fp = [a for a in resueltas if a["is_fraud"] == 0]
    n_legit = sum(1 for a in alerts if a["is_fraud"] == 0)

    summary = {
        "total": n,
        "auto_cerradas": by_estado.get("auto_cerrada", 0),
        "cerradas_fp": by_estado.get("cerrada_fp", 0),
        "en_revision": by_estado.get("en_revision", 0),
        "escaladas": by_estado.get("escalada", 0),
        # tasa de FP: proporción de alertas que NO son fraude (la métrica que
        # ahoga a un TM real); acá sobre datos sintéticos con etiqueta perfecta.
        "tasa_fp": round(n_legit / n, 3) if n else 0,
        "reduccion_carga": round(by_estado.get("auto_cerrada", 0) / n, 3) if n else 0,
    }

    json.dump({"summary": summary, "alerts": alerts},
              open(f"{data_dir}/alerts.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(f"  → alerts.json  ({n} alertas · {summary['escaladas']} escaladas · "
          f"FP {summary['tasa_fp'] * 100:.0f}% · auto-cerradas {summary['auto_cerradas']})")


if __name__ == "__main__":
    build()
