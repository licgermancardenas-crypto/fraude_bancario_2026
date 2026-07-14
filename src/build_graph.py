"""
Build a PyTorch Geometric Data object from raw CSVs.

Design decisions (documented here per project spec):
- Direction: transactions are directed (src→dst). We apply ToUndirected() so
  each directed edge becomes two undirected edges. This lets each node receive
  messages from both its senders and receivers — critical for ring detection
  where information must flow around the cycle in both directions.
- Normalisation: mean/std computed ONLY on train nodes to avoid leakage.
  Applied to all nodes (train, val, test) using train statistics.
- Splits: loaded from data/processed/ (created by train_baseline.py) so the
  GNN uses exactly the same train/val/test partition as the tabular baselines.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch_geometric.data import Data
from torch_geometric.transforms import ToUndirected
import yaml

from src.features import build_node_features, get_feature_matrix


def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def build_graph(config_path="config/config.yaml") -> Data:
    cfg = load_config(config_path)
    raw = cfg["data"]["raw_dir"]
    processed = cfg["data"]["processed_dir"]

    # ── 1. Load raw data ──────────────────────────────────────────────────────
    acc = pd.read_csv(f"{raw}/accounts.csv")
    txn = pd.read_csv(f"{raw}/transactions.csv")

    # ── 2. Node features ──────────────────────────────────────────────────────
    feats = build_node_features(acc, txn)
    X, y, feat_names = get_feature_matrix(feats)          # (N, F), (N,)
    node_ids = feats["account_id"].tolist()
    id2idx   = {nid: i for i, nid in enumerate(node_ids)}

    # ── 3. Load splits & normalise with train statistics ─────────────────────
    train_idx = np.load(f"{processed}/train_idx.npy")

    X_mean = X[train_idx].mean(axis=0)
    X_std  = X[train_idx].std(axis=0) + 1e-8
    X_norm = (X - X_mean) / X_std

    val_idx  = np.load(f"{processed}/val_idx.npy")
    test_idx = np.load(f"{processed}/test_idx.npy")

    N = len(node_ids)
    train_mask = torch.zeros(N, dtype=torch.bool)
    val_mask   = torch.zeros(N, dtype=torch.bool)
    test_mask  = torch.zeros(N, dtype=torch.bool)
    train_mask[train_idx] = True
    val_mask[val_idx]     = True
    test_mask[test_idx]   = True

    # ── 4. Build edge_index ───────────────────────────────────────────────────
    src_nodes = txn["src"].map(id2idx).dropna().astype(int)
    dst_nodes = txn["dst"].map(id2idx).dropna().astype(int)
    valid     = src_nodes.notna() & dst_nodes.notna()
    edge_index = torch.tensor(
        [src_nodes[valid].tolist(), dst_nodes[valid].tolist()],
        dtype=torch.long,
    )
    edge_attr = torch.tensor(
        txn.loc[valid.index[valid], "amount"].values, dtype=torch.float32
    ).unsqueeze(1)

    # ── 5. Assemble Data object ───────────────────────────────────────────────
    data = Data(
        x          = torch.tensor(X_norm, dtype=torch.float32),
        y          = torch.tensor(y, dtype=torch.long),
        edge_index = edge_index,
        edge_attr  = edge_attr,
        train_mask = train_mask,
        val_mask   = val_mask,
        test_mask  = test_mask,
    )
    data.feat_names  = feat_names
    data.norm_mean   = X_mean
    data.norm_std    = X_std
    data.node_ids    = node_ids

    # ── 6. ToUndirected (see module docstring) ────────────────────────────────
    data = ToUndirected()(data)

    # ── 7. Save ───────────────────────────────────────────────────────────────
    Path(processed).mkdir(parents=True, exist_ok=True)
    torch.save(data, f"{processed}/graph.pt")

    print(f"[build_graph] Nodes={data.num_nodes}  Edges={data.num_edges}  "
          f"Features={data.num_node_features}")
    print(f"  Train={train_mask.sum().item()}  Val={val_mask.sum().item()}  "
          f"Test={test_mask.sum().item()}")
    print(f"  Fraud nodes: {(data.y==1).sum().item()} / {data.num_nodes}")
    print(f"  Saved → {processed}/graph.pt")

    return data


if __name__ == "__main__":
    build_graph()
