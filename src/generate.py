"""
Generate synthetic bank fraud graph dataset.

Produces two CSVs in data/raw/:
  accounts.csv   — nodes  (one row per account, with fraud_typology label)
  transactions.csv — edges (one row per transaction)

Fraud typologies embedded (GAFI/FATF-aligned):
  - anillo_lavado    Cyclic laundering rings A→B→…→A (4-7 hops) + exit fan-out
  - estructuracion   Structuring (pitufeo): one source splitting into many small transfers
  - agregacion_fondos Fan-in: many mules funnelling into one collector
  - cuenta_paso      Flow-through: money in and out within hours, ~0 retention
  - shell_layering   Layering through shell-company (business) conduits
  - cuenta_durmiente Dormant account suddenly reactivated with large bursts
  - red_mulas        Mule-recruitment network: fan-out to many fresh disposable accounts
  - round_tripping   U-turn / round-tripping: money leaves and returns (integration)

Each fraud account is labelled with exactly one typology in the
`fraud_typology` column; legitimate accounts carry "".

Scale factor controls graph size (transaction count assumes the default
365-day window; see time_window_days below):
  scale=0.01  →  ~1 500 accounts,  ~8 000 transactions  (dev/test)
  scale=0.10  →  ~15 000 accounts, ~80 000 transactions
  scale=1.00  →  ~150 000 accounts, ~800 000 transactions

time_window_days stretches (or compresses) the date range transactions are
spread over, keeping the same daily transaction density: doubling it from
the default 365 to 730 doubles transaction count for a given scale.
"""

import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


# ── helpers ──────────────────────────────────────────────────────────────────

def load_config(path: str = "config/config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)


# ── generation ───────────────────────────────────────────────────────────────

BASE_ACCOUNTS     = 150_000   # scale=0.01 → ~1 500 accounts
BASE_TRANSACTIONS = 800_000   # scale=0.01 → ~8 000 transactions
BASE_RINGS        = 200       # scale=0.01 → ~2 rings
BASE_STRUCT_NETS  = 100       # scale=0.01 → ~1 structuring net
BASE_FLOWTHROUGH  = 120       # flow-through chains
BASE_SHELL        = 80        # shell-company layering schemes
BASE_DORMANT      = 80        # dormant-account reactivations
BASE_MULENET      = 60        # mule-recruitment networks
BASE_ROUNDTRIP    = 60        # round-tripping / U-turn schemes
FRAUD_EDGE_NOISE  = 0.005
BASE_TS           = 1_700_000_000

# Legitimate economy: fraction of business/merchant accounts that behave like a
# real going concern (payroll, suppliers, customer receipts) rather than a flat
# noise floor. Adds a plausible legit layer whose high-activity accounts stress
# the detector with realistic false-positive pressure.
ECON_ACTIVE_BUSINESS = 0.25
ECON_ACTIVE_MERCHANT = 0.35


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


def generate_legitimate_txns(
    accounts: pd.DataFrame,
    n_txns: int,
    rng: np.random.Generator,
    base_ts: int = BASE_TS,
    time_window_days: int = 365,
) -> list[dict]:
    """Generate random legitimate transactions between accounts."""
    ids = np.asarray(accounts["account_id"])
    txns = []
    for i in range(n_txns):
        src, dst = rng.choice(ids, size=2, replace=False)
        amount = round(float(rng.lognormal(mean=4.5, sigma=1.5)), 2)  # ~$90 median
        ts = int(base_ts + rng.integers(0, time_window_days * 24 * 3600))
        txns.append({
            "transaction_id": f"TXN{i:09d}",
            "src": src,
            "dst": dst,
            "amount": amount,
            "timestamp": ts,
            "transaction_type": rng.choice(
                ["transfer", "payment", "withdrawal"],
                p=[0.5, 0.35, 0.15],
            ),
            "is_fraud": 0,
        })
    return txns


def embed_laundering_rings(
    accounts: pd.DataFrame,
    n_rings: int,
    rng: np.random.Generator,
    claimed: set[str],
    txn_offset: int = 0,
    base_ts: int = BASE_TS,
    time_window_days: int = 365,
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


def embed_legitimate_economy(
    accounts: pd.DataFrame,
    rng: np.random.Generator,
    claimed: set[str],
    txn_offset: int = 0,
    base_ts: int = BASE_TS,
    time_window_days: int = 365,
) -> list[dict]:
    """
    Give business and merchant accounts realistic *legitimate* behaviour so the
    graph carries a plausible economy instead of a flat noise floor:
      - merchants receive many small customer payments (legit fan-in)
      - businesses run payroll (recurring fan-out to employee accounts) and pay
        suppliers (recurring outflows to other businesses)

    All edges are is_fraud=0. Fraud-claimed accounts are never used as the
    business/merchant actor, so their behaviour stays driven by their typology
    — but they may appear as counterparties (a mule can be someone's customer).
    This deliberately creates legit high-fan-in / high-fan-out / high-volume
    accounts that look superficially like laundering, the realistic false-
    positive pressure a real transaction-monitoring system must cope with.
    """
    by_type = accounts.groupby("account_type")["account_id"].apply(list).to_dict()
    businesses = [a for a in by_type.get("business", []) if a not in claimed]
    merchants  = [a for a in by_type.get("merchant", []) if a not in claimed]
    personals  = by_type.get("personal", [])
    new_txns: list[dict] = []
    c = txn_offset
    span = max(1, time_window_days)

    def _ts() -> int:
        return int(base_ts + rng.integers(0, span * 24 * 3600))

    # ── merchants: customer receipts (legit fan-in) ───────────────────────────
    n_active_m = int(len(merchants) * ECON_ACTIVE_MERCHANT)
    for m in random.sample(merchants, n_active_m) if merchants else []:
        n_cust = int(rng.integers(12, 35))
        for cust in random.sample(personals, min(n_cust, len(personals))):
            amt = round(float(rng.lognormal(mean=5.5, sigma=1.0)), 2)  # ~$250 median
            new_txns.append({
                "transaction_id": f"TXN{c:09d}",
                "src": cust, "dst": m, "amount": amt,
                "timestamp": _ts(), "transaction_type": "payment", "is_fraud": 0,
            })
            c += 1

    # ── businesses: payroll (fan-out) + supplier payments ─────────────────────
    n_active_b = int(len(businesses) * ECON_ACTIVE_BUSINESS)
    n_periods  = max(2, time_window_days // 180)   # ~ twice a year
    for b in random.sample(businesses, n_active_b) if businesses else []:
        # payroll to a stable set of employees, repeated each pay period
        n_emp = int(rng.integers(4, 11))
        employees = random.sample(personals, min(n_emp, len(personals)))
        base_salary = float(rng.uniform(800, 3000))
        for _ in range(n_periods):
            period_ts = _ts()
            for emp in employees:
                amt = round(base_salary * rng.uniform(0.9, 1.1), 2)
                ts = int(period_ts + rng.integers(0, 3 * 24 * 3600))
                new_txns.append({
                    "transaction_id": f"TXN{c:09d}",
                    "src": b, "dst": emp, "amount": amt,
                    "timestamp": ts, "transaction_type": "transfer", "is_fraud": 0,
                })
                c += 1
        # recurring supplier payments to other businesses
        n_sup = int(rng.integers(2, 5))
        for sup in random.sample(businesses, min(n_sup, len(businesses))):
            for _ in range(int(rng.integers(2, 5))):
                amt = round(float(rng.uniform(3_000, 25_000)), 2)
                new_txns.append({
                    "transaction_id": f"TXN{c:09d}",
                    "src": b, "dst": sup, "amount": amt,
                    "timestamp": _ts(), "transaction_type": "payment", "is_fraud": 0,
                })
                c += 1

    return new_txns


# ── main ─────────────────────────────────────────────────────────────────────

# ── enriquecimiento transaccional (metadata realista) ────────────────────────
_CANAL_COD = {
    "Transferencia inmediata (CBU)": "TRA-CBU", "Transferencia (CVU/alias)": "TRA-CVU",
    "Home Banking": "HB", "DEBIN": "DEBIN",
    "Pago con tarjeta de débito (POS)": "POS", "Pago electrónico (VEP)": "VEP",
    "Débito automático": "DEB-AUT", "Billetera virtual (QR)": "QR",
    "Cajero automático (ATM)": "ATM", "Ventanilla / caja": "CAJA", "Extracción en comercio": "EXT-COM",
}
_MCC_MERCHANT = [("5411", "Supermercados y almacenes"), ("5812", "Restaurantes y bares"),
                 ("5912", "Farmacias"), ("5541", "Estaciones de servicio"),
                 ("5651", "Indumentaria y calzado"), ("5732", "Electrónica y tecnología"),
                 ("5999", "Comercio minorista varios"), ("5814", "Comidas rápidas")]
_MCC_BUSINESS = [("7372", "Servicios informáticos"), ("8931", "Servicios contables"),
                 ("1520", "Construcción"), ("4214", "Transporte de cargas"),
                 ("5122", "Distribución mayorista"), ("6513", "Alquiler inmobiliario")]


def enrich_transactions(txns_df: pd.DataFrame, accounts: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """
    Añade campos transaccionales realistas (canal, código, CBU/alias del destino,
    MCC/rubro, glosa, estado, comisión, impuesto Ley 25.413, moneda, referencia).

    Es METADATA de presentación: NO altera src/dst/amount/timestamp/transaction_type/
    is_fraud, así que el grafo y el modelo quedan idénticos. Determinístico (rng propio).
    """
    rng = np.random.default_rng(seed + 777)
    n = len(txns_df)
    at = accounts.set_index("account_id")["account_type"]
    dst_type = txns_df["dst"].map(at).fillna("personal").to_numpy()
    ttype = txns_df["transaction_type"].to_numpy()
    amount = txns_df["amount"].to_numpy(dtype=float)
    idx = txns_df.index

    is_tr, is_pay, is_wd = ttype == "transfer", ttype == "payment", ttype == "withdrawal"

    ch_tr = rng.choice(["Transferencia inmediata (CBU)", "Transferencia (CVU/alias)", "Home Banking", "DEBIN"], n, p=[.45, .25, .2, .1])
    ch_pay = rng.choice(["Pago con tarjeta de débito (POS)", "Pago electrónico (VEP)", "Débito automático", "Billetera virtual (QR)"], n, p=[.4, .2, .25, .15])
    ch_wd = rng.choice(["Cajero automático (ATM)", "Ventanilla / caja", "Extracción en comercio"], n, p=[.7, .2, .1])
    canal = np.where(is_tr, ch_tr, np.where(is_pay, ch_pay, ch_wd))
    canal_cod = pd.Series(canal, index=idx).map(_CANAL_COD).to_numpy()

    # CBU estable por cuenta destino (22 dígitos) + alias para canal CVU
    accs = accounts["account_id"].to_numpy()
    digits = np.random.default_rng(seed + 888).integers(0, 10, size=(len(accs), 22))
    cbu_map = {a: "".join(map(str, digits[i])) for i, a in enumerate(accs)}
    cbu_dst = txns_df["dst"].map(cbu_map).to_numpy()
    alias_dst = np.where(canal == "Transferencia (CVU/alias)",
                         pd.Series(txns_df["dst"].to_numpy(), index=idx).map(lambda x: f"{x[-4:].lower()}.brs.ar").to_numpy(), "")

    # MCC / rubro para pagos a comercios y empresas
    mcc = np.array([""] * n, dtype=object); rubro = np.array([""] * n, dtype=object)
    mask_m, mask_b = is_pay & (dst_type == "merchant"), is_pay & (dst_type == "business")
    for mask, table in ((mask_m, _MCC_MERCHANT), (mask_b, _MCC_BUSINESS)):
        k = int(mask.sum())
        if k:
            pick = rng.integers(0, len(table), k)
            mcc[mask] = [table[i][0] for i in pick]
            rubro[mask] = [table[i][1] for i in pick]

    # glosa (orden: cada regla posterior pisa a la anterior)
    g = pd.Series("Transferencia entre cuentas", index=idx)
    g[dst_type == "business"] = "Transferencia a proveedor"
    g[dst_type == "merchant"] = "Pago a comercio"
    g[is_pay] = "Pago de servicios"
    g[mask_m | mask_b] = "Pago - " + pd.Series(rubro, index=idx)[mask_m | mask_b]
    g[is_wd] = "Extracción de efectivo"

    estado = rng.choice(["liquidada", "pendiente", "reversada"], n, p=[.965, .025, .01])

    comision = np.zeros(n)
    m_atm = canal == "Cajero automático (ATM)"
    k = int(m_atm.sum())
    if k:
        comision[m_atm] = np.round(rng.uniform(80, 420, k) * (rng.random(k) < 0.35), 2)

    # impuesto a débitos y créditos (Ley 25.413, 0,6%) — aplica a parte de la operatoria
    impuesto = np.zeros(n)
    m_imp = (is_tr | is_pay) & (rng.random(n) < 0.5)
    impuesto[m_imp] = np.round(amount[m_imp] * 0.006, 2)

    referencia = [f"REF-{r}" for r in rng.integers(10_000_000, 99_999_999, n)]

    out = txns_df.copy()
    out["canal"] = canal
    out["canal_codigo"] = canal_cod
    out["cbu_dst"] = cbu_dst
    out["alias_dst"] = alias_dst
    out["mcc"] = mcc
    out["rubro"] = rubro
    out["glosa"] = g.to_numpy()
    out["estado"] = estado
    out["comision"] = comision
    out["impuesto"] = impuesto
    out["moneda"] = "ARS"
    out["referencia"] = referencia
    return out


def generate(scale: float, output_dir: str, seed: int = 42, time_window_days: int = 365):
    set_seed(seed)
    rng = np.random.default_rng(seed)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    duration_factor = time_window_days / 365
    n_accounts   = max(100, int(BASE_ACCOUNTS * scale))
    n_txns       = max(200, int(BASE_TRANSACTIONS * scale * duration_factor))
    n_rings      = max(1,   int(BASE_RINGS * scale))
    n_structs    = max(1,   int(BASE_STRUCT_NETS * scale))
    n_flow       = max(1,   int(BASE_FLOWTHROUGH * scale))
    n_shell      = max(1,   int(BASE_SHELL * scale))
    n_dormant    = max(1,   int(BASE_DORMANT * scale))
    n_mulenet    = max(1,   int(BASE_MULENET * scale))
    n_roundtrip  = max(1,   int(BASE_ROUNDTRIP * scale))

    print(f"[generate] scale={scale}  accounts={n_accounts}  transactions={n_txns}  "
          f"time_window_days={time_window_days}")
    print(f"[generate] typologies: rings={n_rings} structuring={n_structs} "
          f"flowthrough={n_flow} shell={n_shell} dormant={n_dormant} "
          f"mule_net={n_mulenet} roundtrip={n_roundtrip}")

    # 1. Accounts
    accounts = generate_accounts(n_accounts, rng)

    # 2. Legitimate transactions
    legit_txns = generate_legitimate_txns(accounts, n_txns, rng, time_window_days=time_window_days)
    txn_offset = len(legit_txns)

    # 3. Fraud typologies — each claims disjoint accounts and appends its txns
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

    for fn, n in zip(scenarios, counts):
        typ, txns = fn(
            accounts, n, rng, claimed,
            txn_offset=txn_offset, time_window_days=time_window_days,
        )
        typology.update(typ)
        fraud_txns.extend(txns)
        txn_offset += len(txns)

    # 3b. Legitimate economy — business/merchant realistic behaviour (is_fraud=0)
    econ_txns = embed_legitimate_economy(
        accounts, rng, claimed, txn_offset=txn_offset, time_window_days=time_window_days,
    )
    txn_offset += len(econ_txns)

    # 4. Label fraud accounts + typology
    fraud_accs = set(typology)
    accounts.loc[accounts["account_id"].isin(fraud_accs), "is_fraud"] = 1
    accounts["fraud_typology"] = accounts["account_id"].map(typology).fillna("")

    # 4b. Behavioural touch-ups tied to typology
    #     dormant accounts look long-standing; recruited mules look brand-new
    dormant_ids = [a for a, t in typology.items() if t == "cuenta_durmiente"]
    mule_ids    = [a for a, t in typology.items() if t == "red_mulas"]
    if dormant_ids:
        mask = accounts["account_id"].isin(dormant_ids)
        accounts.loc[mask, "opened_days_ago"] = rng.integers(365 * 3, 365 * 10, size=mask.sum())
    if mule_ids:
        mask = accounts["account_id"].isin(mule_ids)
        accounts.loc[mask, "opened_days_ago"] = rng.integers(5, 90, size=mask.sum())

    # 5. Assemble transactions
    all_txns = legit_txns + econ_txns + fraud_txns
    txns_df = pd.DataFrame(all_txns).sort_values("timestamp").reset_index(drop=True)

    # 5b. Enriquecimiento transaccional (metadata realista; no toca la estructura)
    txns_df = enrich_transactions(txns_df, accounts, seed=seed)

    # 6. Save
    acc_path  = Path(output_dir) / "accounts.csv"
    txn_path  = Path(output_dir) / "transactions.csv"
    accounts.to_csv(acc_path, index=False)
    txns_df.to_csv(txn_path, index=False)

    # 7. Summary
    n_fraud_acc  = int(accounts["is_fraud"].sum())
    n_fraud_txn  = int(txns_df["is_fraud"].sum())
    pct_acc  = 100 * n_fraud_acc / len(accounts)
    pct_txn  = 100 * n_fraud_txn / len(txns_df)

    print(f"\n{'='*55}")
    print(f"  accounts.csv    : {len(accounts):>7,} rows  —  fraud nodes : {n_fraud_acc:>5,} ({pct_acc:.1f}%)")
    print(f"  transactions.csv: {len(txns_df):>7,} rows  —  fraud edges : {n_fraud_txn:>5,} ({pct_txn:.1f}%)")
    print(f"{'-'*55}")
    print("  fraud accounts by typology:")
    for t, c in accounts.loc[accounts.is_fraud == 1, "fraud_typology"].value_counts().items():
        print(f"    {t:<20} {c:>5,}")
    print(f"{'='*55}")
    print(f"  Output: {output_dir}/")

    return accounts, txns_df


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

    generate(scale=scale, output_dir=outdir, seed=seed, time_window_days=window)


if __name__ == "__main__":
    main()
