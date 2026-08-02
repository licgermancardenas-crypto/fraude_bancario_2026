"""
Generates synthetic persona data for all 1 500 accounts and enriches
all dashboard JSONs with human-readable identity fields.

Run once after the pipeline:
    python -m src.enrich_personas

Outputs:
    data/raw/personas.csv
    dashboard/public/data/top_accounts.json   ← persona fields added
    dashboard/public/data/origin_trace.json   ← persona fields added
    dashboard/public/data/placement_candidates.json ← persona fields added
    dashboard/public/data/rings.json          ← nombre_completo added to nodes
"""

import json
import random
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ── Geographic data ───────────────────────────────────────────────────────────

PROV_DATA = [
    ("Ciudad Autónoma de Buenos Aires", 8, [
        "Palermo", "Belgrano", "Caballito", "San Telmo", "Almagro",
        "Flores", "Villa Urquiza", "Barracas", "Recoleta", "Balvanera",
        "Congreso", "Villa del Parque", "Mataderos",
    ]),
    ("Buenos Aires", 40, [
        "La Plata", "Mar del Plata", "Quilmes", "Lanús", "Lomas de Zamora",
        "Morón", "Merlo", "Berazategui", "San Martín", "Tigre",
        "Bahía Blanca", "Tandil", "Pergamino", "Junín", "Zárate",
        "Florencio Varela", "San Isidro", "Vicente López", "Avellaneda",
        "Hurlingham", "Tres de Febrero", "Almirante Brown", "Ezeiza",
        "Ituzaingó", "José C. Paz", "Malvinas Argentinas", "Ensenada",
    ]),
    ("Córdoba", 8, [
        "Córdoba Capital", "Villa Carlos Paz", "Río Cuarto", "San Francisco",
        "Villa María", "Alta Gracia", "Cosquín", "Marcos Juárez", "Bell Ville",
        "Río Tercero",
    ]),
    ("Santa Fe", 7, [
        "Rosario", "Santa Fe Capital", "Rafaela", "Venado Tuerto",
        "Santo Tomé", "Reconquista", "Villa Gobernador Gálvez", "Casilda",
        "Cañada de Gómez",
    ]),
    ("Mendoza", 4, [
        "Mendoza Capital", "San Rafael", "Godoy Cruz", "Luján de Cuyo",
        "Maipú", "Guaymallén", "Las Heras", "Tunuyán",
    ]),
    ("Tucumán", 3, [
        "San Miguel de Tucumán", "Tafí Viejo", "Yerba Buena",
        "Banda del Río Salí", "Concepción", "Aguilares",
    ]),
    ("Entre Ríos", 3, [
        "Paraná", "Concepción del Uruguay", "Gualeguaychú", "Concordia",
        "Colón", "Villaguay",
    ]),
    ("Salta", 3, [
        "Salta Capital", "Tartagal", "Orán", "Rosario de la Frontera",
        "Cafayate",
    ]),
    ("Misiones", 2, [
        "Posadas", "Oberá", "Eldorado", "Puerto Iguazú", "Apóstoles",
    ]),
    ("Chaco", 2, [
        "Resistencia", "Presidencia R. Sáenz Peña", "Villa Ángela", "Charata",
    ]),
    ("Corrientes", 2, [
        "Corrientes Capital", "Goya", "Mercedes", "Curuzú Cuatiá", "Paso de los Libres",
    ]),
    ("Santiago del Estero", 2, [
        "Santiago del Estero Capital", "La Banda", "Termas de Río Hondo",
        "Añatuya",
    ]),
    ("San Juan", 2, [
        "San Juan Capital", "Chimbas", "Rivadavia", "Caucete", "Santa Lucía",
    ]),
    ("Jujuy", 2, [
        "San Salvador de Jujuy", "Palpalá", "San Pedro de Jujuy",
        "Libertador Gral. San Martín",
    ]),
    ("Río Negro", 2, [
        "Viedma", "Bariloche", "General Roca", "Cipolletti", "Allen",
    ]),
    ("Neuquén", 2, [
        "Neuquén Capital", "Zapala", "San Martín de los Andes",
        "Centenario", "Cutral Có",
    ]),
    ("Formosa", 1, [
        "Formosa Capital", "Clorinda", "Pirané",
    ]),
    ("Chubut", 1, [
        "Rawson", "Comodoro Rivadavia", "Puerto Madryn", "Trelew", "Esquel",
    ]),
    ("San Luis", 1, [
        "San Luis Capital", "Villa Mercedes", "Merlo", "Quines",
    ]),
    ("Catamarca", 1, [
        "S.F. del Valle de Catamarca", "Andalgalá", "Belén",
    ]),
    ("La Rioja", 1, [
        "La Rioja Capital", "Chilecito", "Aimogasta",
    ]),
    ("La Pampa", 1, [
        "Santa Rosa", "General Pico", "Eduardo Castex",
    ]),
    ("Santa Cruz", 1, [
        "Río Gallegos", "Caleta Olivia", "El Calafate", "Pico Truncado",
    ]),
    ("Tierra del Fuego", 1, [
        "Ushuaia", "Río Grande", "Tolhuin",
    ]),
]

_PROV_WEIGHTS = [p[1] for p in PROV_DATA]
_PROV_NAMES   = [p[0] for p in PROV_DATA]
_PROV_CITIES  = {p[0]: p[2] for p in PROV_DATA}

# ── Identity ─────────────────────────────────────────────────────────────────

NACIONALIDADES = (
    ["Argentina"] * 93 + ["Paraguay"] * 3 + ["Bolivia"] * 2 +
    ["Uruguay"] * 1 + ["Perú"] * 1
)

NOMBRES_M = [
    "Juan", "Carlos", "Luis", "Ricardo", "Pablo", "Diego", "Fernando",
    "Sergio", "Marcelo", "Eduardo", "Gustavo", "Rodrigo", "Alejandro",
    "Martín", "Daniel", "Miguel", "Roberto", "Jorge", "Claudio", "Ramón",
    "Gabriel", "Andrés", "Néstor", "Santiago", "Matías", "Leonardo",
    "Facundo", "Maximiliano", "Ignacio", "Federico", "Sebastián",
    "Cristian", "Nicolás", "Tomás", "Agustín", "Emiliano", "Ezequiel",
    "Leandro", "Patricio", "Raúl", "Héctor", "Óscar", "Alberto", "Mario",
    "Hugo", "Walter", "Ariel", "Damián", "Esteban", "Germán",
]

NOMBRES_F = [
    "María", "Ana", "Claudia", "Silvana", "Patricia", "Andrea", "Laura",
    "Cecilia", "Verónica", "Gabriela", "Mariana", "Carolina", "Natalia",
    "Sandra", "Alejandra", "Marcela", "Vanesa", "Valeria", "Romina",
    "Florencia", "Agustina", "Pamela", "Lorena", "Mónica", "Graciela",
    "Cristina", "Beatriz", "Susana", "Liliana", "Norma", "Rosa", "Julia",
    "Silvia", "Diana", "Nora", "Jimena", "Melina", "Lucrecia", "Soledad",
    "Viviana", "Karina", "Miriam", "Estela", "Adriana", "Paola", "Gisela",
]

APELLIDOS = [
    "González", "Rodríguez", "Fernández", "López", "García", "Martínez",
    "Díaz", "Pérez", "Sánchez", "Romero", "Torres", "Ramírez", "Flores",
    "Acosta", "Medina", "Herrera", "Ruiz", "Molina", "Castro", "Ortiz",
    "Vargas", "Gutiérrez", "Morales", "Delgado", "Vázquez", "Ríos",
    "Álvarez", "Gómez", "Benítez", "Cabrera", "Ramos", "Suárez", "Cruz",
    "Reyes", "Méndez", "Rojas", "Silva", "Jiménez", "Ayala", "Giménez",
    "Oliveira", "Ferreyra", "Navarro", "Paredes", "Muñoz", "Pinto",
    "Figueroa", "Zamora", "Aguilar", "Espinoza", "Luna", "Vera", "Sosa",
    "Bustos", "Pereyra", "Quiroga", "Moyano", "Villalba", "Cabral",
    "Leiva", "Cáceres", "Palavecino", "Correa", "Miranda", "Barrios",
    "Ibáñez", "Arias", "Palacios", "Salinas", "Cano", "Rivero", "Bravo",
    "Cardozo", "Zárate", "Rubio", "Salas", "Blanco", "Carrizo", "Juárez",
    "Vega", "Meza", "Serrano", "Núñez", "Coria", "Mansilla", "Godoy",
]

CALLES = [
    "Av. San Martín", "Sarmiento", "Rivadavia", "Belgrano", "Av. Corrientes",
    "Mitre", "Colón", "Urquiza", "9 de Julio", "25 de Mayo", "Av. Libertador",
    "Las Heras", "Paraguay", "Santa Fe", "Córdoba", "Tucumán", "Jujuy",
    "Entre Ríos", "H. Yrigoyen", "Av. de Mayo", "Lavalle", "Av. Callao",
    "Thames", "Soler", "Nicaragua", "Honduras", "Guatemala", "Av. Las Américas",
    "Av. J. B. Justo", "Av. Directorio", "Independencia", "Av. Gaona",
    "Av. Warnes", "Av. Forest", "Monroe", "Olazábal", "Av. Cabildo",
    "Cangallo", "Suipacha", "Florida", "Reconquista", "25 de Octubre",
    "Av. Vélez Sarsfield", "Av. Colón", "Bv. San Juan", "Av. Perón",
]

DOMINIOS = [
    "gmail.com", "hotmail.com", "yahoo.com.ar", "outlook.com",
    "fibertel.com.ar", "arnet.com.ar", "speedy.com.ar", "icloud.com",
    "personal.com.ar",
]

SUCURSALES = [
    "Casa Central — CABA",    "BRS Palermo — CABA",     "BRS Caballito — CABA",
    "BRS La Plata Centro",    "BRS Mar del Plata",       "BRS Quilmes",
    "BRS Morón",              "BRS Bahía Blanca",        "BRS Córdoba Capital",
    "BRS Villa Carlos Paz",   "BRS Rosario Centro",      "BRS Santa Fe Capital",
    "BRS Mendoza Capital",    "BRS Tucumán Centro",      "BRS Paraná",
    "BRS Salta Capital",      "BRS Posadas",             "BRS Resistencia",
    "BRS Corrientes Capital", "BRS San Juan Capital",    "BRS Neuquén Capital",
    "BRS Bariloche",          "BRS Comodoro Rivadavia",  "BRS Río Gallegos",
]

# ── AFIP ──────────────────────────────────────────────────────────────────────

CONDICIONES_AFIP = [
    ("Relación de dependencia", 35),
    ("Monotributista",          30),
    ("No inscripto",            20),
    ("Responsable Inscripto",   12),
    ("Exento",                   3),
]
_COND_NAMES   = [c[0] for c in CONDICIONES_AFIP]
_COND_WEIGHTS = [c[1] for c in CONDICIONES_AFIP]

CATEGORIAS_MONO = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]
_MONO_WEIGHTS   = [25, 20, 15, 12, 10,  7,  4,  3,  2,  1,  1]

# ── Perfiles coherentes ──────────────────────────────────────────────────────
# Cada perfil ata ocupación ↔ actividad económica ↔ condición AFIP ↔ tipos de
# cuenta compatibles, para que no salga "Peluquero/a" con actividad "Comercio de
# alimentos" en una cuenta business. La selección se hace por account_type.
# Campos: (ocupacion, actividad_economica, condicion_afip, {account_types}, peso)
PERFILES = [
    # ── empleados en relación de dependencia → personal ──
    ("Empleado/a de comercio",   "Empleado/a de comercio minorista",              "Relación de dependencia", {"personal"}, 6),
    ("Docente",                  "Docencia de nivel primario o secundario",       "Relación de dependencia", {"personal"}, 5),
    ("Enfermero/a",              "Auxiliar de enfermería en sector salud",        "Relación de dependencia", {"personal"}, 4),
    ("Administrativo/a",         "Empleado/a administrativo/a del sector privado","Relación de dependencia", {"personal"}, 6),
    ("Operario/a industrial",    "Operario/a en industria manufacturera",         "Relación de dependencia", {"personal"}, 5),
    ("Guardia de seguridad",     "Agente de seguridad privada",                   "Relación de dependencia", {"personal"}, 3),
    ("Técnico/a informático/a",  "Técnico/a en sistemas e informática",           "Relación de dependencia", {"personal"}, 3),
    ("Cajero/a bancario/a",      "Empleado/a administrativo/a bancario/a",        "Relación de dependencia", {"personal"}, 2),
    ("Mecánico/a",               "Mecánico/a automotriz en taller",               "Relación de dependencia", {"personal"}, 3),
    # ── monotributistas / independientes → personal y/o merchant ──
    ("Comerciante",              "Comercio al por menor de productos alimenticios","Monotributista", {"personal", "merchant"}, 6),
    ("Peluquero/a",              "Actividades de peluquería y tratamientos de belleza", "Monotributista", {"personal", "merchant"}, 4),
    ("Modista",                  "Confección y venta de indumentaria",            "Monotributista", {"personal", "merchant"}, 3),
    ("Programador/a freelance",  "Servicios de programación informática",         "Monotributista", {"personal"}, 3),
    ("Gasista matriculado/a",    "Servicios de plomería y gasfitería matriculada","Monotributista", {"personal"}, 2),
    ("Electricista matriculado/a","Servicios de instalaciones eléctricas",        "Monotributista", {"personal"}, 2),
    ("Remisero/a",               "Servicio de taxi o remís",                      "Monotributista", {"personal"}, 3),
    ("Fotógrafo/a",              "Actividades de fotografía y audiovisual",       "Monotributista", {"personal"}, 2),
    ("Comerciante",              "Venta de indumentaria y accesorios de moda",    "Monotributista", {"merchant"}, 5),
    ("Comerciante",              "Venta de productos electrónicos y tecnología",  "Monotributista", {"merchant"}, 4),
    ("Comerciante gastronómico/a","Servicios de bar, café y comidas rápidas",     "Monotributista", {"merchant"}, 4),
    ("Kiosquero/a",              "Comercio al por menor en kioscos y maxikioscos","Monotributista", {"merchant"}, 4),
    # ── no inscriptos / pasivos → personal ──
    ("Estudiante universitario/a","Consumidor final — sin actividad registrada",  "No inscripto", {"personal"}, 5),
    ("Jubilado/a",               "Consumidor final — clase pasiva",               "No inscripto", {"personal"}, 4),
    ("Pensionado/a",             "Consumidor final — clase pasiva",               "No inscripto", {"personal"}, 3),
    ("Ama/o de casa",            "Consumidor final — sin actividad registrada",   "No inscripto", {"personal"}, 3),
    # ── responsables inscriptos / empresas → business (y merchant grande) ──
    ("Empresario/a gastronómico/a","Servicios de restaurante y catering",         "Responsable Inscripto", {"business", "merchant"}, 5),
    ("Comerciante mayorista",    "Comercio al por mayor de alimentos y bebidas",  "Responsable Inscripto", {"business"}, 6),
    ("Industrial",               "Fabricación de productos metálicos elaborados", "Responsable Inscripto", {"business"}, 5),
    ("Importador/a",             "Servicios de importación y exportación",        "Responsable Inscripto", {"business"}, 4),
    ("Empresario/a de la construcción","Construcción de edificios y obras",       "Responsable Inscripto", {"business"}, 4),
    ("Consultor/a empresarial",  "Servicios de consultoría empresarial y gestión","Responsable Inscripto", {"business"}, 4),
    ("Transportista",            "Transporte automotor de cargas generales",      "Responsable Inscripto", {"business"}, 4),
    ("Empresario/a agroindustrial","Actividades agroindustriales",                "Responsable Inscripto", {"business"}, 3),
    ("Propietario/a de empresa", "Actividades inmobiliarias por cuenta propia",   "Responsable Inscripto", {"business"}, 3),
]


def _pick_perfil(account_type: str):
    """Coherent (ocupacion, actividad, condicion_afip) bundle for an account type."""
    pool = [p for p in PERFILES if account_type in p[3]] or \
           [p for p in PERFILES if "personal" in p[3]]
    weights = [p[4] for p in pool]
    ocup, activ, cond, _types, _w = random.choices(pool, weights=weights)[0]
    return ocup, activ, cond


# ── CUIL verifier ────────────────────────────────────────────────────────────

def _cuil(prefix: int, dni: int) -> str:
    digits = [int(c) for c in f"{prefix:02d}{dni:08d}"]
    mults  = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total  = sum(d * m for d, m in zip(digits, mults))
    v = 11 - (total % 11)
    if v == 11:
        v = 0
    elif v == 10:
        # special case: reassign prefix to 23 and recalculate
        prefix = 23
        digits = [int(c) for c in f"{prefix:02d}{dni:08d}"]
        total  = sum(d * m for d, m in zip(digits, mults))
        v = 11 - (total % 11)
        if v in (10, 11):
            v = 9
    return f"{prefix:02d}-{dni:08d}-{v}"


def _normalize(s: str) -> str:
    return (s.lower()
             .replace("á", "a").replace("é", "e").replace("í", "i")
             .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
             .replace(" ", ""))


# ── Generator ─────────────────────────────────────────────────────────────────

def generate_personas(accounts_df: pd.DataFrame) -> pd.DataFrame:
    n    = len(accounts_df)
    dnis = random.sample(range(10_000_000, 50_000_000), n)
    rows = []

    for i, (_, acc) in enumerate(accounts_df.iterrows()):
        genero   = random.choice(["M", "F"])
        nombre   = random.choice(NOMBRES_M if genero == "M" else NOMBRES_F)
        apellido = random.choice(APELLIDOS)
        if random.random() < 0.30:
            apellido = f"{apellido} {random.choice(APELLIDOS)}"

        dni    = dnis[i]
        prefix = 20 if genero == "M" else 27
        cuil   = _cuil(prefix, dni)

        is_owner = acc.get("account_type", "personal") in ("business", "merchant")
        edad     = random.randint(30, 65) if is_owner else random.randint(18, 72)
        year   = 2026 - edad
        fecha_nac = f"{random.randint(1,28):02d}/{random.randint(1,12):02d}/{year}"

        nacionalidad = random.choice(NACIONALIDADES)

        prov_idx  = random.choices(range(len(_PROV_NAMES)), weights=_PROV_WEIGHTS)[0]
        provincia = _PROV_NAMES[prov_idx]
        municipio = random.choice(_PROV_CITIES[provincia])

        calle    = random.choice(CALLES)
        numero   = random.randint(1, 5999)
        piso_str = ""
        if random.random() < 0.35:
            piso_str = f", Piso {random.randint(1,15)} Dpto {random.choice('ABCDEFGH')}"
        direccion = f"{calle} {numero}{piso_str}"
        cp        = str(random.randint(1000, 9400))

        account_type = acc.get("account_type", "personal")
        ocupacion, actividad, cond = _pick_perfil(account_type)

        cat_mono = None
        if cond == "Monotributista":
            # las empresas/comercios monotributistas suelen estar en categorías más altas
            weights = _MONO_WEIGHTS if account_type == "personal" else _MONO_WEIGHTS[::-1]
            cat_mono = random.choices(CATEGORIAS_MONO, weights=weights)[0]

        tipo_cuenta = (
            "Cuenta Corriente" if account_type == "business"
            else random.choices(["Cuenta Corriente", "Caja de Ahorro"], weights=[60, 40])[0]
            if account_type == "merchant"
            else random.choices(["Caja de Ahorro", "Cuenta Corriente"], weights=[80, 20])[0]
        )

        antiguedad = max(1, round(int(acc.get("opened_days_ago", 365)) / 30))
        sucursal   = random.choice(SUCURSALES)

        area = random.randint(11, 299)
        tel  = f"+54 9 {area:03d} {random.randint(100,999)}-{random.randint(1000,9999)}"

        base  = f"{_normalize(nombre)}.{_normalize(apellido.split(' ')[0])}"
        email = f"{base}{random.randint(1, 99)}@{random.choice(DOMINIOS)}"

        rows.append({
            "account_id":          acc["account_id"],
            "nombre":              nombre,
            "apellido":            apellido,
            "nombre_completo":     f"{nombre} {apellido}",
            "dni":                 dni,
            "cuil":                cuil,
            "fecha_nacimiento":    fecha_nac,
            "edad":                edad,
            "genero":              genero,
            "nacionalidad":        nacionalidad,
            "provincia":           provincia,
            "municipio":           municipio,
            "direccion":           direccion,
            "codigo_postal":       cp,
            "condicion_afip":      cond,
            "categoria_mono":      cat_mono,
            "actividad_economica": actividad,
            "ocupacion":           ocupacion,
            "tipo_cuenta":         tipo_cuenta,
            "antiguedad_meses":    antiguedad,
            "sucursal":            sucursal,
            "telefono":            tel,
            "email":               email,
        })

    return pd.DataFrame(rows)


# ── JSON enrichment ───────────────────────────────────────────────────────────

def _load_json(path: str):
    with open(path) as f:
        return json.load(f)


def _save_json(obj, path: str):
    with open(path, "w") as f:
        json.dump(obj, f, separators=(",", ":"))
    kb = Path(path).stat().st_size / 1024
    print(f"  → {path}  ({kb:.1f} KB)")


def _native(v):
    """Convert numpy scalars to Python native types for JSON serialization."""
    if pd.isna(v) if not isinstance(v, (list, dict)) else False:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    return v


def _persona_dict(row: pd.Series, fields=None) -> dict:
    """Return a dict of persona fields from a DataFrame row."""
    all_fields = [
        "nombre", "apellido", "nombre_completo", "dni", "cuil",
        "fecha_nacimiento", "edad", "genero", "nacionalidad",
        "provincia", "municipio", "direccion", "codigo_postal",
        "condicion_afip", "categoria_mono", "actividad_economica",
        "ocupacion", "tipo_cuenta", "antiguedad_meses",
        "sucursal", "telefono", "email",
    ]
    selected = fields or all_fields
    return {k: _native(row[k]) for k in selected if k in row.index}


BRIEF_FIELDS = [
    "nombre_completo", "dni", "cuil", "edad", "genero",
    "ocupacion", "condicion_afip", "municipio", "provincia", "sucursal",
]


def enrich_top_accounts(personas: pd.DataFrame, data_dir: str):
    path    = f"{data_dir}/top_accounts.json"
    records = _load_json(path)
    p_map   = personas.set_index("account_id")
    for rec in records:
        aid = rec["account_id"]
        if aid in p_map.index:
            rec.update(_persona_dict(p_map.loc[aid]))
    _save_json(records, path)


def enrich_origin_trace(personas: pd.DataFrame, data_dir: str):
    path  = f"{data_dir}/origin_trace.json"
    obj   = _load_json(path)
    p_map = personas.set_index("account_id")

    for perp in obj.get("perpetrators", []):
        aid = perp["node_id"]
        if aid in p_map.index:
            perp.update(_persona_dict(p_map.loc[aid], BRIEF_FIELDS))

    for node in obj.get("ring_nodes", []):
        aid = node["node_id"]
        if aid in p_map.index:
            node.update(_persona_dict(p_map.loc[aid], BRIEF_FIELDS))

    _save_json(obj, path)


def enrich_placement(personas: pd.DataFrame, data_dir: str):
    path  = f"{data_dir}/placement_candidates.json"
    obj   = _load_json(path)
    p_map = personas.set_index("account_id")

    for cand in obj.get("candidates", []):
        aid = cand["account_id"]
        if aid in p_map.index:
            cand.update(_persona_dict(p_map.loc[aid], BRIEF_FIELDS))

    _save_json(obj, path)


def enrich_rings(personas: pd.DataFrame, data_dir: str):
    path  = f"{data_dir}/rings.json"
    rings = _load_json(path)
    p_map = personas.set_index("account_id")

    for ring in rings:
        for node in ring.get("nodes", []):
            aid = node["id"]
            if aid in p_map.index:
                node["nombre_completo"] = p_map.loc[aid, "nombre_completo"]
                node["ocupacion"]       = p_map.loc[aid, "ocupacion"]
                node["municipio"]       = p_map.loc[aid, "municipio"]

    _save_json(rings, path)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    import yaml
    with open("config/config.yaml") as f:
        cfg = yaml.safe_load(f)

    raw_dir  = cfg["data"]["raw_dir"]
    data_dir = cfg["paths"]["dashboard_data_dir"]

    print("=" * 55)
    print("  Generando personas sintéticas")
    print("=" * 55)

    acc_df   = pd.read_csv(f"{raw_dir}/accounts.csv")
    personas = generate_personas(acc_df)
    out_csv  = f"{raw_dir}/personas.csv"
    personas.to_csv(out_csv, index=False)
    kb = Path(out_csv).stat().st_size / 1024
    print(f"  → {out_csv}  ({kb:.1f} KB, {len(personas)} personas)")

    print("\n  Enriqueciendo JSONs del dashboard…")
    enrich_top_accounts(personas, data_dir)
    enrich_origin_trace(personas, data_dir)
    enrich_placement(personas, data_dir)
    enrich_rings(personas, data_dir)

    print("=" * 55)
    print("  Listo. Recuerda re-exportar si regenerás los modelos:")
    print("    python -m src.export_dashboard && python -m src.enrich_personas")
    print("=" * 55)


if __name__ == "__main__":
    main()
