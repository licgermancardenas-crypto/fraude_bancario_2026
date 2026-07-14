"""Create notebooks/02_baseline.ipynb programmatically."""
import nbformat as nbf

nb = nbf.v4.new_notebook()
nb.metadata = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.13.0"},
}

def md(text): return nbf.v4.new_markdown_cell(text)
def code(src): return nbf.v4.new_code_cell(src)

cells = []

cells.append(md("""# Fase D — Baselines Tabulares: LogReg vs XGBoost

**Objetivo:** establecer el piso de rendimiento con modelos que NO usan estructura del grafo.
El argumento comercial del GNN es "mejora X puntos de PR-AUC sobre XGBoost".

**Splits:** 70/15/15 estratificados, seed=42 — los mismos que usará el GNN.
"""))

cells.append(code("""\
import sys, os
sys.path.insert(0, os.path.abspath(".."))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
%matplotlib inline
plt.rcParams["figure.dpi"] = 110
"""))

cells.append(code("""\
from src.train_baseline import main
results, feats, X, y, train_idx, val_idx, test_idx, feat_names = main(
    config_path="../config/config.yaml"
)
"""))

cells.append(md("""---
## Resultados — Tabla comparativa

| Métrica | Descripción operativa |
|---|---|
| **PR-AUC** | Métrica principal — resume toda la curva precisión-recall (crítica con clases desbalanceadas) |
| **ROC-AUC** | Secundaria — referencia estándar de industria |
| **Recall@P90** | Con 9 de cada 10 alertas correctas, ¿qué % del fraude detectamos? |
| **F1-óptimo** | Balance precisión/recall en el threshold que maximiza F1 |
"""))

cells.append(code("""\
from src.evaluate import build_comparison_table
table = build_comparison_table(results)
print(table.to_markdown())
"""))

cells.append(md("""---
## Curva Precisión-Recall

La curva PR es la visualización principal del proyecto — resume el trade-off operativo.
El área bajo la curva (PR-AUC) es la métrica que comparamos entre los tres modelos.
"""))

cells.append(code("""\
img = mpimg.imread("../reports/figures/08_pr_curves_baseline.png")
fig, ax = plt.subplots(figsize=(8, 6))
ax.imshow(img); ax.axis("off")
plt.tight_layout(); plt.show()
"""))

cells.append(md("""---
## Importancia de Features — XGBoost

¿Qué variables tabulates capturan mejor la señal de fraude?
Esta figura informa el feature engineering del GNN.
"""))

cells.append(code("""\
img = mpimg.imread("../reports/figures/09_feature_importance_xgb.png")
fig, ax = plt.subplots(figsize=(8, 5))
ax.imshow(img); ax.axis("off")
plt.tight_layout(); plt.show()
"""))

cells.append(md("""---
## Interpretación para BRS

**Logistic Regression (PR-AUC = 0.555):**
- Captura la señal de balance y grado pero no la interacción entre features
- Recall@P90 = 0% → imposible mantener 90% de precisión con recall > 0
- Referencia mínima: lo que haría un sistema de reglas simples

**XGBoost (PR-AUC = 0.925):**
- Captura interacciones no lineales: grado + monto + tipo_cuenta
- Recall@P90 = 80% → con 90% de precisión detecta 4 de 5 fraudes del test set
- Escalado a BRS: ~21 alertas/día, 80% del fraude detectado
- Este es el **piso de referencia** para el GNN

**Gap que el GNN debe superar:**
- El GNN tiene acceso a información adicional: quiénes son los vecinos
- Con homofilia 14.3x (de la Fase C), esperamos que el GNN mejore recall@P90 y PR-AUC
- Hipótesis: el GNN detectará nodos de anillos que XGBoost pierde porque
  sus features tabulares individuales parecen "normales"

---
**Siguiente:** Fase E — GraphSAGE sobre el mismo test set
"""))

cells.append(code("""\
# Verificar que splits están guardados para el GNN
train_idx_loaded = np.load("../data/processed/train_idx.npy")
val_idx_loaded   = np.load("../data/processed/val_idx.npy")
test_idx_loaded  = np.load("../data/processed/test_idx.npy")
print(f"train_idx guardado: {len(train_idx_loaded)} muestras")
print(f"val_idx   guardado: {len(val_idx_loaded)} muestras")
print(f"test_idx  guardado: {len(test_idx_loaded)} muestras")
print("Splits listos para el GNN ✓")
"""))

nb.cells = cells

out = "../notebooks/02_baseline.ipynb"
with open(out, "w") as f:
    nbf.write(nb, f)
print(f"Notebook creado: {out}")
