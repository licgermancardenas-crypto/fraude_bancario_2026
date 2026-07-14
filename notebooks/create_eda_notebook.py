"""Script to create 01_eda.ipynb programmatically."""
import nbformat as nbf

nb = nbf.v4.new_notebook()
nb.metadata = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.13.0"},
}

cells = []

def md(text):
    return nbf.v4.new_markdown_cell(text)

def code(src):
    return nbf.v4.new_code_cell(src)

# ── cells ──────────────────────────────────────────────────────────────────

cells.append(md("""# EDA — Detección de Fraude / Banco Regional del Sur (BRS)

**Proyecto:** Detección de redes de lavado mediante inteligencia de grafos
**Autor:** Germán Cárdenas
**Dataset:** Sintético — `gen-fraud-graph` equivalente, scale=0.01, seed=42

---

Este notebook recorre el análisis exploratorio del grafo transaccional siguiendo la skill `eda-grafo`.
La lógica reutilizable está en `src/eda.py`; aquí se narra la interpretación de negocio.
"""))

cells.append(code("""\
import sys, os
sys.path.insert(0, os.path.abspath(".."))

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from IPython.display import display

%matplotlib inline
plt.rcParams["figure.dpi"] = 110
"""))

cells.append(code("""\
from src.eda import run_eda
stats, G, acc, txn, fraud_ids = run_eda(config_path="../config/config.yaml")
"""))

cells.append(md("""---
## 1. Estadísticas del grafo

El grafo transaccional de BRS (escala 0.01) tiene:
- **1 500 nodos** (cuentas bancarias)
- **8 030 aristas** (transacciones)
- **Densidad 0.0036** — grafo muy disperso, típico de redes financieras reales
- **1 componente débilmente conexa** — todos los nodos están interconectados
- **17 componentes fuertemente conexas** — los ciclos de lavado detectables
"""))

cells.append(code("""\
print(f"Nodos: {stats['n_nodes']:,}")
print(f"Aristas: {stats['n_edges']:,}")
print(f"Densidad: {stats['density']:.6f}")
print(f"Componentes débiles: {stats['weakly_connected_components']}")
print(f"Componentes fuertes: {stats['strongly_connected_components']}")
print(f"% en componente mayor: {stats['pct_in_largest_wcc']:.1f}%")
print()
print(f"Nodos fraude: {stats['fraud_nodes']} ({stats['pct_fraud_nodes']:.2f}%)")
print(f"Aristas fraude: {stats['fraud_edges']} ({stats['pct_fraud_edges']:.2f}%)")
"""))

cells.append(md("""---
## 2. Distribución de grado in/out — Fraude vs. Legítimo

Las cuentas fraudulentas tienen **1.36x más out-degree** que las legítimas (7.24 vs. 5.32).
El patrón es simétrico (in ≈ out), fingerprint del comportamiento de *router* o *mula*.
"""))

cells.append(code("""\
img = mpimg.imread("../reports/figures/01_degree_distribution.png")
fig, ax = plt.subplots(figsize=(12, 4))
ax.imshow(img); ax.axis("off")
plt.tight_layout(); plt.show()

print(f"In-degree  — fraude: {stats['mean_in_deg_fraud']:.2f}  legítimo: {stats['mean_in_deg_legit']:.2f}  ratio: {stats['ratio_in_deg']:.2f}x")
print(f"Out-degree — fraude: {stats['mean_out_deg_fraud']:.2f}  legítimo: {stats['mean_out_deg_legit']:.2f}  ratio: {stats['ratio_out_deg']:.2f}x")
"""))

cells.append(md("""---
## 3. Distribución de montos — Fraude vs. Legítimo

La mediana de montos en transacciones fraudulentas es **13.7x mayor** que en legítimas.
⚠️ Pero dentro de un anillo, el monto se va reduciendo salto a salto — los saltos intermedios
se camuflan entre el tráfico cotidiano.
"""))

cells.append(code("""\
img = mpimg.imread("../reports/figures/02_amount_distribution.png")
fig, ax = plt.subplots(figsize=(12, 4))
ax.imshow(img); ax.axis("off")
plt.tight_layout(); plt.show()

print(f"Mediana monto fraude:   ${stats['median_amount_fraud']:>10,.2f}")
print(f"Mediana monto legítimo: ${stats['median_amount_legit']:>10,.2f}")
print(f"Ratio: {stats['ratio_median_amount']:.1f}x")
"""))

cells.append(md("""---
## 4. Homofilia — ¿Justifica el GNN?

**Resultado clave:** lift fraude→fraude = **14.3x**.
Los vecinos de nodos fraudulentos son 14x más propensos a ser fraudulentos que el azar.
Este resultado **justifica cuantitativamente** el uso de un GNN sobre baselines tabulares.
"""))

cells.append(code("""\
img = mpimg.imread("../reports/figures/03_homophily.png")
fig, ax = plt.subplots(figsize=(8, 5))
ax.imshow(img); ax.axis("off")
plt.tight_layout(); plt.show()

print(f"Fraude→fraude observado: {stats['observed_ff_pct']:.3f}%")
print(f"Fraude→fraude esperado:  {stats['expected_ff_pct']:.3f}%")
print(f"Lift F-F: {stats['ff_lift']:.1f}x")
print(f"Coeficiente de homofilia h: {stats['homophily_h']:.4f}")
"""))

cells.append(md("""---
## 5. Risk Score Externo — ¿Es útil para detectar lavado?

Cohen d = **0.055** — el risk score crediticio es prácticamente ciego al lavado de dinero.
Las cuentas mula son crediticiamente "normales" — el problema es de red, no de perfil.
"""))

cells.append(code("""\
img = mpimg.imread("../reports/figures/04_risk_score.png")
fig, ax = plt.subplots(figsize=(8, 4))
ax.imshow(img); ax.axis("off")
plt.tight_layout(); plt.show()

print(f"Media risk_score fraude:   {stats['mean_risk_score_fraud']:.4f}")
print(f"Media risk_score legítimo: {stats['mean_risk_score_legit']:.4f}")
print(f"Cohen d: {stats['effect_size_risk_score']:.3f}  → separación prácticamente nula")
"""))

cells.append(md("""---
## 6. Patrones Temporales

El fraude muestra un pico a las **20:00 h** y los **jueves** — fuera del horario de revisión manual.
Los anillos de 72 h se completan antes de la apertura del día siguiente.
"""))

cells.append(code("""\
img = mpimg.imread("../reports/figures/05_temporal.png")
fig, ax = plt.subplots(figsize=(12, 4))
ax.imshow(img); ax.axis("off")
plt.tight_layout(); plt.show()

print(f"Hora pico fraude: {stats['fraud_peak_hour']:02d}:00 h")
print(f"Día pico fraude:  {stats['fraud_peak_weekday']}")
"""))

cells.append(md("""---
## 7. Visualización de Anillos de Lavado

Se detectaron **3 anillos cíclicos** en el subgrafo de fraude (7, 3 y 7 saltos).
Cada anillo muestra el ciclo completo de lavado: entry → hops → fan-out exit.
"""))

cells.append(code("""\
img = mpimg.imread("../reports/figures/06_fraud_rings.png")
fig, ax = plt.subplots(figsize=(14, 5))
ax.imshow(img); ax.axis("off")
plt.tight_layout(); plt.show()

print(f"Anillos detectados: {stats['n_rings_detected']}")
print(f"Longitudes: {stats['ring_lengths']}")
print(f"Longitud promedio: {stats['avg_ring_length']:.1f} saltos")
"""))

cells.append(md("""---
## 8. Fraude por Tipo de Cuenta

La prevalencia es uniforme (~1.8-2.0%) en personal, business y merchant.
No hay tipo de cuenta sobre-representado → filtrar por tipo no aporta.
"""))

cells.append(code("""\
img = mpimg.imread("../reports/figures/07_account_type_fraud.png")
fig, ax = plt.subplots(figsize=(7, 4))
ax.imshow(img); ax.axis("off")
plt.tight_layout(); plt.show()

for tipo, pct in stats["fraud_pct_by_type"].items():
    print(f"  {tipo:<12}: {pct:.2f}%")
"""))

cells.append(md("""---
## Resumen de hallazgos clave

| # | Hallazgo | Métrica |
|---|---|---|
| 1 | Montos fraude >> legítimo, pero se camuflan en saltos intermedios | Ratio mediana 13.7x |
| 2 | Risk score externo inútil para AML | Cohen d = 0.055 |
| 3 | Homofilia fraude muy alta | Lift F-F = 14.3x |
| 4 | Grafo completamente conectado | 1 WCC, 17 SCC |
| 5 | Cuentas mula: grado simétrico in ≈ out | Out-degree ratio 1.36x |
| 6 | Fraude uniforme por tipo de cuenta | 1.8-2.0% en todos |
| 7 | Anillos operan en ventanas de 72 h | 3 anillos detectados |
| 8 | Pico temporal fuera de horario bancario | 20:00 h, jueves |

👉 Ver `reports/insights.md` para la narrativa completa con implicancias y acciones para BRS.

**Siguiente fase:** Baselines tabulares (LogReg + XGBoost) → `notebooks/02_baseline.ipynb`
"""))

# ── assemble ──────────────────────────────────────────────────────────────────

nb.cells = cells

out_path = "../notebooks/01_eda.ipynb"
with open(out_path, "w") as f:
    nbf.write(nb, f)

print(f"Notebook creado: {out_path}")
