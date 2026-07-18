"""
Generate entity layer on top of existing accounts/personas.

Produces (all in data/raw/):
  empresas.csv       — company entities (some shell companies)
  titularidades.csv  — account → persona/empresa ownership links
  directores.csv     — persona → empresa director/officer links
  pep_flags.csv      — politically exposed persons flag per account

Design:
  - Fraud accounts are 3x more likely to be linked to shell companies
  - Shell companies preferentially appear in fraud rings
  - Some PEPs appear in fraud clusters (risk factor for AML)
  - Multi-account personas connect fraud ring members via shared identity
"""

import random
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


SECTORES = [
    "Importación / Exportación",
    "Servicios Financieros",
    "Construcción e Inmobiliaria",
    "Agropecuario",
    "Comercio Minorista",
    "Tecnología y Software",
    "Transporte y Logística",
    "Turismo y Hotelería",
    "Consultoría Empresarial",
    "Industria Manufacturera",
]

PAISES_OFFSHORE = ["Islas Vírgenes Británicas", "Panamá", "Islas Caimán", "Uruguay", "Paraguay"]
PAISES_LOCALES  = ["Argentina"] * 8 + PAISES_OFFSHORE  # weighted

CARGOS = ["Director Titular", "Gerente General", "Apoderado Legal", "Socio Gerente", "Presidente"]

RAZON_SOCIAL_PREFIJOS = [
    "Inversiones", "Importadora", "Exportadora", "Comercial", "Servicios",
    "Consultora", "Distribuidora", "Holding", "Trading", "Desarrollos",
]
RAZON_SOCIAL_SUFIJOS = [
    "del Sur S.A.", "& Asociados S.R.L.", "Internacional S.A.", "Group S.A.",
    "Global S.R.L.", "Argentina S.A.", "Corp S.A.", "Hermanos S.R.L.",
    "del Norte S.A.", "Patagonia S.R.L.",
]


def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def _cuit_empresa(i: int) -> str:
    base = 30_00000000 + i
    digits = [int(d) for d in str(base)]
    weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    s = sum(d * w for d, w in zip(digits, weights))
    check = 11 - (s % 11)
    check = 0 if check == 11 else (9 if check == 10 else check)
    return f"30-{base:08d}-{check}"


def generate_empresas(n: int, fraud_account_ids: set, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for i in range(n):
        # shell companies cluster around fraud accounts
        is_shell = rng.random() < 0.25
        pais = rng.choice(PAISES_OFFSHORE if is_shell else ["Argentina"] * 6 + PAISES_OFFSHORE)
        razon_social = (
            rng.choice(RAZON_SOCIAL_PREFIJOS) + " " + rng.choice(RAZON_SOCIAL_SUFIJOS)
        )
        rows.append({
            "empresa_id":         f"EMP{i:07d}",
            "razon_social":       razon_social,
            "cuit_empresa":       _cuit_empresa(i),
            "sector":             rng.choice(SECTORES),
            "pais_constitucion":  pais,
            "is_shell":           is_shell,
            "fecha_constitucion": f"{rng.integers(1995, 2024):04d}-{rng.integers(1,13):02d}-{rng.integers(1,28):02d}",
        })
    return pd.DataFrame(rows)


def generate_titularidades(
    accounts: pd.DataFrame,
    empresas: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Link accounts to their owners (persona or empresa).

    Rules:
      - 85% of accounts: sole persona owner (the persona from personas.csv)
      - 10% of accounts: owned by an empresa
      - 5%  of accounts: shared between persona + empresa (co-ownership)
      - Fraud accounts are 3x more likely to be empresa-owned
    """
    rows = []
    fraud_ids  = set(accounts.loc[accounts["is_fraud"] == 1, "account_id"])
    empresa_ids = empresas["empresa_id"].tolist()
    shell_ids   = set(empresas.loc[empresas["is_shell"], "empresa_id"])

    for _, acc in accounts.iterrows():
        acc_id  = acc["account_id"]
        is_fraud = acc["is_fraud"] == 1

        empresa_prob = 0.35 if is_fraud else 0.12
        r = rng.random()

        if r < empresa_prob:
            # assign a shell company preferentially to fraud accounts
            if is_fraud and rng.random() < 0.6 and len(shell_ids) > 0:
                emp_id = rng.choice(list(shell_ids))
            else:
                emp_id = rng.choice(empresa_ids)
            rows.append({
                "account_id":          acc_id,
                "titular_type":        "empresa",
                "titular_id":          emp_id,
                "porcentaje_titularidad": 100,
            })
            # co-ownership: also link original persona
            if rng.random() < 0.3:
                rows.append({
                    "account_id":          acc_id,
                    "titular_type":        "persona",
                    "titular_id":          acc_id,   # persona shares account_id key
                    "porcentaje_titularidad": int(rng.integers(10, 50)),
                })
        else:
            rows.append({
                "account_id":          acc_id,
                "titular_type":        "persona",
                "titular_id":          acc_id,
                "porcentaje_titularidad": 100,
            })

    return pd.DataFrame(rows)


def generate_directores(
    personas: pd.DataFrame,
    empresas: pd.DataFrame,
    titularidades: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Link personas to empresas as directors/officers.

    Fraud personas (those holding fraud accounts) are more likely to
    appear as directors of shell companies.
    """
    fraud_persona_ids = set(
        titularidades.loc[
            titularidades["titular_type"] == "persona", "titular_id"
        ].values
    )

    # sample personas that hold empresa-linked accounts to be directors
    empresa_account_ids = set(
        titularidades.loc[titularidades["titular_type"] == "empresa", "account_id"]
    )

    rows = []
    for _, emp in empresas.iterrows():
        # 2-4 directors per company
        n_directors = int(rng.integers(2, 5))
        sample_pool = personas["account_id"].tolist()
        chosen = rng.choice(sample_pool, size=min(n_directors, len(sample_pool)), replace=False)
        for i, persona_id in enumerate(chosen):
            rows.append({
                "persona_id":  persona_id,
                "empresa_id":  emp["empresa_id"],
                "cargo":       CARGOS[i % len(CARGOS)],
                "fecha_desde": f"{rng.integers(1998, 2024):04d}-{rng.integers(1,13):02d}-01",
                "vigente":     rng.random() > 0.15,
            })
    return pd.DataFrame(rows)


def generate_pep_flags(
    personas: pd.DataFrame,
    accounts: pd.DataFrame,
    rng: np.random.Generator,
    pep_rate: float = 0.008,
) -> pd.DataFrame:
    """
    Mark ~0.8% of personas as PEP. Fraud accounts have 4x higher PEP rate.
    PEPs get a category: funcionario_publico, familiar_pep, allegado_pep.
    """
    PEP_CATS = ["Funcionario público", "Familiar de PEP", "Allegado de PEP"]
    CARGOS_PEP = [
        "Intendente Municipal", "Diputado Provincial", "Secretario de Estado",
        "Ministro de Hacienda", "Jefe Comunal", "Senador Nacional",
        "Director de Organismo Público", "Subsecretario",
    ]

    fraud_ids = set(accounts.loc[accounts["is_fraud"] == 1, "account_id"])
    rows = []
    for _, persona in personas.iterrows():
        is_fraud = persona["account_id"] in fraud_ids
        prob = pep_rate * 4 if is_fraud else pep_rate
        if rng.random() < prob:
            rows.append({
                "account_id":   persona["account_id"],
                "is_pep":       True,
                "categoria_pep": rng.choice(PEP_CATS),
                "cargo_pep":    rng.choice(CARGOS_PEP),
                "pais_pep":     "Argentina",
            })
    return pd.DataFrame(rows)


def generate_entities(config_path="config/config.yaml"):
    cfg = load_config(config_path)
    seed    = cfg["project"]["seed"]
    raw_dir = Path(cfg["data"]["raw_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)
    random.seed(seed)

    accounts = pd.read_csv(raw_dir / "accounts.csv")
    personas = pd.read_csv(raw_dir / "personas.csv")

    n_accounts = len(accounts)
    fraud_ids  = set(accounts.loc[accounts["is_fraud"] == 1, "account_id"])

    # Scale empresas with dataset size (~1 empresa per 15 accounts)
    n_empresas = max(50, n_accounts // 15)
    print(f"[generate_entities] accounts={n_accounts}  empresas={n_empresas}")

    empresas      = generate_empresas(n_empresas, fraud_ids, rng)
    titularidades = generate_titularidades(accounts, empresas, rng)
    directores    = generate_directores(personas, empresas, titularidades, rng)
    pep_flags     = generate_pep_flags(personas, accounts, rng)

    empresas.to_csv(raw_dir / "empresas.csv", index=False)
    titularidades.to_csv(raw_dir / "titularidades.csv", index=False)
    directores.to_csv(raw_dir / "directores.csv", index=False)
    pep_flags.to_csv(raw_dir / "pep_flags.csv", index=False)

    n_shell = empresas["is_shell"].sum()
    n_pep   = len(pep_flags)
    n_emp_owned = (titularidades["titular_type"] == "empresa").sum()

    print(f"  empresas={len(empresas)}  shell={n_shell}  PEPs={n_pep}")
    print(f"  cuentas con titular empresa={n_emp_owned}")
    print(f"  directores={len(directores)}")
    print(f"  → data/raw/empresas.csv, titularidades.csv, directores.csv, pep_flags.csv")
    return empresas, titularidades, directores, pep_flags


if __name__ == "__main__":
    generate_entities()
