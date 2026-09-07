"""
Build a PyTorch Geometric Data object from raw CSVs.

Design decisions (documented here per project spec):
- Direction: transactions are directed (src→dst). We apply ToUndirected() so
  each directed edge becomes two undirected edges. This lets each node receive
  messages from both its senders and receivers — critical for ring detection
  where information must flow around the cycle in both directions.
- Normalisation: mean/std computed ONLY on train nodes to avoid leakage.
  Applied to all nodes (train, val, test) using train statistics.
- Aristas: se agregan las transacciones paralelas a una arista por par
  (src,dst); edge_attr lleva [cantidad, monto_total, monto_medio].
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

from src import txn_store


def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def build_graph(config_path="config/config.yaml") -> Data:
    cfg = load_config(config_path)
    raw = cfg["data"]["raw_dir"]
    processed = cfg["data"]["processed_dir"]

    # ── 1. Load raw data ──────────────────────────────────────────────────────
    acc = pd.read_csv(f"{raw}/accounts.csv")
    txn = txn_store.load_transactions(raw, columns=["src", "dst", "amount", "timestamp"])

    # ── 2. Node features ──────────────────────────────────────────────────────
    feats = build_node_features(acc, txn)
    X, y, feat_names = get_feature_matrix(feats)          # (N, F), (N,)
    node_ids = feats["account_id"].tolist()
    id2idx   = {nid: i for i, nid in enumerate(node_ids)}

    # ── 3. Load splits & normalise with train statistics ─────────────────────
    N = len(node_ids)
    train_idx = np.load(f"{processed}/train_idx.npy")

    X_mean = X[train_idx].mean(axis=0)
    X_std  = X[train_idx].std(axis=0) + 1e-8
    X_norm = (X - X_mean) / X_std

    val_idx  = np.load(f"{processed}/val_idx.npy")
    test_idx = np.load(f"{processed}/test_idx.npy")

    train_mask = torch.zeros(N, dtype=torch.bool)
    val_mask   = torch.zeros(N, dtype=torch.bool)
    test_mask  = torch.zeros(N, dtype=torch.bool)
    train_mask[train_idx] = True
    val_mask[val_idx]     = True
    test_mask[test_idx]   = True

    # ── 4. Build edge_index — aristas paralelas agregadas ────────────────────
    # El libro tiene 11,7M transacciones sobre 1,58M pares distintos: con la
    # economía de contrapartes recurrentes, una relación se repite 7,4 veces en
    # promedio. Se agrega a UNA arista por par y la intensidad de la relación
    # pasa a edge_attr (cantidad, monto total, monto medio).
    #
    # Por qué agregar y no dejar las 11,7M aristas:
    #  - el paso de mensajes no gana nada repitiendo el mismo vecino: con
    #    agregación media, un supermercado visitado 40 veces pesaría 40 veces
    #    más que una contraparte de una sola operación, que es justamente la
    #    que interesa en lavado;
    #  - 11,7M aristas dirigidas se vuelven 23,5M al aplicar ToUndirected, y a
    #    64 canales ocultos los mensajes intermedios no entran en memoria.
    # No se pierde información: la intensidad queda en edge_attr, y las features
    # de nodo se siguen calculando sobre el stream completo, no sobre el grafo.
    cats = txn["src"].cat.categories
    cat2idx = np.array([id2idx.get(c, -1) for c in cats], dtype=np.int64)
    src_nodes = cat2idx[txn["src"].cat.codes.to_numpy()]
    dst_nodes = cat2idx[txn["dst"].cat.codes.to_numpy()]
    valid = (src_nodes >= 0) & (dst_nodes >= 0)
    src_nodes, dst_nodes = src_nodes[valid], dst_nodes[valid]
    amounts = txn["amount"].to_numpy(dtype=np.float64)[valid]

    pair = src_nodes * N + dst_nodes
    uniq, inverse = np.unique(pair, return_inverse=True)
    n_txn = np.bincount(inverse, minlength=len(uniq))
    sum_amt = np.bincount(inverse, weights=amounts, minlength=len(uniq))

    edge_index = torch.tensor(
        np.stack([uniq // N, uniq % N]), dtype=torch.long
    )
    edge_attr = torch.tensor(
        np.stack([n_txn, sum_amt, sum_amt / np.maximum(n_txn, 1)], axis=1),
        dtype=torch.float32,
    )
    print(f"[build_graph] {len(src_nodes):,} transacciones → {len(uniq):,} aristas "
          f"únicas ({len(src_nodes)/max(len(uniq),1):.2f} txns por arista)")

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
