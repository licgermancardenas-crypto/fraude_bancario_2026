"""
Generate synthetic bank fraud graph dataset.

Produces two CSVs in data/raw/:
  accounts.csv   — nodes  (one row per account)
  transactions.csv — edges (one row per transaction)

Fraud patterns embedded:
  - Cyclic laundering rings: A→B→C→…→A (4-7 hops), money exits via fan-out
  - Structuring (pitufeo): one source splitting large sums into many small transfers
  - Fan-in aggregation: many mule accounts funneling into one collector

Scale factor controls graph size:
  scale=0.01  →  ~1 500 accounts,  ~8 000 transactions  (dev/test)
  scale=0.10  →  ~15 000 accounts, ~80 000 transactions
  scale=1.00  →  ~150 000 accounts, ~800 000 transactions
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
FRAUD_EDGE_NOISE  = 0.005


def _account_id(i: int) -> str:
    return f"ACC{i:07d}"


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
    })
    return df


def generate_legitimate_txns(
    accounts: pd.DataFrame,
    n_txns: int,
    rng: np.random.Generator,
    base_ts: int = 1_700_000_000,
) -> list[dict]:
    """Generate random legitimate transactions between accounts."""
    ids = np.asarray(accounts["account_id"])
    txns = []
    for i in range(n_txns):
        src, dst = rng.choice(ids, size=2, replace=False)
        amount = round(float(rng.lognormal(mean=4.5, sigma=1.5)), 2)  # ~$90 median
        ts = int(base_ts + rng.integers(0, 365 * 24 * 3600))
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
    txns: list[dict],
    n_rings: int,
    rng: np.random.Generator,
    base_ts: int = 1_700_000_000,
    txn_offset: int = 0,
) -> tuple[set[str], list[dict]]:
    """
    Embed cyclic money-laundering rings (4-7 hops).
    Each ring: money enters from outside → cycles N times → exits in small chunks.
    Returns set of fraud account IDs and new transaction records.
    """
    ids = accounts["account_id"].tolist()
    fraud_accounts: set[str] = set()
    new_txns: list[dict] = []
    txn_counter = txn_offset

    for r in range(n_rings):
        ring_len = int(rng.integers(4, 8))      # 4-7 nodes
        ring_nodes = random.sample(ids, ring_len)
        fraud_accounts.update(ring_nodes)

        # entry transaction (outside → ring[0])
        entry_src = random.choice([a for a in ids if a not in fraud_accounts])
        entry_amount = round(float(rng.uniform(5_000, 50_000)), 2)
        entry_ts = int(base_ts + rng.integers(0, 300 * 24 * 3600))

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

    return fraud_accounts, new_txns


def embed_structuring(
    accounts: pd.DataFrame,
    txns: list[dict],
    n_nets: int,
    rng: np.random.Generator,
    base_ts: int = 1_700_000_000,
    txn_offset: int = 0,
) -> tuple[set[str], list[dict]]:
    """
    Embed structuring (pitufeo) patterns: one source fans out into many small
    transfers to avoid detection thresholds, then a collector aggregates them.
    """
    ids = accounts["account_id"].tolist()
    fraud_accounts: set[str] = set()
    new_txns: list[dict] = []
    txn_counter = txn_offset

    for _ in range(n_nets):
        n_mules = int(rng.integers(5, 15))
        source = random.choice(ids)
        collector = random.choice([a for a in ids if a != source])
        mules = random.sample([a for a in ids if a not in (source, collector)], n_mules)
        fraud_accounts.update([source, collector] + mules)

        total = round(float(rng.uniform(10_000, 100_000)), 2)
        base = int(base_ts + rng.integers(0, 300 * 24 * 3600))

        # source → mules (structured, below $10k each)
        per_mule = total / n_mules
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

    return fraud_accounts, new_txns


# ── main ─────────────────────────────────────────────────────────────────────

def generate(scale: float, output_dir: str, seed: int = 42):
    set_seed(seed)
    rng = np.random.default_rng(seed)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    n_accounts = max(100, int(BASE_ACCOUNTS * scale))
    n_txns     = max(200, int(BASE_TRANSACTIONS * scale))
    n_rings    = max(1,   int(BASE_RINGS * scale))
    n_structs  = max(1,   int(BASE_STRUCT_NETS * scale))

    print(f"[generate] scale={scale}  accounts={n_accounts}  transactions={n_txns}  "
          f"rings={n_rings}  structuring_nets={n_structs}")

    # 1. Accounts
    accounts = generate_accounts(n_accounts, rng)

    # 2. Legitimate transactions
    legit_txns = generate_legitimate_txns(accounts, n_txns, rng)
    txn_offset = len(legit_txns)

    # 3. Fraud patterns
    fraud_accs: set[str] = set()

    ring_accs, ring_txns = embed_laundering_rings(
        accounts, legit_txns, n_rings, rng, txn_offset=txn_offset
    )
    fraud_accs.update(ring_accs)
    txn_offset += len(ring_txns)

    struct_accs, struct_txns = embed_structuring(
        accounts, legit_txns, n_structs, rng, txn_offset=txn_offset
    )
    fraud_accs.update(struct_accs)
    txn_offset += len(struct_txns)

    # 4. Label fraud accounts
    accounts.loc[accounts["account_id"].isin(fraud_accs), "is_fraud"] = 1

    # 5. Assemble transactions
    all_txns = legit_txns + ring_txns + struct_txns
    txns_df = pd.DataFrame(all_txns).sort_values("timestamp").reset_index(drop=True)

    # 6. Save
    acc_path  = Path(output_dir) / "accounts.csv"
    txn_path  = Path(output_dir) / "transactions.csv"
    accounts.to_csv(acc_path, index=False)
    txns_df.to_csv(txn_path, index=False)

    # 7. Summary
    n_fraud_acc  = accounts["is_fraud"].sum()
    n_fraud_txn  = txns_df["is_fraud"].sum()
    pct_acc  = 100 * n_fraud_acc / len(accounts)
    pct_txn  = 100 * n_fraud_txn / len(txns_df)

    print(f"\n{'='*55}")
    print(f"  accounts.csv    : {len(accounts):>7,} rows  —  fraud nodes : {n_fraud_acc:>5,} ({pct_acc:.1f}%)")
    print(f"  transactions.csv: {len(txns_df):>7,} rows  —  fraud edges : {n_fraud_txn:>5,} ({pct_txn:.1f}%)")
    print(f"{'='*55}")
    print(f"  Output: {output_dir}/")

    return accounts, txns_df


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic fraud graph dataset")
    parser.add_argument("--scale",  type=float, default=None)
    parser.add_argument("--config", default="config/config.yaml")
    args = parser.parse_args()

    cfg    = load_config(args.config)
    scale  = args.scale if args.scale is not None else cfg["data"]["scale_factor"]
    outdir = cfg["data"]["raw_dir"]
    seed   = cfg["project"]["seed"]

    generate(scale=scale, output_dir=outdir, seed=seed)


if __name__ == "__main__":
    main()
