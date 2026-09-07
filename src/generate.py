"""
Generate synthetic bank fraud graph dataset.

Produces in data/raw/:
  accounts.csv       — nodos (una fila por cuenta, con la etiqueta fraud_typology)
  transactions/      — aristas, en el almacén columnar compacto (ver txn_store)

Fraud typologies embedded (GAFI/FATF-aligned):
  - anillo_lavado    Cyclic laundering rings A→B→…→A (4-7 hops) + exit fan-out
  - estructuracion   Structuring (pitufeo): one source splitting into many small transfers
  - agregacion_fondos Fan-in: many mules funnelling into one collector
  - cuenta_paso      Flow-through: money in and out within hours, ~0 retention
  - shell_layering   Layering through shell-company (business) conduits
  - cuenta_durmiente Dormant account suddenly reactivated with large bursts
  - red_mulas        Mule-recruitment network: fan-out to many fresh disposable accounts
  - round_tripping   U-turn / round-tripping: money leaves and returns (integration)

Cada cuenta de fraude lleva exactamente una tipología en `fraud_typology`; las
legítimas llevan "". Cada esquema corre CAMPAIGNS_PER_SCHEME veces al año: una
operación de lavado real cicla y repone, no mueve el dinero una sola vez.

DENSIDAD. La capa legítima la construye `economy.build_retail_economy` sobre
círculos de contrapartes recurrentes, no sorteando pares al azar. El padrón
queda en ~313 movimientos por cuenta y por año —dentro del rango minorista real
de 200-600— con 7,4 transacciones por arista. El generador anterior producía
14,5 movimientos anuales y 1,09 transacciones por arista, un grafo aleatorio en
el que la concentración de contrapartes no distinguía a nadie; ver la
justificación completa en el encabezado de economy.py.

`scale` controla el tamaño del padrón; el volumen transaccional sale de la
intensidad por cuenta, no de un total fijado a mano:
  scale=0.02  →   ~3 000 cuentas,   ~0,46M transacciones  (dev/test)
  scale=0.50  →  ~75 000 cuentas,  ~11,7M transacciones   (entregable actual)
  scale=1.00  → ~150 000 cuentas,  ~23,5M transacciones

time_window_days estira o comprime el rango de fechas manteniendo la cadencia
anual de cada flujo.
"""

import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src import txn_store
from src import economy
from src.economy import build_retail_economy


# ── helpers ──────────────────────────────────────────────────────────────────

def load_config(path: str = "config/config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)


# ── generation ───────────────────────────────────────────────────────────────

BASE_ACCOUNTS     = 150_000   # scale=0.01 → ~1 500 accounts
BASE_RINGS        = 200       # scale=0.01 → ~2 rings
BASE_STRUCT_NETS  = 100       # scale=0.01 → ~1 structuring net
BASE_FLOWTHROUGH  = 120       # flow-through chains
BASE_SHELL        = 80        # shell-company layering schemes
BASE_DORMANT      = 80        # dormant-account reactivations
BASE_MULENET      = 60        # mule-recruitment networks
BASE_ROUNDTRIP    = 60        # round-tripping / U-turn schemes
FRAUD_EDGE_NOISE  = 0.005
BASE_TS           = 1_700_000_000


def _account_id(i: int) -> str:
    return f"ACC{i:07d}"


def _pick(ids: list[str], k: int, claimed: set[str]) -> list[str]:
    """Sample k account ids not already claimed by another typology."""
    pool = [a for a in ids if a not in claimed]
    return random.sample(pool, min(k, len(pool)))


def generate_accounts(n: int, rng: np.random.Generator) -> pd.DataFrame:
    """Create n legitimate account records."""
    balance = np.round(rng.lognormal(mean=7.5, sigma=1.8, size=n), 2)  # ~$1 800 median
    risk_score = np.round(rng.beta(2, 8, size=n), 4)                   # skewed low (legit)
    account_type = rng.choice(
        ["personal", "business", "merchant"],
        size=n,
        p=[0.70, 0.20, 0.10],
    )
    opened_days_ago = rng.integers(30, 365 * 10, size=n)

    df = pd.DataFrame({
        "account_id":      [_account_id(i) for i in range(n)],
        "balance":         balance,
        "risk_score":      risk_score,
        "account_type":    account_type,
        "opened_days_ago": opened_days_ago,
        "is_fraud":        0,
        "fraud_typology":  "",
    })
    return df


def embed_laundering_rings(
    accounts: pd.DataFrame,
    n_rings: int,
    rng: np.random.Generator,
    claimed: set[str],
    txn_offset: int = 0,
    base_ts: int = BASE_TS,
    time_window_days: int = 365,
    campaigns: int = 1,
) -> tuple[dict[str, str], list[dict]]:
    """
    Embed cyclic money-laundering rings (4-7 hops).
    Each ring: money enters from outside → cycles N times → exits in small chunks.
    Returns {account_id: typology} and new transaction records.
    """
    ids = accounts["account_id"].tolist()
    typ: dict[str, str] = {}
    new_txns: list[dict] = []
    txn_counter = txn_offset

    # Leave a tail buffer so hops (up to 7 x 72h) + exit fan-out (up to 48h)
    # always land inside the window — worst case is ~31 days.
    entry_window_days = max(1, time_window_days - 40)

    for r in range(n_rings):
        ring_len = int(rng.integers(4, 8))      # 4-7 nodes
        ring_nodes = _pick(ids, ring_len, claimed)
        if len(ring_nodes) < 4:
            continue
        claimed.update(ring_nodes)
        for a in ring_nodes:
            typ[a] = "anillo_lavado"

        # entry transaction (outside → ring[0])
        entry_src = _pick(ids, 1, claimed)[0]
        for _ in range(campaigns):
            entry_amount = round(float(rng.uniform(5_000, 50_000)), 2)
            entry_ts = int(base_ts + rng.integers(0, entry_window_days * 24 * 3600))

            new_txns.append({
                "transaction_id": f"TXN{txn_counter:09d}",
                "src": entry_src,
                "dst": ring_nodes[0],
                "amount": entry_amount,
                "timestamp": entry_ts,
                "transaction_type": "transfer",
                "is_fraud": 1,
            })
            txn_counter += 1

            # cyclic hops — each hop within 72 h of previous (pitufeo timing)
            current_amount = entry_amount
            current_ts = entry_ts
            for hop in range(ring_len):
                next_node = ring_nodes[(hop + 1) % ring_len]
                hop_amount = round(current_amount * rng.uniform(0.85, 0.98), 2)
                hop_ts = int(current_ts + rng.integers(600, 72 * 3600))
                new_txns.append({
                    "transaction_id": f"TXN{txn_counter:09d}",
                    "src": ring_nodes[hop],
                    "dst": next_node,
                    "amount": hop_amount,
                    "timestamp": hop_ts,
                    "transaction_type": "transfer",
                    "is_fraud": 1,
                })
                txn_counter += 1
                current_amount = hop_amount
                current_ts = hop_ts

            # exit: ring[-1] fans out into 3-5 legitimate-looking accounts (small chunks)
            n_exit = int(rng.integers(3, 6))
            exit_targets = random.sample(ids, n_exit)
            for j in range(n_exit):
                chunk = round(current_amount / n_exit * rng.uniform(0.8, 1.2), 2)
                exit_ts = int(current_ts + rng.integers(3600, 48 * 3600))
                new_txns.append({
                    "transaction_id": f"TXN{txn_counter:09d}",
                    "src": ring_nodes[-1],
                    "dst": exit_targets[j],
                    "amount": chunk,
                    "timestamp": exit_ts,
                    "transaction_type": "transfer",
                    "is_fraud": 1,
                })
                txn_counter += 1

    return typ, new_txns


def embed_structuring(
    accounts: pd.DataFrame,
    n_nets: int,
    rng: np.random.Generator,
    claimed: set[str],
    txn_offset: int = 0,
    base_ts: int = BASE_TS,
    time_window_days: int = 365,
    campaigns: int = 1,
) -> tuple[dict[str, str], list[dict]]:
    """
    Embed structuring (pitufeo) patterns: one source fans out into many small
    transfers to avoid detection thresholds, then a collector aggregates them.
    Source + mules are labelled `estructuracion`; the collector `agregacion_fondos`.
    """
    ids = accounts["account_id"].tolist()
    typ: dict[str, str] = {}
    new_txns: list[dict] = []
    txn_counter = txn_offset

    entry_window_days = max(1, time_window_days - 40)

    for _ in range(n_nets):
        n_mules = int(rng.integers(5, 15))
        picked = _pick(ids, n_mules + 2, claimed)
        if len(picked) < 4:
            continue
        source, collector, *mules = picked
        claimed.update(picked)
        typ[source] = "estructuracion"
        typ[collector] = "agregacion_fondos"
        for m in mules:
            typ[m] = "estructuracion"

        for _ in range(campaigns):
            total = round(float(rng.uniform(10_000, 100_000)), 2)
            base = int(base_ts + rng.integers(0, entry_window_days * 24 * 3600))

            # source → mules (structured, below $10k each)
            per_mule = total / len(mules)
            for mule in mules:
                amount = round(per_mule * rng.uniform(0.7, 0.99), 2)
                ts = int(base + rng.integers(0, 48 * 3600))
                new_txns.append({
                    "transaction_id": f"TXN{txn_counter:09d}",
                    "src": source,
                    "dst": mule,
                    "amount": amount,
                    "timestamp": ts,
                    "transaction_type": "transfer",
                    "is_fraud": 1,
                })
                txn_counter += 1

            # mules → collector (fan-in)
            for mule in mules:
                amount = round(per_mule * rng.uniform(0.7, 0.99), 2)
                ts = int(base + rng.integers(48 * 3600, 120 * 3600))
                new_txns.append({
                    "transaction_id": f"TXN{txn_counter:09d}",
                    "src": mule,
                    "dst": collector,
                    "amount": amount,
                    "timestamp": ts,
                    "transaction_type": "transfer",
                    "is_fraud": 1,
                })
                txn_counter += 1

    return typ, new_txns


def embed_flowthrough(
    accounts: pd.DataFrame,
    n_chains: int,
    rng: np.random.Generator,
    claimed: set[str],
    txn_offset: int = 0,
    base_ts: int = BASE_TS,
    time_window_days: int = 365,
    campaigns: int = 1,
) -> tuple[dict[str, str], list[dict]]:
    """
    Flow-through / pass-through accounts (cuentas de paso): money enters and is
    forwarded within hours, leaving a near-zero balance. The account is a pure
    conduit — its signature is amount_out ≈ amount_in and sub-day retention.
    """
    ids = accounts["account_id"].tolist()
    typ: dict[str, str] = {}
    new_txns: list[dict] = []
    txn_counter = txn_offset
    entry_window_days = max(1, time_window_days - 10)

    for _ in range(n_chains):
        chain_len = int(rng.integers(2, 5))        # 2-4 pass-through hops
        chain = _pick(ids, chain_len, claimed)
        if len(chain) < 2:
            continue
        claimed.update(chain)
        for a in chain:
            typ[a] = "cuenta_paso"

        source = _pick(ids, 1, claimed)[0]
        dest   = _pick(ids, 1, claimed)[0]
        for _ in range(campaigns):
            amount = round(float(rng.uniform(20_000, 80_000)), 2)
            ts = int(base_ts + rng.integers(0, entry_window_days * 24 * 3600))

            # source → chain[0] → chain[1] → ... → dest, each hop within a few hours
            path = [source] + chain + [dest]
            current = amount
            for i in range(len(path) - 1):
                ts = int(ts + rng.integers(600, 12 * 3600))  # sub-day forwarding
                current = round(current * rng.uniform(0.97, 0.995), 2)  # tiny fee retained
                new_txns.append({
                    "transaction_id": f"TXN{txn_counter:09d}",
                    "src": path[i],
                    "dst": path[i + 1],
                    "amount": current,
                    "timestamp": ts,
                    "transaction_type": "transfer",
                    "is_fraud": 1,
                })
                txn_counter += 1

    return typ, new_txns


def embed_shell_layering(
    accounts: pd.DataFrame,
    n_schemes: int,
    rng: np.random.Generator,
    claimed: set[str],
    txn_offset: int = 0,
    base_ts: int = BASE_TS,
    time_window_days: int = 365,
    campaigns: int = 1,
) -> tuple[dict[str, str], list[dict]]:
    """
    Layering through shell-company conduits: dirty money enters a business
    account (the shell), is broken up and passed through 1-2 further business
    conduits, then dispersed to several recipients — giving the flow a
    commercial appearance. Shell conduits are business accounts and are
    returned so the entity layer can attach shell companies to them.
    """
    ids = accounts["account_id"].tolist()
    business_ids = accounts.loc[accounts["account_type"] == "business", "account_id"].tolist()
    typ: dict[str, str] = {}
    new_txns: list[dict] = []
    txn_counter = txn_offset
    entry_window_days = max(1, time_window_days - 30)

    for _ in range(n_schemes):
        n_conduits = int(rng.integers(1, 3))        # 1-2 shell conduits
        conduits = [c for c in _pick(business_ids, n_conduits + 2, claimed)][:n_conduits]
        if not conduits:
            continue
        claimed.update(conduits)
        for c in conduits:
            typ[c] = "shell_layering"

        source = _pick(ids, 1, claimed)[0]
        for _ in range(campaigns):
            amount = round(float(rng.uniform(40_000, 250_000)), 2)
            ts = int(base_ts + rng.integers(0, entry_window_days * 24 * 3600))

            # source → shell conduits (chain), booked as "payment" for commercial cover
            current = amount
            prev = source
            for c in conduits:
                ts = int(ts + rng.integers(3600, 96 * 3600))
                current = round(current * rng.uniform(0.9, 0.99), 2)
                new_txns.append({
                    "transaction_id": f"TXN{txn_counter:09d}",
                    "src": prev, "dst": c, "amount": current,
                    "timestamp": ts, "transaction_type": "payment", "is_fraud": 1,
                })
                txn_counter += 1
                prev = c

            # final shell disperses to 3-6 recipients (invoiced-looking payments)
            n_out = int(rng.integers(3, 7))
            recipients = _pick(ids, n_out, claimed)
            for rcp in recipients:
                chunk = round(current / len(recipients) * rng.uniform(0.7, 1.2), 2)
                out_ts = int(ts + rng.integers(3600, 72 * 3600))
                new_txns.append({
                    "transaction_id": f"TXN{txn_counter:09d}",
                    "src": prev, "dst": rcp, "amount": chunk,
                    "timestamp": out_ts, "transaction_type": "payment", "is_fraud": 1,
                })
                txn_counter += 1

    return typ, new_txns


def embed_dormant_reactivation(
    accounts: pd.DataFrame,
    n_accounts: int,
    rng: np.random.Generator,
    claimed: set[str],
    txn_offset: int = 0,
    base_ts: int = BASE_TS,
    time_window_days: int = 365,
    campaigns: int = 1,
) -> tuple[dict[str, str], list[dict]]:
    """
    Dormant account reactivation: an old account with little history suddenly
    receives and moves a large sum in a tight burst late in the window. The
    account's `opened_days_ago` is forced high (long-standing but idle) and the
    burst is concentrated in the final weeks — a classic sleeper-mule signature.

    Also returns the reactivated ids via the typology map so the caller can
    bump their opened_days_ago.
    """
    ids = accounts["account_id"].tolist()
    typ: dict[str, str] = {}
    new_txns: list[dict] = []
    txn_counter = txn_offset

    # burst lands in the last ~30 days of the window
    burst_start = max(1, time_window_days - 30)

    for _ in range(n_accounts):
        acc = _pick(ids, 1, claimed)
        if not acc:
            continue
        acc = acc[0]
        claimed.add(acc)
        typ[acc] = "cuenta_durmiente"

        n_in = int(rng.integers(2, 5))
        funders = _pick(ids, n_in, claimed)
        for _ in range(campaigns):
            base = int(base_ts + rng.integers(burst_start, time_window_days) * 24 * 3600)

            # sudden inflows
            total_in = 0.0
            for f in funders:
                amt = round(float(rng.uniform(15_000, 60_000)), 2)
                total_in += amt
                ts = int(base + rng.integers(0, 5 * 24 * 3600))
                new_txns.append({
                    "transaction_id": f"TXN{txn_counter:09d}",
                    "src": f, "dst": acc, "amount": amt,
                    "timestamp": ts, "transaction_type": "transfer", "is_fraud": 1,
                })
                txn_counter += 1

            # rapid outflow to a few targets, draining the account
            n_out = int(rng.integers(2, 5))
            targets = _pick(ids, n_out, claimed)
            for t in targets:
                amt = round(total_in / len(targets) * rng.uniform(0.8, 1.0), 2)
                ts = int(base + rng.integers(5 * 24 * 3600, 12 * 24 * 3600))
                new_txns.append({
                    "transaction_id": f"TXN{txn_counter:09d}",
                    "src": acc, "dst": t, "amount": amt,
                    "timestamp": ts, "transaction_type": "transfer", "is_fraud": 1,
                })
                txn_counter += 1

    return typ, new_txns


def embed_mule_network(
    accounts: pd.DataFrame,
    n_networks: int,
    rng: np.random.Generator,
    claimed: set[str],
    txn_offset: int = 0,
    base_ts: int = BASE_TS,
    time_window_days: int = 365,
    campaigns: int = 1,
) -> tuple[dict[str, str], list[dict]]:
    """
    Mule-recruitment network: a recruiter fans out modest sums to many freshly
    opened disposable accounts, which forward the funds to a cash-out point.
    Distinct tree topology (high out-degree from the recruiter) vs. the ring's
    cycle. Recruited mules get a low opened_days_ago (fresh accounts).
    """
    ids = accounts["account_id"].tolist()
    typ: dict[str, str] = {}
    new_txns: list[dict] = []
    txn_counter = txn_offset
    entry_window_days = max(1, time_window_days - 20)

    for _ in range(n_networks):
        n_mules = int(rng.integers(10, 30))
        picked = _pick(ids, n_mules + 2, claimed)
        if len(picked) < 5:
            continue
        recruiter, cashout, *mules = picked
        claimed.update(picked)
        typ[recruiter] = "red_mulas"
        typ[cashout] = "red_mulas"
        for m in mules:
            typ[m] = "red_mulas"

        for _ in range(campaigns):
            base = int(base_ts + rng.integers(0, entry_window_days * 24 * 3600))

            for mule in mules:
                amt = round(float(rng.uniform(3_000, 9_500)), 2)   # small, below threshold
                ts_in = int(base + rng.integers(0, 72 * 3600))
                new_txns.append({
                    "transaction_id": f"TXN{txn_counter:09d}",
                    "src": recruiter, "dst": mule, "amount": amt,
                    "timestamp": ts_in, "transaction_type": "transfer", "is_fraud": 1,
                })
                txn_counter += 1
                # mule forwards most of it to the cash-out point
                ts_out = int(ts_in + rng.integers(3600, 72 * 3600))
                new_txns.append({
                    "transaction_id": f"TXN{txn_counter:09d}",
                    "src": mule, "dst": cashout,
                    "amount": round(amt * rng.uniform(0.85, 0.97), 2),
                    "timestamp": ts_out, "transaction_type": "transfer", "is_fraud": 1,
                })
                txn_counter += 1

    return typ, new_txns


def embed_roundtripping(
    accounts: pd.DataFrame,
    n_schemes: int,
    rng: np.random.Generator,
    claimed: set[str],
    txn_offset: int = 0,
    base_ts: int = BASE_TS,
    time_window_days: int = 365,
    campaigns: int = 1,
) -> tuple[dict[str, str], list[dict]]:
    """
    Round-tripping / U-turn (integration): money leaves an origin account,
    passes through a couple of intermediary ("external / offshore") accounts and
    returns to the origin (or a closely linked account) with a legitimate cover
    such as a loan repayment or investment return — the classic integration move
    that gives laundered funds a clean provenance.
    """
    ids = accounts["account_id"].tolist()
    typ: dict[str, str] = {}
    new_txns: list[dict] = []
    txn_counter = txn_offset
    entry_window_days = max(1, time_window_days - 30)

    for _ in range(n_schemes):
        n_hops = int(rng.integers(2, 4))
        nodes = _pick(ids, n_hops + 2, claimed)
        if len(nodes) < 3:
            continue
        origin, *intermediaries = nodes
        return_to = origin  # U-turn: funds come back to the origin
        claimed.update(nodes)
        for a in nodes:
            typ[a] = "round_tripping"

        for _ in range(campaigns):
            amount = round(float(rng.uniform(50_000, 200_000)), 2)
            ts = int(base_ts + rng.integers(0, entry_window_days * 24 * 3600))

            path = [origin] + intermediaries + [return_to]
            current = amount
            for i in range(len(path) - 1):
                ts = int(ts + rng.integers(24 * 3600, 120 * 3600))
                current = round(current * rng.uniform(0.95, 1.02), 2)  # ± "returns/fees"
                ttype = "payment" if i == len(path) - 2 else "transfer"
                new_txns.append({
                    "transaction_id": f"TXN{txn_counter:09d}",
                    "src": path[i], "dst": path[i + 1], "amount": current,
                    "timestamp": ts, "transaction_type": ttype, "is_fraud": 1,
                })
                txn_counter += 1

    return typ, new_txns


# ── main ─────────────────────────────────────────────────────────────────────

# ── enriquecimiento transaccional (metadata realista) ────────────────────────
# El vocabulario (canales, MCC, rubros) vive en txn_store, porque lo comparten
# esta función —que ASIGNA— y txn_store.hydrate() —que DERIVA código y glosa.

# Canal según el tipo de operación, con su probabilidad.
CANAL_BY_TYPE = {
    "transfer": (["Transferencia inmediata (CBU)", "Transferencia (CVU/alias)",
                  "Home Banking", "DEBIN"], [.45, .25, .20, .10]),
    "payment": (["Pago con tarjeta de débito (POS)", "Pago electrónico (VEP)",
                 "Débito automático", "Billetera virtual (QR)"], [.40, .20, .25, .15]),
    "withdrawal": (["Cajero automático (ATM)", "Ventanilla / caja",
                    "Extracción en comercio"], [.70, .20, .10]),
}
ESTADO_CATS = ["liquidada", "pendiente", "reversada"]
ESTADO_P = [.965, .025, .010]

# Comisión de cajero, en la unidad sintética del generador: ×100 la deja entre
# $1.500 y $6.000 de 2026. (El generador anterior sorteaba 80-420, que tras el
# reescalado daban comisiones de $8.000 a $42.000 por una extracción.)
ATM_FEE = (15.0, 60.0)
ATM_FEE_RATE = 0.35          # fracción de extracciones que cobran comisión
IIBB_RATE = 0.006            # impuesto a débitos y créditos, Ley 25.413
IIBB_SHARE = 0.50            # fracción de la operatoria alcanzada


def enrich_transactions(txns: pd.DataFrame, accounts: pd.DataFrame,
                        seed: int = 42) -> pd.DataFrame:
    """
    Añade canal, MCC, estado, comisión e impuesto al libro.

    Es METADATA: no toca src/dst/amount/timestamp/transaction_type/is_fraud, así
    que el grafo y las etiquetas quedan idénticos. Determinístico (rng propio).

    Trabaja con CÓDIGOS, no con texto: a ~10M filas un `rng.choice` sobre una
    lista de strings devuelve un array de objetos de ~800 MB por columna, que no
    entra en la máquina. Las columnas salen como Categorical, que es además el
    formato que espera txn_store.
    """
    rng = np.random.default_rng(seed + 777)
    n = len(txns)
    ttype = txns["transaction_type"].astype(str).to_numpy()

    # ── canal ────────────────────────────────────────────────────────────────
    canal_cats = list(txn_store.CANAL_COD)
    canal_pos = {c: i for i, c in enumerate(canal_cats)}
    canal_codes = np.zeros(n, dtype=np.int8)
    for t, (opts, probs) in CANAL_BY_TYPE.items():
        mask = ttype == t
        k = int(mask.sum())
        if k:
            pool = np.array([canal_pos[o] for o in opts], dtype=np.int8)
            canal_codes[mask] = pool[rng.choice(len(pool), k, p=probs)]

    # ── MCC / rubro: sólo pagos a comercios y empresas ───────────────────────
    mcc_cats = [""] + [m for m, _ in txn_store.MCC_MERCHANT] \
                    + [m for m, _ in txn_store.MCC_BUSINESS]
    mcc_pos = {m: i for i, m in enumerate(mcc_cats)}
    dst_type = accounts["account_type"].to_numpy()[np.asarray(txns["dst"])]
    is_pay = ttype == "payment"
    mcc_codes = np.zeros(n, dtype=np.int8)
    for kind, table in (("merchant", txn_store.MCC_MERCHANT),
                        ("business", txn_store.MCC_BUSINESS)):
        mask = is_pay & (dst_type == kind)
        k = int(mask.sum())
        if k:
            pool = np.array([mcc_pos[m] for m, _ in table], dtype=np.int8)
            mcc_codes[mask] = pool[rng.integers(0, len(pool), k)]

    # ── estado, comisión, impuesto ───────────────────────────────────────────
    estado_codes = rng.choice(len(ESTADO_CATS), n, p=ESTADO_P).astype(np.int8)

    amount = np.asarray(txns["amount"], dtype=np.float32)
    comision = np.zeros(n, dtype=np.float32)
    m_atm = canal_codes == canal_pos["Cajero automático (ATM)"]
    k = int(m_atm.sum())
    if k:
        fee = rng.uniform(*ATM_FEE, k) * (rng.random(k) < ATM_FEE_RATE)
        comision[m_atm] = np.round(fee, 2)

    impuesto = np.zeros(n, dtype=np.float32)
    m_imp = ((ttype == "transfer") | is_pay) & (rng.random(n) < IIBB_SHARE)
    impuesto[m_imp] = np.round(amount[m_imp] * IIBB_RATE, 2)

    out = txns.copy()
    out["canal"] = pd.Categorical.from_codes(canal_codes, categories=canal_cats)
    out["mcc"] = pd.Categorical.from_codes(mcc_codes, categories=mcc_cats)
    out["estado"] = pd.Categorical.from_codes(estado_codes, categories=ESTADO_CATS)
    out["comision"] = comision
    out["impuesto"] = impuesto
    return out


# ── escala monetaria ─────────────────────────────────────────────────────────
# Columnas expresadas en dinero. El resto (mcc, timestamps, grados, ratios) no.
MONETARY_COLS_TXN = ("amount", "comision", "impuesto")
MONETARY_COLS_ACC = ("balance",)


def rescale_amounts(txns_df: pd.DataFrame, accounts: pd.DataFrame,
                    factor: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Lleva los montos de la unidad sintética del generador a pesos argentinos.

    Es un factor LINEAL sobre las columnas monetarias. No toca src/dst/timestamp/
    transaction_type/is_fraud, así que el grafo es idéntico; y como build_graph
    normaliza las features con media/desvío de train, el factor se cancela
    exactamente —  (Kx - Kμ)/(Kσ) = (x - μ)/σ  — con lo cual data.x no cambia.

    Los umbrales monetarios de config.yaml están en la MISMA escala, de modo que
    ambos motores de reglas disparan exactamente sobre las mismas cuentas.
    """
    if factor == 1:
        return txns_df, accounts
    txns_df, accounts = txns_df.copy(), accounts.copy()
    for col in MONETARY_COLS_TXN:
        if col in txns_df.columns:
            txns_df[col] = np.round(
                np.asarray(txns_df[col], dtype=np.float64) * factor, 2
            ).astype(np.float32)
    for col in MONETARY_COLS_ACC:
        if col in accounts.columns:
            accounts[col] = (accounts[col] * factor).round(2)
    return txns_df, accounts


# ── intensidad de las tipologías ─────────────────────────────────────────────
# Campañas por esquema y por año. Una operación de lavado real no mueve el
# dinero una sola vez: cicla, repone y vuelve a dispersar durante todo el
# período. Con la economía minorista densa de fondo (~230 movimientos anuales
# por cuenta personal), una única campaña de ~20 transacciones dejaría la señal
# de fraude en el 1% de la actividad de la cuenta — una dilución que es artefacto
# del generador, no una propiedad del lavado.
#
# El orden sigue a `scenarios` en generate().
CAMPAIGNS_PER_SCHEME = (12, 15, 20, 12, 4, 12, 10)

# Tipologías cuya definición EXIGE poca actividad lícita propia: la cuenta
# durmiente lo es por definición, y la mula reclutada es una cuenta recién
# abierta y descartable. Al resto se le da actividad minorista normal a
# propósito — si las cuentas de fraude tuvieran sistemáticamente menos vida
# legítima, "moverse poco" sería una fuga que el modelo aprendería en lugar de
# aprender la estructura del lavado.
QUIET_TYPOLOGIES = {
    # la durmiente no tiene operatoria propia: es su definición
    "cuenta_durmiente": economy.TIER_DORMANT,
    # la mula reclutada es una cuenta recién abierta y descartable, con algo de
    # vida propia pero mucho menos que una cuenta establecida
    "red_mulas": economy.TIER_LOW,
}


def generate(scale: float, output_dir: str, seed: int = 42, time_window_days: int = 365,
             monetary_scale: float = 1.0):
    set_seed(seed)
    rng = np.random.default_rng(seed)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    n_accounts   = max(100, int(BASE_ACCOUNTS * scale))
    n_rings      = max(1,   int(BASE_RINGS * scale))
    n_structs    = max(1,   int(BASE_STRUCT_NETS * scale))
    n_flow       = max(1,   int(BASE_FLOWTHROUGH * scale))
    n_shell      = max(1,   int(BASE_SHELL * scale))
    n_dormant    = max(1,   int(BASE_DORMANT * scale))
    n_mulenet    = max(1,   int(BASE_MULENET * scale))
    n_roundtrip  = max(1,   int(BASE_ROUNDTRIP * scale))

    print(f"[generate] scale={scale}  accounts={n_accounts}  "
          f"time_window_days={time_window_days}")
    print(f"[generate] typologies: rings={n_rings} structuring={n_structs} "
          f"flowthrough={n_flow} shell={n_shell} dormant={n_dormant} "
          f"mule_net={n_mulenet} roundtrip={n_roundtrip}  "
          f"campaigns={CAMPAIGNS_PER_SCHEME}")

    # 1. Cuentas
    accounts = generate_accounts(n_accounts, rng)

    # 2. Tipologías de fraude — reclaman cuentas disjuntas y emiten sus txns.
    #    Van ANTES que la economía legítima porque su asignación decide a qué
    #    cuentas se les fuerza baja actividad lícita (ver QUIET_TYPOLOGIES).
    claimed: set[str] = set()
    typology: dict[str, str] = {}
    fraud_txns: list[dict] = []

    scenarios = [
        embed_laundering_rings,
        embed_structuring,
        embed_flowthrough,
        embed_shell_layering,
        embed_dormant_reactivation,
        embed_mule_network,
        embed_roundtripping,
    ]
    counts = [n_rings, n_structs, n_flow, n_shell, n_dormant, n_mulenet, n_roundtrip]

    for fn, n, camp in zip(scenarios, counts, CAMPAIGNS_PER_SCHEME):
        typ, txns = fn(
            accounts, n, rng, claimed,
            txn_offset=0, time_window_days=time_window_days, campaigns=camp,
        )
        typology.update(typ)
        fraud_txns.extend(txns)

    # 3. Etiquetas de fraude + tipología
    fraud_accs = set(typology)
    accounts.loc[accounts["account_id"].isin(fraud_accs), "is_fraud"] = 1
    accounts["fraud_typology"] = accounts["account_id"].map(typology).fillna("")

    # 3b. Retoques de comportamiento atados a la tipología:
    #     la durmiente parece antigua; la mula reclutada, recién abierta
    dormant_ids = [a for a, t in typology.items() if t == "cuenta_durmiente"]
    mule_ids    = [a for a, t in typology.items() if t == "red_mulas"]
    if dormant_ids:
        mask = accounts["account_id"].isin(dormant_ids)
        accounts.loc[mask, "opened_days_ago"] = rng.integers(365 * 3, 365 * 10, size=mask.sum())
    if mule_ids:
        mask = accounts["account_id"].isin(mule_ids)
        accounts.loc[mask, "opened_days_ago"] = rng.integers(5, 90, size=mask.sum())

    # 4. Economía minorista densa con contrapartes recurrentes
    act = economy.activity_weights(len(accounts), rng)
    typ_col = accounts["fraud_typology"].to_numpy()
    for typ_name, tier in QUIET_TYPOLOGIES.items():
        mask = typ_col == typ_name
        if mask.any():
            lo, hi = economy.ACTIVITY_TIERS[tier][1]
            act[mask] = rng.uniform(lo, hi, int(mask.sum()))
    econ = build_retail_economy(
        accounts, rng, base_ts=BASE_TS, window_days=time_window_days, weights=act,
    )
    n_econ = len(econ["src"])
    print(f"[generate] economía minorista: {n_econ:,} transacciones legítimas")

    # 5. Ensamblado compacto — índices posicionales, nunca strings por fila
    acc_index = pd.Index(accounts["account_id"])
    fdf = pd.DataFrame(fraud_txns)
    n_fraud = len(fdf)
    print(f"[generate] tipologías de fraude: {n_fraud:,} transacciones")

    ttype_cats = ["payment", "transfer", "withdrawal"]
    econ_tt = np.asarray(econ["transaction_type"].codes, dtype=np.int8) \
        if hasattr(econ["transaction_type"], "codes") else None
    econ_tt_cats = list(econ["transaction_type"].categories)
    remap = np.array([ttype_cats.index(c) for c in econ_tt_cats], dtype=np.int8)

    src = np.concatenate([econ["src"],
                          acc_index.get_indexer(fdf["src"]).astype(np.int32)])
    dst = np.concatenate([econ["dst"],
                          acc_index.get_indexer(fdf["dst"]).astype(np.int32)])
    amount = np.concatenate([econ["amount"],
                             fdf["amount"].to_numpy(dtype=np.float32)])
    timestamp = np.concatenate([econ["timestamp"],
                                fdf["timestamp"].to_numpy(dtype=np.int32)])
    tt = np.concatenate([
        remap[econ_tt],
        np.array([ttype_cats.index(t) for t in fdf["transaction_type"]], dtype=np.int8),
    ])
    is_fraud = np.concatenate([np.zeros(n_econ, dtype=np.int8),
                               np.ones(n_fraud, dtype=np.int8)])
    del econ, fdf, fraud_txns

    order = np.argsort(timestamp, kind="stable")
    txns = pd.DataFrame({
        "src": src[order], "dst": dst[order],
        "amount": amount[order], "timestamp": timestamp[order],
        "transaction_type": pd.Categorical.from_codes(tt[order], categories=ttype_cats),
        "is_fraud": is_fraud[order],
    })
    del src, dst, amount, timestamp, tt, is_fraud, order

    # 6. Metadata realista y escala monetaria
    txns = enrich_transactions(txns, accounts, seed=seed)
    txns, accounts = rescale_amounts(txns, accounts, monetary_scale)

    # 7. Persistencia
    acc_path = Path(output_dir) / "accounts.csv"
    accounts.to_csv(acc_path, index=False)
    store = txn_store.save_transactions(txns, output_dir, list(accounts["account_id"]))

    # 8. Resumen
    n_fraud_acc = int(accounts["is_fraud"].sum())
    n_fraud_txn = int(txns["is_fraud"].sum())
    deg = (np.bincount(np.asarray(txns["src"]), minlength=n_accounts)
           + np.bincount(np.asarray(txns["dst"]), minlength=n_accounts))
    pairs = len(np.unique(np.asarray(txns["src"], dtype=np.int64) * n_accounts
                          + np.asarray(txns["dst"])))

    print(f"\n{'='*62}")
    print(f"  accounts.csv    : {len(accounts):>10,} filas  —  nodos fraude : "
          f"{n_fraud_acc:>6,} ({100*n_fraud_acc/len(accounts):.1f}%)")
    print(f"  {store.name+'/':<16}: {len(txns):>10,} filas  —  aristas fraude: "
          f"{n_fraud_txn:>6,} ({100*n_fraud_txn/len(txns):.2f}%)")
    print(f"{'-'*62}")
    print(f"  movimientos por cuenta y año : media {deg.mean():.0f}  "
          f"mediana {np.median(deg):.0f}  P99 {np.percentile(deg, 99):.0f}")
    print(f"  aristas únicas               : {pairs:,}  "
          f"({len(txns)/pairs:.2f} txns por arista)")
    print(f"{'-'*62}")
    print("  cuentas de fraude por tipología:")
    for t, c in accounts.loc[accounts.is_fraud == 1, "fraud_typology"].value_counts().items():
        print(f"    {t:<20} {c:>5,}")
    print(f"{'='*62}")
    print(f"  Salida: {output_dir}/")

    return accounts, txns
def main():
    parser = argparse.ArgumentParser(description="Generate synthetic fraud graph dataset")
    parser.add_argument("--scale",  type=float, default=None)
    parser.add_argument("--config", default="config/config.yaml")
    args = parser.parse_args()

    cfg     = load_config(args.config)
    scale   = args.scale if args.scale is not None else cfg["data"]["scale_factor"]
    outdir  = cfg["data"]["raw_dir"]
    seed    = cfg["project"]["seed"]
    window  = cfg["data"].get("time_window_days", 365)

    mscale  = cfg.get("monetary", {}).get("scale", 1.0)

    generate(scale=scale, output_dir=outdir, seed=seed, time_window_days=window,
             monetary_scale=mscale)


if __name__ == "__main__":
    main()
