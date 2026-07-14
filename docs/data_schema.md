# Esquema del Dataset — fraude_bancario_2026

**Generado por:** `src/generate.py`  
**Parámetros:** `scale=0.01`, `seed=42`  
**Fecha de generación:** 2026-07-14

---

## Resumen estadístico

| Archivo | Filas | Columnas | Fraude |
|---|---|---|---|
| `data/raw/accounts.csv` | 1 500 | 6 | 29 nodos (1.93%) |
| `data/raw/transactions.csv` | 8 050 | 7 | 50 aristas (0.62%) |

**Nota de desbalance:** El desbalance real (~1.9% nodos, ~0.6% aristas) es el esperado en fraude financiero. Las métricas de accuracy son inútiles en este contexto — PR-AUC y recall@precision=0.90 son las métricas operativas del proyecto.

---

## accounts.csv — Nodos del grafo

Cada fila representa una cuenta bancaria.

| Columna | Tipo | Descripción | Rango / Valores |
|---|---|---|---|
| `account_id` | string | Identificador único de cuenta | `ACC0000000` … `ACC0001499` |
| `balance` | float64 | Saldo de la cuenta (USD) | $2.54 … $552 349 (mediana $1 819) |
| `risk_score` | float64 | Score de riesgo crediticio externo | 0.0015 … 0.7086 (media 0.197) |
| `account_type` | string | Tipo de cuenta | `personal` (70.6%), `business` (18.8%), `merchant` (10.6%) |
| `opened_days_ago` | int64 | Antigüedad de la cuenta en días | 31 … 3 649 (media 1 808) |
| `is_fraud` | int64 | **Label supervisado** — ¿cuenta involucrada en fraude? | 0 (legítima) / 1 (fraudulenta) |

### Patrones de fraude en cuentas
- **Anillos de lavado (cyclic rings):** cuentas en ciclos de 4-7 saltos donde el dinero circula antes de salir. Tienden a tener grado in ≈ grado out.
- **Pitufeo (structuring):** cuentas "mula" con alto grado de entrada (reciben de source) y alta salida (envían al colector). El source y el collector también son fraud nodes.

---

## transactions.csv — Aristas del grafo

Cada fila representa una transacción entre dos cuentas. El grafo es **dirigido** (src → dst).

| Columna | Tipo | Descripción | Rango / Valores |
|---|---|---|---|
| `transaction_id` | string | Identificador único de transacción | `TXN000000000` … |
| `src` | string | Cuenta origen | FK → `accounts.account_id` |
| `dst` | string | Cuenta destino | FK → `accounts.account_id` |
| `amount` | float64 | Monto transferido (USD) | $0.53 … $48 411 (mediana $95.79) |
| `timestamp` | int64 | Unix timestamp de la transacción | 2023-11-14 … 2024-11-13 (~1 año) |
| `transaction_type` | string | Tipo de transacción | `transfer` (50%), `payment` (35%), `withdrawal` (15%) |
| `is_fraud` | int64 | **Label supervisado** — ¿transacción fraudulenta? | 0 (legítima) / 1 (fraudulenta) |

### Distribución de montos
- Transacciones legítimas: lognormal, mediana ~$90 (variedad cotidiana)
- Transacciones fraudulentas: montos iniciales $5 000–$50 000 que se van reduciendo en cada salto del anillo (~85-98% del monto anterior)

---

## Sorpresas / Decisiones de diseño

1. **Label dual (nodo y arista):** el label está presente tanto en accounts (`is_fraud`) como en transactions (`is_fraud`). El GNN usa el label a nivel **nodo**; el label de arista queda disponible para análisis exploratorio y para modelos futuros (edge classification).

2. **Grafo dirigido:** las transacciones tienen dirección (src → dst). En la Fase E, al construir el objeto PyG se decide si se aplica `ToUndirected()` o se trabajan aristas inversas explícitas — decisión documentada en `src/build_graph.py`.

3. **Timestamps Unix:** almacenados como int64. Se convierten a features de ciclo temporal en `src/features.py` (hora del día, día de semana) para capturar patrones temporales de lavado.

4. **Fraud rate bajo (0.6% aristas):** consistente con fraude real. El desbalance domina cualquier decisión de modelado — `class_weight='balanced'` en baselines, `scale_pos_weight` en XGBoost, CrossEntropy con pesos en GNN.

5. **Cuentas con `risk_score` bajo pueden ser fraud nodes:** el risk score externo (crediticio) no detecta lavado estructurado — ese es exactamente el problema que el GNN resuelve.
