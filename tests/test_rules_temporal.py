"""
Tests de los escenarios de ventana temporal (R09-R13).

Se construyen streams mínimos a mano: lo que se verifica es que cada escenario
dispare por la razón correcta — la secuencia y el intervalo — y no por el
agregado, que es justamente lo que estos escenarios existen para ver.
"""
import pandas as pd
import pytest

from src import rules_temporal as rt

# Los montos van en PESOS, en la misma escala que config.yaml::monetary.
H = 3_600
D = 86_400
T0 = 1_700_000_000


def _acc(**tipos):
    """Cuentas con su tipo; por defecto todo personal."""
    filas = [{"account_id": a, "account_type": t} for a, t in tipos.items()]
    return pd.DataFrame(filas or [{"account_id": "ACC1", "account_type": "personal"}])


def _txns(filas):
    """filas = [(src, dst, amount, ts_offset_segundos)]"""
    return pd.DataFrame([
        {"transaction_id": f"TXN{i:04d}", "src": s, "dst": d, "amount": float(a),
         "timestamp": T0 + off, "transaction_type": "transfer"}
        for i, (s, d, a, off) in enumerate(filas)
    ])


def _ids(res, rid):
    return set(res.get(rid, {}))


# ── R09 · dispersión en ráfaga ───────────────────────────────────────────────

def test_r09_dispara_con_rafaga_concentrada():
    txn = _txns([("ACC1", f"DST{i}", 300_000, i * H) for i in range(4)])
    acc = _acc(ACC1="personal", **{f"DST{i}": "personal" for i in range(4)})
    res = rt.evaluate_rules(txn, acc, None, only=["R09"])
    assert "ACC1" in _ids(res, "R09")
    ev = res["R09"]["ACC1"]
    assert ev["contrapartes"] == 4
    assert ev["monto_total"] == pytest.approx(1_200_000.0)
    assert len(ev["operaciones"]) == 4


def test_r09_no_dispara_si_las_mismas_operaciones_se_reparten_en_el_tiempo():
    """Mismo total y mismas contrapartes, pero espaciadas: el agregado no
    distingue los dos casos y la ventana sí. Es la razón de ser del motor."""
    txn = _txns([("ACC1", f"DST{i}", 300_000, i * 10 * D) for i in range(4)])
    acc = _acc(ACC1="personal", **{f"DST{i}": "personal" for i in range(4)})
    assert _ids(rt.evaluate_rules(txn, acc, None, only=["R09"]), "R09") == set()


def test_r09_no_dispara_con_contraparte_repetida():
    """Cuatro envíos al mismo destinatario no son dispersión."""
    txn = _txns([("ACC1", "DST0", 300_000, i * H) for i in range(4)])
    acc = _acc(ACC1="personal", DST0="personal")
    assert _ids(rt.evaluate_rules(txn, acc, None, only=["R09"]), "R09") == set()


def test_r09_umbral_segmentado_por_tipo_de_cuenta():
    """La nómina de una empresa es fan-out lícito: umbral mucho más alto."""
    filas = [("EMP", f"DST{i}", 300_000, i * H) for i in range(4)]
    acc = _acc(EMP="business", **{f"DST{i}": "personal" for i in range(4)})
    assert _ids(rt.evaluate_rules(_txns(filas), acc, None, only=["R09"]), "R09") == set()

    acc_p = _acc(EMP="personal", **{f"DST{i}": "personal" for i in range(4)})
    assert "EMP" in _ids(rt.evaluate_rules(_txns(filas), acc_p, None, only=["R09"]), "R09")


# ── R10 · agregación en ráfaga ───────────────────────────────────────────────

def test_r10_dispara_con_fan_in_concentrado():
    txn = _txns([(f"SRC{i}", "ACC1", 300_000, i * H) for i in range(4)])
    acc = _acc(ACC1="personal", **{f"SRC{i}": "personal" for i in range(4)})
    assert "ACC1" in _ids(rt.evaluate_rules(txn, acc, None, only=["R10"]), "R10")


# ── R11 · operación circular (U-turn) ────────────────────────────────────────

def test_r11_dispara_cuando_el_dinero_vuelve_por_otra_contraparte():
    txn = _txns([("ACC1", "INT1", 10_000_000, 0), ("INT2", "ACC1", 9_800_000, 5 * D)])
    acc = _acc(ACC1="personal", INT1="personal", INT2="personal")
    res = rt.evaluate_rules(txn, acc, None, only=["R11"])
    assert "ACC1" in _ids(res, "R11")
    ev = res["R11"]["ACC1"]
    assert ev["contraparte_origen"] == "INT1" and ev["contraparte_destino"] == "INT2"
    assert len(ev["operaciones"]) == 2


def test_r11_no_dispara_si_el_retorno_viene_de_la_misma_contraparte():
    """Ida y vuelta con el mismo tercero es una devolución, no un circuito."""
    txn = _txns([("ACC1", "INT1", 10_000_000, 0), ("INT1", "ACC1", 9_800_000, 5 * D)])
    acc = _acc(ACC1="personal", INT1="personal")
    assert _ids(rt.evaluate_rules(txn, acc, None, only=["R11"]), "R11") == set()


def test_r11_no_dispara_fuera_de_la_ventana():
    txn = _txns([("ACC1", "INT1", 10_000_000, 0), ("INT2", "ACC1", 9_800_000, 90 * D)])
    acc = _acc(ACC1="personal", INT1="personal", INT2="personal")
    assert _ids(rt.evaluate_rules(txn, acc, None, only=["R11"]), "R11") == set()


# ── R12 · tránsito emparejado ────────────────────────────────────────────────

def test_r12_dispara_con_par_entrada_salida_emparejado():
    txn = _txns([("ORI", "ACC1", 2_000_000, 0), ("ACC1", "DST", 1_900_000, 6 * H)])
    acc = _acc(ACC1="personal", ORI="personal", DST="personal")
    res = rt.evaluate_rules(txn, acc, None, only=["R12"])
    assert "ACC1" in _ids(res, "R12")
    ev = res["R12"]["ACC1"]
    assert ev["cobertura"] == pytest.approx(0.95)
    assert ev["horas_transcurridas"] == pytest.approx(6.0)


def test_r12_no_dispara_si_la_cuenta_retiene_el_grueso():
    """Salida del 30% de lo que entró: la cuenta retuvo, no fue conducto."""
    txn = _txns([("ORI", "ACC1", 2_000_000, 0), ("ACC1", "DST", 600_000, 6 * H)])
    acc = _acc(ACC1="personal", ORI="personal", DST="personal")
    assert _ids(rt.evaluate_rules(txn, acc, None, only=["R12"]), "R12") == set()


# ── R13 · desvío del perfil ──────────────────────────────────────────────────

def test_r13_dispara_con_pico_contra_la_baseline_propia():
    filas = [("ACC1", "DST", 50_000, i * D) for i in range(6)]
    filas.append(("ACC1", "DST", 6_000_000, 7 * D))
    acc = _acc(ACC1="personal", DST="personal")
    res = rt.evaluate_rules(_txns(filas), acc, None, only=["R13"])
    assert "ACC1" in _ids(res, "R13")
    ev = res["R13"]["ACC1"]
    assert ev["volumen_pico"] == pytest.approx(6_000_000.0)
    assert ev["multiplo"] and ev["multiplo"] >= 20


def test_r13_no_dispara_sin_historia_suficiente():
    """Sin días activos mínimos no hay baseline contra la cual comparar."""
    filas = [("ACC1", "DST", 50_000, 0), ("ACC1", "DST", 6_000_000, D)]
    acc = _acc(ACC1="personal", DST="personal")
    assert _ids(rt.evaluate_rules(_txns(filas), acc, None, only=["R13"]), "R13") == set()


# ── API ──────────────────────────────────────────────────────────────────────

def test_evaluate_agrega_score_y_evidencia():
    txn = _txns([("ORI", "ACC1", 2_000_000, 0), ("ACC1", "DST", 1_900_000, 6 * H)])
    acc = _acc(ACC1="personal", ORI="personal", DST="personal")
    res = rt.evaluate(txn, acc)
    assert res["ACC1"]["rules_fired"] == ["R12"]
    assert res["ACC1"]["rule_score"] == 40          # R12 es severidad alta
    assert "R12" in res["ACC1"]["evidence"]


def test_only_restringe_los_escenarios_evaluados():
    txn = _txns([("ORI", "ACC1", 2_000_000, 0), ("ACC1", "DST", 1_900_000, 6 * H)])
    acc = _acc(ACC1="personal", ORI="personal", DST="personal")
    assert set(rt.evaluate_rules(txn, acc, None, only=["R11"])) == {"R11"}
    assert set(rt.evaluate_rules(txn, acc, None)) == set(rt.TEMPORAL_RULE_IDS)


def test_config_pisa_los_umbrales_por_defecto():
    txn = _txns([("ORI", "ACC1", 2_000_000, 0), ("ACC1", "DST", 1_900_000, 6 * H)])
    acc = _acc(ACC1="personal", ORI="personal", DST="personal")
    cfg = {"rules_temporal": {"passthrough_min_amount": 5_000_000}}
    assert _ids(rt.evaluate_rules(txn, acc, cfg, only=["R12"]), "R12") == set()


def test_las_extracciones_no_cuentan_como_dispersion():
    """En este dataset el efectivo es siempre operatoria legítima; R09 lo ignora."""
    txn = _txns([("ACC1", f"DST{i}", 300_000, i * H) for i in range(4)])
    txn["transaction_type"] = "withdrawal"
    acc = _acc(ACC1="personal", **{f"DST{i}": "personal" for i in range(4)})
    assert _ids(rt.evaluate_rules(txn, acc, None, only=["R09"]), "R09") == set()
