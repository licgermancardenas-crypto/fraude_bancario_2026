"""
Genera dashboard/public/data/kyc_profiles.json — el legajo del cliente (Customer
360 / Debida Diligencia del Cliente, CDD). Es la mitad "de cliente" del programa
AML: identidad, calificación de riesgo CDD, PEP/sanciones, cuentas, historial de
alertas, revisión periódica y disparadores de Debida Diligencia Reforzada (EDD).

Consolida datos ya existentes (personas, cuentas, screening, PEP, casos) y agrega
una capa CDD (calificación por factores, calendario de revisión y estado de
verificación) — determinística (seed=42).
"""
import json
import random
from datetime import date, timedelta

import pandas as pd
import yaml

HIGH_RISK_ACT = {
    "Servicios de importación y exportación",
    "Servicios de bar, café y comidas rápidas",
    "Servicios de restaurante y catering",
    "Comercio al por mayor de alimentos y bebidas",
    "Actividades inmobiliarias por cuenta propia",
    "Comercio al por menor en kioscos y maxikioscos",
}


def _kyc_tier(rs: float) -> str:
    return "Bajo" if rs < 0.13 else "Medio" if rs < 0.30 else "Alto"


def build(config_path="config/config.yaml"):
    cfg = yaml.safe_load(open(config_path, encoding="utf-8"))
    data_dir = cfg["paths"]["dashboard_data_dir"]
    raw = cfg["data"]["raw_dir"]

    accounts = pd.read_csv(f"{raw}/accounts.csv").set_index("account_id")
    personas = pd.read_csv(f"{raw}/personas.csv").set_index("account_id")
    pep = pd.read_csv(f"{raw}/pep_flags.csv").set_index("account_id")
    sanc = pd.read_csv(f"{raw}/sanctions_hits.csv")
    sanc_by = {r.account_id: r for r in sanc.itertuples()}
    cases = json.load(open(f"{data_dir}/cases.json", encoding="utf-8"))
    top = json.load(open(f"{data_dir}/top_accounts.json", encoding="utf-8"))

    cases_by: dict[str, list] = {}
    for c in cases:
        cases_by.setdefault(c["account_id"], []).append(c)

    id2score = {c["account_id"]: c["gnn_score"] for c in cases}
    for t in top:
        id2score.setdefault(t["account_id"], t["gnn_score"])

    profile_ids = list(dict.fromkeys(
        [c["account_id"] for c in cases] + [t["account_id"] for t in top]
    ))

    rng = random.Random(42)
    # Muestra de clientes de riesgo normal (fuera del top): dan una cartera con
    # mezcla realista de niveles CDD, no sólo cuentas de alto riesgo. Su score GNN
    # es bajo por definición (no están en el top-200), se toma 0.
    top_set = set(profile_ids)
    pool = [x for x in accounts.index if x not in top_set and x in personas.index]
    profile_ids += rng.sample(pool, min(160, len(pool)))

    today = date.today()
    profiles: dict[str, dict] = {}

    for aid in profile_ids:
        if aid not in personas.index or aid not in accounts.index:
            continue
        per = personas.loc[aid]
        a = accounts.loc[aid]
        score = float(id2score.get(aid, 0))
        is_pep = aid in pep.index
        pep_info = None
        if is_pep:
            pr = pep.loc[aid]
            pep_info = {"categoria": str(pr.get("categoria_pep", "")),
                        "cargo": str(pr.get("cargo_pep", "")),
                        "pais": str(pr.get("pais_pep", ""))}
        hit = sanc_by.get(aid)
        case_list = cases_by.get(aid, [])
        indirect = []
        for c in case_list:
            indirect += c.get("screening", {}).get("exposicion_indirecta", [])

        # ── calificación de riesgo CDD por factores ──────────────────────────
        factores, pts = [], 0.0
        if is_pep:
            factores.append({"factor": "Persona Expuesta Políticamente (PEP)", "nivel": "alto"}); pts += 3
        if hit is not None:
            factores.append({"factor": f"Coincidencia en lista {hit.lista} ({hit.estado})", "nivel": "alto"}); pts += 3
        elif indirect:
            factores.append({"factor": "Exposición indirecta a lista de sanciones", "nivel": "medio"}); pts += 1.5
        if score >= 0.7:
            factores.append({"factor": "Comportamiento transaccional de alto riesgo (score GNN)", "nivel": "alto"}); pts += 3
        elif score >= 0.4:
            factores.append({"factor": "Comportamiento transaccional atípico", "nivel": "medio"}); pts += 1
        act = str(per.get("actividad_economica", ""))
        if act in HIGH_RISK_ACT:
            factores.append({"factor": f"Actividad de alto riesgo: {act}", "nivel": "medio"}); pts += 1
        if str(a.account_type) in ("business", "merchant"):
            factores.append({"factor": "Actividad intensiva en efectivo", "nivel": "bajo"}); pts += 0.5

        nivel = "Alto" if pts >= 3 else "Medio" if pts >= 1 else "Bajo"
        edd_motivos = []
        if nivel == "Alto":
            edd_motivos.append("Calificación de riesgo CDD Alta")
        if is_pep:
            edd_motivos.append("Cliente PEP")
        if hit is not None:
            edd_motivos.append("Coincidencia en lista de sanciones")
        edd = len(edd_motivos) > 0

        # ── revisión periódica (cadencia por riesgo) ─────────────────────────
        freq_m = {"Alto": 6, "Medio": 12, "Bajo": 24}[nivel]
        opened = int(a.get("opened_days_ago", 365))
        alta = today - timedelta(days=opened)
        p_over = 0.32 if nivel == "Alto" else 0.14 if nivel == "Medio" else 0.06
        if rng.random() < p_over:
            proxima = today - timedelta(days=rng.randint(5, 160)); vencida = True
        else:
            proxima = today + timedelta(days=rng.randint(15, freq_m * 30)); vencida = False
        ultima = max(alta, proxima - timedelta(days=freq_m * 30))

        # ── documentación / verificación (simulada) ──────────────────────────
        docs = [
            {"tipo": "DNI / documento de identidad", "estado": "Verificado"},
            {"tipo": "Constancia de CUIL/CUIT", "estado": "Verificado"},
            {"tipo": "Comprobante de domicilio",
             "estado": "Verificado" if rng.random() < 0.85 else "Pendiente"},
            {"tipo": "Declaración jurada de origen de fondos",
             "estado": ("Verificado" if (not edd and rng.random() < 0.7)
                        else "Requerida (EDD)" if edd else "Pendiente")},
        ]
        if edd:
            docs.append({"tipo": "Debida Diligencia Reforzada (EDD)", "estado": "Pendiente"})
        verif = "Verificada" if docs[0]["estado"] == "Verificado" and docs[1]["estado"] == "Verificado" else "Pendiente"

        # ── historial de alertas (casos actuales + histórico sintético) ──────
        alertas = []
        for c in case_list:
            alertas.append({"ref": c["case_id"], "fecha": c["alert_date"], "patron": c["pattern"],
                            "score": c["gnn_score"], "estado": "En investigación"})
        n_hist = {"Alto": rng.randint(1, 3), "Medio": rng.randint(0, 2), "Bajo": rng.randint(0, 1)}[nivel]
        for _ in range(n_hist):
            d = today - timedelta(days=rng.randint(60, 900))
            disp = rng.choices(
                ["Desestimada (falso positivo)", "ROS enviado", "Desestimada (sin mérito)"],
                weights=[70, 12, 18])[0]
            alertas.append({"ref": f"ALT-{rng.randint(10000, 99999)}", "fecha": d.isoformat(),
                            "patron": rng.choice(["estructuracion", "cuenta_paso", "red_mulas", "round_tripping"]),
                            "score": round(rng.uniform(0.5, 0.95), 3), "estado": disp})
        alertas.sort(key=lambda x: x["fecha"], reverse=True)

        profiles[aid] = {
            "account_id": aid,
            "persona": {k: (str(per[k]) if pd.notna(per[k]) else "") for k in per.index},
            "cuentas": [{
                "account_id": aid, "tipo": str(per.get("tipo_cuenta", "")),
                "account_type": str(a.account_type), "balance": round(float(a.balance), 2),
                "gnn_score": round(score, 4), "is_fraud": int(a.is_fraud),
            }],
            "pep": is_pep, "pep_info": pep_info,
            "screening": {
                "hit_directo": ({"lista": str(hit.lista), "estado": str(hit.estado),
                                 "nombre": str(hit.nombre_coincidencia),
                                 "score_match": round(float(hit.score_match), 2)} if hit is not None else None),
                "exposicion_indirecta": indirect,
            },
            "cdd": {
                "riesgo_nivel": nivel, "riesgo_score": round(pts, 1), "factores": factores,
                "kyc_onboarding": _kyc_tier(float(a.risk_score)),
                "fecha_alta": alta.isoformat(), "ultima_revision": ultima.isoformat(),
                "proxima_revision": proxima.isoformat(), "revision_vencida": vencida,
                "edd_requerida": edd, "edd_motivos": edd_motivos,
                "verificacion_identidad": verif, "documentos": docs,
            },
            "alertas": alertas,
        }

    out = f"{data_dir}/kyc_profiles.json"
    json.dump(profiles, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from pathlib import Path
    kb = Path(out).stat().st_size / 1024
    n_alto = sum(1 for p in profiles.values() if p["cdd"]["riesgo_nivel"] == "Alto")
    n_edd = sum(1 for p in profiles.values() if p["cdd"]["edd_requerida"])
    n_venc = sum(1 for p in profiles.values() if p["cdd"]["revision_vencida"])
    print(f"  → {out}  ({kb:.1f} KB, {len(profiles)} legajos · {n_alto} alto riesgo · {n_edd} con EDD · {n_venc} revisión vencida)")


if __name__ == "__main__":
    build()
