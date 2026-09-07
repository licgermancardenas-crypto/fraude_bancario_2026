"""
Economía minorista densa con contrapartes recurrentes.

POR QUÉ EXISTE. La capa legítima anterior sorteaba src y dst uniformemente sobre
el padrón (`rng.choice(ids, size=2)`), lo que produce un grafo aleatorio de
Erdős–Rényi: 1,09 transacciones por arista, el 93% de las aristas de un solo uso.
La consecuencia medida sobre el dataset viejo es que

    unique_counterparts / degree  =  0,913 legítimas   vs   0,980 fraude

o sea que la CONCENTRACIÓN DE CONTRAPARTES —de las señales más fuertes que usa
un sistema ALD real— no discriminaba nada. Una cuenta minorista real tiene
degree ~250 contra ~30 contrapartes distintas (ratio ~0,12); una mula opera con
contrapartes casi siempre nuevas (ratio ~1,0). El dataset no modelaba esa
diferencia porque nadie repetía contraparte.

Densificar subiendo `n_txns` sobre el sorteo uniforme habría EMPEORADO el
problema: más aristas de un solo uso empujan el ratio legítimo aún más cerca de
1,0 y convierten el grafo en un hairball donde el fan-in/fan-out deja de
discriminar. Densidad y estructura son acá la misma palanca.

CÓMO. Cada cuenta elige un círculo estable de contrapartes —el supermercado de
siempre, el empleador, cuatro servicios con débito automático, un puñado de
pares— y opera repetidamente con ellas a lo largo del año. El degree sube al
rango real, unique_counterparts se mantiene bajo, y el ratio nace como
discriminador.

Todo se construye con arrays de numpy y `np.repeat`: a ~10M filas un bucle de
Python por transacción (lo que hacía el generador anterior) tardaba horas y el
`list[dict]` intermedio no entraba en memoria.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SECONDS_PER_DAY = 86_400

# ── intensidad por tipo de cuenta ────────────────────────────────────────────
# Calibrado para dejar el promedio del padrón dentro del rango minorista real
# (200-600 movimientos por cuenta y por año). Los valores son POR FLUJO: el
# degree final de una cuenta es la suma de los flujos que la tocan, de salida y
# de entrada. Los comercios terminan siendo los más densos porque concentran el
# fan-in de las compras de todos los demás, que es lo que pasa en un banco real.

# personal → comercio (compras con débito/QR): el grueso de la actividad
PURCHASE_CIRCLE = (8, 18)      # comercios habituales por persona
PURCHASE_VISITS = (3, 14)      # visitas al año a cada uno

# personal → empresa (servicios con débito automático / VEP): cadencia mensual
SERVICE_CIRCLE = (2, 6)
SERVICE_MONTHS = (6, 13)       # meses del año en que se paga cada servicio

# personal → personal (transferencias entre pares)
PEER_CIRCLE = (3, 10)
PEER_VISITS = (1, 6)

# personal → extracciones de efectivo (dst = el comercio/cajero de siempre)
ATM_CIRCLE = (1, 4)
ATM_VISITS = (4, 15)

# empresa → personal (nómina): plantilla estable, cadencia mensual
PAYROLL_STAFF = (3, 14)
PAYROLL_MONTHS = (11, 13)

# empresa → empresa/comercio (proveedores): cadencia mensual
SUPPLIER_CIRCLE = (2, 7)
SUPPLIER_MONTHS = (4, 13)

# comercio → empresa (liquidación de adquirencia, alquiler, servicios)
SETTLE_CIRCLE = (1, 5)
SETTLE_MONTHS = (6, 13)

# ── montos ───────────────────────────────────────────────────────────────────
# En la unidad sintética del generador; `monetary.scale` (×100) los lleva a
# pesos de 2026. La mediana buscada de cada flujo está anotada en ARS.
AMOUNTS = {
    "purchase": (5.6, 0.90),   # ~$27.000
    "service":  (5.9, 0.70),   # ~$36.500
    "peer":     (6.2, 1.10),   # ~$49.300
    "atm":      (6.3, 0.60),   # ~$54.500
    "payroll":  (8.9, 0.45),   # ~$733.000  (~2 SMVM)
    "supplier": (8.5, 1.00),   # ~$491.000
    "settle":   (8.2, 0.95),   # ~$364.000
}
# Dispersión de un mismo vínculo alrededor de su monto típico: comprar siempre
# en el mismo supermercado da tickets parecidos, no independientes.
LINK_JITTER = 0.35


def _empty_stream(ttype: str) -> dict[str, np.ndarray]:
    """Flujo vacío con el mismo esquema que uno poblado (tipos incluidos)."""
    return {
        "src": np.array([], dtype=np.int32),
        "dst": np.array([], dtype=np.int32),
        "amount": np.array([], dtype=np.float32),
        "timestamp": np.array([], dtype=np.int32),
        "transaction_type": ttype,
    }


def _circle_stream(
    payers: np.ndarray,
    targets: np.ndarray,
    rng: np.random.Generator,
    *,
    circle: tuple[int, int],
    visits: tuple[int, int],
    amount: tuple[float, float],
    ttype: str,
    base_ts: int,
    window_days: int,
    monthly: bool = False,
    jitter: float = LINK_JITTER,
    weight: np.ndarray | None = None,
    target_weight: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """
    Construye un flujo de contrapartes recurrentes.

    Cada pagador sortea un círculo de tamaño `circle` sobre `targets` y opera
    con cada contraparte `visits` veces. El monto típico se sortea POR VÍNCULO y
    cada operación lo perturba con `jitter`, de modo que la relación tiene un
    ticket característico en vez de montos independientes.

    `monthly=True` reparte las operaciones en meses distintos (servicios,
    nómina, proveedores) en lugar de uniformemente sobre la ventana; sin eso la
    regla R13 (desvío contra la baseline diaria propia) vería ráfagas que no son.

    `weight` escala el círculo cuenta por cuenta (ver ACTIVITY_TIERS): con 0,1 la
    cuenta queda casi inactiva y con 2,5 es de las más movidas del banco.

    `target_weight` sesga la ELECCIÓN de contraparte por la misma actividad. Sin
    esto una cuenta inactiva igual recibía cobros, nómina y transferencias de
    pares, y terminaba con ~100 movimientos anuales: no quedaba ninguna cuenta
    genuinamente quieta en el padrón, lo que vuelve trivial la tipología de
    cuenta durmiente. A nadie le debita el servicio que no contrató.
    """
    n_payers = len(payers)
    if n_payers == 0 or len(targets) == 0:
        return _empty_stream(ttype)

    sizes = rng.integers(circle[0], circle[1], n_payers)
    if weight is not None:
        sizes = np.rint(sizes * weight).astype(np.int64).clip(0, None)
    slot_payer = np.repeat(np.arange(n_payers), sizes)
    n_slots = len(slot_payer)
    if target_weight is None:
        slot_target = rng.integers(0, len(targets), n_slots)
    else:
        # inverso de la CDF: mucho más rápido que rng.choice(p=...) con decenas
        # de miles de destinos y cientos de miles de sorteos
        cdf = np.cumsum(target_weight)
        if cdf[-1] <= 0:            # todos los destinos dormidos: sin sesgo
            slot_target = rng.integers(0, len(targets), n_slots)
        else:
            slot_target = np.searchsorted(cdf, rng.random(n_slots) * cdf[-1])
            slot_target = np.clip(slot_target, 0, len(targets) - 1)
    slot_visits = rng.integers(visits[0], visits[1], n_slots)
    slot_amount = rng.lognormal(amount[0], amount[1], n_slots)

    total = int(slot_visits.sum())
    if total == 0:
        return _empty_stream(ttype)
    src = payers[slot_payer.repeat(slot_visits)].astype(np.int32)
    dst = targets[slot_target.repeat(slot_visits)].astype(np.int32)
    amt = (np.repeat(slot_amount, slot_visits)
           * rng.lognormal(0.0, jitter, total)).astype(np.float32)

    if monthly:
        # una operación por mes distinto: se sortea el mes sin reemplazo por
        # vínculo aproximándolo con un offset inicial + paso mensual
        month_len = window_days / 12.0
        # índice de ocurrencia dentro de cada vínculo, sin bucle de Python:
        # arange global menos el offset de arranque de cada tramo
        starts = np.repeat(np.cumsum(slot_visits) - slot_visits, slot_visits)
        occurrence = np.arange(total) - starts
        start_month = np.repeat(rng.random(n_slots), slot_visits)
        day = (start_month + occurrence) * month_len
        day = np.mod(day, window_days)
        ts = base_ts + (day * SECONDS_PER_DAY).astype(np.int64)
        ts += rng.integers(0, 3 * SECONDS_PER_DAY, total)      # día del mes flexible
    else:
        ts = base_ts + rng.integers(0, window_days * SECONDS_PER_DAY, total)

    return {
        "src": src,
        "dst": dst,
        "amount": np.round(amt, 2),
        "timestamp": ts.astype(np.int32),
        "transaction_type": ttype,
    }


# ── niveles de actividad ─────────────────────────────────────────────────────
# Una cartera real no tiene a todos los clientes operando parejo: hay cuentas
# casi dormidas, el grueso normal, y una cola de cuentas muy movidas. Importa
# por dos motivos que no son estéticos:
#   - sin cuentas genuinamente quietas, la regla de reactivación de cuenta
#     durmiente (R04) no tiene sobre qué disparar, y si las únicas quietas
#     fueran las de fraude, estar quieta alcanzaría para delatarlas;
#   - la cola de cuentas muy movidas es la que genera la presión de falsos
#     positivos sobre las reglas de volumen y de fan-in/fan-out.
ACTIVITY_TIERS = (
    (0.08, (0.00, 0.02)),   # durmientes: sin operatoria propia
    (0.14, (0.05, 0.30)),   # baja actividad
    (0.60, (0.70, 1.30)),   # normales
    (0.18, (1.60, 3.00)),   # muy activas
)
TIER_DORMANT, TIER_LOW = 0, 1


def activity_weights(n: int, rng: np.random.Generator) -> np.ndarray:
    """Multiplicador de actividad por cuenta, sorteado de ACTIVITY_TIERS."""
    probs = np.array([p for p, _ in ACTIVITY_TIERS])
    tier = rng.choice(len(ACTIVITY_TIERS), size=n, p=probs / probs.sum())
    lo = np.array([r[0] for _, r in ACTIVITY_TIERS])[tier]
    hi = np.array([r[1] for _, r in ACTIVITY_TIERS])[tier]
    return rng.uniform(lo, hi)


def build_retail_economy(
    accounts: pd.DataFrame,
    rng: np.random.Generator,
    base_ts: int,
    window_days: int = 365,
    weights: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """
    Genera la economía legítima completa como índices posicionales sobre
    `accounts`. Devuelve arrays, no `list[dict]`: a ~10M filas la lista de
    diccionarios del generador anterior no entra en memoria.

    Las cuentas de fraude PARTICIPAN de esta capa con la misma distribución de
    actividad que las legítimas de su tipo. Es deliberado: si se les diera menos
    actividad legítima, "tener poco movimiento lícito" se volvería una fuga que
    el modelo aprendería en lugar de aprender la estructura del lavado. El costo
    es que la señal de fraude queda embebida en un fondo realista, que es
    exactamente el problema difícil que enfrenta un sistema ALD real.

    La excepción entra por `weights`, que permite al llamador fijar el nivel de
    actividad de cuentas concretas: las tipologías cuya DEFINICIÓN es la
    inactividad —la cuenta durmiente, la mula recién reclutada y descartable— se
    bajan a mano. No es una fuga porque el 22% de las cuentas legítimas también
    vive en esos dos niveles: quedarse quieta no identifica a nadie por sí sola.
    """
    idx = np.arange(len(accounts))
    atype = accounts["account_type"].to_numpy()
    personal = idx[atype == "personal"]
    business = idx[atype == "business"]
    merchant = idx[atype == "merchant"]
    biz_or_merch = np.concatenate([business, merchant]) if len(business) or len(merchant) else business

    w = activity_weights(len(accounts), rng) if weights is None else np.asarray(weights)
    common = {"base_ts": base_ts, "window_days": window_days}

    streams = [
        # personal → comercio: compras con débito/QR, el grueso del volumen
        _circle_stream(personal, merchant, rng, circle=PURCHASE_CIRCLE,
                       visits=PURCHASE_VISITS, amount=AMOUNTS["purchase"],
                       ttype="payment", weight=w[personal],
                       target_weight=w[merchant], **common),
        # personal → empresa: servicios con débito automático, cadencia mensual
        _circle_stream(personal, business, rng, circle=SERVICE_CIRCLE,
                       visits=SERVICE_MONTHS, amount=AMOUNTS["service"],
                       ttype="payment", monthly=True, weight=w[personal],
                       target_weight=w[business], **common),
        # personal → personal: transferencias entre pares
        _circle_stream(personal, personal, rng, circle=PEER_CIRCLE,
                       visits=PEER_VISITS, amount=AMOUNTS["peer"],
                       ttype="transfer", weight=w[personal],
                       target_weight=w[personal], **common),
        # personal → comercio/cajero: extracciones de efectivo
        _circle_stream(personal, merchant, rng, circle=ATM_CIRCLE,
                       visits=ATM_VISITS, amount=AMOUNTS["atm"],
                       ttype="withdrawal", weight=w[personal],
                       target_weight=w[merchant], **common),
        # empresa → personal: nómina, plantilla estable, mensual
        _circle_stream(business, personal, rng, circle=PAYROLL_STAFF,
                       visits=PAYROLL_MONTHS, amount=AMOUNTS["payroll"],
                       ttype="transfer", monthly=True, jitter=0.08,
                       weight=w[business], target_weight=w[personal], **common),
        # empresa → empresa/comercio: proveedores, mensual
        _circle_stream(business, biz_or_merch, rng, circle=SUPPLIER_CIRCLE,
                       visits=SUPPLIER_MONTHS, amount=AMOUNTS["supplier"],
                       ttype="payment", monthly=True, weight=w[business],
                       target_weight=w[biz_or_merch], **common),
        # comercio → empresa: liquidación de adquirencia, alquiler, servicios
        _circle_stream(merchant, business, rng, circle=SETTLE_CIRCLE,
                       visits=SETTLE_MONTHS, amount=AMOUNTS["settle"],
                       ttype="payment", monthly=True, weight=w[merchant],
                       target_weight=w[business], **common),
    ]

    n_total = sum(len(s["src"]) for s in streams)
    out = {
        "src": np.empty(n_total, dtype=np.int32),
        "dst": np.empty(n_total, dtype=np.int32),
        "amount": np.empty(n_total, dtype=np.float32),
        "timestamp": np.empty(n_total, dtype=np.int32),
    }
    # el tipo se guarda como código: un array de objetos de 10M de strings
    # cuesta ~800 MB y no hay presupuesto para eso
    ttype_cats = sorted({s["transaction_type"] for s in streams})
    ttype = np.empty(n_total, dtype=np.int8)
    at = 0
    for i, s in enumerate(streams):
        k = len(s["src"])
        if k:
            sl = slice(at, at + k)
            out["src"][sl] = s["src"]
            out["dst"][sl] = s["dst"]
            out["amount"][sl] = s["amount"]
            out["timestamp"][sl] = s["timestamp"]
            ttype[sl] = ttype_cats.index(s["transaction_type"])
            at += k
        streams[i] = None      # liberar el flujo apenas se copia

    # una cuenta no se paga a sí misma
    keep = out["src"] != out["dst"]
    if not keep.all():
        for k in out:
            out[k] = out[k][keep]
        ttype = ttype[keep]
    out["transaction_type"] = pd.Categorical.from_codes(ttype, categories=ttype_cats)
    return out
