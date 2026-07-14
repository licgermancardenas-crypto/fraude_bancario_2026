"""
Training loop for GAT — same split, same evaluation harness as GraphSAGE.
Saves best model to models/gat_best.pt.
Appends results to reports/results_all.json and updates dashboard JSONs.
"""

import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import average_precision_score, precision_recall_curve
import yaml

from src.models.gat import GAT
from src.features import FEATURE_COLS
from src.evaluate import evaluate_model


NAVY = "#0A1F44"
GOLD = "#C9A227"


def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def class_weights(y_train: torch.Tensor) -> torch.Tensor:
    n_pos = (y_train == 1).sum().float()
    n_neg = (y_train == 0).sum().float()
    return torch.tensor([1.0, (n_neg / (n_pos + 1e-8)).item()])


@torch.no_grad()
def eval_pr_auc(model, data, mask):
    model.eval()
    logits = model(data.x, data.edge_index)
    probs  = F.softmax(logits, dim=1)[:, 1].numpy()
    y_true = data.y.numpy()
    return average_precision_score(y_true[mask.numpy()], probs[mask.numpy()])


def train(cfg):
    proc    = cfg["data"]["processed_dir"]
    models  = cfg["paths"]["models_dir"]
    reports = cfg["paths"]["reports_dir"]
    figs    = cfg["paths"]["figures_dir"]
    gat_cfg = cfg["model"]["gat"]

    # ── load graph ──────────────────────────────────────────
    data = torch.load(f"{proc}/graph.pt", weights_only=False)
    print(f"  Grafo: {data.x.shape[0]} nodos, {data.edge_index.shape[1]} aristas")

    # ── model ───────────────────────────────────────────────
    model = GAT(
        in_channels=len(FEATURE_COLS),
        hidden_channels=gat_cfg["hidden_channels"],
        num_layers=gat_cfg["num_layers"],
        heads=gat_cfg["heads"],
        dropout=gat_cfg["dropout"],
    )
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Parámetros: {n_params:,}")

    # ── optimizer + loss ─────────────────────────────────────
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=gat_cfg["lr"],
        weight_decay=gat_cfg["weight_decay"],
    )
    cw   = class_weights(data.y[data.train_mask])
    loss_fn = torch.nn.CrossEntropyLoss(weight=cw)

    # ── training loop ────────────────────────────────────────
    best_val, best_epoch, patience_count = 0.0, 0, 0
    patience = gat_cfg["patience"]
    epochs   = gat_cfg["epochs"]
    history  = []

    print(f"\n  Entrenando {epochs} épocas (early stop paciencia={patience})…")
    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad()
        logits = model(data.x, data.edge_index)
        loss   = loss_fn(logits[data.train_mask], data.y[data.train_mask])
        loss.backward()
        optimizer.step()

        val_prauc = eval_pr_auc(model, data, data.val_mask)
        history.append((epoch, loss.item(), val_prauc))

        if val_prauc > best_val:
            best_val   = val_prauc
            best_epoch = epoch
            patience_count = 0
            Path(models).mkdir(exist_ok=True)
            torch.save({
                "model_state": model.state_dict(),
                "in_channels": len(FEATURE_COLS),
                "config":      gat_cfg,
            }, f"{models}/gat_best.pt")
        else:
            patience_count += 1
            if patience_count >= patience:
                print(f"  Early stopping en época {epoch}")
                break

        if epoch % 20 == 0 or epoch == 1:
            print(f"  Época {epoch:>3} | loss={loss.item():.4f} | val PR-AUC={val_prauc:.4f}")

    print(f"\n  Mejor época: {best_epoch}  |  val PR-AUC: {best_val:.4f}")

    # ── load best and evaluate ───────────────────────────────
    ckpt = torch.load(f"{models}/gat_best.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    with torch.no_grad():
        logits = model(data.x, data.edge_index)
        probs  = F.softmax(logits, dim=1)[:, 1].numpy()

    test_mask  = data.test_mask.numpy()
    y_true     = data.y.numpy()
    y_score    = probs[test_mask]
    y_true_test = y_true[test_mask]

    results = evaluate_model("GAT", y_true_test, y_score)

    # save test scores
    np.save(f"{proc}/scores_gat.npy", y_score)

    return model, data, probs, results, history


def plot_training_curves(history, best_epoch, figs):
    epochs     = [h[0] for h in history]
    train_loss = [h[1] for h in history]
    val_prauc  = [h[2] for h in history]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    fig.patch.set_facecolor("white")

    ax1.plot(epochs, train_loss, color=NAVY, linewidth=1.5)
    ax1.set_xlabel("Época"); ax1.set_ylabel("Loss (CrossEntropy)")
    ax1.set_title("Curva de Entrenamiento — GAT", color=NAVY)
    ax1.grid(True, color="#E0E0E0", linewidth=0.5)

    ax2.plot(epochs, val_prauc, color=GOLD, linewidth=1.5, label="Val PR-AUC")
    ax2.axvline(best_epoch, color=NAVY, linestyle="--", linewidth=1,
                label=f"Mejor época ({best_epoch})")
    ax2.set_xlabel("Época"); ax2.set_ylabel("PR-AUC (validación)")
    ax2.set_title(f"PR-AUC Validación — GAT  [mejor: {max(val_prauc):.4f}]", color=NAVY)
    ax2.legend(); ax2.grid(True, color="#E0E0E0", linewidth=0.5)

    plt.tight_layout()
    path = f"{figs}/18_gat_training_curves.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {path}")


def plot_pr_curves_updated(results_all, figs):
    """Fig 19 — updated PR curve with GAT added."""
    proc = "data/processed"
    data = torch.load(f"{proc}/graph.pt", weights_only=False)
    y_true_test = data.y.numpy()[data.test_mask.numpy()]

    model_files = {
        "Logistic Regression": f"{proc}/scores_logreg.npy",
        "XGBoost":             f"{proc}/scores_xgboost.npy",
        "GraphSAGE":           f"{proc}/scores_graphsage.npy",
        "GAT":                 f"{proc}/scores_gat.npy",
    }
    colors = {
        "Logistic Regression": "#BDC3C7",
        "XGBoost":             "#C9A227",
        "GraphSAGE":           "#C0392B",
        "GAT":                 "#2E86AB",
    }

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#FAFAFA")

    baseline = y_true_test.mean()
    ax.axhline(baseline, color="#95A5A6", linestyle=":", linewidth=1,
               label=f"Azar (prevalencia={baseline:.3f})")

    for name, path in model_files.items():
        if not Path(path).exists():
            continue
        scores = np.load(path)
        prec, rec, _ = precision_recall_curve(y_true_test, scores)
        prauc = average_precision_score(y_true_test, scores)
        lw = 2.5 if name in ("GraphSAGE", "GAT") else 1.5
        ax.plot(rec, prec, color=colors[name], linewidth=lw,
                label=f"{name} (PR-AUC={prauc:.3f})")

    ax.set_xlabel("Recall", fontsize=12)
    ax.set_ylabel("Precisión", fontsize=12)
    ax.set_title("Curva Precisión-Recall — GraphSAGE vs GAT vs Baselines",
                 fontsize=13, color=NAVY, fontweight="bold")
    ax.legend(fontsize=10, loc="upper right")
    ax.grid(True, color="#E0E0E0", linewidth=0.5)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.05)

    path = f"{figs}/19_pr_curves_with_gat.png"
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {path}")


def update_results_json(new_result, reports):
    path = f"{reports}/results_all.json"
    with open(path) as f:
        results = json.load(f)

    # replace if already exists, else append
    names = [r["model"] for r in results]
    if new_result["model"] in names:
        results[names.index(new_result["model"])] = new_result
    else:
        results.append(new_result)

    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  → {path}  ({len(results)} modelos)")


def update_dashboard_pr_curves(reports, dashboard_data):
    """Regenerate pr_curves.json adding GAT."""
    proc = "data/processed"
    data = torch.load(f"{proc}/graph.pt", weights_only=False)
    y_true_test = data.y.numpy()[data.test_mask.numpy()]

    model_files = {
        "Logistic Regression": f"{proc}/scores_logreg.npy",
        "XGBoost":             f"{proc}/scores_xgboost.npy",
        "GraphSAGE":           f"{proc}/scores_graphsage.npy",
        "GAT":                 f"{proc}/scores_gat.npy",
    }

    curves = []
    for name, path in model_files.items():
        if not Path(path).exists():
            continue
        scores = np.load(path)
        prec, rec, _ = precision_recall_curve(y_true_test, scores)
        prauc = average_precision_score(y_true_test, scores)
        step = max(1, len(prec) // 200)
        curves.append({
            "model":  name,
            "pr_auc": round(float(prauc), 4),
            "points": [{"precision": round(float(p), 4), "recall": round(float(r), 4)}
                       for p, r in zip(prec[::step], rec[::step])],
        })

    out = f"{dashboard_data}/pr_curves.json"
    with open(out, "w") as f:
        json.dump(curves, f)
    print(f"  → {out}  ({len(curves)} curvas)")


def main(config_path="config/config.yaml"):
    cfg = load_config(config_path)

    print("=" * 55)
    print("  GAT — Graph Attention Network")
    print("=" * 55)

    # Add GAT config defaults if not present
    if "gat" not in cfg["model"]:
        cfg["model"]["gat"] = {
            "hidden_channels": 64,
            "num_layers": 2,
            "heads": 4,
            "dropout": 0.3,
            "lr": 0.005,
            "weight_decay": 0.0005,
            "epochs": 300,
            "patience": 20,
        }

    print("\n── 1. Entrenamiento ────────────────────────────────────")
    model, data, all_probs, results, history = train(cfg)

    best_epoch = history[int(np.argmax([h[2] for h in history]))][0]

    figs    = cfg["paths"]["figures_dir"]
    reports = cfg["paths"]["reports_dir"]
    dd      = cfg["paths"]["dashboard_data_dir"]

    print("\n── 2. Figuras ──────────────────────────────────────────")
    plot_training_curves(history, best_epoch, figs)
    plot_pr_curves_updated(results, figs)

    print("\n── 3. Actualizando resultados ──────────────────────────")
    update_results_json(results, reports)

    print("\n── 4. Actualizando dashboard ───────────────────────────")
    update_dashboard_pr_curves(reports, dd)

    print("\n" + "=" * 55)
    print(f"  GAT  PR-AUC={results['pr_auc']:.4f}  "
          f"Recall@P90={results['rec_at_p90']:.2f}  "
          f"F1={results['f1_optimal']:.4f}")
    print("=" * 55)


if __name__ == "__main__":
    main()
