"""Tests de la métrica operativa recall@precision."""
from src.evaluate import recall_at_precision


def test_separable_reaches_full_recall():
    y = [0, 0, 1, 1]
    s = [0.1, 0.2, 0.8, 0.9]
    rec, thr = recall_at_precision(y, s, 0.90)
    assert rec == 1.0
    assert thr is not None


def test_recall_in_unit_range():
    y = [0, 1, 0, 1, 0, 1]
    s = [0.50, 0.40, 0.60, 0.55, 0.45, 0.70]
    rec, _ = recall_at_precision(y, s, 0.90)
    assert 0.0 <= rec <= 1.0


def test_impossible_precision_returns_zero():
    y = [0, 1]
    s = [0.9, 0.1]  # el modelo ordena al revés → no alcanza alta precisión
    rec, thr = recall_at_precision(y, s, 0.99)
    assert rec == 0.0
