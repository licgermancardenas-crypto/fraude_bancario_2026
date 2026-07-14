"""
Export model outputs as static JSONs consumed by the Next.js dashboard.

Outputs (all in dashboard/public/data/):
  kpis.json              — headline metrics for the overview page
  pr_curves.json         — PR curve points for all 3 models
  score_distribution.json — histogram of GNN scores (fraud vs legit)
  rings.json             — top fraud rings with node scores and amounts
  top_accounts.json      — top-200 accounts by GNN risk score
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
import networkx as nx
import yaml

from sklearn.metrics import precision_recall_curve, average_precision_score

from src.features import build_node_features, get_feature_matrix
from src.models.graphsage import GraphSAGE
from src.evaluate import recall_at_precision


def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def _save(obj, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, separators=(",", ":"))
    kb = Path(path).stat().st_size / 1024
    print(f"  → {path}  ({kb:.1f} KB)")


# ── load artefacts ────────────────────────────────────────────────────────────

def load_all(cfg):
    raw       = cfg["data"]["raw_dir"]
    processed = cfg["data"]["processed_dir"]

    acc = pd.read_csv(f"{raw}/accounts.csv")
    txn = pd.read_csv(f"{raw}/transactions.csv")

    data = torch.load(f"{processed}/graph.pt", weights_only=False)

    ckpt  = torch.load("models/graphsage_best.pt", weights_only=False)
    model = GraphSAGE(data.num_node_features, **{
        k: ckpt["config"][k] for k in ["hidden_channels", "num_layers", "dropout"]
    })
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    with torch.no_grad():
        scores_all = F.softmax(model(data.x, data.edge_index), dim=1)[:, 1].numpy()

    scores_lr  = np.load(f"{processed}/scores_logreg.npy")
    scores_xgb = np.load(f"{processed}/scores_xgboost.npy")
    scores_gnn = np.load(f"{processed}/scores_graphsage.npy")
    y_test     = np.load(f"{processed}/y_test.npy")

    return acc, txn, data, scores_all, scores_lr, scores_xgb, scores_gnn, y_test


# ── 1. kpis.json ─────────────────────────────────────────────────────────────

def export_kpis(acc, data, scores_gnn, y_test, out_dir):
    n_accounts   = int(data.num_nodes)
    n_fraud      = int((data.y == 1).sum())
    pct_fraud    = round(100 * n_fraud / n_accounts, 2)
    pr_auc_gnn   = round(float(average_precision_score(y_test, scores_gnn)), 4)
    rec_p90, _   = recall_at_precision(y_test, scores_gnn, 0.90)

    obj = {
        "n_accounts":   n_accounts,
        "n_fraud":      n_fraud,
        "pct_fraud":    pct_fraud,
        "pr_auc_gnn":   pr_auc_gnn,
        "recall_at_p90": round(float(rec_p90), 4),
        "model":        "GraphSAGE (2 capas, 64 hidden)",
        "dataset":      "Sintético — Santander AI Lab equiv.",
        "client":       "Banco Regional del Sur (BRS)",
    }
    _save(obj, f"{out_dir}/kpis.json")


# ── 2. pr_curves.json ────────────────────────────────────────────────────────

def export_pr_curves(y_test, scores_lr, scores_xgb, scores_gnn, out_dir):
    def _curve(y, s, name):
        prec, rec, _ = precision_recall_curve(y, s)
        # downsample to ≤200 points to keep JSON small
        step = max(1, len(prec) // 200)
        return {
            "model":    name,
            "pr_auc":   round(float(average_precision_score(y, s)), 4),
            "precision": [round(float(p), 4) for p in prec[::step]],
            "recall":    [round(float(r), 4) for r in rec[::step]],
        }

    obj = [
        _curve(y_test, scores_lr,  "Logistic Regression"),
        _curve(y_test, scores_xgb, "XGBoost"),
        _curve(y_test, scores_gnn, "GraphSAGE"),
    ]
    _save(obj, f"{out_dir}/pr_curves.json")


# ── 3. score_distribution.json ────────────────────────────────────────────────

def export_score_distribution(data, scores_all, out_dir, n_bins=40):
    y_all    = data.y.numpy()
    bins     = np.linspace(0, 1, n_bins + 1)
    centers  = ((bins[:-1] + bins[1:]) / 2).tolist()

    fraud_hist, _ = np.histogram(scores_all[y_all == 1], bins=bins, density=False)
    legit_hist, _ = np.histogram(scores_all[y_all == 0], bins=bins, density=False)

    obj = {
        "bin_centers": [round(c, 3) for c in centers],
        "fraud":       fraud_hist.tolist(),
        "legit":       legit_hist.tolist(),
    }
    _save(obj, f"{out_dir}/score_distribution.json")


# ── 4. rings.json ─────────────────────────────────────────────────────────────

def export_rings(acc, txn, data, scores_all, out_dir, top_n=10):
    node_ids  = data.node_ids
    id2score  = {nid: float(scores_all[i]) for i, nid in enumerate(node_ids)}
    fraud_set = set(acc.loc[acc.is_fraud == 1, "account_id"])

    G = nx.DiGraph()
    for _, row in acc.iterrows():
        G.add_node(row.account_id, is_fraud=int(row.is_fraud),
                   balance=row.balance, risk_score=row.risk_score)
    for _, row in txn.iterrows():
        G.add_edge(row.src, row.dst, amount=row.amount,
                   timestamp=int(row.timestamp), is_fraud=int(row.is_fraud))

    Gf = G.subgraph(fraud_set).copy()
    rings = []
    try:
        for cycle in nx.simple_cycles(Gf):
            if 3 <= len(cycle) <= 10:
                rings.append(cycle)
                if len(rings) >= top_n:
                    break
    except Exception:
        pass

    out_rings = []
    for i, ring in enumerate(rings):
        nodes_data = []
        for nid in ring:
            row = acc[acc.account_id == nid].iloc[0]
            nodes_data.append({
                "id":           nid,
                "gnn_score":    round(id2score.get(nid, 0.0), 4),
                "is_fraud":     int(row.is_fraud),
                "balance":      round(float(row.balance), 2),
                "risk_score":   round(float(row.risk_score), 4),
                "account_type": row.account_type,
            })

        ring_edges = []
        total_amount = 0.0
        for j in range(len(ring)):
            src, dst = ring[j], ring[(j+1) % len(ring)]
            if G.has_edge(src, dst):
                ed = G[src][dst]
                amt = round(float(ed.get("amount", 0)), 2)
                ring_edges.append({"src": src, "dst": dst, "amount": amt})
                total_amount += amt

        out_rings.append({
            "ring_id":      i + 1,
            "n_nodes":      len(ring),
            "total_amount": round(total_amount, 2),
            "avg_score":    round(np.mean([n["gnn_score"] for n in nodes_data]), 4),
            "nodes":        nodes_data,
            "edges":        ring_edges,
        })

    _save(out_rings, f"{out_dir}/rings.json")


# ── 5. top_accounts.json ──────────────────────────────────────────────────────

def export_top_accounts(acc, txn, data, scores_all, out_dir, top_n=200):
    node_ids = data.node_ids
    feats    = build_node_features(acc, txn)

    fraud_set = set(acc.loc[acc.is_fraud == 1, "account_id"])
    G = nx.DiGraph()
    for _, row in txn.iterrows():
        G.add_edge(row.src, row.dst, amount=row.amount)

    records = []
    for i, nid in enumerate(node_ids):
        row = acc[acc.account_id == nid].iloc[0]
        f   = feats[feats.account_id == nid]
        records.append({
            "account_id":       nid,
            "gnn_score":        round(float(scores_all[i]), 4),
            "is_fraud":         int(row.is_fraud),
            "balance":          round(float(row.balance), 2),
            "risk_score":       round(float(row.risk_score), 4),
            "account_type":     row.account_type,
            "degree_in":        int(G.in_degree(nid)),
            "degree_out":       int(G.out_degree(nid)),
            "total_sent":       round(float(f["total_sent"].values[0]) if len(f) else 0, 2),
            "total_received":   round(float(f["total_received"].values[0]) if len(f) else 0, 2),
            "in_ring":          nid in fraud_set,
        })

    records.sort(key=lambda r: r["gnn_score"], reverse=True)
    _save(records[:top_n], f"{out_dir}/top_accounts.json")


# ── master ────────────────────────────────────────────────────────────────────

def export_all(config_path="config/config.yaml"):
    cfg     = load_config(config_path)
    out_dir = cfg["paths"]["dashboard_data_dir"]
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    print("=" * 55)
    print("  Exportando JSONs para dashboard")
    print("=" * 55)

    acc, txn, data, scores_all, scores_lr, scores_xgb, scores_gnn, y_test = load_all(cfg)

    export_kpis(acc, data, scores_gnn, y_test, out_dir)
    export_pr_curves(y_test, scores_lr, scores_xgb, scores_gnn, out_dir)
    export_score_distribution(data, scores_all, out_dir)
    export_rings(acc, txn, data, scores_all, out_dir)
    export_top_accounts(acc, txn, data, scores_all, out_dir)

    # check total size
    total_kb = sum(p.stat().st_size for p in Path(out_dir).glob("*.json")) / 1024
    print(f"\n  Total JSONs: {total_kb:.1f} KB  "
          f"({'OK' if total_kb < 2048 else 'ATENCIÓN: supera 2MB'})")
    print("=" * 55)


if __name__ == "__main__":
    export_all()
