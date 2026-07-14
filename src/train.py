"""
Training loop for GraphSAGE with early stopping on validation PR-AUC.
Logs per-epoch metrics to reports/training_log.csv.
Saves best model to models/graphsage_best.pt.
"""

import csv
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import average_precision_score
import yaml

from src.build_graph import build_graph
from src.models.graphsage import GraphSAGE
from src.evaluate import evaluate_model


NAVY = "#0A1F44"
GOLD = "#C9A227"
GRID = "#E0E0E0"


def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def class_weights(y_train: torch.Tensor, device) -> torch.Tensor:
    n_pos = (y_train == 1).sum().float()
    n_neg = (y_train == 0).sum().float()
    w_pos = n_neg / (n_pos + 1e-8)
    return torch.tensor([1.0, w_pos.item()], device=device)


@torch.no_grad()
def eval_pr_auc(model, data, mask, device):
    model.eval()
    logits = model(data.x.to(device), data.edge_index.to(device))
    probs  = F.softmax(logits, dim=1)[:, 1].cpu().numpy()
    y_true = data.y.numpy()
    return average_precision_score(y_true[mask.numpy()], probs[mask.numpy()])


def plot_training_curves(log_path: str, figures_dir: str):
    rows = []
    with open(log_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k: float(v) for k, v in row.items()})

    epochs     = [r["epoch"]         for r in rows]
    train_loss = [r["train_loss"]     for r in rows]
    val_prauc  = [r["val_pr_auc"]     for r in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    fig.patch.set_facecolor("white")

    ax1.plot(epochs, train_loss, color=NAVY, linewidth=1.5)
    ax1.set_xlabel("Época", fontsize=11)
    ax1.set_ylabel("Loss (CrossEntropy)", fontsize=11)
    ax1.set_title("Curva de Entrenamiento — GraphSAGE", fontsize=12, color=NAVY)
    ax1.grid(True, color=GRID, linewidth=0.5)
    ax1.set_facecolor("#FAFAFA")

    ax2.plot(epochs, val_prauc, color=GOLD, linewidth=1.5, label="Val PR-AUC")
    best_epoch = int(rows[int(np.argmax(val_prauc))]["epoch"])
    best_val   = max(val_prauc)
    ax2.axvline(best_epoch, color=NAVY, linestyle="--", linewidth=1,
                label=f"Mejor época ({best_epoch})")
    ax2.set_xlabel("Época", fontsize=11)
    ax2.set_ylabel("PR-AUC (validación)", fontsize=11)
    ax2.set_title(f"PR-AUC de Validación — Mejor: {best_val:.4f}", fontsize=12, color=NAVY)
    ax2.legend(fontsize=10)
    ax2.grid(True, color=GRID, linewidth=0.5)
    ax2.set_facecolor("#FAFAFA")

    plt.tight_layout()
    path = Path(figures_dir) / "10_training_curves.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → Figura: {path}")


def train(config_path="config/config.yaml"):
    cfg     = load_config(config_path)
    seed    = cfg["project"]["seed"]
    gnn_cfg = cfg["model"]["graphsage"]
    reports = cfg["paths"]["reports_dir"]
    figures = cfg["paths"]["figures_dir"]
    Path(reports).mkdir(parents=True, exist_ok=True)
    Path(figures).mkdir(parents=True, exist_ok=True)

    torch.manual_seed(seed)
    np.random.seed(seed)
    device = torch.device("cpu")

    # ── 1. Build / load graph ─────────────────────────────────────────────────
    print("=" * 55)
    print("  FASE E — GraphSAGE")
    print("=" * 55)
    print("\n── 1. Construyendo grafo ────────────────────────────────")
    data = build_graph(config_path)

    # ── 2. Model & optimiser ─────────────────────────────────────────────────
    print("\n── 2. Modelo ────────────────────────────────────────────")
    model = GraphSAGE(
        in_channels     = data.num_node_features,
        hidden_channels = gnn_cfg["hidden_channels"],
        num_layers      = gnn_cfg["num_layers"],
        dropout         = gnn_cfg["dropout"],
    ).to(device)

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Parámetros: {n_params:,}")
    print(f"  {model}")

    cw = class_weights(data.y[data.train_mask], device)
    print(f"  Class weights: legítimo={cw[0]:.2f}  fraude={cw[1]:.2f}")

    optimiser = torch.optim.Adam(
        model.parameters(),
        lr           = gnn_cfg["lr"],
        weight_decay = gnn_cfg["weight_decay"],
    )

    # ── 3. Training loop with early stopping ─────────────────────────────────
    print(f"\n── 3. Entrenamiento (max {gnn_cfg['epochs']} épocas, "
          f"paciencia={gnn_cfg['patience']}) ─────")

    x          = data.x.to(device)
    edge_index = data.edge_index.to(device)
    y          = data.y.to(device)
    train_mask = data.train_mask
    val_mask   = data.val_mask

    best_val_prauc = 0.0
    best_state     = None
    patience_count = 0
    log_path       = f"{reports}/training_log.csv"

    with open(log_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["epoch", "train_loss", "val_pr_auc"])
        writer.writeheader()

        for epoch in range(1, gnn_cfg["epochs"] + 1):
            # train step
            model.train()
            optimiser.zero_grad()
            logits = model(x, edge_index)
            loss   = F.cross_entropy(
                logits[train_mask],
                y[train_mask],
                weight=cw,
            )
            loss.backward()
            optimiser.step()

            # validation
            val_prauc = eval_pr_auc(model, data, val_mask, device)

            writer.writerow({
                "epoch":       epoch,
                "train_loss":  round(loss.item(), 6),
                "val_pr_auc":  round(val_prauc, 6),
            })

            if epoch % 20 == 0 or epoch == 1:
                print(f"  Época {epoch:>4}  loss={loss.item():.4f}  "
                      f"val_PR-AUC={val_prauc:.4f}")

            # early stopping
            if val_prauc > best_val_prauc + 1e-5:
                best_val_prauc = val_prauc
                best_state     = {k: v.clone() for k, v in model.state_dict().items()}
                patience_count = 0
            else:
                patience_count += 1
                if patience_count >= gnn_cfg["patience"]:
                    print(f"  Early stopping en época {epoch} "
                          f"(mejor val_PR-AUC={best_val_prauc:.4f})")
                    break

    # ── 4. Restore best model & save ─────────────────────────────────────────
    model.load_state_dict(best_state)
    torch.save({"model_state": best_state,
                "in_channels": data.num_node_features,
                "config":      gnn_cfg},
               "models/graphsage_best.pt")
    torch.save(data, "data/processed/graph.pt")
    print(f"\n  Mejor val_PR-AUC: {best_val_prauc:.4f}")
    print("  Guardado → models/graphsage_best.pt")

    # ── 5. Evaluate on TEST set ───────────────────────────────────────────────
    print("\n── 4. Evaluación en test set ────────────────────────────")
    model.eval()
    with torch.no_grad():
        logits     = model(x, edge_index)
        score_gnn  = F.softmax(logits, dim=1)[:, 1].cpu().numpy()

    test_mask_np = data.test_mask.numpy()
    y_test       = data.y.numpy()[test_mask_np]
    scores_test  = score_gnn[test_mask_np]

    result = evaluate_model(
        "GraphSAGE",
        y_test,
        scores_test,
        dataset_n_accounts = data.num_nodes,
        dataset_fraud_rate = (data.y == 1).float().mean().item(),
    )

    # save scores for comparison
    np.save("data/processed/scores_graphsage.npy", scores_test)

    # ── 6. Figures ────────────────────────────────────────────────────────────
    print("\n── 5. Figuras ───────────────────────────────────────────")
    plot_training_curves(log_path, figures)

    print("\n" + "=" * 55)
    print("  GraphSAGE completado.")
    print(f"  PR-AUC test: {result['pr_auc']:.4f}")
    print("=" * 55)

    return result, model, data, score_gnn


if __name__ == "__main__":
    train()
