"""
Node2Vec — transductive graph embedding baseline.

Pipeline:
  1. Build networkx graph from graph.pt edge_index
  2. Biased random walks (p=1, q=0.5 → DFS-like, explores fraud rings)
  3. Word2Vec on walk sequences → 64-dim node embeddings
  4. LogReg + XGBoost classifiers trained on train embeddings
  5. Evaluate best on same test split (same test_mask as GNN models)

Node2Vec is TRANSDUCTIVE (no new nodes at inference time) and uses
NO node features — pure topology signal. This quantifies exactly how
much information lives in the graph structure without any account metadata.
"""

import json
import random
from pathlib import Path

import numpy as np
import torch
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from gensim.models import Word2Vec
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score, precision_recall_curve
from xgboost import XGBClassifier
import yaml

from src.evaluate import evaluate_model


NAVY = "#0A1F44"
GOLD = "#C9A227"

SEED = 42
random.seed(SEED)
np.random.seed(SEED)


# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────

def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


# ─────────────────────────────────────────────────────────────
# Graph + random walks
# ─────────────────────────────────────────────────────────────

def build_nx_graph(edge_index: torch.Tensor, n_nodes: int) -> nx.Graph:
    """Build undirected networkx graph from PyG edge_index."""
    G = nx.Graph()
    G.add_nodes_from(range(n_nodes))
    edges = edge_index.numpy().T.tolist()
    G.add_edges_from(edges)
    return G


def _transition_probs(G: nx.Graph, prev: int, cur: int, p: float, q: float) -> np.ndarray:
    neighbors = list(G.neighbors(cur))
    probs = np.empty(len(neighbors))
    for i, nbr in enumerate(neighbors):
        if nbr == prev:
            probs[i] = 1.0 / p       # return to previous
        elif G.has_edge(prev, nbr):
            probs[i] = 1.0            # BFS step
        else:
            probs[i] = 1.0 / q       # DFS step (explore new territory)
    probs /= probs.sum()
    return neighbors, probs


def biased_random_walk(G: nx.Graph, start: int, walk_length: int,
                       p: float, q: float) -> list[int]:
    walk = [start]
    while len(walk) < walk_length:
        cur = walk[-1]
        nbrs = list(G.neighbors(cur))
        if not nbrs:
            break
        if len(walk) == 1:
            walk.append(random.choice(nbrs))
        else:
            prev = walk[-2]
            nbrs, probs = _transition_probs(G, prev, cur, p, q)
            walk.append(int(np.random.choice(nbrs, p=probs)))
    return walk


def generate_walks(G: nx.Graph, walks_per_node: int, walk_length: int,
                   p: float, q: float) -> list[list[str]]:
    nodes = list(G.nodes())
    walks = []
    for _ in range(walks_per_node):
        random.shuffle(nodes)
        for node in nodes:
            walk = biased_random_walk(G, node, walk_length, p, q)
            walks.append([str(n) for n in walk])
    print(f"  {len(walks)} walks generados "
          f"({walks_per_node} × {len(nodes)} nodos, largo={walk_length})")
    return walks


# ─────────────────────────────────────────────────────────────
# Embeddings
# ─────────────────────────────────────────────────────────────

def train_word2vec(walks: list[list[str]], embedding_dim: int,
                   window: int, epochs: int, workers: int = 1) -> Word2Vec:
    model = Word2Vec(
        sentences=walks,
        vector_size=embedding_dim,
        window=window,
        min_count=0,
        sg=1,                # skip-gram
        workers=workers,
        epochs=epochs,
        seed=SEED,
    )
    return model


def get_embeddings(wv_model: Word2Vec, n_nodes: int,
                   embedding_dim: int) -> np.ndarray:
    emb = np.zeros((n_nodes, embedding_dim))
    for i in range(n_nodes):
        key = str(i)
        if key in wv_model.wv:
            emb[i] = wv_model.wv[key]
    return emb


# ─────────────────────────────────────────────────────────────
# Classifiers
# ─────────────────────────────────────────────────────────────

def train_classifiers(emb: np.ndarray, data, train_mask, val_mask):
    X_train = emb[train_mask.numpy()]
    y_train = data.y.numpy()[train_mask.numpy()]
    X_val   = emb[val_mask.numpy()]
    y_val   = data.y.numpy()[val_mask.numpy()]

    scaler  = StandardScaler().fit(X_train)
    X_train_s = scaler.transform(X_train)
    X_val_s   = scaler.transform(X_val)

    n_pos = (y_train == 1).sum()
    n_neg = (y_train == 0).sum()
    scale_pos = n_neg / max(n_pos, 1)

    # LogReg
    lr = LogisticRegression(class_weight="balanced", max_iter=2000,
                            random_state=SEED)
    lr.fit(X_train_s, y_train)
    val_prauc_lr = average_precision_score(
        y_val, lr.predict_proba(X_val_s)[:, 1])

    # XGBoost
    xgb = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05,
                        scale_pos_weight=scale_pos, random_state=SEED,
                        eval_metric="aucpr", verbosity=0)
    xgb.fit(X_train_s, y_train)
    val_prauc_xgb = average_precision_score(
        y_val, xgb.predict_proba(X_val_s)[:, 1])

    print(f"  Val PR-AUC → LogReg={val_prauc_lr:.4f}  XGBoost={val_prauc_xgb:.4f}")
    return scaler, lr, xgb, val_prauc_lr, val_prauc_xgb


# ─────────────────────────────────────────────────────────────
# Figures
# ─────────────────────────────────────────────────────────────

def fig_embedding_umap(emb: np.ndarray, y: np.ndarray, output_path: str):
    """Fig 20 — 2D UMAP projection of Node2Vec embeddings coloured by fraud label."""
    try:
        from umap import UMAP
        reducer = UMAP(n_components=2, random_state=SEED, n_neighbors=15)
        proj = reducer.fit_transform(emb)
        method = "UMAP"
    except ImportError:
        from sklearn.decomposition import PCA
        proj = PCA(n_components=2, random_state=SEED).fit_transform(emb)
        method = "PCA"

    fig, ax = plt.subplots(figsize=(8, 6), facecolor=NAVY)
    ax.set_facecolor(NAVY)

    legit = y == 0
    ax.scatter(proj[legit, 0], proj[legit, 1], c="#BDC3C7",
               alpha=0.4, s=12, label=f"Legítimo (n={legit.sum()})", linewidths=0)
    ax.scatter(proj[~legit, 0], proj[~legit, 1], c="#C0392B",
               alpha=0.9, s=60, label=f"Fraude (n={(~legit).sum()})",
               edgecolors="white", linewidths=0.5, zorder=5)

    ax.set_title(f"Node2Vec embeddings — proyección {method}\n"
                 "Separabilidad de cuentas fraude vs. legítimas por estructura de red",
                 color="white", fontsize=12, fontweight="bold")
    ax.legend(facecolor=NAVY, edgecolor=GOLD, labelcolor="white", fontsize=10)
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color(GOLD)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=NAVY)
    plt.close()
    print(f"  → {output_path}")


def fig_pr_curves_final(figs_dir: str, proc_dir: str, data):
    """Fig 21 — final PR curve: all 5 models."""
    y_true = data.y.numpy()[data.test_mask.numpy()]

    model_scores = {
        "Logistic Regression": f"{proc_dir}/scores_logreg.npy",
        "XGBoost":             f"{proc_dir}/scores_xgboost.npy",
        "Node2Vec + XGBoost":  f"{proc_dir}/scores_node2vec.npy",
        "GAT":                 f"{proc_dir}/scores_gat.npy",
        "GraphSAGE":           f"{proc_dir}/scores_graphsage.npy",
    }
    colors = {
        "Logistic Regression": "#BDC3C7",
        "XGBoost":             "#C9A227",
        "Node2Vec + XGBoost":  "#27AE60",
        "GAT":                 "#2E86AB",
        "GraphSAGE":           "#C0392B",
    }

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.set_facecolor("#FAFAFA")
    fig.patch.set_facecolor("white")
    ax.axhline(y_true.mean(), color="#95A5A6", linestyle=":", linewidth=1,
               label=f"Azar (prevalencia={y_true.mean():.3f})")

    for name, path in model_scores.items():
        if not Path(path).exists():
            continue
        scores = np.load(path)
        prec, rec, _ = precision_recall_curve(y_true, scores)
        prauc = average_precision_score(y_true, scores)
        lw    = 2.5 if name == "GraphSAGE" else 1.8
        ax.plot(rec, prec, color=colors[name], linewidth=lw,
                label=f"{name}  PR-AUC={prauc:.3f}")

    ax.set_xlabel("Recall", fontsize=12)
    ax.set_ylabel("Precisión", fontsize=12)
    ax.set_title("Comparativa final — 5 modelos\n"
                 "Banco Regional del Sur · Detección de Lavado",
                 fontsize=13, color=NAVY, fontweight="bold")
    ax.legend(fontsize=9.5, loc="upper right",
              facecolor="white", edgecolor="#D0D0D0")
    ax.grid(True, color="#E0E0E0", linewidth=0.5)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.05)

    path = f"{figs_dir}/21_pr_curves_final_all.png"
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {path}")


# ─────────────────────────────────────────────────────────────
# Dashboard update
# ─────────────────────────────────────────────────────────────

def update_dashboard_pr_curves(dd: str, proc: str, data):
    y_true = data.y.numpy()[data.test_mask.numpy()]
    model_files = {
        "Logistic Regression": f"{proc}/scores_logreg.npy",
        "XGBoost":             f"{proc}/scores_xgboost.npy",
        "Node2Vec + XGBoost":  f"{proc}/scores_node2vec.npy",
        "GAT":                 f"{proc}/scores_gat.npy",
        "GraphSAGE":           f"{proc}/scores_graphsage.npy",
    }
    curves = []
    for name, path in model_files.items():
        if not Path(path).exists():
            continue
        scores = np.load(path)
        prec, rec, _ = precision_recall_curve(y_true, scores)
        prauc = average_precision_score(y_true, scores)
        step = max(1, len(prec) // 200)
        curves.append({
            "model":  name,
            "pr_auc": round(float(prauc), 4),
            "points": [{"precision": round(float(p), 4), "recall": round(float(r), 4)}
                       for p, r in zip(prec[::step], rec[::step])],
        })
    out = f"{dd}/pr_curves.json"
    with open(out, "w") as f:
        json.dump(curves, f)
    print(f"  → {out}  ({len(curves)} curvas)")


def update_results_json(new_result: dict, reports: str):
    path = f"{reports}/results_all.json"
    with open(path) as f:
        results = json.load(f)
    names = [r["model"] for r in results]
    if new_result["model"] in names:
        results[names.index(new_result["model"])] = new_result
    else:
        results.append(new_result)
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  → {path}  ({len(results)} modelos)")


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main(config_path="config/config.yaml"):
    cfg  = load_config(config_path)
    proc = cfg["data"]["processed_dir"]
    figs = cfg["paths"]["figures_dir"]
    dd   = cfg["paths"]["dashboard_data_dir"]
    rep  = cfg["paths"]["reports_dir"]
    n2v  = cfg["model"].get("node2vec", {
        "embedding_dim": 64, "walk_length": 30, "context_size": 10,
        "walks_per_node": 15, "p": 1.0, "q": 0.5,
        "w2v_epochs": 10, "w2v_workers": 1,
    })

    print("=" * 55)
    print("  Node2Vec — embedding transductivo de grafos")
    print("=" * 55)

    print("\n── 1. Cargando grafo ───────────────────────────────────")
    data = torch.load(f"{proc}/graph.pt", weights_only=False)
    n    = data.x.shape[0]
    print(f"  {n} nodos, {data.edge_index.shape[1]} aristas")

    print("\n── 2. Construyendo grafo NetworkX ──────────────────────")
    G = build_nx_graph(data.edge_index, n)
    print(f"  Nodos: {G.number_of_nodes()}  Aristas: {G.number_of_edges()}")

    print("\n── 3. Generando random walks ───────────────────────────")
    print(f"  p={n2v['p']}  q={n2v['q']}  largo={n2v['walk_length']}  "
          f"walks/nodo={n2v['walks_per_node']}")
    walks = generate_walks(
        G,
        walks_per_node=n2v["walks_per_node"],
        walk_length=n2v["walk_length"],
        p=n2v["p"],
        q=n2v["q"],
    )

    print("\n── 4. Entrenando Word2Vec ──────────────────────────────")
    print(f"  embedding_dim={n2v['embedding_dim']}  "
          f"window={n2v['context_size']}  epochs={n2v['w2v_epochs']}")
    wv_model = train_word2vec(
        walks,
        embedding_dim=n2v["embedding_dim"],
        window=n2v["context_size"],
        epochs=n2v["w2v_epochs"],
    )
    emb = get_embeddings(wv_model, n, n2v["embedding_dim"])
    print(f"  Embeddings shape: {emb.shape}")

    print("\n── 5. Clasificadores sobre embeddings ──────────────────")
    scaler, lr_clf, xgb_clf, val_lr, val_xgb = train_classifiers(
        emb, data, data.train_mask, data.val_mask)

    # use whichever is better on val
    best_name = "XGBoost" if val_xgb >= val_lr else "LogReg"
    print(f"  Mejor clasificador en val: {best_name}")

    X_test    = scaler.transform(emb[data.test_mask.numpy()])
    y_true    = data.y.numpy()[data.test_mask.numpy()]
    scores_xgb = xgb_clf.predict_proba(X_test)[:, 1]
    scores_lr  = lr_clf.predict_proba(X_test)[:, 1]
    best_scores = scores_xgb if val_xgb >= val_lr else scores_lr

    model_label = f"Node2Vec + {best_name}"
    results = evaluate_model(model_label, y_true, best_scores)
    results["model"] = "Node2Vec + XGBoost" if best_name == "XGBoost" else "Node2Vec + LogReg"

    np.save(f"{proc}/scores_node2vec.npy", best_scores)

    print("\n── 6. Figuras ──────────────────────────────────────────")
    fig_embedding_umap(emb, data.y.numpy(), f"{figs}/20_node2vec_embeddings.png")
    fig_pr_curves_final(figs, proc, data)

    print("\n── 7. Actualizando resultados y dashboard ──────────────")
    update_results_json(results, rep)
    update_dashboard_pr_curves(dd, proc, data)

    print("\n" + "=" * 55)
    print(f"  Node2Vec + {best_name}")
    print(f"  PR-AUC={results['pr_auc']:.4f}  "
          f"Recall@P90={results['rec_at_p90']:.2f}  "
          f"F1={results['f1_optimal']:.4f}")
    print("=" * 55)


if __name__ == "__main__":
    main()
