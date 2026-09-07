"""
Almacén columnar compacto para el libro de transacciones.

MOTIVO. La densificación transaccional lleva el dataset de 544K a ~10M filas.
En el formato anterior (CSV con strings) cada fila costaba 786 bytes en pandas
— 428 MB para 544K —, de los cuales el 54% eran strings de cardinalidad ≤19
almacenados como objetos. A 10M filas eso serían ~7 GB, imposible en la máquina
de trabajo (5,2 GB de RAM total).

DISEÑO. Un directorio con un .npy por columna, todas de ancho fijo:

    data/raw/transactions/
        _meta.json    catálogos de categorías + padrón de cuentas + n_filas
        src.npy       int32   índice en el padrón de cuentas
        dst.npy       int32
        amount.npy    float32
        timestamp.npy int32
        ...

Son 29 bytes por fila en vez de 786 — 27× menos —, y como cada columna es un
archivo aparte, `load_transactions(columns=[...])` sólo toca lo que se pide y
`mmap=True` evita cargarla siquiera. Los motores de reglas y el grafo usan seis
columnas; la metadata de presentación sólo la tocan los exports, que muestrean
antes.

Se eligió .npy sobre Parquet porque pyarrow no está instalado y agregarlo
obligaría a instalarlo también en el job de CI para nada: todas las columnas son
numéricas de ancho fijo, que es exactamente lo que .npy hace bien.

COLUMNAS DERIVADAS. transaction_id, cbu_dst, alias_dst, referencia, canal_codigo,
rubro, glosa y moneda NO se almacenan: son función determinística de las que sí,
y a 10M filas costaban ~700 MB cada una. `hydrate()` las reconstruye sobre el
subconjunto que el llamador vaya a mostrar.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

# ── esquema ──────────────────────────────────────────────────────────────────

CORE_COLS = ("src", "dst", "amount", "timestamp", "transaction_type", "is_fraud")
META_COLS = ("canal", "mcc", "estado", "comision", "impuesto")
ALL_COLS = CORE_COLS + META_COLS

# columnas categóricas: se guardan como códigos int8 contra un catálogo en _meta
CAT_COLS = ("transaction_type", "canal", "mcc", "estado")

_DTYPES = {
    "src": np.int32, "dst": np.int32,
    "amount": np.float32, "comision": np.float32, "impuesto": np.float32,
    "timestamp": np.int32,
    "is_fraud": np.int8,
    "transaction_type": np.int8, "canal": np.int8, "mcc": np.int8, "estado": np.int8,
}

STORE_DIRNAME = "transactions"


def store_path(raw_dir: str | Path) -> Path:
    return Path(raw_dir) / STORE_DIRNAME


def exists(raw_dir: str | Path) -> bool:
    return (store_path(raw_dir) / "_meta.json").exists()


# ── escritura ────────────────────────────────────────────────────────────────

def save_transactions(txns: pd.DataFrame, raw_dir: str | Path,
                      account_ids: list[str]) -> Path:
    """
    Persiste el libro en el almacén columnar.

    `txns` llega con src/dst como account_id (str o categórica) y las columnas
    categóricas como texto; acá se codifican contra el padrón y los catálogos.
    """
    out = store_path(raw_dir)
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("*.npy"):
        stale.unlink()

    n = len(txns)
    acc_index = pd.Index(account_ids)
    meta: dict = {"n_rows": n, "account_ids": list(account_ids), "categories": {}}

    for col in ("src", "dst"):
        values = txns[col]
        if pd.api.types.is_integer_dtype(values):
            # ya vienen como índice posicional: el generador nunca materializa
            # los account_id fila por fila, que a 10M filas costaría ~800 MB
            codes = np.asarray(values, dtype=np.int64)
            if codes.min() < 0 or codes.max() >= len(acc_index):
                raise ValueError(f"{col}: índices fuera del padrón")
        else:
            codes = acc_index.get_indexer(pd.Index(np.asarray(values, dtype=object)))
            if (codes < 0).any():
                raise ValueError(f"{col}: {int((codes < 0).sum())} cuentas fuera del padrón")
        np.save(out / f"{col}.npy", codes.astype(np.int32))

    for col in CAT_COLS:
        values = pd.Series(txns[col]).fillna("").astype(str)
        cats = sorted(values.unique())
        if len(cats) > 127:
            raise ValueError(f"{col}: {len(cats)} categorías, no entra en int8")
        lookup = {c: i for i, c in enumerate(cats)}
        np.save(out / f"{col}.npy", values.map(lookup).to_numpy(dtype=np.int8))
        meta["categories"][col] = cats

    for col in ("amount", "comision", "impuesto", "timestamp", "is_fraud"):
        np.save(out / f"{col}.npy", np.asarray(txns[col], dtype=_DTYPES[col]))

    (out / "_meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return out


# ── lectura ──────────────────────────────────────────────────────────────────

def load_meta(raw_dir: str | Path) -> dict:
    return json.loads((store_path(raw_dir) / "_meta.json").read_text(encoding="utf-8"))


def load_transactions(raw_dir: str | Path, columns=None, mmap: bool = False,
                      rows: np.ndarray | None = None,
                      with_row_id: bool = False) -> pd.DataFrame:
    """
    Carga el libro. `columns=None` trae todo el esquema almacenado.

    src/dst vuelven como Categorical de account_id: 4 bytes por fila más un
    diccionario de 75K entradas, en vez de ~40 bytes por fila en texto. Se
    comportan como strings para .map() y comparaciones; para groupby hace falta
    observed=True (pandas expandiría el producto cartesiano de categorías).

    `rows` toma un subconjunto por posición sin materializar el resto — útil
    para las capas de presentación, que muestrean unos miles de filas.

    `with_row_id` agrega `transaction_id` como la POSICIÓN entera de la fila. El
    identificador visible (TXN000000123) es función de esa posición y lo arma
    hydrate(); materializarlo acá costaría ~800 MB de strings para que los
    motores de reglas lo usen sólo como clave de la evidencia.
    """
    src_dir = store_path(raw_dir)
    if not (src_dir / "_meta.json").exists():
        raise FileNotFoundError(
            f"No hay almacén columnar en {src_dir}. Correr `python -m src.generate`."
        )
    meta = load_meta(raw_dir)
    cols = list(columns) if columns is not None else list(ALL_COLS)
    mm = "r" if mmap else None
    acc_ids = pd.Index(meta["account_ids"])

    data = {}
    for col in cols:
        arr = np.load(src_dir / f"{col}.npy", mmap_mode=mm)
        if rows is not None:
            arr = np.asarray(arr[rows])
        if col in ("src", "dst"):
            data[col] = pd.Categorical.from_codes(np.asarray(arr), categories=acc_ids)
        elif col in CAT_COLS:
            data[col] = pd.Categorical.from_codes(
                np.asarray(arr), categories=meta["categories"][col]
            )
        else:
            data[col] = np.asarray(arr)
    df = pd.DataFrame(data)
    if with_row_id:
        df["transaction_id"] = (np.asarray(rows, dtype=np.int32) if rows is not None
                                else np.arange(len(df), dtype=np.int32))
    return df


def n_rows(raw_dir: str | Path) -> int:
    return int(load_meta(raw_dir)["n_rows"])


# ── vocabulario de presentación ──────────────────────────────────────────────
# Vive acá y no en generate.py porque lo necesitan los dos lados: el generador
# para ASIGNAR canal/mcc, y hydrate() para DERIVAR código, rubro y glosa.

CANAL_COD = {
    "Transferencia inmediata (CBU)": "TRA-CBU", "Transferencia (CVU/alias)": "TRA-CVU",
    "Home Banking": "HB", "DEBIN": "DEBIN",
    "Pago con tarjeta de débito (POS)": "POS", "Pago electrónico (VEP)": "VEP",
    "Débito automático": "DEB-AUT", "Billetera virtual (QR)": "QR",
    "Cajero automático (ATM)": "ATM", "Ventanilla / caja": "CAJA",
    "Extracción en comercio": "EXT-COM",
}
MCC_MERCHANT = [("5411", "Supermercados y almacenes"), ("5812", "Restaurantes y bares"),
                ("5912", "Farmacias"), ("5541", "Estaciones de servicio"),
                ("5651", "Indumentaria y calzado"), ("5732", "Electrónica y tecnología"),
                ("5999", "Comercio minorista varios"), ("5814", "Comidas rápidas")]
MCC_BUSINESS = [("7372", "Servicios informáticos"), ("8931", "Servicios contables"),
                ("1520", "Construcción"), ("4214", "Transporte de cargas"),
                ("5122", "Distribución mayorista"), ("6513", "Alquiler inmobiliario")]
MCC_RUBRO = dict(MCC_MERCHANT + MCC_BUSINESS)

CBU_SEED_OFFSET = 888


@lru_cache(maxsize=4)
def _cbu_padron(n: int, seed: int) -> np.ndarray:
    digits = np.random.default_rng(seed + CBU_SEED_OFFSET).integers(0, 10, size=(n, 22))
    return np.array(["".join(map(str, row)) for row in digits], dtype=object)


def account_cbus(account_ids, seed: int = 42) -> np.ndarray:
    """CBU de 22 dígitos, estable por cuenta y reproducible desde la semilla.

    El CBU sale de la POSICIÓN en el padrón, así que el resultado depende sólo
    de cuántas cuentas hay y de la semilla — de ahí que se pueda memoizar. Sin
    la caché, armar los 75K CBUs cuesta ~0,35 s y `hydrate()` los rearmaba en
    cada llamada; el legajo de un caso hace varias decenas.
    """
    return _cbu_padron(len(account_ids), seed)


def hydrate(txns: pd.DataFrame, accounts: pd.DataFrame, seed: int = 42,
            row_ids: np.ndarray | None = None) -> pd.DataFrame:
    """
    Reconstruye las columnas de presentación derivables sobre un subconjunto.

    Pensada para las capas de export, que muestrean unos miles de filas: sobre
    el libro entero materializaría ~700 MB de strings por columna, que es
    justamente lo que el almacén evita. `row_ids` da los transaction_id cuando
    el llamador ya filtró (si falta, se usa la posición en `txns`).
    """
    out = txns.copy()
    n = len(out)
    ids = np.asarray(row_ids) if row_ids is not None else np.arange(n)
    out["transaction_id"] = [f"TXN{i:09d}" for i in ids]

    canal = out["canal"].astype(str)
    out["canal_codigo"] = canal.map(CANAL_COD).fillna("")

    acc_ids = accounts["account_id"].to_numpy()
    cbu_map = dict(zip(acc_ids, account_cbus(acc_ids, seed)))
    dst_str = out["dst"].astype(str)
    out["cbu_dst"] = dst_str.map(cbu_map)
    out["alias_dst"] = np.where(
        canal.to_numpy() == "Transferencia (CVU/alias)",
        [f"{d[-4:].lower()}.brs.ar" for d in dst_str],
        "",
    )

    mcc = out["mcc"].astype(str)
    out["rubro"] = mcc.map(MCC_RUBRO).fillna("")

    at = accounts.set_index("account_id")["account_type"]
    dst_type = dst_str.map(at).fillna("personal").to_numpy()
    ttype = out["transaction_type"].astype(str).to_numpy()
    is_pay, is_wd = ttype == "payment", ttype == "withdrawal"
    has_rubro = out["rubro"].to_numpy() != ""

    glosa = pd.Series("Transferencia entre cuentas", index=out.index)
    glosa[dst_type == "business"] = "Transferencia a proveedor"
    glosa[dst_type == "merchant"] = "Pago a comercio"
    glosa[is_pay] = "Pago de servicios"
    m_rubro = is_pay & has_rubro
    glosa[m_rubro] = "Pago - " + out["rubro"][m_rubro]
    glosa[is_wd] = "Extracción de efectivo"
    out["glosa"] = glosa.to_numpy()

    out["moneda"] = "ARS"
    ref = np.random.default_rng(seed + 999).integers(10_000_000, 99_999_999, len(ids))
    out["referencia"] = [f"REF-{r}" for r in ref]
    return out


# ── serialización ────────────────────────────────────────────────────────────

def json_default(obj):
    """
    Conversor para `json.dump(..., default=json_default)`.

    Los dtypes compactos del almacén (float32, int32, int8) llegan a las capas de
    export como escalares de numpy, que el módulo json no sabe serializar —
    float64 sí funcionaba por herencia de `float`, y por eso el problema aparece
    recién al compactar el esquema.
    """
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"No serializable a JSON: {type(obj).__name__}")
