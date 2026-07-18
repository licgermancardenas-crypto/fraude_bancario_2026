"""
Unsupervised money-laundering ring detection via Louvain community detection.

Complements the supervised GNN: finds suspicious clusters without labels.

Outputs:
    reports/figures/26_communities.png
    dashboard/public/data/communities.json
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
import yaml

from src.models.graphsage import GraphSAGE


def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def main(config_path="config/config.yaml"):
    cfg      = load_config(config_path)
    raw_dir  = cfg["data"]["raw_dir"]
    proc_dir = cfg["data"]["processed_dir"]
    fig_dir  = cfg["paths"]["figures_dir"]
    data_dir = cfg["paths"]["dashboard_data_dir"]

    print("=" * 55)
    print("  Detección de comunidades (Louvain)")
    print("=" * 55)

    acc = pd.read_csv(f"{raw_dir}/accounts.csv")
    txn = pd.read_csv(f"{raw_dir}/transactions.csv")

    # Load personas if available
    persona_path = Path(f"{raw_dir}/personas.csv")
    personas = pd.read_csv(persona_path).set_index("account_id") if persona_path.exists() else None

    # GNN scores for all nodes
    data = torch.load(f"{proc_dir}/graph.pt", weights_only=False)
    ckpt  = torch.load("models/graphsage_best.pt", weights_only=False)
    model = GraphSAGE(data.num_node_features, **{
        k: ckpt["config"][k] for k in ["hidden_channels", "num_layers", "dropout"]
    })
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    with torch.no_grad():
        scores_all = F.softmax(model(data.x, data.edge_index), dim=1)[:, 1].numpy()

    node_ids  = data.node_ids
    y_all     = data.y.numpy()
    id2score  = {nid: float(scores_all[i]) for i, nid in enumerate(node_ids)}
    id2fraud  = {nid: int(y_all[i])        for i, nid in enumerate(node_ids)}

    # Build undirected weighted graph
    G = nx.Graph()
    for _, row in acc.iterrows():
        G.add_node(row.account_id, is_fraud=row.is_fraud)

    for _, row in txn.iterrows():
        if G.has_edge(row.src, row.dst):
            G[row.src][row.dst]["weight"] += row.amount
        else:
            G.add_edge(row.src, row.dst, weight=row.amount)

    print(f"  Grafo: {G.number_of_nodes()} nodos, {G.number_of_edges()} aristas")

    # Louvain
    communities = list(nx.community.louvain_communities(G, seed=42, weight="weight"))
    modularity  = nx.community.modularity(G, communities, weight="weight")
    print(f"  Louvain: {len(communities)} comunidades, modularity={modularity:.4f}")

    # Build community records
    fraud_set = set(acc.loc[acc.is_fraud == 1, "account_id"])
    records   = []

    for i, comm in enumerate(communities):
        comm_list    = list(comm)
        n            = len(comm_list)
        n_fraud      = sum(1 for a in comm_list if a in fraud_set)
        fraud_density = round(n_fraud / n, 4) if n else 0.0

        # Internal transaction amount
        internal_amt = sum(
            G[u][v]["weight"]
            for u in comm_list
            for v in comm_list
            if G.has_edge(u, v) and u < v
        )

        # Top accounts by GNN score
        comm_sorted = sorted(comm_list, key=lambda a: id2score.get(a, 0.0), reverse=True)
        top3 = []
        for aid in comm_sorted[:3]:
            entry = {
                "account_id": aid,
                "gnn_score":  round(id2score.get(aid, 0.0), 4),
                "is_fraud":   id2fraud.get(aid, 0),
            }
            if personas is not None and aid in personas.index:
                p = personas.loc[aid]
                entry["nombre_completo"] = str(p.get("nombre_completo", ""))
                entry["ocupacion"]       = str(p.get("ocupacion", ""))
                entry["condicion_afip"]  = str(p.get("condicion_afip", ""))
            top3.append(entry)

        avg_score = round(float(np.mean([id2score.get(a, 0.0) for a in comm_list])), 4)

        records.append({
            "community_id":   i + 1,
            "n_nodes":        n,
            "n_fraud":        n_fraud,
            "fraud_density":  fraud_density,
            "avg_gnn_score":  avg_score,
            "internal_amount": round(float(internal_amt), 2),
            "top_accounts":   top3,
            "node_ids":       comm_list[:20],  # cap at 20 for JSON size
        })

    # Sort by fraud density desc, then avg_gnn_score
    records.sort(key=lambda r: (r["fraud_density"], r["avg_gnn_score"]), reverse=True)

    n_suspicious = sum(1 for r in records if r["fraud_density"] > 0)
    print(f"  Comunidades con fraude: {n_suspicious}/{len(records)}")
    print(f"  Top-3 comunidades:")
    for r in records[:3]:
        print(f"    id={r['community_id']:3d}  nodos={r['n_nodes']:3d}  "
              f"fraude={r['n_fraud']}  densidad={r['fraud_density']:.2f}  "
              f"score_avg={r['avg_gnn_score']:.3f}")

    obj = {
        "algorithm":      "Louvain",
        "seed":           42,
        "n_communities":  len(records),
        "modularity":     round(modularity, 4),
        "n_suspicious":   n_suspicious,
        "communities":    records,
    }

    out = f"{data_dir}/communities.json"
    with open(out, "w") as f:
        json.dump(obj, f, separators=(",", ":"))
    size_kb = Path(out).stat().st_size / 1024
    print(f"  → {out}  ({size_kb:.1f} KB)")

    # Figure
    _plot(records, modularity, fig_dir)
    print("=" * 55)


def _plot(records, modularity, figures_dir):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor("#F8FAFC")

    # Left: community size distribution colored by fraud density
    ax = axes[0]
    ax.set_facecolor("#FFFFFF")
    sizes    = [r["n_nodes"]       for r in records]
    densities = [r["fraud_density"] for r in records]
    colors   = ["#DC2626" if d > 0.2 else "#F59E0B" if d > 0 else "#94A3B8" for d in densities]
    ax.scatter(range(len(records)), sizes, c=colors, alpha=0.7, s=60, edgecolors="white", linewidths=0.5)
    ax.set_xlabel("Comunidad (ordenada por densidad de fraude)", fontsize=11)
    ax.set_ylabel("Tamaño de la comunidad (nodos)", fontsize=11)
    ax.set_title(f"Distribución de comunidades\nLouvain — {len(records)} clusters, Q={modularity:.3f}",
                 fontsize=12, fontweight="bold", color="#0F172A")
    patches = [
        mpatches.Patch(color="#DC2626", label="Densidad > 20% fraude"),
        mpatches.Patch(color="#F59E0B", label="Contiene fraude"),
        mpatches.Patch(color="#94A3B8", label="Sin fraude detectado"),
    ]
    ax.legend(handles=patches, fontsize=9)
    ax.grid(axis="y", color="#F1F5F9", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)

    # Right: top 10 communities by fraud density
    ax2 = axes[1]
    ax2.set_facecolor("#FFFFFF")
    top10 = [r for r in records if r["n_fraud"] > 0][:10]
    labels = [f"C{r['community_id']}\n({r['n_nodes']} nodos)" for r in top10]
    fdens  = [r["fraud_density"] * 100 for r in top10]
    bar_colors = ["#DC2626" if d > 20 else "#F59E0B" for d in fdens]
    bars = ax2.barh(labels, fdens, color=bar_colors, alpha=0.85, edgecolor="white")
    ax2.set_xlabel("Densidad de fraude (%)", fontsize=11)
    ax2.set_title("Top 10 comunidades sospechosas\n(por % de nodos fraude)", fontsize=12, fontweight="bold", color="#0F172A")
    ax2.axvline(100 * 29 / 1500, color="#94A3B8", lw=1.5, linestyle="--", label="Prevalencia global (1.9%)")
    for bar, val in zip(bars, fdens):
        ax2.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                 f"{val:.0f}%", va="center", fontsize=9, color="#0F172A")
    ax2.legend(fontsize=9)
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.invert_yaxis()

    plt.tight_layout(pad=2)
    out = f"{figures_dir}/26_communities.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  → {out}")


if __name__ == "__main__":
    main()
