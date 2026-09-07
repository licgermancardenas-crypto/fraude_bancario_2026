"""
Calibración del score del GNN para la capa de servicio.

POR QUÉ EXISTE. El modelo entrena con cross-entropy pesada (32x a favor de la
clase fraude, que es el desbalance del padrón). Eso corre la frontera de decisión
hacia los extremos y satura el softmax: **el 51% de las cuentas de fraude del
TEST sale con probabilidad >= 0,9999**, y las 80 cuentas de la cola de casos
salían todas con 1,0000 exacto. La cola no podía priorizar y el legajo publicaba
una certeza que el modelo no tiene.

No es memorización: el train satura al 53% y el test al 51%, casi lo mismo. Es
calibración.

QUÉ HACE. Dos salidas, para dos usos distintos, porque una sola no sirve:

  probabilidad calibrada  →  lo que se MUESTRA. Isotónica ajustada sobre el
      split de VALIDACIÓN (que el modelo no vio para entrenar) contra el margen
      de logits. El Brier en test pasa de 0,01872 a 0,00496. El 1,0000 se
      convierte en 0,9950, que es la precisión real de ese grupo.

  margen de logits        →  con lo que se ORDENA. `logit_fraude - logit_legítimo`
      no está acotado y no lo aplasta el float32: donde la probabilidad deja 196
      valores distintos entre 1.220 cuentas saturadas, el margen deja 1.204. Su
      PR-AUC (0,9435) es incluso marginalmente mejor que el de la probabilidad
      cruda (0,9431), justamente porque no pierde resolución al redondear.

Por qué NO se ordena por la probabilidad calibrada: la isotónica es una función
escalonada y empata a propósito los tramos que no puede distinguir, así que
ordenar por ella pierde ranking (PR-AUC 0,9248). Calibrar sirve para decir
*cuánta* certeza hay, no para decidir *quién va primero*.

SALVEDAD DECLARADA. El calibrador se ajusta sobre validación y se aplica a todo
el padrón, incluidos los nodos de entrenamiento. Es defendible acá porque la
saturación de train y test es casi idéntica (53% contra 51%), pero sobre datos
reales conviene rehacer la medición: si el modelo memoriza más, el calibrador va
a subestimar la confianza de los nodos vistos en entrenamiento.

Las métricas del informe (PR-AUC, recall@P90) NO se recalculan sobre el score
calibrado: se siguen reportando sobre el score crudo, que es lo comparable entre
modelos. Esto es una capa de servicio, no un cambio de modelo.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
import yaml
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, brier_score_loss

from src.models.graphsage import GraphSAGE

CALIBRATOR_PATH = "models/calibrator.pkl"


def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def model_outputs(data, ckpt_path="models/graphsage_best.pt"):
    """Devuelve (probabilidad cruda, margen de logits) para todo el padrón."""
    ck = torch.load(ckpt_path, weights_only=False)
    model = GraphSAGE(data.num_node_features, **{
        k: ck["config"][k] for k in ["hidden_channels", "num_layers", "dropout"]
    })
    model.load_state_dict(ck["model_state"])
    model.eval()
    with torch.no_grad():
        logits = model(data.x, data.edge_index)
    prob = F.softmax(logits, dim=1)[:, 1].numpy().astype(np.float64)
    margin = (logits[:, 1] - logits[:, 0]).numpy().astype(np.float64)
    return prob, margin


def expected_calibration_error(y, p, n_bins=15):
    """ECE con bins de igual ancho: |confianza media − exactitud| ponderado."""
    edges = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, n_bins - 1)
    ece = 0.0
    for b in range(n_bins):
        m = idx == b
        if m.sum():
            ece += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(ece)


def reliability_curve(y, p, n_bins=10):
    """Puntos (confianza media, frecuencia observada, n) para el diagrama."""
    edges = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, n_bins - 1)
    out = []
    for b in range(n_bins):
        m = idx == b
        if m.sum():
            out.append({"bin": b, "confianza": float(p[m].mean()),
                        "observado": float(y[m].mean()), "n": int(m.sum())})
    return out


def fit(config_path="config/config.yaml"):
    cfg = load_config(config_path)
    proc = cfg["data"]["processed_dir"]
    data = torch.load(f"{proc}/graph.pt", weights_only=False)

    prob, margin = model_outputs(data)
    y = data.y.numpy()
    val = data.val_mask.numpy()
    test = data.test_mask.numpy()

    # El calibrador se ajusta contra el MARGEN, no contra la probabilidad: sobre
    # la probabilidad saturada la isotónica no tiene sobre qué discriminar.
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(margin[val], y[val])
    cal = iso.predict(margin)

    metrics = {
        "n_val": int(val.sum()),
        "n_test": int(test.sum()),
        "brier_raw": float(brier_score_loss(y[test], prob[test])),
        "brier_calibrated": float(brier_score_loss(y[test], cal[test])),
        "ece_raw": expected_calibration_error(y[test], prob[test]),
        "ece_calibrated": expected_calibration_error(y[test], cal[test]),
        "pr_auc_raw": float(average_precision_score(y[test], prob[test])),
        "pr_auc_calibrated": float(average_precision_score(y[test], cal[test])),
        "pr_auc_margin": float(average_precision_score(y[test], margin[test])),
        "pct_saturated_raw": float((prob[test & (y == 1)] >= 0.9999).mean()),
        "distinct_raw_top1000": int(len(np.unique(prob[np.argsort(-margin)[:1000]].round(6)))),
        "distinct_margin_top1000": int(len(np.unique(margin[np.argsort(-margin)[:1000]].round(3)))),
        "reliability_raw": reliability_curve(y[test], prob[test]),
        "reliability_calibrated": reliability_curve(y[test], cal[test]),
    }

    Path(CALIBRATOR_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CALIBRATOR_PATH, "wb") as f:
        pickle.dump(iso, f)

    out = Path(cfg["paths"]["reports_dir"]) / "calibration.json"
    out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("=" * 55)
    print("  Calibración del score GNN")
    print("=" * 55)
    print(f"  Brier (test):  crudo {metrics['brier_raw']:.5f}  →  "
          f"calibrado {metrics['brier_calibrated']:.5f}  "
          f"({metrics['brier_raw'] / metrics['brier_calibrated']:.1f}x mejor)")
    print(f"  ECE   (test):  crudo {metrics['ece_raw']:.5f}  →  "
          f"calibrado {metrics['ece_calibrated']:.5f}")
    print(f"  PR-AUC:        crudo {metrics['pr_auc_raw']:.4f} · "
          f"margen {metrics['pr_auc_margin']:.4f} · "
          f"calibrado {metrics['pr_auc_calibrated']:.4f}")
    print(f"  Fraude de test saturado (>=0,9999): {metrics['pct_saturated_raw']:.1%}")
    print(f"  Resolución en el top-1000 — probabilidad: "
          f"{metrics['distinct_raw_top1000']} valores distintos · "
          f"margen: {metrics['distinct_margin_top1000']}")
    print(f"\n  → {CALIBRATOR_PATH}")
    print(f"  → {out}")
    print("=" * 55)
    return iso, metrics


def load_calibrator(path=CALIBRATOR_PATH):
    """Devuelve el calibrador ajustado, o None si todavía no se corrió `fit`."""
    p = Path(path)
    if not p.exists():
        return None
    with open(p, "rb") as f:
        return pickle.load(f)


if __name__ == "__main__":
    fit()
