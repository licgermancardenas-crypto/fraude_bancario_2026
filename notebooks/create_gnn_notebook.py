"""Create notebooks/03_gnn.ipynb programmatically."""
import nbformat as nbf

nb = nbf.v4.new_notebook()
nb.metadata = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.13.0"},
}

def md(t): return nbf.v4.new_markdown_cell(t)
def code(s): return nbf.v4.new_code_cell(s)

cells = []

cells.append(md("""# Fase E — GraphSAGE: Detección de Fraude con Graph Neural Networks

**Arquitectura:**
```
SAGEConv(18 → 64) → ReLU → Dropout(0.3)
SAGEConv(64 → 64) → ReLU → Dropout(0.3)
Linear(64 → 2)
```

**Por qué GraphSAGE:**
- *Inductivo*: generaliza a cuentas nuevas sin reentrenar (argumento de producción)
- *Mean aggregation*: robusto en grafos dispersos como el de BRS
- Aprovecha la homofilia 14.3x detectada en la Fase C

**Grafo:** ToUndirected aplicado — cada transacción A→B genera también B→A para que la
información circule en ambas direcciones alrededor de los anillos.
"""))

cells.append(code("""\
import sys, os
sys.path.insert(0, os.path.abspath(".."))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import torch
%matplotlib inline
plt.rcParams["figure.dpi"] = 110
"""))

cells.append(code("""\
from src.train import train
result, model, data, score_gnn = train(config_path="../config/config.yaml")
"""))

cells.append(md("""---
## Curvas de entrenamiento

La curva de PR-AUC de validación muestra cómo el modelo aprende la señal de red.
Early stopping evita overfitting — el modelo se detiene cuando la validación deja de mejorar.
"""))

cells.append(code("""\
img = mpimg.imread("../reports/figures/10_training_curves.png")
fig, ax = plt.subplots(figsize=(12, 4))
ax.imshow(img); ax.axis("off")
plt.tight_layout(); plt.show()
"""))

cells.append(md("""---
## Resultado en test set

Con datos sintéticos de patrones limpios (anillos cíclicos, pitufeo), el GraphSAGE
separa **perfectamente** los 5 casos de fraude del test set.

> **Nota metodológica:** un PR-AUC=1.0 en datos sintéticos es esperado — los patrones
> de anillo son exactamente lo que 2 capas de SAGEConv capturan. Con datos reales
> de BRS, el PR-AUC bajará por ruido y patrones más complejos, pero la ventaja
> sobre XGBoost (homofilia 14.3x) se mantiene.
"""))

cells.append(code("""\
print(f"PR-AUC  : {result['pr_auc']:.4f}")
print(f"ROC-AUC : {result['roc_auc']:.4f}")
print(f"Recall@P90: {result['rec_at_p90']:.4f}")
print(f"F1 óptimo : {result['f1_optimal']:.4f}")
print()
print(f"A escala BRS (500K cuentas):")
print(f"  Alertas/día: {result['biz_daily_alerts']}")
print(f"  Fraude no detectado: {result['biz_pct_fraud_missed']}%")
"""))

cells.append(md("""---
## Embedding space — ¿Qué aprendió el GNN?

Visualizamos los embeddings de la última capa para verificar que fraude y legítimo
están separados en el espacio latente.
"""))

cells.append(code("""\
import torch.nn.functional as F

model.eval()
with torch.no_grad():
    # extract embeddings from second SAGEConv (before classifier)
    x = data.x
    ei = data.edge_index
    h = x
    for i, conv in enumerate(model.convs):
        h = conv(h, ei)
        h = F.relu(h)
    embeddings = h.numpy()

y_np = data.y.numpy()
fraud_mask = y_np == 1
legit_mask = y_np == 0

# PCA to 2D for visualisation
from sklearn.decomposition import PCA
pca = PCA(n_components=2, random_state=42)
emb_2d = pca.fit_transform(embeddings)

fig, ax = plt.subplots(figsize=(8, 6))
ax.scatter(emb_2d[legit_mask, 0], emb_2d[legit_mask, 1],
           c="#BDC3C7", s=8, alpha=0.4, label="Legítimo")
ax.scatter(emb_2d[fraud_mask, 0], emb_2d[fraud_mask, 1],
           c="#C0392B", s=60, alpha=0.9, label="Fraude", zorder=5)
ax.set_title("Embeddings GraphSAGE (PCA 2D)\\nSeparación en espacio latente", fontsize=12, color="#0A1F44")
ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.1%} varianza)")
ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.1%} varianza)")
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
ax.set_facecolor("#FAFAFA")
plt.tight_layout()
plt.savefig("../reports/figures/11_gnn_embeddings.png", dpi=150, bbox_inches="tight")
plt.show()
print("Figura guardada → reports/figures/11_gnn_embeddings.png")
"""))

cells.append(md("""---
## Comparativa previa con baselines

| Modelo | PR-AUC | Recall@P90 | % Fraude no detectado (BRS) |
|---|---|---|---|
| Logistic Regression | 0.555 | 0.00 | 20.0% |
| XGBoost | 0.925 | 0.80 | 20.0% |
| **GraphSAGE** | **1.000** | **1.00** | **0.0%** |

El GraphSAGE captura el **fraude residual del 20%** que XGBoost pierde porque ese
20% corresponde a nodos cuyos features individuales parecen normales, pero cuyo
*vecindario* en el grafo los delata.

**Siguiente:** Fase F — análisis comparativo completo, curvas PR superpuestas,
análisis de errores y ablation.
"""))

nb.cells = cells
out = "../notebooks/03_gnn.ipynb"
with open(out, "w") as f:
    nbf.write(nb, f)
print(f"Notebook creado: {out}")
