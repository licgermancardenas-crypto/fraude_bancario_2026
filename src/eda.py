"""
EDA of the fraud transaction graph.
Generates figures to reports/figures/ and returns stats dict.
Called by notebooks/01_eda.ipynb and can also be run standalone.
"""

from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import yaml

warnings.filterwarnings("ignore")

# ── palette ──────────────────────────────────────────────────────────────────
FRAUD_COLOR  = "#C0392B"
LEGIT_COLOR  = "#BDC3C7"
NAVY         = "#0A1F44"
GOLD         = "#C9A227"
GRID_COLOR   = "#E0E0E0"

FIG_DPI = 150


def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def load_data(cfg):
    raw = cfg["data"]["raw_dir"]
    acc = pd.read_csv(f"{raw}/accounts.csv")
    txn = pd.read_csv(f"{raw}/transactions.csv")
    return acc, txn


def build_nx_graph(acc: pd.DataFrame, txn: pd.DataFrame) -> nx.DiGraph:
    G = nx.DiGraph()
    fraud_ids = set(acc.loc[acc.is_fraud == 1, "account_id"])
    for _, row in acc.iterrows():
        G.add_node(row.account_id,
                   is_fraud=int(row.is_fraud),
                   balance=row.balance,
                   risk_score=row.risk_score,
                   account_type=row.account_type)
    for _, row in txn.iterrows():
        G.add_edge(row.src, row.dst,
                   amount=row.amount,
                   timestamp=row.timestamp,
                   is_fraud=int(row.is_fraud),
                   transaction_type=row.transaction_type)
    return G, fraud_ids


def ensure_figures_dir(cfg):
    p = Path(cfg["paths"]["figures_dir"])
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── 1. Graph statistics ───────────────────────────────────────────────────────

def section_graph_stats(G: nx.DiGraph, acc, txn, figures_dir) -> dict:
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()
    density = nx.density(G)
    wcc     = nx.number_weakly_connected_components(G)
    scc     = nx.number_strongly_connected_components(G)
    largest_wcc = max(nx.weakly_connected_components(G), key=len)
    pct_in_wcc  = 100 * len(largest_wcc) / n_nodes

    fraud_nodes = acc.is_fraud.sum()
    fraud_edges = txn.is_fraud.sum()
    pct_fn = 100 * fraud_nodes / n_nodes
    pct_fe = 100 * fraud_edges / n_edges

    stats = {
        "n_nodes": n_nodes,
        "n_edges": n_edges,
        "density": density,
        "weakly_connected_components": wcc,
        "strongly_connected_components": scc,
        "pct_in_largest_wcc": pct_in_wcc,
        "fraud_nodes": int(fraud_nodes),
        "fraud_edges": int(fraud_edges),
        "pct_fraud_nodes": pct_fn,
        "pct_fraud_edges": pct_fe,
    }

    print("\n── 1. ESTADÍSTICAS DEL GRAFO ──────────────────────────────────")
    print(f"  Nodos             : {n_nodes:>7,}")
    print(f"  Aristas           : {n_edges:>7,}")
    print(f"  Densidad          : {density:.6f}")
    print(f"  Comp. débilmente conexas : {wcc:>4,}  (mayor: {pct_in_wcc:.1f}% de los nodos)")
    print(f"  Comp. fuertemente conexas: {scc:>4,}")
    print(f"  Nodos fraude      : {fraud_nodes:>4} / {n_nodes}  ({pct_fn:.2f}%)")
    print(f"  Aristas fraude    : {fraud_edges:>4} / {n_edges}  ({pct_fe:.2f}%)")

    return stats


# ── 2. Degree distributions ───────────────────────────────────────────────────

def section_degree_dist(G: nx.DiGraph, acc, figures_dir) -> dict:
    fraud_ids = set(acc.loc[acc.is_fraud == 1, "account_id"])

    in_deg  = dict(G.in_degree())
    out_deg = dict(G.out_degree())

    in_fraud  = [in_deg[n]  for n in fraud_ids  if n in in_deg]
    in_legit  = [in_deg[n]  for n in G.nodes()  if n not in fraud_ids]
    out_fraud = [out_deg[n] for n in fraud_ids  if n in out_deg]
    out_legit = [out_deg[n] for n in G.nodes()  if n not in fraud_ids]

    stats = {
        "mean_in_deg_fraud":  np.mean(in_fraud),
        "mean_in_deg_legit":  np.mean(in_legit),
        "mean_out_deg_fraud": np.mean(out_fraud),
        "mean_out_deg_legit": np.mean(out_legit),
        "ratio_in_deg":       np.mean(in_fraud) / max(np.mean(in_legit), 1e-9),
        "ratio_out_deg":      np.mean(out_fraud) / max(np.mean(out_legit), 1e-9),
    }

    print("\n── 2. DISTRIBUCIÓN DE GRADO ───────────────────────────────────")
    print(f"  In-degree  media  — fraude: {stats['mean_in_deg_fraud']:.2f}  "
          f"legítimo: {stats['mean_in_deg_legit']:.2f}  "
          f"ratio: {stats['ratio_in_deg']:.2f}x")
    print(f"  Out-degree media  — fraude: {stats['mean_out_deg_fraud']:.2f}  "
          f"legítimo: {stats['mean_out_deg_legit']:.2f}  "
          f"ratio: {stats['ratio_out_deg']:.2f}x")

    # figure
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    fig.patch.set_facecolor("white")

    for ax, (fraud_vals, legit_vals, label) in zip(
        axes,
        [(in_fraud, in_legit, "In-degree"), (out_fraud, out_legit, "Out-degree")],
    ):
        max_deg = max(max(fraud_vals + [1]), max(legit_vals + [1]))
        bins = np.logspace(0, np.log10(max_deg + 1), 25)

        ax.hist(legit_vals, bins=bins, alpha=0.6, color=LEGIT_COLOR,
                label="Legítimo", density=True)
        ax.hist(fraud_vals, bins=bins, alpha=0.8, color=FRAUD_COLOR,
                label="Fraude", density=True)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(label, fontsize=11)
        ax.set_ylabel("Densidad (log)", fontsize=11)
        ax.set_title(f"Distribución {label} — Fraude vs. Legítimo", fontsize=12, color=NAVY)
        ax.legend(fontsize=10)
        ax.grid(True, color=GRID_COLOR, linewidth=0.5)
        ax.set_facecolor("#FAFAFA")

    plt.tight_layout()
    path = figures_dir / "01_degree_distribution.png"
    plt.savefig(path, dpi=FIG_DPI, bbox_inches="tight")
    plt.close()
    print(f"  → Figura: {path}")

    return stats


# ── 3. Amount distributions ───────────────────────────────────────────────────

def section_amount_dist(txn: pd.DataFrame, figures_dir) -> dict:
    fraud_amounts = txn.loc[txn.is_fraud == 1, "amount"]
    legit_amounts = txn.loc[txn.is_fraud == 0, "amount"]

    stats = {
        "median_amount_fraud": float(fraud_amounts.median()),
        "median_amount_legit": float(legit_amounts.median()),
        "mean_amount_fraud":   float(fraud_amounts.mean()),
        "mean_amount_legit":   float(legit_amounts.mean()),
        "ratio_median_amount": float(fraud_amounts.median() / legit_amounts.median()),
    }

    print("\n── 3. DISTRIBUCIÓN DE MONTOS ──────────────────────────────────")
    print(f"  Mediana monto — fraude  : ${stats['median_amount_fraud']:>10,.2f}")
    print(f"  Mediana monto — legítimo: ${stats['median_amount_legit']:>10,.2f}")
    print(f"  Ratio                   : {stats['ratio_median_amount']:.1f}x")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    fig.patch.set_facecolor("white")

    # histogram (log scale)
    ax = axes[0]
    bins = np.logspace(np.log10(max(txn.amount.min(), 0.01)), np.log10(txn.amount.max()), 40)
    ax.hist(legit_amounts, bins=bins, alpha=0.6, color=LEGIT_COLOR, label="Legítimo", density=True)
    ax.hist(fraud_amounts, bins=bins, alpha=0.8, color=FRAUD_COLOR, label="Fraude", density=True)
    ax.set_xscale("log")
    ax.set_xlabel("Monto (USD, escala log)", fontsize=11)
    ax.set_ylabel("Densidad", fontsize=11)
    ax.set_title("Distribución de Montos por Transacción", fontsize=12, color=NAVY)
    ax.legend(fontsize=10)
    ax.grid(True, color=GRID_COLOR, linewidth=0.5)
    ax.set_facecolor("#FAFAFA")

    # box plot
    ax = axes[1]
    data_box = [np.log10(legit_amounts + 1), np.log10(fraud_amounts + 1)]
    bp = ax.boxplot(data_box, patch_artist=True, widths=0.5,
                    medianprops=dict(color=NAVY, linewidth=2))
    bp["boxes"][0].set_facecolor(LEGIT_COLOR)
    bp["boxes"][1].set_facecolor(FRAUD_COLOR)
    ax.set_xticks([1, 2])
    ax.set_xticklabels(["Legítimo", "Fraude"], fontsize=11)
    ax.set_ylabel("log₁₀(Monto + 1)", fontsize=11)
    ax.set_title("Box Plot de Montos (log₁₀)", fontsize=12, color=NAVY)
    ax.grid(True, axis="y", color=GRID_COLOR, linewidth=0.5)
    ax.set_facecolor("#FAFAFA")

    plt.tight_layout()
    path = figures_dir / "02_amount_distribution.png"
    plt.savefig(path, dpi=FIG_DPI, bbox_inches="tight")
    plt.close()
    print(f"  → Figura: {path}")

    return stats


# ── 4. Homophily ─────────────────────────────────────────────────────────────

def section_homophily(G: nx.DiGraph, acc, figures_dir) -> dict:
    fraud_ids = set(acc.loc[acc.is_fraud == 1, "account_id"])
    pf = len(fraud_ids) / G.number_of_nodes()

    edges = list(G.edges())
    ff = sum(1 for u, v in edges if u in fraud_ids and v in fraud_ids)
    fl = sum(1 for u, v in edges if u in fraud_ids and v not in fraud_ids)
    lf = sum(1 for u, v in edges if u not in fraud_ids and v in fraud_ids)
    ll = sum(1 for u, v in edges if u not in fraud_ids and v not in fraud_ids)

    total = len(edges)
    # expected fraction fraud-fraud under random (null model)
    expected_ff = pf ** 2
    observed_ff = ff / total
    # homophily h: fraction same-class edges (fraud-fraud + legit-legit)
    same_class   = ff + ll
    homophily_h  = same_class / total
    # fraud-fraud lift: observed / expected
    ff_lift = observed_ff / expected_ff if expected_ff > 0 else 0

    stats = {
        "edges_ff": ff, "edges_fl": fl, "edges_lf": lf, "edges_ll": ll,
        "pct_ff": 100 * ff / total,
        "pct_fl": 100 * fl / total,
        "pct_lf": 100 * lf / total,
        "pct_ll": 100 * ll / total,
        "expected_ff_pct":  100 * expected_ff,
        "observed_ff_pct":  100 * observed_ff,
        "ff_lift":           ff_lift,
        "homophily_h":       homophily_h,
    }

    print("\n── 4. HOMOFILIA ───────────────────────────────────────────────")
    print(f"  Aristas fraude→fraude : {ff:>4} ({100*ff/total:.2f}%)")
    print(f"  Aristas fraude→legít  : {fl:>4} ({100*fl/total:.2f}%)")
    print(f"  Aristas legít→fraude  : {lf:>4} ({100*lf/total:.2f}%)")
    print(f"  Aristas legít→legít   : {ll:>4} ({100*ll/total:.2f}%)")
    print(f"  Fraude→fraude esperado (azar): {100*expected_ff:.3f}%")
    print(f"  Fraude→fraude observado      : {100*observed_ff:.3f}%")
    print(f"  Lift F-F                     : {ff_lift:.1f}x")
    print(f"  Coeficiente de homofilia h   : {homophily_h:.4f}")

    # stacked bar
    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor("white")

    categories = ["Observado", "Esperado\n(azar)"]
    ff_pcts    = [100 * ff / total,   100 * expected_ff]
    other_pcts = [100 - ff_pcts[0],   100 - ff_pcts[1]]

    x = np.arange(len(categories))
    ax.bar(x, ff_pcts,    color=FRAUD_COLOR, label="Fraude → Fraude", alpha=0.85)
    ax.bar(x, other_pcts, color=LEGIT_COLOR, label="Resto",           alpha=0.6,
           bottom=ff_pcts)

    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=12)
    ax.set_ylabel("% de aristas del grafo", fontsize=11)
    ax.set_title(f"Homofilia: Aristas Fraude→Fraude\nObservado vs. Esperado por Azar  (lift = {ff_lift:.1f}x)",
                 fontsize=12, color=NAVY)
    ax.legend(fontsize=10)
    ax.grid(True, axis="y", color=GRID_COLOR, linewidth=0.5)
    ax.set_facecolor("#FAFAFA")

    for i, v in enumerate(ff_pcts):
        ax.text(i, v / 2, f"{v:.3f}%", ha="center", va="center",
                color="white", fontweight="bold", fontsize=11)

    plt.tight_layout()
    path = figures_dir / "03_homophily.png"
    plt.savefig(path, dpi=FIG_DPI, bbox_inches="tight")
    plt.close()
    print(f"  → Figura: {path}")

    return stats


# ── 5. Risk score distribution ───────────────────────────────────────────────

def section_risk_score(acc: pd.DataFrame, figures_dir) -> dict:
    fraud_rs = acc.loc[acc.is_fraud == 1, "risk_score"]
    legit_rs = acc.loc[acc.is_fraud == 0, "risk_score"]

    overlap = (
        (fraud_rs.mean() - legit_rs.mean()) /
        ((fraud_rs.std() + legit_rs.std()) / 2 + 1e-9)
    )

    stats = {
        "mean_risk_score_fraud": float(fraud_rs.mean()),
        "mean_risk_score_legit": float(legit_rs.mean()),
        "std_risk_score_fraud":  float(fraud_rs.std()),
        "effect_size_risk_score": float(overlap),
    }

    print("\n── 5. RISK SCORE EXTERNO ──────────────────────────────────────")
    print(f"  Media risk_score — fraude  : {stats['mean_risk_score_fraud']:.4f}")
    print(f"  Media risk_score — legítimo: {stats['mean_risk_score_legit']:.4f}")
    print(f"  Tamaño del efecto (Cohen d): {overlap:.3f}")

    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor("white")
    bins = np.linspace(0, 1, 30)
    ax.hist(legit_rs, bins=bins, alpha=0.6, color=LEGIT_COLOR, label="Legítimo", density=True)
    ax.hist(fraud_rs, bins=bins, alpha=0.8, color=FRAUD_COLOR, label="Fraude", density=True)
    ax.axvline(fraud_rs.mean(), color=FRAUD_COLOR, linestyle="--", linewidth=1.5,
               label=f"Media fraude ({fraud_rs.mean():.3f})")
    ax.axvline(legit_rs.mean(), color=NAVY, linestyle="--", linewidth=1.5,
               label=f"Media legítimo ({legit_rs.mean():.3f})")
    ax.set_xlabel("Risk Score (externo / crediticio)", fontsize=11)
    ax.set_ylabel("Densidad", fontsize=11)
    ax.set_title("Distribución del Risk Score Externo\n(¿separa fraude de legítimo?)",
                 fontsize=12, color=NAVY)
    ax.legend(fontsize=9)
    ax.grid(True, color=GRID_COLOR, linewidth=0.5)
    ax.set_facecolor("#FAFAFA")

    plt.tight_layout()
    path = figures_dir / "04_risk_score.png"
    plt.savefig(path, dpi=FIG_DPI, bbox_inches="tight")
    plt.close()
    print(f"  → Figura: {path}")

    return stats


# ── 6. Temporal patterns ─────────────────────────────────────────────────────

def section_temporal(txn: pd.DataFrame, figures_dir) -> dict:
    txn = txn.copy()
    txn["dt"]      = pd.to_datetime(txn["timestamp"], unit="s")
    txn["hour"]    = txn["dt"].dt.hour
    txn["weekday"] = txn["dt"].dt.weekday  # 0=Mon

    fraud = txn[txn.is_fraud == 1]
    legit = txn[txn.is_fraud == 0]

    fraud_peak_hour    = int(fraud.hour.mode()[0]) if len(fraud) > 0 else -1
    fraud_peak_weekday = int(fraud.weekday.mode()[0]) if len(fraud) > 0 else -1
    days = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    stats = {
        "fraud_peak_hour":    fraud_peak_hour,
        "fraud_peak_weekday": days[fraud_peak_weekday] if fraud_peak_weekday >= 0 else "N/A",
    }

    print("\n── 6. PATRONES TEMPORALES ─────────────────────────────────────")
    print(f"  Hora pico fraude   : {fraud_peak_hour:02d}:00")
    print(f"  Día pico fraude    : {stats['fraud_peak_weekday']}")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    fig.patch.set_facecolor("white")

    ax = axes[0]
    h_legit = legit.groupby("hour").size() / max(len(legit), 1)
    h_fraud = fraud.groupby("hour").size() / max(len(fraud), 1)
    h_legit = h_legit.reindex(range(24), fill_value=0)
    h_fraud = h_fraud.reindex(range(24), fill_value=0)
    ax.bar(range(24), h_legit, alpha=0.6, color=LEGIT_COLOR, label="Legítimo")
    ax.bar(range(24), h_fraud, alpha=0.8, color=FRAUD_COLOR, label="Fraude")
    ax.set_xlabel("Hora del día", fontsize=11)
    ax.set_ylabel("Fracción de transacciones", fontsize=11)
    ax.set_title("Distribución Horaria de Transacciones", fontsize=12, color=NAVY)
    ax.legend(fontsize=10)
    ax.grid(True, axis="y", color=GRID_COLOR, linewidth=0.5)
    ax.set_facecolor("#FAFAFA")

    ax = axes[1]
    d_legit = legit.groupby("weekday").size() / max(len(legit), 1)
    d_fraud = fraud.groupby("weekday").size() / max(len(fraud), 1)
    d_legit = d_legit.reindex(range(7), fill_value=0)
    d_fraud = d_fraud.reindex(range(7), fill_value=0)
    x = np.arange(7)
    w = 0.35
    ax.bar(x - w/2, d_legit, w, alpha=0.6, color=LEGIT_COLOR, label="Legítimo")
    ax.bar(x + w/2, d_fraud, w, alpha=0.8, color=FRAUD_COLOR, label="Fraude")
    ax.set_xticks(x)
    ax.set_xticklabels(days, fontsize=10)
    ax.set_ylabel("Fracción de transacciones", fontsize=11)
    ax.set_title("Distribución por Día de Semana", fontsize=12, color=NAVY)
    ax.legend(fontsize=10)
    ax.grid(True, axis="y", color=GRID_COLOR, linewidth=0.5)
    ax.set_facecolor("#FAFAFA")

    plt.tight_layout()
    path = figures_dir / "05_temporal.png"
    plt.savefig(path, dpi=FIG_DPI, bbox_inches="tight")
    plt.close()
    print(f"  → Figura: {path}")

    return stats


# ── 7. Ring visualization ─────────────────────────────────────────────────────

def find_fraud_rings(G: nx.DiGraph, fraud_ids: set, max_len: int = 8) -> list:
    """Find cyclic paths in the fraud subgraph."""
    Gf = G.subgraph(fraud_ids).copy()
    rings = []
    try:
        for cycle in nx.simple_cycles(Gf):
            if 3 <= len(cycle) <= max_len:
                rings.append(cycle)
                if len(rings) >= 10:
                    break
    except Exception:
        pass
    return rings


def section_rings(G: nx.DiGraph, acc: pd.DataFrame, txn: pd.DataFrame, figures_dir) -> dict:
    fraud_ids = set(acc.loc[acc.is_fraud == 1, "account_id"])
    rings = find_fraud_rings(G, fraud_ids)

    print("\n── 7. ANILLOS DE LAVADO ───────────────────────────────────────")
    print(f"  Anillos detectados (≤8 saltos): {len(rings)}")
    for i, r in enumerate(rings[:5]):
        print(f"  Ring {i+1}: {' → '.join(r)} → {r[0]}  ({len(r)} nodos)")

    stats = {
        "n_rings_detected": len(rings),
        "ring_lengths":     [len(r) for r in rings],
        "avg_ring_length":  float(np.mean([len(r) for r in rings])) if rings else 0,
    }

    if not rings:
        print("  (sin anillos detectados — revisar patrones de generación)")
        return stats

    # visualize up to 3 rings
    n_show = min(3, len(rings))
    fig, axes = plt.subplots(1, n_show, figsize=(6 * n_show, 5))
    fig.patch.set_facecolor("white")
    if n_show == 1:
        axes = [axes]

    for idx, (ax, ring) in enumerate(zip(axes, rings[:n_show])):
        # subgraph: ring nodes + immediate neighbors
        neighborhood = set(ring)
        for node in ring:
            neighborhood.update(list(G.predecessors(node))[:3])
            neighborhood.update(list(G.successors(node))[:3])
        Gsub = G.subgraph(neighborhood).copy()

        # color nodes
        node_colors = []
        for n in Gsub.nodes():
            node_colors.append(FRAUD_COLOR if n in fraud_ids else LEGIT_COLOR)

        pos = nx.spring_layout(Gsub, seed=42 + idx, k=2.5)
        nx.draw_networkx_nodes(Gsub, pos, node_color=node_colors,
                               node_size=300, ax=ax, alpha=0.9)
        # draw ring edges in red, rest grey
        ring_edges = [(ring[i], ring[(i+1) % len(ring)]) for i in range(len(ring))]
        other_edges = [(u, v) for u, v in Gsub.edges() if (u, v) not in ring_edges]
        nx.draw_networkx_edges(Gsub, pos, edgelist=ring_edges,
                               edge_color=FRAUD_COLOR, width=2.5,
                               arrows=True, arrowsize=15, ax=ax)
        nx.draw_networkx_edges(Gsub, pos, edgelist=other_edges,
                               edge_color="#CCCCCC", width=1, alpha=0.5,
                               arrows=True, arrowsize=10, ax=ax)
        labels = {n: n[-4:] for n in Gsub.nodes()}
        nx.draw_networkx_labels(Gsub, pos, labels, font_size=7, ax=ax)

        fraud_patch  = mpatches.Patch(color=FRAUD_COLOR, label="Cuenta fraude")
        legit_patch  = mpatches.Patch(color=LEGIT_COLOR, label="Cuenta legítima")
        ax.legend(handles=[fraud_patch, legit_patch], fontsize=9, loc="upper right")
        ax.set_title(f"Anillo #{idx+1} — {len(ring)} saltos", fontsize=12, color=NAVY)
        ax.axis("off")
        ax.set_facecolor("white")

    plt.suptitle("Anillos de Lavado Detectados (grafo transaccional)",
                 fontsize=14, fontweight="bold", color=NAVY, y=1.01)
    plt.tight_layout()
    path = figures_dir / "06_fraud_rings.png"
    plt.savefig(path, dpi=FIG_DPI, bbox_inches="tight")
    plt.close()
    print(f"  → Figura: {path}")

    return stats


# ── 8. Account type breakdown ────────────────────────────────────────────────

def section_account_types(acc: pd.DataFrame, figures_dir) -> dict:
    ct = acc.groupby("account_type")["is_fraud"].agg(["sum", "count"])
    ct["pct_fraud"] = 100 * ct["sum"] / ct["count"]

    print("\n── 8. FRAUDE POR TIPO DE CUENTA ───────────────────────────────")
    print(ct.rename(columns={"sum": "fraud_count", "count": "total"}).to_string())

    fig, ax = plt.subplots(figsize=(7, 4))
    fig.patch.set_facecolor("white")
    colors = [FRAUD_COLOR if v > ct["pct_fraud"].mean() else NAVY
              for v in ct["pct_fraud"]]
    ax.bar(ct.index, ct["pct_fraud"], color=colors, alpha=0.85)
    ax.axhline(ct["pct_fraud"].mean(), color=GOLD, linestyle="--", linewidth=1.5,
               label=f"Media ({ct['pct_fraud'].mean():.2f}%)")
    ax.set_xlabel("Tipo de cuenta", fontsize=11)
    ax.set_ylabel("% de cuentas fraudulentas", fontsize=11)
    ax.set_title("Prevalencia de Fraude por Tipo de Cuenta", fontsize=12, color=NAVY)
    ax.legend(fontsize=10)
    ax.grid(True, axis="y", color=GRID_COLOR, linewidth=0.5)
    ax.set_facecolor("#FAFAFA")
    for i, (idx, row) in enumerate(ct.iterrows()):
        ax.text(i, row["pct_fraud"] + 0.1, f"{row['pct_fraud']:.1f}%",
                ha="center", fontsize=10)
    plt.tight_layout()
    path = figures_dir / "07_account_type_fraud.png"
    plt.savefig(path, dpi=FIG_DPI, bbox_inches="tight")
    plt.close()
    print(f"  → Figura: {path}")

    return {"fraud_pct_by_type": ct["pct_fraud"].to_dict()}


# ── master runner ─────────────────────────────────────────────────────────────

def run_eda(config_path: str = "config/config.yaml") -> dict:
    cfg = load_config(config_path)
    acc, txn = load_data(cfg)
    G, fraud_ids = build_nx_graph(acc, txn)
    figures_dir = ensure_figures_dir(cfg)

    print("=" * 60)
    print("  EDA — Detección de Fraude / Banco Regional del Sur (BRS)")
    print("=" * 60)

    all_stats = {}
    all_stats.update(section_graph_stats(G, acc, txn, figures_dir))
    all_stats.update(section_degree_dist(G, acc, figures_dir))
    all_stats.update(section_amount_dist(txn, figures_dir))
    all_stats.update(section_homophily(G, acc, figures_dir))
    all_stats.update(section_risk_score(acc, figures_dir))
    all_stats.update(section_temporal(txn, figures_dir))
    ring_stats = section_rings(G, acc, txn, figures_dir)
    all_stats.update(ring_stats)
    all_stats.update(section_account_types(acc, figures_dir))

    print("\n" + "=" * 60)
    print("  EDA completado.")
    print(f"  Figuras guardadas en: {figures_dir}")
    print("=" * 60)

    return all_stats, G, acc, txn, fraud_ids


if __name__ == "__main__":
    run_eda()
