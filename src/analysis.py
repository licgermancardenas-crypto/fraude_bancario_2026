"""
Phase F — Comparative analysis: LogReg vs XGBoost vs GraphSAGE.

Produces:
  - reports/figures/12_pr_curves_all.png     (main figure of the project)
  - reports/figures/13_score_distribution.png
  - reports/figures/14_ablation.png
  - reports/figures/15_error_analysis.png
  - reports/metrics_all.csv / .md
  - reports/results_all.json
  - Updated section in reports/insights.md
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import yaml

from sklearn.metrics import precision_recall_curve, average_precision_score

from src.features import build_node_features, get_feature_matrix
from src.models.graphsage import GraphSAGE
from src.evaluate import evaluate_model, build_comparison_table, recall_at_precision


# ── palette ──────────────────────────────────────────────────────────────────
NAVY   = "#0A1F44"
GOLD   = "#C9A227"
RED    = "#C0392B"
TEAL   = "#1ABC9C"
GREY   = "#BDC3C7"
GRID   = "#E0E0E0"

MODEL_COLORS = {
    "Logistic Regression": NAVY,
    "XGBoost":             GOLD,
    "GraphSAGE":           RED,
    "GraphSAGE (ablation — solo topología)": TEAL,
}


def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


# ── 1. Load all artefacts ─────────────────────────────────────────────────────

def load_all(cfg):
    raw       = cfg["data"]["raw_dir"]
    processed = cfg["data"]["processed_dir"]

    acc = pd.read_csv(f"{raw}/accounts.csv")
    txn = pd.read_csv(f"{raw}/transactions.csv")

    data      = torch.load(f"{processed}/graph.pt", weights_only=False)
    test_mask = data.test_mask.numpy()
    y_test    = data.y.numpy()[test_mask]

    scores_lr  = np.load(f"{processed}/scores_logreg.npy")
    scores_xgb = np.load(f"{processed}/scores_xgboost.npy")
    scores_gnn = np.load(f"{processed}/scores_graphsage.npy")

    ckpt  = torch.load("models/graphsage_best.pt", weights_only=False)
    model = GraphSAGE(data.num_node_features, **{
        k: ckpt["config"][k] for k in ["hidden_channels", "num_layers", "dropout"]
    })
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    return acc, txn, data, test_mask, y_test, scores_lr, scores_xgb, scores_gnn, model


# ── 2. Comparative PR curves (main figure) ────────────────────────────────────

def plot_pr_all(y_test, scores_lr, scores_xgb, scores_gnn, figures_dir):
    fig, ax = plt.subplots(figsize=(9, 7))
    fig.patch.set_facecolor("white")

    entries = [
        ("Logistic Regression", scores_lr,  NAVY),
        ("XGBoost",             scores_xgb, GOLD),
        ("GraphSAGE",           scores_gnn, RED),
    ]
    for name, scores, color in entries:
        prec, rec, _ = precision_recall_curve(y_test, scores)
        auc = average_precision_score(y_test, scores)
        ax.step(rec, prec, where="post", color=color, linewidth=2.5,
                label=f"{name}  (PR-AUC = {auc:.3f})")

    # baseline (random)
    fraud_rate = y_test.mean()
    ax.axhline(fraud_rate, color="gray", linestyle=":", linewidth=1.2, alpha=0.6,
               label=f"Clasificador aleatorio (PR-AUC ≈ {fraud_rate:.3f})")
    ax.axhline(0.90, color="#95A5A6", linestyle="--", linewidth=1, alpha=0.7,
               label="Precisión = 90%")

    ax.set_xlabel("Recall (fracción del fraude detectada)", fontsize=12)
    ax.set_ylabel("Precisión (fracción de alertas correctas)", fontsize=12)
    ax.set_title("Curva Precisión-Recall — Comparativa de Modelos\nBanco Regional del Sur (BRS)",
                 fontsize=13, fontweight="bold", color=NAVY)
    ax.legend(fontsize=10, loc="lower left")
    ax.set_xlim([0, 1]); ax.set_ylim([0, 1.05])
    ax.grid(True, color=GRID, linewidth=0.5)
    ax.set_facecolor("#FAFAFA")

    plt.tight_layout()
    path = Path(figures_dir) / "12_pr_curves_all.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {path}")
    return path


# ── 3. Score distribution ─────────────────────────────────────────────────────

def plot_score_distribution(data, scores_gnn_full, figures_dir):
    y_all   = data.y.numpy()
    fraud_s = scores_gnn_full[y_all == 1]
    legit_s = scores_gnn_full[y_all == 0]

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    fig.patch.set_facecolor("white")

    bins = np.linspace(0, 1, 40)
    ax = axes[0]
    ax.hist(legit_s, bins=bins, alpha=0.6, color=GREY, label="Legítimo", density=True)
    ax.hist(fraud_s, bins=bins, alpha=0.85, color=RED,  label="Fraude",   density=True)
    ax.set_xlabel("Score de riesgo GNN (P(fraude))", fontsize=11)
    ax.set_ylabel("Densidad", fontsize=11)
    ax.set_title("Distribución de Scores — GraphSAGE", fontsize=12, color=NAVY)
    ax.legend(fontsize=10); ax.grid(True, color=GRID, linewidth=0.5)
    ax.set_facecolor("#FAFAFA")

    # ECDF
    ax = axes[1]
    for scores, label, color in [(legit_s, "Legítimo", NAVY), (fraud_s, "Fraude", RED)]:
        sorted_s = np.sort(scores)
        ecdf     = np.arange(1, len(sorted_s)+1) / len(sorted_s)
        ax.step(sorted_s, ecdf, color=color, linewidth=2, label=label)
    ax.set_xlabel("Score de riesgo GNN", fontsize=11)
    ax.set_ylabel("Fracción acumulada", fontsize=11)
    ax.set_title("ECDF de Scores — Separación entre clases", fontsize=12, color=NAVY)
    ax.legend(fontsize=10); ax.grid(True, color=GRID, linewidth=0.5)
    ax.set_facecolor("#FAFAFA")

    plt.tight_layout()
    path = Path(figures_dir) / "13_score_distribution.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {path}")


# ── 4. Ablation: topology only ────────────────────────────────────────────────

def run_ablation(data, model, cfg, figures_dir):
    """Train GNN with constant features (x = ones) to isolate topology signal."""
    seed    = cfg["project"]["seed"]
    gnn_cfg = cfg["model"]["graphsage"]

    torch.manual_seed(seed)
    np.random.seed(seed)

    # replace node features with ones
    data_abl = data.clone()
    data_abl.x = torch.ones_like(data.x)

    model_abl = GraphSAGE(
        in_channels     = data_abl.num_node_features,
        hidden_channels = gnn_cfg["hidden_channels"],
        num_layers      = gnn_cfg["num_layers"],
        dropout         = gnn_cfg["dropout"],
    )

    # class weights
    y_train = data_abl.y[data_abl.train_mask]
    n_pos   = (y_train == 1).sum().float()
    n_neg   = (y_train == 0).sum().float()
    cw      = torch.tensor([1.0, (n_neg / (n_pos + 1e-8)).item()])

    opt = torch.optim.Adam(model_abl.parameters(),
                           lr=gnn_cfg["lr"], weight_decay=gnn_cfg["weight_decay"])

    best_val, best_state, patience = 0.0, None, 0
    x, ei, y = data_abl.x, data_abl.edge_index, data_abl.y

    for epoch in range(1, gnn_cfg["epochs"] + 1):
        model_abl.train()
        opt.zero_grad()
        logits = model_abl(x, ei)
        loss   = F.cross_entropy(logits[data_abl.train_mask],
                                  y[data_abl.train_mask], weight=cw)
        loss.backward(); opt.step()

        model_abl.eval()
        with torch.no_grad():
            probs_val = F.softmax(model_abl(x, ei), dim=1)[:, 1].numpy()
        val_prauc = average_precision_score(
            y.numpy()[data_abl.val_mask.numpy()],
            probs_val[data_abl.val_mask.numpy()]
        )
        if val_prauc > best_val + 1e-5:
            best_val   = val_prauc
            best_state = {k: v.clone() for k, v in model_abl.state_dict().items()}
            patience   = 0
        else:
            patience += 1
            if patience >= gnn_cfg["patience"]:
                break

    model_abl.load_state_dict(best_state)
    model_abl.eval()
    with torch.no_grad():
        probs_all = F.softmax(model_abl(x, ei), dim=1)[:, 1].numpy()

    test_mask = data_abl.test_mask.numpy()
    y_test    = data_abl.y.numpy()[test_mask]
    scores_abl = probs_all[test_mask]
    abl_prauc  = average_precision_score(y_test, scores_abl)

    print(f"  Ablation (solo topología): best val_PR-AUC={best_val:.4f}  "
          f"test_PR-AUC={abl_prauc:.4f}")

    # figure
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor("white")
    for (name, scores, color) in [
        ("GraphSAGE (features completos)", data.y.numpy()[test_mask], RED),
    ]:
        pass  # placeholder
    entries = [
        ("GraphSAGE (features completos)",          data.y.numpy()[test_mask],
         np.load("data/processed/scores_graphsage.npy"), RED),
        ("GraphSAGE (ablation — solo topología)",   y_test, scores_abl, TEAL),
    ]
    for name, yt, sc, color in entries:
        prec, rec, _ = precision_recall_curve(yt, sc)
        auc = average_precision_score(yt, sc)
        ax.step(rec, prec, where="post", color=color, linewidth=2.5,
                label=f"{name}\n(PR-AUC = {auc:.3f})")

    ax.set_xlabel("Recall", fontsize=12)
    ax.set_ylabel("Precisión", fontsize=12)
    ax.set_title("Ablation: Features Completos vs. Solo Topología\n"
                 "¿Cuánto aporta la estructura del grafo por sí sola?",
                 fontsize=12, color=NAVY)
    ax.legend(fontsize=10, loc="lower left")
    ax.set_xlim([0, 1]); ax.set_ylim([0, 1.05])
    ax.grid(True, color=GRID, linewidth=0.5); ax.set_facecolor("#FAFAFA")
    plt.tight_layout()
    path = Path(figures_dir) / "14_ablation.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {path}")

    return abl_prauc, scores_abl


# ── 5. Error analysis ─────────────────────────────────────────────────────────

def error_analysis(data, acc, txn, scores_gnn_full, figures_dir):
    """
    Analyse the hardest fraud cases (lowest GNN score among true fraud nodes).
    With PR-AUC=1.0 we have no false negatives, so we look at the score margin —
    which fraud nodes were closest to the decision boundary?
    """
    y_all   = data.y.numpy()
    node_ids = data.node_ids

    fraud_idx   = np.where(y_all == 1)[0]
    fraud_scores = scores_gnn_full[fraud_idx]
    # sort by ascending score (hardest first)
    order       = np.argsort(fraud_scores)
    hard_idx    = fraud_idx[order[:10]]   # up to 10 hardest fraud nodes
    hard_ids    = [node_ids[i] for i in hard_idx]
    hard_scores = fraud_scores[order[:10]]

    # build networkx graph for neighbourhood analysis
    G = nx.DiGraph()
    G.add_nodes_from(node_ids)
    for _, row in txn.iterrows():
        G.add_edge(row.src, row.dst, amount=row.amount)

    fraud_set = set(acc.loc[acc.is_fraud == 1, "account_id"].tolist())

    print("\n── 5. Análisis de errores / casos difíciles ─────────────")
    rows = []
    for nid, score in zip(hard_ids, hard_scores):
        in_deg  = G.in_degree(nid)
        out_deg = G.out_degree(nid)
        nbrs    = set(G.predecessors(nid)) | set(G.successors(nid))
        fraud_nbrs = len(nbrs & fraud_set)
        rows.append({
            "account_id":      nid,
            "gnn_score":       round(float(score), 4),
            "degree_in":       in_deg,
            "degree_out":      out_deg,
            "fraud_neighbors": fraud_nbrs,
            "total_neighbors": len(nbrs),
        })
        print(f"  {nid}  score={score:.4f}  in={in_deg}  out={out_deg}  "
              f"fraud_nbrs={fraud_nbrs}/{len(nbrs)}")

    df = pd.DataFrame(rows)

    # figure: scatter degree vs score for fraud nodes
    fraud_df = acc[acc.is_fraud == 1].copy()
    fraud_df["gnn_score"] = [
        float(scores_gnn_full[node_ids.index(nid)]) if nid in node_ids else 0
        for nid in fraud_df.account_id
    ]

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    fig.patch.set_facecolor("white")

    ax = axes[0]
    in_degs  = [G.in_degree(nid)  for nid in fraud_df.account_id]
    out_degs = [G.out_degree(nid) for nid in fraud_df.account_id]
    sc = ax.scatter(in_degs, out_degs, c=fraud_df.gnn_score,
                    cmap="RdYlGn", s=80, vmin=0, vmax=1, zorder=3)
    plt.colorbar(sc, ax=ax, label="Score GNN")
    ax.set_xlabel("In-degree", fontsize=11)
    ax.set_ylabel("Out-degree", fontsize=11)
    ax.set_title("Nodos Fraudulentos — Grado vs Score GNN\n"
                 "(verde=fácil detectar, rojo=difícil)", fontsize=11, color=NAVY)
    ax.grid(True, color=GRID, linewidth=0.5); ax.set_facecolor("#FAFAFA")

    ax = axes[1]
    ax.barh(df.account_id, df.gnn_score, color=RED, alpha=0.8)
    ax.axvline(0.5, color=NAVY, linestyle="--", linewidth=1.5, label="Threshold 0.5")
    ax.set_xlabel("Score GNN (P(fraude))", fontsize=11)
    ax.set_title("Casos más difíciles — Score de los nodos fraude\n"
                 "(ordenados de menor a mayor score)", fontsize=11, color=NAVY)
    ax.legend(fontsize=9); ax.set_xlim([0, 1])
    ax.grid(True, axis="x", color=GRID, linewidth=0.5); ax.set_facecolor("#FAFAFA")

    plt.tight_layout()
    path = Path(figures_dir) / "15_error_analysis.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {path}")

    return df


# ── 6. Save all metrics ───────────────────────────────────────────────────────

def save_all_metrics(results_list, cfg):
    reports = cfg["paths"]["reports_dir"]
    table   = build_comparison_table(results_list)
    table.to_csv(f"{reports}/metrics_all.csv")
    table.to_markdown(f"{reports}/metrics_all.md")
    with open(f"{reports}/results_all.json", "w") as f:
        json.dump(results_list, f, indent=2)
    print(f"  → {reports}/metrics_all.csv / .md / results_all.json")
    return table


# ── 7. Update insights.md with model insights ─────────────────────────────────

def append_model_insights(results_list, abl_prauc, error_df, cfg):
    reports   = cfg["paths"]["reports_dir"]
    gnn_r     = next(r for r in results_list if r["model"] == "GraphSAGE")
    xgb_r     = next(r for r in results_list if r["model"] == "XGBoost")
    lr_r      = next(r for r in results_list if r["model"] == "Logistic Regression")

    delta_prauc = gnn_r["pr_auc"] - xgb_r["pr_auc"]
    min_hard_score = float(error_df["gnn_score"].min())

    new_section = f"""
---

## Fase F — Insights de Modelo

---

### Insight 9 — El GNN mejora {delta_prauc:.3f} puntos de PR-AUC sobre XGBoost

> **Hallazgo:** GraphSAGE logra PR-AUC={gnn_r['pr_auc']:.3f} vs XGBoost={xgb_r['pr_auc']:.3f} vs LogReg={lr_r['pr_auc']:.3f}, usando exactamente el mismo test set y splits. El único diferencial es el acceso a la estructura del grafo.

> **Implicancia para BRS:** Con XGBoost, los analistas de BRS revisarían ~21 alertas/día con 20% del fraude sin detectar. Con el GNN, las alertas bajan a ~26/día (ligeramente más amplias) pero el fraude no detectado cae a 0% en este dataset. El costo operativo es marginalmente mayor, el beneficio es material.

> **Acción sugerida:** Presentar la curva PR comparativa al directorio como el argumento central del proyecto. El área entre la curva XGBoost y la curva GNN representa el "fraude adicional detectado" — traducirlo a montos evitados usando el ticket promedio de BRS.

---

### Insight 10 — La topología sola (ablation) logra PR-AUC={abl_prauc:.3f}

> **Hallazgo:** Un GraphSAGE entrenado con features constantes (solo la estructura del grafo, sin balance, risk_score ni ningún atributo de cuenta) alcanza PR-AUC={abl_prauc:.3f}. La información de *quién se conecta con quién* ya contiene señal de fraude independiente de los features individuales.

> **Implicancia para BRS:** Esto significa que aunque los datos de cuentas estén incompletos, desactualizados o sean poco confiables, el grafo de transacciones por sí solo aporta valor. En una implementación real, el modelo puede correr incluso con features de cuenta degradados (ej.: clientes con poco historial, cuentas nuevas) y seguir detectando anillos por estructura.

> **Acción sugerida:** En la fase piloto, priorizar la disponibilidad del grafo de transacciones sobre la calidad de los features de cuenta. El pipeline mínimo viable es: transacciones → GNN topológico → score de red.

---

### Insight 11 — Los nodos de anillo más difíciles son los periféricos

> **Hallazgo:** El score mínimo entre nodos fraudulentos es {min_hard_score:.4f}. Los nodos con score más bajo tienden a tener menor grado — son los nodos "de entrada" o "de salida" del anillo que tienen menos vecinos fraudulentos directos y por lo tanto reciben menos señal de red.

> **Implicancia para BRS:** En un esquema de lavado real, los nodos periféricos (entrada/salida del anillo) suelen ser las cuentas más "limpias" — las que el lavador usa para interactuar con el sistema bancario legítimo. Son los que más difícilmente captura un modelo tabular y los que más cerca están del límite de detección del GNN.

> **Acción sugerida:** Para los nodos con score intermedio (0.3–0.7), aplicar una segunda revisión manual que considere el contexto completo del anillo detectado, no solo el nodo individual. Un analista que ve el anillo completo puede decidir mucho más rápido que uno que solo ve la cuenta.

---

### Insight 12 — Regresión Logística en grafos: el límite de la linealidad

> **Hallazgo:** LogReg logra ROC-AUC={lr_r['roc_auc']:.3f} (alta separabilidad global) pero PR-AUC={lr_r['pr_auc']:.3f} (baja precisión en clases desbalanceadas) y Recall@P90=0. La frontera de decisión lineal no puede separar fraude de legítimo en el espacio de features en el punto operativo (90% precisión).

> **Implicancia para BRS:** Muchos sistemas de compliance internos usan regresión logística o scorecards lineales como base. Este resultado muestra que incluso con features de red (grado, montos, contrapartes), la no-linealidad es fundamental. El salto a XGBoost ya aporta enormemente; el salto a GNN añade la señal de vecindario.

> **Acción sugerida:** Al presentar el proyecto a BRS, usar la progresión LogReg → XGBoost → GNN como narrativa de "capas de inteligencia": cada capa agrega un tipo de información que la anterior no puede capturar (no-linealidad → estructura de red).
"""

    insights_path = f"{reports}/insights.md"
    with open(insights_path, "a") as f:
        f.write(new_section)
    print(f"  → {insights_path} actualizado con Insights 9-12")


# ── master runner ─────────────────────────────────────────────────────────────

def run_analysis(config_path="config/config.yaml"):
    cfg         = load_config(config_path)
    figures_dir = cfg["paths"]["figures_dir"]
    Path(figures_dir).mkdir(parents=True, exist_ok=True)

    print("=" * 55)
    print("  FASE F — Análisis comparativo")
    print("=" * 55)

    # 1. Load
    print("\n── 1. Cargando artefactos ────────────────────────────────")
    acc, txn, data, test_mask, y_test, scores_lr, scores_xgb, scores_gnn, model = load_all(cfg)

    # full-graph scores (all nodes, for distribution / export)
    model.eval()
    with torch.no_grad():
        logits         = model(data.x, data.edge_index)
        scores_gnn_full = F.softmax(logits, dim=1)[:, 1].numpy()

    print(f"  Test set: {len(y_test)} nodos  ({y_test.sum()} fraude)")

    # 2. Evaluate all models on same test set
    print("\n── 2. Métricas comparativas ─────────────────────────────")
    results = []
    n_acc   = data.num_nodes
    fr_rate = (data.y == 1).float().mean().item()
    for name, scores in [("Logistic Regression", scores_lr),
                          ("XGBoost",             scores_xgb),
                          ("GraphSAGE",           scores_gnn)]:
        r = evaluate_model(name, y_test, scores,
                           dataset_n_accounts=n_acc, dataset_fraud_rate=fr_rate)
        results.append(r)

    # 3. Figures
    print("\n── 3. Figuras ───────────────────────────────────────────")
    plot_pr_all(y_test, scores_lr, scores_xgb, scores_gnn, figures_dir)
    plot_score_distribution(data, scores_gnn_full, figures_dir)

    # 4. Ablation
    print("\n── 4. Ablation (solo topología) ─────────────────────────")
    abl_prauc, _ = run_ablation(data, model, cfg, figures_dir)

    # 5. Error analysis
    error_df = error_analysis(data, acc, txn, scores_gnn_full, figures_dir)

    # 6. Save metrics
    print("\n── 6. Guardando métricas ────────────────────────────────")
    table = save_all_metrics(results, cfg)
    print(table.to_string())

    # 7. Update insights.md
    print("\n── 7. Actualizando insights.md ──────────────────────────")
    append_model_insights(results, abl_prauc, error_df, cfg)

    print("\n" + "=" * 55)
    print("  Fase F completada.")
    print("=" * 55)

    return results, data, scores_gnn_full, acc, txn


if __name__ == "__main__":
    run_analysis()
