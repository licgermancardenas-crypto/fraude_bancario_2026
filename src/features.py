"""
Tabular node feature engineering from the raw transaction graph.
Produces one row per account with graph-derived, account-level and
behavioural/temporal features. Used by both baseline models and as input
features for the GNNs.

The behavioural block derives velocity, latency, burstiness and retention
signals from transaction timestamps — the kind of features real AML
transaction-monitoring systems rely on, and the ones that expose typologies
whose signature is temporal rather than purely structural (dormant-account
reactivation, flow-through/pass-through accounts, mule networks).
"""

import numpy as np
import pandas as pd
import networkx as nx


SECONDS_PER_DAY = 86_400
SECONDS_PER_HOUR = 3_600
EPS = 1e-6


def _behavioural_features(txn: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-account temporal / behavioural features from transaction
    timestamps. Returns a DataFrame indexed by account_id.
    """
    # unified activity timeline: every txn is an event for both counterparties
    out_ev = txn[["src", "timestamp"]].rename(columns={"src": "account_id"})
    in_ev  = txn[["dst", "timestamp"]].rename(columns={"dst": "account_id"})
    ev = pd.concat([out_ev, in_ev], ignore_index=True)
    ev["day"]      = ev["timestamp"] // SECONDS_PER_DAY
    ev["is_night"] = ((ev["timestamp"] // SECONDS_PER_HOUR) % 24) < 6

    g = ev.groupby("account_id")
    agg = g.agg(
        first_ts=("timestamp", "min"),
        last_ts=("timestamp", "max"),
        n_ev=("timestamp", "size"),
        active_days=("day", "nunique"),
        night_ratio=("is_night", "mean"),
    )

    # burstiness: largest share of an account's activity landing in a single day
    per_day = ev.groupby(["account_id", "day"]).size()
    agg["max_day_ev"] = per_day.groupby("account_id").max()

    agg["activity_span_days"] = (agg["last_ts"] - agg["first_ts"]) / SECONDS_PER_DAY
    agg["burst_ratio"] = agg["max_day_ev"] / agg["n_ev"].clip(lower=1)
    agg["mean_interval_hours"] = np.where(
        agg["n_ev"] > 1,
        (agg["last_ts"] - agg["first_ts"]) / SECONDS_PER_HOUR / (agg["n_ev"] - 1).clip(lower=1),
        0.0,
    )

    gmin, gmax = ev["timestamp"].min(), ev["timestamp"].max()
    agg["recency_ratio"] = (agg["last_ts"] - gmin) / max(gmax - gmin, 1)

    # rapid_out_ratio: fraction of inflows forwarded back out within 24 h — the
    # hallmark of a pass-through / mule conduit. Computed with an as-of join
    # matching each inflow to the next outflow of the same account.
    inflow  = txn[["dst", "timestamp"]].rename(columns={"dst": "account_id"}).sort_values("timestamp")
    outflow = txn[["src", "timestamp"]].rename(columns={"src": "account_id"}).sort_values("timestamp")
    outflow["_out"] = 1
    matched = pd.merge_asof(
        inflow, outflow[["account_id", "timestamp", "_out"]],
        on="timestamp", by="account_id",
        direction="forward", tolerance=24 * SECONDS_PER_HOUR,
    )
    matched["_hit"] = matched["_out"].notna()
    agg["rapid_out_ratio"] = matched.groupby("account_id")["_hit"].mean()

    return agg[[
        "active_days", "activity_span_days", "burst_ratio", "night_ratio",
        "mean_interval_hours", "recency_ratio", "rapid_out_ratio",
    ]]


def build_node_features(acc: pd.DataFrame, txn: pd.DataFrame) -> pd.DataFrame:
    """
    Compute tabular features for each node (account).

    Graph-derived features (computed from transactions):
      degree_in, degree_out, total_received, total_sent,
      avg_received, avg_sent, unique_senders, unique_receivers,
      degree_ratio, amount_ratio, max_sent, max_received,
      txn_count (total transactions involving this account)

    Behavioural / temporal features (from transaction timestamps):
      active_days, activity_span_days, burst_ratio, night_ratio,
      mean_interval_hours, recency_ratio, rapid_out_ratio,
      balance_retention, in_out_symmetry

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

    behav = _behavioural_features(txn)

    feats = (
        acc.set_index("account_id")
        .join(recv, how="left")
        .join(sent, how="left")
        .join(in_deg, how="left")
        .join(out_deg, how="left")
        .join(behav, how="left")
    )

    # fill accounts with zero transactions
    zero_fill = ["total_received", "avg_received", "max_received", "unique_senders",
                 "total_sent", "avg_sent", "max_sent", "unique_receivers",
                 "degree_in", "degree_out",
                 "active_days", "activity_span_days", "burst_ratio", "night_ratio",
                 "mean_interval_hours", "recency_ratio", "rapid_out_ratio"]
    for col in zero_fill:
        feats[col] = feats[col].fillna(0.0)

    # derived ratios (eps avoids div-by-zero)
    feats["degree_ratio"]  = feats["degree_out"] / (feats["degree_in"]  + EPS)
    feats["amount_ratio"]  = feats["total_sent"] / (feats["total_received"] + EPS)
    feats["txn_count"]     = feats["degree_in"] + feats["degree_out"]

    # behavioural ratios that reuse the aggregated amounts
    feats["balance_retention"] = np.where(
        feats["total_received"] > 0,
        (feats["balance"] / (feats["total_received"] + EPS)).clip(upper=100.0),
        0.0,
    )
    feats["in_out_symmetry"] = (
        (feats["total_sent"] - feats["total_received"]).abs()
        / (feats["total_sent"] + feats["total_received"] + EPS)
    )

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
    # behavioural / temporal
    "active_days", "activity_span_days", "burst_ratio", "night_ratio",
    "mean_interval_hours", "recency_ratio", "rapid_out_ratio",
    "balance_retention", "in_out_symmetry",
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
