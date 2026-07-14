"""
Train and evaluate tabular baseline models (Logistic Regression, XGBoost).
Saves splits to data/processed/ so GNN uses the same train/val/test partition.
Outputs metrics to reports/metrics_baseline.csv and reports/metrics_baseline.md.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.metrics import precision_recall_curve
import yaml

from src.features import build_node_features, get_feature_matrix
from src.models.baseline import build_logreg, build_xgboost, save_model
from src.evaluate import evaluate_model, build_comparison_table


# ── palette ──────────────────────────────────────────────────────────────────
NAVY = "#0A1F44"
GOLD = "#C9A227"
RED  = "#C0392B"
GRID = "#E0E0E0"
MODEL_COLORS = {"Logistic Regression": NAVY, "XGBoost": GOLD}


def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def load_raw(cfg):
    raw = cfg["data"]["raw_dir"]
    acc = pd.read_csv(f"{raw}/accounts.csv")
    txn = pd.read_csv(f"{raw}/transactions.csv")
    return acc, txn


# ── splits ────────────────────────────────────────────────────────────────────

def make_splits(y: np.ndarray, cfg: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    seed  = cfg["project"]["seed"]
    train_ratio = cfg["split"]["train"]
    val_ratio   = cfg["split"]["val"]

    sss1 = StratifiedShuffleSplit(n_splits=1, test_size=1 - train_ratio, random_state=seed)
    train_idx, temp_idx = next(sss1.split(np.zeros(len(y)), y))

    y_temp = y[temp_idx]
    val_frac = val_ratio / (1 - train_ratio)
    sss2 = StratifiedShuffleSplit(n_splits=1, test_size=1 - val_frac, random_state=seed)
    val_rel, test_rel = next(sss2.split(np.zeros(len(y_temp)), y_temp))
    val_idx  = temp_idx[val_rel]
    test_idx = temp_idx[test_rel]

    return train_idx, val_idx, test_idx


def save_splits(train_idx, val_idx, test_idx, cfg):
    out = Path(cfg["data"]["processed_dir"])
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "train_idx.npy", train_idx)
    np.save(out / "val_idx.npy",   val_idx)
    np.save(out / "test_idx.npy",  test_idx)
    print(f"  Splits guardados en {out}/")


# ── PR curve figure ───────────────────────────────────────────────────────────

def plot_pr_curves(results_with_curves, figures_dir):
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor("white")

    colors = [NAVY, GOLD, RED]
    for (name, prec, rec, pr_auc), color in zip(results_with_curves, colors):
        ax.step(rec, prec, where="post", color=color, linewidth=2,
                label=f"{name}  (PR-AUC={pr_auc:.3f})")

    ax.axhline(0.90, color="gray", linestyle="--", linewidth=1, alpha=0.7,
               label="Precision = 90%")
    ax.set_xlabel("Recall", fontsize=12)
    ax.set_ylabel("Precisión", fontsize=12)
    ax.set_title("Curva Precisión-Recall — Baselines Tabulares\nBanco Regional del Sur (BRS)",
                 fontsize=13, color=NAVY)
    ax.legend(fontsize=10, loc="upper right")
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1.05])
    ax.grid(True, color=GRID, linewidth=0.5)
    ax.set_facecolor("#FAFAFA")

    Path(figures_dir).mkdir(parents=True, exist_ok=True)
    path = Path(figures_dir) / "08_pr_curves_baseline.png"
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → Figura: {path}")


# ── feature importance figure ─────────────────────────────────────────────────

def plot_feature_importance(xgb_model, feature_names, figures_dir):
    importances = xgb_model.feature_importances_
    idx = np.argsort(importances)[-15:]  # top 15

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor("white")
    bars = ax.barh([feature_names[i] for i in idx], importances[idx],
                   color=GOLD, alpha=0.85)
    ax.set_xlabel("Importancia (gain)", fontsize=11)
    ax.set_title("Top 15 Features — XGBoost\n(referencia para feature engineering del GNN)",
                 fontsize=12, color=NAVY)
    ax.grid(True, axis="x", color=GRID, linewidth=0.5)
    ax.set_facecolor("#FAFAFA")

    path = Path(figures_dir) / "09_feature_importance_xgb.png"
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → Figura: {path}")


# ── main ──────────────────────────────────────────────────────────────────────

def main(config_path="config/config.yaml"):
    cfg = load_config(config_path)
    seed = cfg["project"]["seed"]
    processed_dir = cfg["data"]["processed_dir"]
    figures_dir   = cfg["paths"]["figures_dir"]
    reports_dir   = cfg["paths"]["reports_dir"]

    print("=" * 55)
    print("  FASE D — Baselines Tabulares")
    print("=" * 55)

    # 1. Load & feature engineering
    print("\n── 1. Feature engineering ────────────────────────────────")
    acc, txn = load_raw(cfg)
    feats    = build_node_features(acc, txn)
    X, y, feat_names = get_feature_matrix(feats)
    print(f"  Feature matrix: {X.shape}  ({y.sum()} fraude / {(y==0).sum()} legítimo)")

    # 2. Splits (save for GNN reuse)
    print("\n── 2. Splits estratificados (70/15/15, seed=42) ─────────")
    train_idx, val_idx, test_idx = make_splits(y, cfg)
    save_splits(train_idx, val_idx, test_idx, cfg)
    print(f"  Train : {len(train_idx):>4} ({y[train_idx].sum()} fraude)")
    print(f"  Val   : {len(val_idx):>4}  ({y[val_idx].sum()} fraude)")
    print(f"  Test  : {len(test_idx):>4}  ({y[test_idx].sum()} fraude)")

    X_train, y_train = X[train_idx], y[train_idx]
    X_val,   y_val   = X[val_idx],   y[val_idx]
    X_test,  y_test  = X[test_idx],  y[test_idx]

    # 3. Train models
    print("\n── 3. Entrenamiento ─────────────────────────────────────")

    # Logistic Regression
    print("  → Logistic Regression...")
    logreg = build_logreg(seed=seed)
    logreg.fit(X_train, y_train)
    save_model(logreg, f"models/logreg.pkl")

    # XGBoost — scale_pos_weight = n_neg / n_pos
    n_pos = y_train.sum()
    n_neg = (y_train == 0).sum()
    spw   = n_neg / max(n_pos, 1)
    print(f"  → XGBoost (scale_pos_weight={spw:.1f})...")
    xgb = build_xgboost(scale_pos_weight=spw, seed=seed)
    xgb.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )
    save_model(xgb, f"models/xgboost.pkl")

    # 4. Evaluate on TEST set
    print("\n── 4. Evaluación en test set ────────────────────────────")
    score_lr  = logreg.predict_proba(X_test)[:, 1]
    score_xgb = xgb.predict_proba(X_test)[:, 1]

    results = []
    curves  = []

    for name, scores in [("Logistic Regression", score_lr), ("XGBoost", score_xgb)]:
        r = evaluate_model(name, y_test, scores,
                           dataset_n_accounts=len(feats),
                           dataset_fraud_rate=y.mean())
        results.append(r)
        prec, rec, _ = precision_recall_curve(y_test, scores)
        curves.append((name, prec, rec, r["pr_auc"]))

    # 5. Figures
    print("\n── 5. Figuras ───────────────────────────────────────────")
    plot_pr_curves(curves, figures_dir)
    plot_feature_importance(xgb, feat_names, figures_dir)

    # 6. Save metrics
    print("\n── 6. Guardando métricas ────────────────────────────────")
    Path(reports_dir).mkdir(parents=True, exist_ok=True)

    table = build_comparison_table(results)
    csv_path = f"{reports_dir}/metrics_baseline.csv"
    md_path  = f"{reports_dir}/metrics_baseline.md"
    table.to_csv(csv_path)
    table.to_markdown(md_path)
    print(f"  → {csv_path}")
    print(f"  → {md_path}")

    # also save raw scores for GNN comparison later
    Path(processed_dir).mkdir(parents=True, exist_ok=True)
    np.save(f"{processed_dir}/y_test.npy",         y_test)
    np.save(f"{processed_dir}/scores_logreg.npy",  score_lr)
    np.save(f"{processed_dir}/scores_xgboost.npy", score_xgb)

    # save full results as JSON
    with open(f"{reports_dir}/results_baseline.json", "w") as f:
        import json
        json.dump(results, f, indent=2)

    print("\n" + "=" * 55)
    print("  Baselines completados.")
    print(f"  Mejor PR-AUC: {max(r['pr_auc'] for r in results):.4f}")
    print("=" * 55)

    return results, feats, X, y, train_idx, val_idx, test_idx, feat_names


if __name__ == "__main__":
    main()
