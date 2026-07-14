"""
Tabular node feature engineering from the raw transaction graph.
Produces one row per account with graph-derived and account-level features.
Used by both baseline models and as input features for GraphSAGE.
"""

import numpy as np
import pandas as pd
import networkx as nx


def build_node_features(acc: pd.DataFrame, txn: pd.DataFrame) -> pd.DataFrame:
    """
    Compute tabular features for each node (account).

    Graph-derived features (computed from transactions):
      degree_in, degree_out, total_received, total_sent,
      avg_received, avg_sent, unique_senders, unique_receivers,
      degree_ratio, amount_ratio, max_sent, max_received,
      txn_count (total transactions involving this account)

    Account-level features (from accounts.csv):
      balance, risk_score, opened_days_ago, account_type_* (one-hot)

    Returns DataFrame indexed by account_id with is_fraud label.
    """
    # ── graph-derived ─────────────────────────────────────────────────────────
    recv = (
        txn.groupby("dst")["amount"]
        .agg(total_received="sum", avg_received="mean",
             max_received="max", unique_senders="count")
        .rename_axis("account_id")
    )
    recv["unique_senders"] = txn.groupby("dst")["src"].nunique()

    sent = (
        txn.groupby("src")["amount"]
        .agg(total_sent="sum", avg_sent="mean",
             max_sent="max")
        .rename_axis("account_id")
    )
    sent["unique_receivers"] = txn.groupby("src")["dst"].nunique()

    in_deg  = txn.groupby("dst").size().rename("degree_in")
    out_deg = txn.groupby("src").size().rename("degree_out")

    feats = (
        acc.set_index("account_id")
        .join(recv, how="left")
        .join(sent, how="left")
        .join(in_deg, how="left")
        .join(out_deg, how="left")
    )

    # fill accounts with zero transactions
    for col in ["total_received", "avg_received", "max_received", "unique_senders",
                "total_sent", "avg_sent", "max_sent", "unique_receivers",
                "degree_in", "degree_out"]:
        feats[col] = feats[col].fillna(0.0)

    # derived ratios (eps avoids div-by-zero)
    eps = 1e-6
    feats["degree_ratio"]  = feats["degree_out"] / (feats["degree_in"]  + eps)
    feats["amount_ratio"]  = feats["total_sent"] / (feats["total_received"] + eps)
    feats["txn_count"]     = feats["degree_in"] + feats["degree_out"]

    # ── account-level ─────────────────────────────────────────────────────────
    # one-hot encode account_type (drop_first avoids perfect collinearity)
    dummies = pd.get_dummies(feats["account_type"], prefix="type", drop_first=True)
    feats = pd.concat([feats, dummies], axis=1)

    return feats.reset_index()


FEATURE_COLS = [
    # graph-derived
    "degree_in", "degree_out", "txn_count",
    "total_received", "total_sent",
    "avg_received", "avg_sent",
    "max_received", "max_sent",
    "unique_senders", "unique_receivers",
    "degree_ratio", "amount_ratio",
    # account-level
    "balance", "risk_score", "opened_days_ago",
    # one-hot (present only if those account types exist)
    "type_merchant", "type_personal",
]


def get_feature_matrix(feats: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Return (X, y, feature_names) as numpy arrays."""
    present_cols = [c for c in FEATURE_COLS if c in feats.columns]
    X = feats[present_cols].values.astype(np.float32)
    y = feats["is_fraud"].values.astype(np.int32)
    return X, y, present_cols
