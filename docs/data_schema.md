# Esquema del Dataset — fraude_bancario_2026

**Generado por:** `src/generate.py`  
**Parámetros:** `scale=0.5`, `seed=42`, `time_window_days=365`, `monetary.scale=100`  
**Fecha de generación:** 2026-09-04

---

## Resumen estadístico

| Archivo | Filas | Columnas | Fraude |
|---|---|---|---|
| `data/raw/accounts.csv` | 75 000 | 7 | 2 255 nodos (3.01%) |
| `data/raw/transactions/` | 11 240 742 | 11 | 52 604 aristas (0.47%) |

**Nota de desbalance:** El desbalance (~3% nodos, ~0.5% aristas) es el esperado en fraude financiero. Las métricas de accuracy son inútiles en este contexto — PR-AUC y recall@precision=0.90 son las métricas operativas del proyecto.

**Densidad transaccional:** ~300 movimientos por cuenta y por año (mediana 221), dentro del rango minorista real de 200-600, con **7,40 transacciones por arista** sobre 1 518 706 pares distintos. Los comercios son los nodos más densos (mediana 872 movimientos), que es lo que ocurre en un banco real: concentran el fan-in de las compras de todos los demás. Un 6% de las cuentas no registra movimiento en el período — cuentas durmientes, necesarias para que la regla de reactivación (R04) tenga sobre qué disparar y para que estar quieta no delate por sí sola a las cuentas de fraude.

---

## accounts.csv — Nodos del grafo

Cada fila representa una cuenta bancaria.

| Columna | Tipo | Descripción | Rango / Valores |
|---|---|---|---|
| `account_id` | string | Identificador único de cuenta | `ACC0000000` … `ACC0001499` |
| `balance` | float64 | Saldo de la cuenta (ARS) | $67 … $1.484.276.972 (mediana $178.684) |
| `risk_score` | float64 | Score de riesgo crediticio externo | 0.0015 … 0.7086 (media 0.197) |
| `account_type` | string | Tipo de cuenta | `personal` (70.6%), `business` (18.8%), `merchant` (10.6%) |
| `opened_days_ago` | int64 | Antigüedad de la cuenta en días | 31 … 3 649 (media 1 808) |
| `is_fraud` | int64 | **Label supervisado** — ¿cuenta involucrada en fraude? | 0 (legítima) / 1 (fraudulenta) |

### Patrones de fraude en cuentas
- **Anillos de lavado (cyclic rings):** cuentas en ciclos de 4-7 saltos donde el dinero circula antes de salir. Tienden a tener grado in ≈ grado out.
- **Pitufeo (structuring):** cuentas "mula" con alto grado de entrada (reciben de source) y alta salida (envían al colector). El source y el collector también son fraud nodes.

---

## transactions/ — Aristas del grafo

Cada fila representa una transacción entre dos cuentas. El grafo es **dirigido** (src → dst).

El libro **no** es un CSV: es un almacén columnar, un `.npy` por columna, leído por
`src/txn_store.py`. A 11,2M de filas el CSV con strings costaba 786 bytes por fila
(~8,8 GB en pandas, imposible en la máquina de trabajo); el almacén cuesta **29 bytes
por fila** — 327 MB en disco — y permite cargar sólo las columnas que cada módulo usa.

| Columna | Tipo | Descripción | Rango / Valores |
|---|---|---|---|
| `src` | categórica | Cuenta origen | FK → `accounts.account_id` |
| `dst` | categórica | Cuenta destino | FK → `accounts.account_id` |
| `amount` | float32 | Monto transferido (ARS) | $165 … $103.945.768 (mediana $44.021) |
| `timestamp` | int32 | Unix timestamp de la transacción | 2023-11-14 … 2024-11-24 (~1 año) |
| `transaction_type` | categórica | Tipo de transacción | `payment` (69.6%), `transfer` (21.8%), `withdrawal` (8.7%) |
| `is_fraud` | int8 | **Label supervisado** — ¿transacción fraudulenta? | 0 (legítima) / 1 (fraudulenta) |
| `canal` | categórica | Canal de la operación | CBU, CVU/alias, POS, VEP, QR, ATM, … (11 valores) |
| `mcc` | categórica | Código de rubro del comercio | 14 valores; vacío fuera de los pagos a comercio/empresa |
| `estado` | categórica | Estado de liquidación | `liquidada` (96.5%), `pendiente`, `reversada` |
| `comision` | float32 | Comisión cobrada (ARS) | 0 salvo extracciones por cajero |
| `impuesto` | float32 | Impuesto Ley 25.413 (0,6%) | 0 en las operaciones no alcanzadas |

### Columnas derivadas (no almacenadas)

`transaction_id`, `canal_codigo`, `cbu_dst`, `alias_dst`, `rubro`, `glosa`, `moneda` y
`referencia` son función determinística de las anteriores y las reconstruye
`txn_store.hydrate()` sobre el subconjunto que se vaya a mostrar. Almacenarlas costaba
~700 MB de strings por columna para que sólo las usaran las capas de presentación, que
muestrean unos pocos miles de filas.

### Distribución de montos
- Transacciones legítimas: mediana $43.710, mezcla de compras (~$27.000), servicios
  (~$36.500), transferencias entre pares (~$49.300), nómina (~$733.000) y pagos a
  proveedores (~$491.000). El monto típico se sortea **por vínculo**: comprar siempre en
  el mismo supermercado da tickets parecidos, no independientes.
- Transacciones fraudulentas: mediana $684.352 (P05 $166.668 – P95 $6.680.416); el monto
  inicial se va reduciendo en cada salto del anillo (~85-98% del monto anterior)

> **Escala monetaria.** El generador emite montos en una unidad sintética y
> `config.yaml::monetary.scale` los lleva a pesos argentinos de 2026. Los umbrales del
> motor de reglas están en la misma escala y se anotan en SMVM para ser auditables
> contra la Res. UIF 78/2025. Ver la sección "Escala monetaria y anclaje regulatorio"
> del README. La limitación de densidad transaccional que declaraba la versión anterior
> quedó saldada: ver "Densidad transaccional" arriba.

---

## Sorpresas / Decisiones de diseño

1. **Label dual (nodo y arista):** el label está presente tanto en accounts (`is_fraud`) como en transactions (`is_fraud`). El GNN usa el label a nivel **nodo**; el label de arista queda disponible para análisis exploratorio y para modelos futuros (edge classification).

2. **Grafo dirigido:** las transacciones tienen dirección (src → dst). En la Fase E, al construir el objeto PyG se decide si se aplica `ToUndirected()` o se trabajan aristas inversas explícitas — decisión documentada en `src/build_graph.py`.

3. **Timestamps Unix:** almacenados como int64. Se convierten a features de ciclo temporal en `src/features.py` (hora del día, día de semana) para capturar patrones temporales de lavado.

4. **Fraud rate bajo (0.6% aristas):** consistente con fraude real. El desbalance domina cualquier decisión de modelado — `class_weight='balanced'` en baselines, `scale_pos_weight` en XGBoost, CrossEntropy con pesos en GNN.

5. **Cuentas con `risk_score` bajo pueden ser fraud nodes:** el risk score externo (crediticio) no detecta lavado estructurado — ese es exactamente el problema que el GNN resuelve.

6. **Contrapartes recurrentes, no pares al azar:** la capa legítima la construye `src/economy.py` dando a cada cuenta un círculo estable de contrapartes (el supermercado de siempre, el empleador, cuatro servicios con débito automático, un puñado de pares) con el que opera repetidamente durante el año. La versión anterior sorteaba `src` y `dst` uniformemente sobre el padrón, lo que producía un grafo aleatorio de Erdős–Rényi: 1,09 transacciones por arista y el 93% de las aristas de un solo uso. La consecuencia medible era que `unique_counterparts / degree` daba 0,913 en las legítimas contra 0,980 en las de fraude — la concentración de contrapartes, una de las señales más fuertes que usa un sistema ALD real, no distinguía nada. Densificar subiendo el total de transacciones sobre el sorteo uniforme lo habría empeorado.

7. **Aristas paralelas agregadas en el grafo:** `build_graph` colapsa las 11,2M de transacciones a **1,52M de aristas únicas** por par (src, dst), y la intensidad de la relación pasa a `edge_attr` = [cantidad, monto total, monto medio]. Dos razones: el paso de mensajes no gana repitiendo el mismo vecino —con agregación media, un supermercado visitado 40 veces pesaría 40 veces más que la contraparte de una sola operación, que es la que interesa en lavado— y 11,2M de aristas dirigidas se vuelven 22,5M al aplicar `ToUndirected()`, tamaño al que los mensajes intermedios no entran en memoria. Las features de nodo se siguen calculando sobre el stream completo, no sobre el grafo agregado.

8. **Las cuentas de fraude tienen vida legítima normal:** participan de la economía minorista con la misma distribución de actividad que las legítimas de su tipo. Si tuvieran sistemáticamente menos actividad lícita, "moverse poco" sería una fuga que el modelo aprendería en lugar de aprender la estructura del lavado. Las dos excepciones son las tipologías cuya definición *es* la inactividad — `cuenta_durmiente` (nivel durmiente) y `red_mulas` (nivel bajo, cuentas recién abiertas y descartables) — y no son fuga porque el 22% de las cuentas legítimas vive en esos mismos dos niveles.
