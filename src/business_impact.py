"""
Translates model performance into operational $ metrics.

For each review threshold k (top-k accounts by GNN score):
  - precision_at_k    = fraud accounts in top-k / k
  - recall_at_k       = fraud accounts in top-k / total fraud
  - amount_recall_at_k = fraud $ linked to top-k / total fraud $

Compares GNN vs. random baseline.

Outputs:
    reports/figures/25_business_impact.png
    dashboard/public/data/business_impact.json
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
import yaml

from src.models.graphsage import GraphSAGE


def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def _fraud_amount_per_account(txn_df: pd.DataFrame) -> dict:
    """Fraud transaction amount attributed to the SOURCE account.
    No double-counting: each fraud transaction is counted once, on the sender.
    """
    fraud_txn = txn_df[txn_df.is_fraud == 1]
    return fraud_txn.groupby("src")["amount"].sum().to_dict()


def compute_cost_curves(
    node_ids: list,
    scores_all: np.ndarray,
    y_all: np.ndarray,
    fraud_amt_map: dict,
    total_fraud_amount: float,
    ks: list[int],
) -> list[dict]:
    """Return cost-curve rows for each k in ks."""
    order    = np.argsort(scores_all)[::-1]
    n_total  = len(node_ids)
    n_fraud  = int(y_all.sum())
    rows     = []

    cum_fraud  = 0
    cum_amount = 0.0

    # iterate over all accounts in score order, record at checkpoints
    k_set = set(ks)
    for rank, idx in enumerate(order, 1):
        nid = node_ids[idx]
        if y_all[idx] == 1:
            cum_fraud  += 1
            cum_amount += fraud_amt_map.get(nid, 0.0)
        if rank in k_set:
            rows.append({
                "k":              rank,
                "accounts_pct":   round(rank / n_total * 100, 2),
                "precision":      round(cum_fraud / rank, 4),
                "recall":         round(cum_fraud / n_fraud, 4),
                "amount_recall":  round(cum_amount / total_fraud_amount, 4) if total_fraud_amount else 0,
                "fraud_found":    cum_fraud,
                "amount_found":   round(cum_amount, 2),
            })
    return rows


def find_threshold(curve: list[dict], target_recall: float) -> dict | None:
    """Return the smallest k that reaches target recall."""
    for row in curve:
        if row["recall"] >= target_recall:
            return row
    return curve[-1]


def plot_curves(curve: list[dict], baseline: list[dict], figures_dir: str):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor("#F8FAFC")

    ks    = [r["k"] for r in curve]
    gnn   = [r["amount_recall"] * 100 for r in curve]
    rand  = [r["amount_recall"] * 100 for r in baseline]
    prec  = [r["precision"] * 100      for r in curve]

    # left: cost curve
    ax = axes[0]
    ax.set_facecolor("#FFFFFF")
    ax.plot(ks, gnn,  color="#2563EB", lw=2.5, label="GraphSAGE GNN")
    ax.plot(ks, rand, color="#94A3B8", lw=1.5, linestyle="--", label="Baseline aleatorio")
    ax.axhline(90, color="#E2E8F0", lw=1, linestyle=":")
    ax.set_xlabel("Cuentas revisadas (top-k por score GNN)", fontsize=11)
    ax.set_ylabel("% del monto lavado capturado", fontsize=11)
    ax.set_title("Curva de costo operativo", fontsize=13, fontweight="bold", color="#0F172A")
    ax.legend(fontsize=10)
    ax.set_xlim(0, max(ks))
    ax.set_ylim(0, 105)
    ax.grid(axis="y", color="#F1F5F9", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)

    # right: precision@k
    ax2 = axes[1]
    ax2.set_facecolor("#FFFFFF")
    ax2.plot(ks, prec, color="#DC2626", lw=2.5, label="Precisión GNN")
    ax2.axhline(90, color="#E2E8F0", lw=1, linestyle=":")
    ax2.set_xlabel("Cuentas revisadas (top-k por score GNN)", fontsize=11)
    ax2.set_ylabel("Precisión (% revisiones que son fraude)", fontsize=11)
    ax2.set_title("Precisión del modelo por umbral", fontsize=13, fontweight="bold", color="#0F172A")
    ax2.legend(fontsize=10)
    ax2.set_xlim(0, max(ks))
    ax2.set_ylim(0, 105)
    ax2.grid(axis="y", color="#F1F5F9", linewidth=0.8)
    ax2.spines[["top", "right"]].set_visible(False)

    plt.tight_layout(pad=2)
    out = f"{figures_dir}/25_business_impact.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  → {out}")


def main(config_path="config/config.yaml"):
    cfg       = load_config(config_path)
    raw_dir   = cfg["data"]["raw_dir"]
    proc_dir  = cfg["data"]["processed_dir"]
    fig_dir   = cfg["paths"]["figures_dir"]
    data_dir  = cfg["paths"]["dashboard_data_dir"]

    print("=" * 55)
    print("  Calculando impacto de negocio")
    print("=" * 55)

    acc = pd.read_csv(f"{raw_dir}/accounts.csv")
    txn = pd.read_csv(f"{raw_dir}/transactions.csv")

    data = torch.load(f"{proc_dir}/graph.pt", weights_only=False)
    ckpt  = torch.load("models/graphsage_best.pt", weights_only=False)
    model = GraphSAGE(data.num_node_features, **{
        k: ckpt["config"][k] for k in ["hidden_channels", "num_layers", "dropout"]
    })
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    with torch.no_grad():
        scores_all = F.softmax(model(data.x, data.edge_index), dim=1)[:, 1].numpy()

    node_ids   = data.node_ids
    y_all      = data.y.numpy()
    n_fraud    = int(y_all.sum())
    n_total    = len(node_ids)

    fraud_amt  = _fraud_amount_per_account(txn)
    total_fa   = txn[txn.is_fraud == 1]["amount"].sum()

    # k checkpoints: fine at top, coarser further down
    ks = list(range(1, 51)) + list(range(55, 101, 5)) + list(range(110, min(n_total+1, 201), 10))

    print(f"  Portfolio: {n_total} cuentas, {n_fraud} fraude ({n_fraud/n_total*100:.1f}%)")
    print(f"  Monto total de fraude: ${total_fa:,.0f}")

    gnn_curve  = compute_cost_curves(node_ids, scores_all, y_all, fraud_amt, total_fa, ks)

    # random baseline (theoretical)
    rand_curve = [
        {
            "k":             r["k"],
            "accounts_pct":  r["accounts_pct"],
            "precision":     round(n_fraud / n_total, 4),
            "recall":        round(r["k"] * n_fraud / n_total / n_fraud, 4),
            "amount_recall": round(r["k"] * n_fraud / n_total / n_fraud, 4),
        }
        for r in gnn_curve
    ]

    # key thresholds
    t10  = next((r for r in gnn_curve if r["k"] >= 10),  None)
    t25  = next((r for r in gnn_curve if r["k"] >= 25),  None)
    t50  = next((r for r in gnn_curve if r["k"] >= 50),  None)
    t100 = next((r for r in gnn_curve if r["k"] >= 100), None)
    t90r = find_threshold(gnn_curve, 0.90)  # first k that reaches 90% recall

    for t, label in [(t10, "Top-10"), (t25, "Top-25"), (t50, "Top-50"), (t100, "Top-100")]:
        if t:
            print(f"  {label:8s}: precisión={t['precision']*100:.1f}%  "
                  f"recall={t['recall']*100:.1f}%  "
                  f"monto recuperado={t['amount_recall']*100:.1f}%")

    if t90r:
        print(f"  Para 90% recall: revisar top-{t90r['k']} ({t90r['accounts_pct']:.1f}% del portfolio)")

    obj = {
        "portfolio_size":       n_total,
        "n_fraud":              n_fraud,
        "prevalence_pct":       round(n_fraud / n_total * 100, 2),
        "total_fraud_amount":   round(float(total_fa), 2),
        "gnn_curve":            gnn_curve,
        "random_curve":         rand_curve,
        "key_thresholds": {
            "top_10":           t10,
            "top_25":           t25,
            "top_50":           t50,
            "top_100":          t100,
            "recall_90_pct":    t90r,
        },
    }

    out = f"{data_dir}/business_impact.json"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(obj, f, separators=(",", ":"))
    print(f"  → {out}")

    plot_curves(gnn_curve, rand_curve, fig_dir)
    print("=" * 55)


if __name__ == "__main__":
    main()
