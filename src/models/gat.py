"""
GAT (Graph Attention Network) for fraud node classification.

Architecture:
  GATConv(18 → 16, heads=4, concat=True)  → 64 dim
  ELU → Dropout(0.3)
  GATConv(64 → 16, heads=4, concat=True)  → 64 dim
  ELU → Dropout(0.3)
  Linear(64 → 2)

Why GAT over GraphSAGE:
  - Attention weights let the model focus on the most suspicious neighbours
  - Interpretable: attention scores show WHICH connections drive the prediction
  - Multi-head attention improves stability on heterophilic graphs
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATConv


class GAT(nn.Module):
    def __init__(self, in_channels: int, hidden_channels: int = 64,
                 num_layers: int = 2, heads: int = 4, dropout: float = 0.3):
        super().__init__()
        self.dropout = dropout
        per_head = hidden_channels // heads   # 64 // 4 = 16 dim per head

        self.convs = nn.ModuleList()
        # first layer: in → hidden (multi-head concat)
        self.convs.append(GATConv(in_channels, per_head, heads=heads,
                                  concat=True, dropout=dropout))
        # subsequent layers: hidden → hidden
        for _ in range(num_layers - 1):
            self.convs.append(GATConv(hidden_channels, per_head, heads=heads,
                                      concat=True, dropout=dropout))

        self.classifier = nn.Linear(hidden_channels, 2)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor,
                return_attention: bool = False):
        attn_weights = []
        for i, conv in enumerate(self.convs):
            if return_attention:
                x, (ei, aw) = conv(x, edge_index, return_attention_weights=True)
                attn_weights.append((ei, aw))
            else:
                x = conv(x, edge_index)
            x = F.elu(x)
            x = F.dropout(x, p=self.dropout, training=self.training)

        out = self.classifier(x)
        if return_attention:
            return out, attn_weights
        return out

    def predict_proba(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        logits = self.forward(x, edge_index)
        return F.softmax(logits, dim=1)[:, 1]
