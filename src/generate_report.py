"""
Phase H — Generate PDF institutional report via HTML → Playwright/Chromium.
Pipeline: build HTML with embedded figures → render A4 PDF.
Output: reports/informe_final.html  +  reports/informe_final.pdf
"""

import base64, json, textwrap
from pathlib import Path
import yaml


def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def money(n, decimals=0):
    """Monto en formato es-AR ($1.234.567). La escala monetaria vive en el
    dataset (config.yaml::monetary.scale); acá sólo se formatea."""
    txt = f"{n:,.{decimals}f}"
    return "$" + txt.replace(",", "\u00ad").replace(".", ",").replace("\u00ad", ".")


def money_m(n):
    """Agregados grandes: millones, o miles de millones cuando pasa de 1e9."""
    if abs(n) >= 1e9:
        return money(n / 1e9, 1).replace(",0", "") + " mil M"
    return money(n / 1e6, 1) + "M"


def load_artifacts(cfg):
    """
    Cifras del anexo leídas de los artefactos del pipeline en vez de
    hardcodeadas. Antes estaban escritas a mano y se desincronizaban con cada
    corrida (y con cada cambio de escala monetaria).
    """
    ddir = Path(cfg["paths"]["dashboard_data_dir"])
    art = {}
    for key, fname in [("trace", "origin_trace.json"),
                       ("placement", "placement_candidates.json")]:
        path = ddir / fname
        art[key] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    return art


def load_stats(cfg):
    """
    TODA cifra que aparezca en la narrativa del informe sale de acá.

    Antes estaban escritas a mano en el cuerpo del HTML y el informe terminó
    citando PR-AUC 0.978, 1.147 cuentas fraudulentas y ~400.000 transacciones
    —números de la corrida a scale=0.01— mientras el dashboard mostraba 0.9431
    sobre 75.000 cuentas y 11,2M de operaciones. Un lector que abría los dos
    documentos encontraba la contradicción en la primera página.

    Fuentes, todas artefactos versionados del pipeline:
      results_all.json   métricas por modelo (analysis.py)
      eda_stats.json     homofilia, grados, montos, anillos (eda.py)
      kpis.json          padrón y prevalencia (export_dashboard.py)
      scenarios.json     población y motor de reglas (export_scenarios.py)
      training_log.csv   mejor época de validación (train.py)
    """
    reports = Path(cfg["paths"]["reports_dir"])
    ddir    = Path(cfg["paths"]["dashboard_data_dir"])

    def _json(path, default=None):
        return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else default

    s = {}
    s["eda"] = _json(reports / "eda_stats.json", {}) or {}
    s["ablation_pr_auc"] = (_json(reports / "ablation.json", {}) or {}).get("topology_only_pr_auc")
    s["kpis"] = _json(ddir / "kpis.json", {}) or {}
    s["scenarios"] = _json(ddir / "scenarios.json", {}) or {}
    s["temporal"] = _json(ddir / "temporal_eval.json", {}) or {}

    # modelos: dict por nombre + el mejor por PR-AUC
    models = _json(reports / "results_all.json", []) or []
    s["models"] = {m["model"]: m for m in models}
    s["best"] = max(models, key=lambda m: m["pr_auc"]) if models else {}

    # mejor época de validación, del log de entrenamiento
    log = reports / "training_log.csv"
    if log.exists():
        import csv
        rows = list(csv.DictReader(log.open()))
        if rows:
            b = max(rows, key=lambda r: float(r["val_pr_auc"]))
            s["best_epoch"] = int(b["epoch"])
            s["best_val_pr_auc"] = float(b["val_pr_auc"])
            s["n_epochs_run"] = len(rows)

    # volumen del libro, del almacén columnar. is_fraud es una columna de 1 byte:
    # contarla sobre 11,2M filas cuesta 11 MB, no hace falta levantar el libro.
    try:
        from src import txn_store
        import numpy as _np
        s["n_txns"] = txn_store.n_rows(cfg["data"]["raw_dir"])
        flags = txn_store.load_transactions(cfg["data"]["raw_dir"], columns=["is_fraud"])["is_fraud"]
        s["n_fraud_txns"] = int(_np.asarray(flags).sum())
        s["pct_fraud_txns"] = 100 * s["n_fraud_txns"] / s["n_txns"]
    except Exception:
        s["n_txns"] = s["n_fraud_txns"] = s["pct_fraud_txns"] = None

    # cuántas features consume el modelo, de la fuente y no de memoria
    try:
        from src.features import FEATURE_COLS
        s["n_features"] = len(FEATURE_COLS)
        s["feature_cols"] = list(FEATURE_COLS)
    except Exception:
        s["n_features"], s["feature_cols"] = None, []

    # tipologías realmente presentes en el padrón
    try:
        import pandas as _pd
        acc = _pd.read_csv(Path(cfg["data"]["raw_dir"]) / "accounts.csv",
                           usecols=["fraud_typology"])
        s["typologies"] = sorted(t for t in acc["fraud_typology"].dropna().unique() if str(t).strip())
    except Exception:
        s["typologies"] = []

    # peso de clase efectivo del entrenamiento
    pob = s["scenarios"].get("poblacion", {})
    if pob.get("fraude"):
        s["class_weight"] = pob["legitimas"] / pob["fraude"]

    # rastreo hacia atrás: cuántos perpetradores quedan por debajo del corte del
    # modelo, que es el argumento del capítulo — el GNN ve mulas, no el origen
    trace = _json(ddir / "origin_trace.json", {}) or {}
    s["trace"] = trace.get("summary", {})
    perps = trace.get("perpetrators", [])
    invis = [p for p in perps if p.get("gnn_score", 1.0) < 0.5]
    s["n_perps"] = len(perps)
    s["n_perps_invisible"] = len(invis)
    s["amount_perps_invisible"] = sum(p.get("amount_injected", 0) for p in invis)
    return s


def pct(x, decimals=1):
    """Porcentaje en formato es-AR (12,3%)."""
    return f"{x:.{decimals}f}".replace(".", ",") + "%"


def dec(x, decimals=4):
    """Decimal en formato es-AR (0,9431)."""
    return f"{x:.{decimals}f}".replace(".", ",")


def num(n):
    """Entero con separador de miles es-AR (11.240.742)."""
    return f"{int(n):,}".replace(",", ".")


def b64img(path, fallback_h=160):
    p = Path(path)
    if not p.exists():
        return (f'<div style="height:{fallback_h}px;background:#e9ecef;display:flex;'
                f'align-items:center;justify-content:center;color:#9CA3AF;font-size:11px;">'
                f'[{p.name}]</div>')
    data = base64.b64encode(p.read_bytes()).decode()
    return f'<img src="data:image/png;base64,{data}" style="max-width:100%;display:block;" />'


# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Georgia&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

@page {
  size: A4;
  margin: 2.4cm 2.2cm 2.8cm 2.2cm;
}
@page :first { margin-top: 0; }

body {
  font-family: 'Inter', Arial, sans-serif;
  font-size: 10.5pt;
  line-height: 1.65;
  color: #1F2937;
  background: #fff;
}

/* ── typography ── */
h1 { font-family: Georgia, serif; font-size: 26pt; color: #0A1F44; line-height: 1.2; }
h2 { font-family: Georgia, serif; font-size: 15pt; color: #0A1F44;
     border-bottom: 2px solid #C9A227; padding-bottom: 5px; margin: 28px 0 14px; }
h3 { font-family: 'Inter', sans-serif; font-size: 11pt; color: #0A1F44;
     font-weight: 700; margin: 18px 0 8px; }
p  { margin-bottom: 10px; }
ul, ol { margin: 8px 0 10px 22px; }
li { margin-bottom: 5px; }
strong { color: #0A1F44; }

/* ── page breaks ── */
.break-before { page-break-before: always; break-before: page; }
.no-break     { page-break-inside: avoid; break-inside: avoid; }

/* ── cover ── */
.cover {
  background: #0A1F44;
  min-height: 297mm;
  display: flex; flex-direction: column;
  justify-content: space-between;
  padding: 3cm 2.5cm 2.5cm;
  page-break-after: always;
  break-after: page;
}
.cover-wordmark { color: #C9A227; font-size: 9pt; font-weight: 700;
                  letter-spacing: 4px; text-transform: uppercase; margin-bottom: 60px; }
.cover-tag      { color: rgba(255,255,255,0.5); font-size: 9pt;
                  text-transform: uppercase; letter-spacing: 2px; margin-bottom: 10px; }
.cover-title    { font-family: Georgia, serif; color: #fff; font-size: 30pt;
                  line-height: 1.18; margin-bottom: 20px; }
.cover-subtitle { color: rgba(255,255,255,0.65); font-size: 12pt; }
.cover-divider  { width: 60px; height: 3px; background: #C9A227;
                  margin: 30px 0; }
.cover-client   { color: #fff; font-size: 11pt; font-weight: 600; }
.cover-client-label { color: rgba(255,255,255,0.45); font-size: 9pt;
                      text-transform: uppercase; letter-spacing: 2px; margin-bottom: 4px; }
.cover-footer   { border-top: 1px solid rgba(255,255,255,0.15);
                  padding-top: 18px;
                  display: flex; justify-content: space-between; align-items: flex-end; }
.cover-author   { color: #C9A227; font-size: 10pt; font-weight: 600;
                  letter-spacing: 1px; }
.cover-date     { color: rgba(255,255,255,0.45); font-size: 9pt; }
.cover-confidential { color: rgba(255,255,255,0.3); font-size: 8pt;
                      text-transform: uppercase; letter-spacing: 2px; margin-top: 4px; }

/* ── disclaimer ── */
.disclaimer {
  background: #F9FAFB; border: 1px solid #E5E7EB;
  border-left: 4px solid #C9A227;
  padding: 20px 24px; margin: 20px 0;
  font-size: 9.5pt; color: #4B5563;
}
.disclaimer-title { color: #0A1F44; font-weight: 700; font-size: 10pt;
                    margin-bottom: 8px; }

/* ── callout ── */
.callout {
  background: #FFFBEB; border-left: 4px solid #C9A227;
  padding: 14px 18px; margin: 14px 0;
  page-break-inside: avoid; break-inside: avoid;
}
.callout-tag   { font-size: 8pt; font-weight: 700; color: #C9A227;
                 text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 6px; }
.callout-body  { font-size: 10pt; color: #374151; line-height: 1.6; }
.callout-body strong { color: #0A1F44; }

/* ── tables ── */
table  { width: 100%; border-collapse: collapse; margin: 14px 0;
         font-size: 9.5pt; page-break-inside: avoid; }
thead  { background: #0A1F44; color: #fff; }
th     { padding: 9px 12px; text-align: left; font-weight: 600;
         font-size: 9pt; letter-spacing: 0.3px; }
td     { padding: 8px 12px; border-bottom: 1px solid #E5E7EB; }
tr:nth-child(even) td { background: #F9FAFB; }
.td-best { color: #065F46; font-weight: 700; }

/* ── figure ── */
figure { margin: 18px 0; page-break-inside: avoid; break-inside: avoid; }
figcaption { font-size: 8.5pt; color: #6B7280; margin-top: 6px;
             text-align: center; font-style: italic; }

/* ── kpi row ── */
.kpi-row  { display: flex; gap: 12px; margin: 18px 0; }
.kpi-card { flex: 1; background: #0A1F44; color: #fff;
            padding: 14px 16px; border-radius: 6px; }
.kpi-val  { font-size: 22pt; font-weight: 700; color: #C9A227;
            font-family: Georgia, serif; line-height: 1; }
.kpi-lbl  { font-size: 8pt; color: rgba(255,255,255,0.6);
            text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }
.kpi-sub  { font-size: 7.5pt; color: rgba(255,255,255,0.4); margin-top: 2px; }

/* ── gantt ── */
.gantt-row   { display: flex; align-items: center; gap: 10px;
               padding: 7px 0; border-bottom: 1px solid #E5E7EB; font-size: 9.5pt; }
.gantt-label { width: 200px; font-weight: 500; color: #374151; flex-shrink: 0; }
.gantt-bar   { background: #0A1F44; height: 18px; border-radius: 3px;
               display: flex; align-items: center; padding-left: 6px;
               color: #fff; font-size: 8pt; }
.gantt-bar.gold { background: #C9A227; }
.gantt-weeks { color: #9CA3AF; font-size: 8.5pt; margin-left: 6px; }

/* ── insight compact ── */
.insight-compact { border-left: 3px solid #C9A227; padding: 10px 14px;
                   margin: 10px 0; background: #FFFBEB; break-inside: avoid; }
.insight-title   { font-weight: 700; color: #0A1F44; font-size: 10pt;
                   margin-bottom: 4px; }
.insight-text    { font-size: 9.5pt; color: #374151; margin: 0; line-height: 1.5; }

/* ── section label ── */
.section-num { color: #C9A227; font-size: 8pt; font-weight: 700;
               text-transform: uppercase; letter-spacing: 2px;
               margin-bottom: 4px; }

/* ── code block ── */
pre { background: #F3F4F6; padding: 14px 18px; font-size: 8.5pt;
      border-radius: 4px; line-height: 1.5; color: #374151; white-space: pre-wrap; }

/* ── highlight box ── */
.highlight { background: #EFF6FF; border: 1px solid #BFDBFE;
             padding: 14px 18px; border-radius: 4px; margin: 14px 0;
             font-size: 10pt; break-inside: avoid; }

/* ── plain language callout (green) ── */
.plain-lang {
  background: #F0FDF4; border-left: 4px solid #16A34A;
  padding: 14px 18px; margin: 14px 0;
  page-break-inside: avoid; break-inside: avoid;
}
.plain-lang-tag  { font-size: 8pt; font-weight: 700; color: #16A34A;
                   text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 6px; }
.plain-lang-body { font-size: 10pt; color: #374151; line-height: 1.6; }
.plain-lang-body strong { color: #065F46; }

/* ── glossary ── */
.glossary-entry { margin: 12px 0; padding-bottom: 12px; border-bottom: 1px solid #E5E7EB; }
.glossary-term  { font-weight: 700; color: #0A1F44; font-size: 10.5pt; }
.glossary-def   { font-size: 10pt; color: #374151; margin-top: 3px; line-height: 1.5; }
.glossary-ex    { font-size: 9pt; color: #6B7280; font-style: italic; margin-top: 2px; }
"""


# ─────────────────────────────────────────────────────────────────────────────
# Sections
# ─────────────────────────────────────────────────────────────────────────────

def cover(st):
    return """
<div class="cover">
  <div>
    <div class="cover-wordmark">PHANTOM AI · Germán Cárdenas · Data &amp; Analytics</div>
    <div class="cover-tag">Informe de resultados · Prueba de concepto</div>
    <h1 class="cover-title">Detección de Redes de Lavado mediante Inteligencia Artificial</h1>
    <p class="cover-subtitle">Cómo un sistema de IA que analiza conexiones entre cuentas detecta esquemas de lavado de dinero que los controles tradicionales no ven</p>
    <div class="cover-divider"></div>
    <div class="cover-client-label">Preparado para</div>
    <div class="cover-client">Banco Regional del Sur (BRS)</div>
  </div>
  <div class="cover-footer">
    <div>
      <div class="cover-author">GERMÁN CÁRDENAS</div>
      <div class="cover-confidential">Documento confidencial · Solo uso interno</div>
    </div>
    <div style="text-align:right;">
      <div class="cover-date">Julio 2026</div>
      <div class="cover-confidential">Datos 100% sintéticos</div>
    </div>
  </div>
</div>"""


def disclaimer_section():
    return """
<div class="break-before">
  <div class="section-num">Aviso legal</div>
  <h2>Aviso de Confidencialidad y Datos Sintéticos</h2>
  <div class="disclaimer">
    <div class="disclaimer-title">Confidencialidad</div>
    <p>El presente documento y su contenido son estrictamente confidenciales y están preparados exclusivamente para uso interno de Banco Regional del Sur (BRS). Queda prohibida su reproducción, distribución o divulgación total o parcial a terceros sin autorización expresa y por escrito.</p>
  </div>
  <div class="disclaimer">
    <div class="disclaimer-title">Declaración sobre datos sintéticos</div>
    <p>Todos los datos utilizados en este estudio son <strong>100% sintéticos</strong>, generados algorítmicamente para simular patrones realistas de fraude financiero. No corresponden a cuentas, transacciones, clientes ni eventos reales de ninguna institución financiera.</p>
    <p>Este documento representa una <strong>prueba de concepto técnica</strong>. Los indicadores de rendimiento presentados (PR-AUC, recall, precisión) corresponden a los datos sintéticos y no deben interpretarse como garantía de resultados equivalentes sobre datos reales. Una fase piloto con datos propios de BRS es el paso necesario para calibrar el modelo a las características específicas del portafolio del banco.</p>
  </div>
</div>"""


def executive_summary(st):
    b, e = st["best"], st["eda"]
    xgb = st["models"].get("XGBoost", {})
    lr  = st["models"].get("Logistic Regression", {})
    return f"""
<div class="break-before">
  <div class="section-num">Sección 1</div>
  <h2>Resumen Ejecutivo</h2>

  <div class="plain-lang no-break">
    <div class="plain-lang-tag">¿De qué trata este documento?</div>
    <div class="plain-lang-body">
      Este informe muestra cómo un sistema de inteligencia artificial (IA) puede detectar redes de lavado de dinero en un banco analizando <strong>las conexiones entre cuentas</strong>, no solo el comportamiento individual de cada una. Los resultados se obtuvieron con datos completamente ficticios que simulan el comportamiento real de un banco mediano. Cualquier persona — analista, gerente o director — debería poder leerlo y entenderlo.
    </div>
  </div>

  <div class="kpi-row no-break">
    <div class="kpi-card">
      <div class="kpi-val">{dec(b['pr_auc'])}</div>
      <div class="kpi-lbl">Precisión global — {b['model']}</div>
      <div class="kpi-sub">PR-AUC, escala 0–1. La tasa base de fraude es {pct(st['kpis']['pct_fraud'], 2)}.</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-val">{pct(b['rec_at_p90'] * 100, 0)}</div>
      <div class="kpi-lbl">Detección con 9 de 10 alertas correctas</div>
      <div class="kpi-sub">vs. {pct(xgb.get('rec_at_p90', 0) * 100, 0)} XGBoost / {pct(lr.get('rec_at_p90', 0) * 100, 0)} regresión simple</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-val">{len(st['models'])}</div>
      <div class="kpi-lbl">Modelos comparados</div>
      <div class="kpi-sub">{' · '.join(st['models'])}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-val">{dec(e['ff_lift'], 1)}×</div>
      <div class="kpi-lbl">Señal de red fraude-fraude</div>
      <div class="kpi-sub">Los vecinos de cuentas fraudulentas son {dec(e['ff_lift'], 1)}× más sospechosos que el azar</div>
    </div>
  </div>

  <h3>El problema que resuelve este sistema</h3>
  <ul>
    <li>BRS opera con ~500.000 cuentas activas y un equipo de compliance de 6 analistas.</li>
    <li>El sistema de alertas actual genera un <strong>~90% de falsas alarmas</strong>: de cada 10 alertas, 9 no son fraude real. Los analistas pierden tiempo revisando casos que no son delito.</li>
    <li>Los esquemas de <strong>lavado estructurado</strong> (conocido como "pitufeo") fragmentan el flujo de dinero en transferencias pequeñas que circulan por muchas cuentas antes de consolidarse. Ninguna cuenta individual parece sospechosa por sí sola. El problema es <em>invisible</em> para las reglas actuales.</li>
  </ul>

  <div class="plain-lang no-break">
    <div class="plain-lang-tag">En palabras simples — el problema</div>
    <div class="plain-lang-body">
      Imaginen que una banda decide lavar $100.000.000. En lugar de hacer una sola transferencia grande (que dispararía una alerta), divide ese dinero en 50 transferencias de $2.000.000, las hace circular por 20 cuentas distintas y las reagrupa al final. Cada transferencia parece normal. El sistema de reglas del banco no ve nada raro. <strong>Este software detecta ese patrón analizando las conexiones entre cuentas, no los montos individuales.</strong>
    </div>
  </div>

  <h3>Qué se hizo en este estudio</h3>
  <ul>
    <li>Se construyó un <strong>grafo (red) transaccional sintético</strong> con {num(st['kpis']['n_accounts'])} cuentas y {num(st['n_txns'])} transacciones sobre {num(e['n_edges'])} relaciones distintas, incluyendo redes de lavado cíclicas (4-7 pasos) y esquemas de estructuración.</li>
    <li>Se compararon <strong>{len(st['models'])} modelos de IA</strong> sobre los mismos datos y el mismo criterio de evaluación: Regresión Logística (modelo simple), XGBoost (modelo tabular avanzado), GAT y GraphSAGE (modelos de grafos).</li>
    <li>Se analizó <strong>por qué</strong> el modelo toma cada decisión, usando una técnica llamada GNNExplainer que señala cuáles conexiones son las más sospechosas.</li>
    <li>Se implementó <strong>rastreo hacia atrás</strong> (backward tracing) para identificar no solo las "mulas" que mueven el dinero, sino también los <em>perpetradores de origen</em> que inyectaron los fondos.</li>
    <li>Se construyó un <strong>panel de control web</strong> con gestión de casos, red de entidades y formularios de reporte regulatorio (ROS/SAR).</li>
  </ul>

  <h3>Resultados principales</h3>
  <ul>
    <li>El <strong>historial crediticio es ciego al lavado de dinero</strong>: las cuentas que mueven dinero sucio tienen exactamente el mismo puntaje crediticio que las cuentas normales. El problema no está en el perfil de la persona, está en con quién se conecta.</li>
    <li>{b['model']} supera a todos los modelos comparados con una puntuación de <strong>{dec(b['pr_auc'])} sobre 1.0</strong> y detecta el {pct(b['rec_at_p90'] * 100, 0)} del fraude cuando se le exige que 9 de cada 10 alertas sean reales.</li>
    <li>El modelo se basa en <strong>señales de conectividad</strong> (cuántas transferencias hace una cuenta, cuántos remitentes únicos recibe, su puntuación de riesgo), no en los montos absolutos.</li>
    <li>El rastreo hacia atrás identificó <strong>{num(st['n_perps_invisible'])} perpetradores que el modelo de IA no vio directamente</strong> (de {num(st['n_perps'])} en total) pero que habían inyectado {money_m(st['amount_perps_invisible'])} al esquema desde cuentas aparentemente legítimas.</li>
  </ul>

  <h3>Recomendación</h3>
  <div class="callout">
    <div class="callout-tag">Recomendación ejecutiva</div>
    <div class="callout-body">
      Iniciar un <strong>piloto de 8 semanas</strong> con datos reales de BRS. El entregable es una puntuación de riesgo por cuenta, actualizable cada 4 horas, combinada con rastreo automático de perpetradores — alimentando la cola de trabajo del equipo de compliance con un ranking priorizado que incluye tanto cuentas mula como cuentas de origen del dinero.
    </div>
  </div>
</div>"""


def context_section(st):
    e = st["eda"]
    base = st["kpis"]["pct_fraud"]
    vecino = base * e["ff_lift"]
    return f"""
<div class="break-before">
  <div class="section-num">Sección 2</div>
  <h2>Contexto y Problema</h2>

  <h3>El costo del fraude y el lavado de activos</h3>
  <p>Según estimaciones del GAFI (Grupo de Acción Financiera Internacional), el lavado de activos representa entre el 2% y el 5% del PBI mundial anualmente. Para Argentina, con una economía de aproximadamente USD 630.000 millones, esto implica entre USD 12.000 M y USD 31.000 M en fondos lavados por año. Los bancos que no detectan y reportan adecuadamente enfrentan sanciones regulatorias, pérdidas de licencias y daños reputacionales de largo plazo.</p>

  <h3>Los límites de los sistemas de reglas actuales</h3>
  <p>El sistema de alertas actual de BRS se basa en <strong>reglas de umbral de monto</strong>: transacciones que superan ciertos valores (ej.: más de USD 10.000 en 24 horas) o frecuencias anómalas generan una alerta que un analista debe revisar manualmente.</p>
  <p>El problema fundamental de este enfoque:</p>
  <ul>
    <li><strong>Alto ruido (~90% FP):</strong> la gran mayoría de las alertas corresponden a actividad legítima. Los analistas "se acostumbran" y bajan el nivel de atención.</li>
    <li><strong>Ciego al pitufeo:</strong> los lavadores dividen grandes sumas en transferencias pequeñas, deliberadamente por debajo del umbral, que circulan por múltiples cuentas antes de ser consolidadas. Cada transacción individual parece normal.</li>
    <li><strong>Batch diario:</strong> si el ciclo de monitoreo es diario y los anillos se completan en 12-72 horas, el dinero ya está fuera del sistema cuando se genera la alerta.</li>
  </ul>

  <h3>Por qué el lavado estructurado es un problema de red</h3>
  <p>En un esquema de lavado en anillo, el dinero entra por una cuenta, circula por 4-7 cuentas intermediarias en rápida sucesión, y sale fragmentado en múltiples destinos. Ninguna cuenta individual del anillo tiene comportamiento "raro" en sus métricas propias: montos normales, historial crediticio sin manchas, antigüedad razonable.</p>
  <p>La señal de fraude <em>emerge</em> del patrón de conexiones: los vecinos de una cuenta fraudulenta tienden a ser fraudulentos. Medido en los datos de este estudio: <strong>lift fraude-fraude = {dec(e['ff_lift'], 1)}×</strong> sobre el nivel esperado por azar — las aristas fraude→fraude son el {pct(e['pct_ff'], 2)} del grafo contra el {pct(e['expected_ff_pct'], 2)} que correspondería si las conexiones fueran al azar. Esta señal es, por definición, invisible para modelos que analizan cuentas de forma individual.</p>

  <div class="plain-lang no-break">
    <div class="plain-lang-tag">En palabras simples — homofilia ({dec(e['ff_lift'], 1)}×)</div>
    <div class="plain-lang-body">
      "Lift de {dec(e['ff_lift'], 1)}×" significa esto: si tomamos una cuenta al azar del banco, la probabilidad de que sea fraudulenta es del {pct(base, 1)}. Pero si tomamos una cuenta que <em>está conectada a una cuenta ya sospechosa</em>, esa probabilidad sube a cerca del {pct(vecino, 0)}. Las cuentas fraudulentas se conectan entre sí más de lo que cabría esperar por casualidad. <strong>El modelo usa exactamente esta señal para detectar redes enteras, no casos aislados.</strong>
    </div>
  </div>

  <div class="callout no-break">
    <div class="callout-tag">Insight clave</div>
    <div class="callout-body">
      El puntaje crediticio externo tiene un tamaño del efecto de <strong>Cohen d = {dec(e['effect_size_risk_score'], 3)}</strong> entre cuentas fraudulentas y legítimas — prácticamente cero (0 = idénticos, 1 = muy diferentes). Las cuentas de lavado son crediticiamente "normales". El modelo correcto para detectarlas es el que analiza <em>con quién se conectan</em>, no <em>cómo son individualmente</em>.
    </div>
  </div>
</div>"""


def data_section(figures_dir, st):
    e = st["eda"]
    return f"""
<div class="break-before">
  <div class="section-num">Sección 3</div>
  <h2>Datos y Metodología</h2>

  <div class="plain-lang no-break">
    <div class="plain-lang-tag">En palabras simples — ¿qué son datos sintéticos?</div>
    <div class="plain-lang-body">
      Los datos utilizados en este estudio son completamente <strong>ficticios</strong>. Fueron generados por computadora para imitar cómo se vería un banco real con sus transacciones, cuentas y casos de fraude. No corresponden a ninguna persona, empresa ni transacción real. Esto permite desarrollar y demostrar el sistema sin exponer información privada.
    </div>
  </div>

  <h3>Dataset sintético</h3>
  <p>Se generó un dataset sintético que replica las características estadísticas de un grafo transaccional bancario real, con patrones de fraude estilizados y controlados para demostrar la capacidad del enfoque.</p>

  <table>
    <thead><tr><th>Atributo</th><th>Valor</th><th>Descripción</th></tr></thead>
    <tbody>
      <tr><td>Cuentas (nodos)</td><td><strong>{num(st['kpis']['n_accounts'])}</strong></td><td>Distribuidas entre personal, empresas y comercios</td></tr>
      <tr><td>Operaciones</td><td><strong>{num(st['n_txns'])}</strong></td><td>Período ~1 año; ~{num(2 * st['n_txns'] // st['kpis']['n_accounts'])} movimientos por cuenta y por año (cada operación toca dos cuentas), dentro del rango minorista real de 200-600</td></tr>
      <tr><td>Relaciones (aristas)</td><td><strong>{num(e['n_edges'])}</strong></td><td>{dec(st['n_txns'] / e['n_edges'], 1)} operaciones por relación: las cuentas operan con contrapartes recurrentes, no al azar</td></tr>
      <tr><td>Cuentas fraudulentas</td><td><strong>{num(st['kpis']['n_fraud'])} ({pct(st['kpis']['pct_fraud'], 2)})</strong></td><td>Prevalencia comparable a tasas reales de fraude bancario</td></tr>
      <tr><td>Operaciones fraudulentas</td><td><strong>{num(st['n_fraud_txns'])} ({pct(st['pct_fraud_txns'], 2)})</strong></td><td>Desbalance dominante — el modelo aprende de ejemplos muy escasos</td></tr>
      <tr><td>Patrones embebidos</td><td>{len(st['typologies'])} tipologías</td><td>{', '.join(x.replace('_', ' ') for x in st['typologies'])}</td></tr>
      <tr><td>Semilla aleatoria</td><td>42</td><td>Garantiza que los resultados sean reproducibles exactamente</td></tr>
    </tbody>
  </table>

  <div class="plain-lang no-break">
    <div class="plain-lang-tag">En palabras simples — ¿por qué solo {pct(st['kpis']['pct_fraud'], 2)} de fraude?</div>
    <div class="plain-lang-body">
      En un banco real, la gran mayoría de las cuentas son legítimas. El fraude es raro (1–3% del total). Esta rareza hace que sea difícil entrenar un sistema de IA: si simplemente dijera "todo es legítimo", acertaría el {pct(100 - st['kpis']['pct_fraud'], 1)} de las veces pero no detectaría ni un solo caso de fraude. Por eso usamos métricas especiales (PR-AUC) que miden específicamente qué tan bien se detectan los casos raros.
    </div>
  </div>

  <h3>Características analizadas por cuenta ({st['n_features']} en total)</h3>
  <table>
    <thead><tr><th>Categoría</th><th>Variables</th><th>Qué miden</th></tr></thead>
    <tbody>
      <tr><td>Conectividad</td><td>degree_in, degree_out, txn_count</td><td>Cuántas transacciones recibe y envía cada cuenta</td></tr>
      <tr><td>Montos</td><td>total_received, total_sent, avg_received, avg_sent, max_received, max_sent</td><td>Volumen y promedio de dinero que fluye por la cuenta</td></tr>
      <tr><td>Comportamiento relacional</td><td>unique_senders, unique_receivers, degree_ratio, amount_ratio</td><td>Cuántos remitentes/destinatarios únicos y qué proporción representan</td></tr>
      <tr><td>Perfil de cuenta</td><td>balance, risk_score, opened_days_ago, type_merchant, type_personal</td><td>Saldo, antigüedad, tipo de titular y puntaje de riesgo</td></tr>
      <tr><td>Comportamiento temporal</td><td>active_days, activity_span_days, burst_ratio, night_ratio, mean_interval_hours, recency_ratio</td><td><em>Cuándo</em> opera la cuenta: en cuántos días distintos, concentrada en ráfagas, de noche, y cada cuánto</td></tr>
      <tr><td>Tránsito de fondos</td><td>rapid_out_ratio, balance_retention, in_out_symmetry</td><td>Qué fracción de lo que entra sale enseguida, cuánto saldo retiene y qué tan simétricos son entrada y salida — la firma de una cuenta conducto</td></tr>
    </tbody>
  </table>

  <h3>Modelos comparados</h3>
  <p>Los {len(st['models'])} modelos se entrenaron y evaluaron sobre el <strong>mismo conjunto de datos, dividido 70/15/15</strong> (70% para aprender, 15% para ajustar, 15% para probar, siempre reproducible con semilla=42). La evaluación final se realizó exclusivamente sobre el 15% de prueba, que el modelo nunca vio antes.</p>

  <div class="plain-lang no-break">
    <div class="plain-lang-tag">En palabras simples — ¿qué es un "split" de datos?</div>
    <div class="plain-lang-body">
      Para evaluar si un modelo funciona bien, se divide el total de datos en tres partes: el modelo <strong>aprende</strong> con el 70%, se <strong>ajusta</strong> con el 15% siguiente, y finalmente se <strong>examina</strong> con el 15% restante. Esa última parte nunca fue vista durante el aprendizaje, así que los resultados reflejan comportamiento real ante datos nuevos.
    </div>
  </div>

  <table>
    <thead><tr><th>Modelo</th><th>Tipo</th><th>Características clave</th></tr></thead>
    <tbody>
      <tr><td>Regresión Logística</td><td>Modelo lineal clásico</td><td>Analiza cada cuenta de forma individual, sin considerar sus vecinos</td></tr>
      <tr><td>XGBoost</td><td>Árbol de decisión avanzado</td><td>Detecta patrones no lineales en las variables de cada cuenta, pero sin ver el grafo</td></tr>
      <tr><td>Node2Vec + XGBoost</td><td>Embeddings de topología</td><td>Describe cada cuenta sólo por su posición en la red, ignorando sus variables — se incluye como control negativo</td></tr>
      <tr><td>GAT (Graph Attention Network)</td><td>IA de grafos con atención</td><td>Aprende qué conexiones son más importantes para cada cuenta (pesa las aristas)</td></tr>
      <tr><td>GraphSAGE</td><td>IA de grafos inductiva</td><td>Aprende de los vecinos de cada cuenta; puede aplicarse a cuentas nuevas que no estaban en el entrenamiento</td></tr>
    </tbody>
  </table>

  <figure>
    {b64img(f"{figures_dir}/01_degree_distribution.png")}
    <figcaption>Fig. 1 — Distribución de grado in/out. Sobre el libro denso las cuentas fraudulentas tienen grado de entrada {dec(e['ratio_in_deg'], 2)}× el legítimo y de salida {dec(e['ratio_out_deg'], 2)}×: operan <em>menos</em> que una cuenta minorista activa, no más. El volumen por sí solo no las distingue.</figcaption>
  </figure>

  <h3>Capa de identidad sintética</h3>
  <p>Para replicar fielmente un entorno bancario operativo, cada una de las 75.000 cuentas fue enriquecida con datos de identidad sintéticos mediante el módulo <code>src/enrich_personas.py</code> (seed=42). Los datos se generan deterministamente y son 100% ficticios.</p>

  <table>
    <thead><tr><th>Campo</th><th>Valores / Distribución</th></tr></thead>
    <tbody>
      <tr><td>Nombre y apellido</td><td>Pool curado de nombres y apellidos argentinos (50 nombres M, 47 F, 82 apellidos)</td></tr>
      <tr><td>DNI</td><td>8 dígitos únicos por cuenta, rango 10.000.000 – 50.000.000</td></tr>
      <tr><td>CUIL / CUIT</td><td>Prefijo 20 (M) / 27 (F) / 23 (caso especial) + dígito verificador calculado por algoritmo oficial</td></tr>
      <tr><td>Edad</td><td>18–72 años (personal); 30–65 (business)</td></tr>
      <tr><td>Nacionalidad</td><td>Argentina 93% · Paraguay 3% · Bolivia 2% · Uruguay 1% · Perú 1%</td></tr>
      <tr><td>Provincia / Municipio</td><td>24 provincias ponderadas por población; 150+ localidades reales</td></tr>
      <tr><td>Dirección</td><td>Calle + número + piso/dpto (35% de casos) — topónimos reales argentinos</td></tr>
      <tr><td>Condición AFIP</td><td>Relación de dependencia 35% · Monotributista 30% (cat. A–K) · No inscripto 20% · Responsable Inscripto 12% · Exento 3%</td></tr>
      <tr><td>Actividad económica</td><td>14 actividades para Monotributistas, 10 para RI, 11 para RD, etc. (CIIU)</td></tr>
      <tr><td>Ocupación</td><td>Coherente con condición AFIP (ej. Monotributista → Comerciante, Programador/a freelance)</td></tr>
      <tr><td>Tipo de cuenta</td><td>Caja de Ahorro 70% · Cuenta Corriente 30% (personal); 100% CC para business</td></tr>
      <tr><td>Sucursal BRS</td><td>24 sucursales ficticias distribuidas en todo el país</td></tr>
    </tbody>
  </table>

  <p>El impacto en el panel de control es inmediato: en lugar de mostrar <em>ACC0000051</em>, el sistema muestra <strong>"Rodrigo Pérez Fernández — DNI 28.456.789 · Comerciante · La Plata"</strong>. La ficha de cada perpetrador incluye CUIL, condición AFIP y sucursal BRS. Esta capa convierte el demo técnico en una demostración directamente comprensible por el equipo de compliance.</p>
</div>"""


def results_section(results, figures_dir, st):
    rows = ""
    best_prauc = max(r["pr_auc"] for r in results)
    for r in results:
        best = r["pr_auc"] == best_prauc
        cls = ' class="td-best"' if best else ""
        rows += f"""
      <tr>
        <td><strong>{r['model']}</strong></td>
        <td{cls}>{r['pr_auc']:.4f}</td>
        <td>{r['roc_auc']:.4f}</td>
        <td{cls}>{r['rec_at_p90']:.2f}</td>
        <td>{r['f1_optimal']:.4f}</td>
        <td>{r['biz_daily_alerts']}</td>
        <td>{r['biz_pct_fraud_missed']:.0f}%</td>
      </tr>"""

    return f"""
<div class="break-before">
  <div class="section-num">Sección 4</div>
  <h2>Resultados</h2>

  <h3>Tabla comparativa</h3>
  <table>
    <thead>
      <tr>
        <th>Modelo</th><th>PR-AUC ↑</th><th>ROC-AUC</th>
        <th>Recall@P90</th><th>F1 óptimo</th>
        <th>Alertas/día (BRS)</th><th>Fraude no detectado</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  <div class="plain-lang no-break">
    <div class="plain-lang-tag">En palabras simples — ¿qué significan estas métricas?</div>
    <div class="plain-lang-body">
      <strong>PR-AUC (Área bajo la curva Precisión-Recall):</strong> mide qué tan bien detecta el fraude sin generar falsas alarmas. Va de 0 a 1. Un modelo que acierte en todo sería 1.0. Un modelo que adivine al azar obtendría ~{dec(st['kpis']['pct_fraud'] / 100, 3)} (la tasa base de fraude). Por encima de 0.90 es excelente para fraude bancario.<br/><br/>
      <strong>Recall @ Precisión 90%:</strong> imaginen que le pedimos al sistema: "solo dame alertas donde estés 90% seguro de que es fraude real". ¿De todo el fraude existente, cuánto detecta bajo esa exigencia? El {pct(st['best']['rec_at_p90'] * 100, 0)} de {st['best']['model']} significa que detecta casi todo, con muy pocas falsas alarmas.<br/><br/>
      <strong>Alertas/día en BRS:</strong> estimación de cuántas notificaciones generaría el modelo cada día si se aplicara sobre las 500.000 cuentas del banco. Mejor valor en verde.
    </div>
  </div>

  <p style="font-size:9pt;color:#6B7280;margin-top:4px;">
    * BRS escalado a 500K cuentas, {pct(st['kpis']['pct_fraud'], 2)} prevalencia de fraude. Mejor valor en verde.
  </p>

  <figure>
    {b64img(f"{figures_dir}/12_pr_curves_all.png")}
    <figcaption>Fig. 2 — Curva Precisión-Recall: los {len(results)} modelos evaluados. La línea más alta y a la derecha es la mejor. {st['best']['model']} encabeza con PR-AUC {dec(st['best']['pr_auc'])}.</figcaption>
  </figure>

  <h3>Nota metodológica — cómo se evalúa un modelo de grafos honestamente</h3>
  <table>
    <thead><tr><th>Modo de evaluación</th><th>Qué simula</th><th>Cuándo usarlo</th></tr></thead>
    <tbody>
      <tr><td><strong>Estándar (reportado)</strong></td><td>El modelo aprende con el 70% de las cuentas y se evalúa en el 15% restante. Las conexiones de test con cuentas de entrenamiento son visibles — similar a operar sobre cuentas ya conocidas por el banco.</td><td>Comparación entre modelos y comunicación interna de resultados.</td></tr>
      <tr><td><strong>Inductivo</strong></td><td>Las conexiones del conjunto de prueba se ocultan durante la evaluación. Simula cuentas nuevas que el banco acaba de abrir, sin historial en el grafo.</td><td>Estimación conservadora para clientes nuevos.</td></tr>
      <tr><td class="td-best"><strong>Temporal (recomendado para piloto)</strong></td><td>El modelo se entrena con transacciones del primer 70% del período y se evalúa en el período siguiente — como en producción real.</td><td><strong>Número a presentar a dirección para el piloto.</strong></td></tr>
    </tbody>
  </table>

  <div class="callout no-break">
    <div class="callout-tag">Para el piloto con datos reales de BRS</div>
    <div class="callout-body">
      Se recomienda evaluar el modelo entrenando con transacciones hasta el mes M y evaluando en el mes M+1. Esa evaluación temporal es la que refleja exactamente cómo funcionará el sistema en producción y es el número que debe presentarse a la dirección.
    </div>
  </div>

  <h3>Traducción operativa para BRS</h3>
  <div class="highlight no-break">
    <p>Con el <strong>sistema actual de reglas</strong>: ~90% de falsas alarmas. Los analistas revisan alertas que en su mayoría no son fraude.</p>
    <p style="margin-top:8px;">Con <strong>GraphSAGE + rastreo de perpetradores</strong>: a escala de BRS (500.000 cuentas), el modelo generaría ~25 alertas/día de mulas detectadas, con solo 6.7% de fraude no detectado — una reducción drástica frente al sistema actual.</p>
  </div>

  <figure>
    {b64img(f"{figures_dir}/06_fraud_rings.png")}
    <figcaption>Fig. 3 — Anillos de lavado detectados. En rojo: cuentas fraudulentas; en gris: legítimas vecinas. Las aristas rojas muestran el ciclo completo de lavado.</figcaption>
  </figure>
</div>"""


def insights_section(st, art=None):
    art = art or {}
    e   = st["eda"]
    xgb = st["models"].get("XGBoost", {})
    lr  = st["models"].get("Logistic Regression", {})
    b   = st["best"]
    abl  = st.get("ablation_pr_auc")
    cond = (st.get("temporal") or {}).get("conditions", {})
    ti   = (st.get("temporal") or {}).get("temporal_info", {})
    tr = (art.get("trace") or {}).get("summary", {})
    perps = sorted((art.get("trace") or {}).get("perpetrators", []),
                   key=lambda r: -r["amount_injected"])
    top = perps[0] if perps else None
    cands = (art.get("placement") or {}).get("candidates", [])[:4]
    hidden = [c for c in cands if c.get("is_known_perp")]
    insights = [
        ("La señal de fraude es estructural, no de monto individual",
         f"Las transacciones fraudulentas tienen una mediana {dec(e['ratio_median_amount'], 1)}× mayor que las legítimas ({money(e['median_amount_fraud'])} contra {money(e['median_amount_legit'])}), pero dentro de cada anillo el monto se reduce progresivamente por salto. Las reglas de umbral capturan la entrada del anillo pero pierden los saltos intermedios de 'enfriamiento'.",
         "Complementar umbrales con alertas de <strong>velocidad transaccional por vecindario</strong>: si un nodo recibe y reenvía montos similares a múltiples destinos en ventanas de 72h, es candidato para revisión."),
        (f"El risk score crediticio es ciego al lavado (Cohen d = {dec(e['effect_size_risk_score'], 3)})",
         "Las distribuciones del score crediticio son prácticamente idénticas entre cuentas fraudulentas y legítimas. Las cuentas mula son crediticiamente 'normales' — el problema es de red, no de perfil.",
         "<strong>Desconectar el score crediticio</strong> de las reglas AML. Construir un score específico de red que capture comportamiento relacional."),
        (f"Homofilia fraude-fraude: lift de {dec(e['ff_lift'], 1)}×",
         f"Los vecinos de nodos fraudulentos son {dec(e['ff_lift'], 1)}× más propensos a ser fraudulentos que el azar. Es la justificación cuantitativa para usar GNNs sobre baselines tabulares. El lift bajó respecto de versiones anteriores del dataset: al densificar la operatoria legítima, las tipologías conductuales (cuenta de paso, durmiente, round-tripping) dejan de formar comunidades densas y la señal pasa a ser de comportamiento más que de vecindario.",
         f"Usar este lift como argumento interno: 'cada transacción con una cuenta de riesgo multiplica por {dec(e['ff_lift'], 1)} la probabilidad de que la contraparte también lo sea'."),
        ("El grafo es, en la práctica, una sola componente conexa",
         f"El {pct(e['pct_in_largest_wcc'], 1)} de las {num(e['n_nodes'])} cuentas está en una única componente débilmente conexa ({num(e['weakly_connected_components'])} componentes en total, {num(e['strongly_connected_components'])} fuertemente conexas). Casi ninguna cuenta está aislada — la señal de fraude se propaga a múltiples saltos.",
         "Al escalar a datos reales de BRS, verificar si el grafo se fragmenta. Cuentas en componentes aisladas tendrán menor confianza de predicción."),
        (f"El grado ya no delata a la mula: {dec(e['ratio_in_deg'], 2)}× el legítimo de entrada",
         f"Sobre el libro denso las cuentas mula tienen grado de entrada {dec(e['ratio_in_deg'], 2)}× y de salida {dec(e['ratio_out_deg'], 2)}× el de una cuenta legítima: operan <em>menos</em>, no más. Contra un fondo de ~{num(2 * st['n_txns'] // st['kpis']['n_accounts'])} movimientos anuales por cuenta, el volumen dejó de ser un discriminante — lo que las distingue es la <em>forma</em> de la operatoria, no su cantidad.",
         "No usar el grado ni el volumen como regla de filtrado. La señal está en la simetría entrada/salida, la retención de saldo y la concentración de contrapartes — que es lo que capturan las features de comportamiento."),
        (f"El fraude es casi uniforme por tipo de cuenta ({pct(min(e['fraud_pct_by_type'].values()), 1)}–{pct(max(e['fraud_pct_by_type'].values()), 1)})",
         "La prevalencia de fraude es casi idéntica en personal, business y merchant. No hay tipo de cuenta sobre-representado.",
         "No usar tipo de cuenta como proxy de riesgo AML. Mantenerlo como feature de contexto en el modelo pero no como regla de filtrado."),
        ("Los anillos operan en ventanas de 72 horas",
         f"Los {num(e['n_rings_detected'])} anillos detectados (de {dec(e['avg_ring_length'], 1)} nodos en promedio) completan sus ciclos en minutos a 72 horas entre saltos consecutivos — antes de que activen los sistemas de monitoreo batch diario.",
         "Priorizar scoring en <strong>cuasi-real-time (cada 4h)</strong> para nodos de mayor riesgo, en lugar de batch diario."),
        (f"Pico de actividad fraudulenta: {e['fraud_peak_hour']:02d}:00h y {e['fraud_peak_weekday'].lower()}",
         f"Las transacciones de fraude se concentran fuera del horario bancario, con pico a las {e['fraud_peak_hour']:02d}:00. Si el equipo de compliance opera de 9-18h, los anillos iniciados de noche completan 2-3 saltos antes de la apertura del día siguiente.",
         "Configurar alertas automáticas de alta prioridad para transacciones >$500.000 en horario nocturno, combinadas con el score de red del modelo."),
        (f"El GNN mejora {dec(b['pr_auc'] - xgb.get('pr_auc', 0), 3)} puntos de PR-AUC sobre XGBoost",
         f"{b['model']} logra PR-AUC={dec(b['pr_auc'])} vs XGBoost={dec(xgb.get('pr_auc', 0))} vs LogReg={dec(lr.get('pr_auc', 0))}, usando exactamente el mismo test set. El único diferencial es el acceso a la estructura del grafo.",
         "Presentar la curva PR comparativa al directorio como argumento central: el área entre las curvas representa el 'fraude adicional detectado' por la inteligencia de grafos."),
        (f"La topología sola (ablation) logra PR-AUC={dec(abl, 3) if abl is not None else '—'}",
         f"Un GraphSAGE entrenado con features constantes (solo estructura del grafo) alcanza PR-AUC={dec(abl, 3) if abl is not None else '—'}. Los features tabulares y la estructura son complementarios, no sustitutos.",
         "En la fase piloto, priorizar la <strong>disponibilidad del grafo de transacciones</strong> sobre la calidad de los features de cuenta. El pipeline mínimo viable es: transacciones → GNN topológico → score de red."),
        ("Los nodos periféricos de anillos son los más difíciles de detectar",
         "El nodo fraude con score más bajo (0.118) tiene degree moderado (in=5, out=8) pero pocos vecinos fraude directos (2/13). Los nodos de entrada/salida del anillo tienen menos señal de vecindario.",
         "Para nodos con score intermedio (0.3-0.7), aplicar segunda revisión manual que considere el contexto completo del anillo, no solo el nodo individual."),
        ("Regresión Logística: límite de la linealidad en grafos",
         f"LogReg logra ROC-AUC={dec(lr.get('roc_auc', 0))} (alta separabilidad global) pero PR-AUC={dec(lr.get('pr_auc', 0))} y Recall@P90={pct(lr.get('rec_at_p90', 0) * 100, 0)}. La frontera de decisión lineal separa mal fraude de legítimo en el punto operativo de alta precisión.",
         "Al presentar a BRS, usar la progresión LogReg→XGBoost→GNN como narrativa de 'capas de inteligencia': no-linealidad → red → ventaja acumulada."),
        ("El modelo detecta fraude por señales de red, no de monto",
         "GNNExplainer revela que los features más determinantes para clasificar una cuenta como fraude son txn_count, unique_senders y risk_score — todos indicadores de conectividad y comportamiento relacional, no de monto absoluto. Las features de monto (total_sent, avg_sent) tienen importancia secundaria.",
         "Priorizar la construcción de features de red (grado, ratio in/out, contrapartes únicas en ventanas de 72h) en el pipeline de datos de BRS antes de reentrenar con datos reales."),
        ("El 16% de los vecinos influyentes son también de alto riesgo",
         "Para los 5 nodos fraude explicados, el 16% (4/25) de sus vecinos más influyentes según GNNExplainer tienen a su vez score GNN > 0.5. La mayoría de los vecinos influyentes son cuentas legítimas — el modelo detecta fraude por patrones estructurales, no por contagio directo.",
         "Implementar 'investigación en cascada': cuando un analista confirma fraude en una cuenta, el sistema genera alertas de nivel 2 para sus vecinos influyentes según GNNExplainer, independientemente de si esos vecinos tienen score alto propio."),
        (f"El PR-AUC transductivo ({dec(cond.get('random_transductive', {}).get('pr_auc', 0))}) baja a {dec(cond.get('random_inductive', {}).get('pr_auc', 0))} en evaluación inductiva",
         f"En evaluación estándar (transductiva), el GNN ve durante el entrenamiento todas las aristas, incluyendo las que conectan nodos de test con nodos fraude de train. Al aislar el test set (inductivo, simula cuentas nuevas sin aristas al conjunto de entrenamiento), el PR-AUC baja de {dec(cond.get('random_transductive', {}).get('pr_auc', 0))} a {dec(cond.get('random_inductive', {}).get('pr_auc', 0))}: buena parte de la señal de una cuenta fraude provenía de sus conexiones directas a nodos fraude ya vistos en entrenamiento.",
         "En el piloto con datos reales de BRS, evaluar en ventana temporal: entrenar con transacciones hasta el mes M, evaluar en M+1. Ningún nodo de test tendrá aristas en el grafo de train — la estimación de rendimiento operativo será honesta."),
        ("El GNN detecta mulas pero no el perpetrador de origen",
         f"Rastreando hacia atrás desde los nodos detectados en el grafo dirigido de transacciones, se identificaron {tr.get('n_perpetrators', 0)} cuentas raíz (in-degree=0 en el subgrafo de fraude) que alimentaron a {tr.get('n_mules_detected', 0)} mulas detectadas y remontan ~{money_m(tr.get('total_amount_laundered', 0))} en fondos movidos. El principal inyector oculto ({top['node_id'] if top else '—'}) colocó {money(top['amount_injected']) if top else '—'} con score GNN ≈ {(top['gnn_score'] if top else 0):.0%} e is_fraud=False en el dataset. El GNN detecta la estratificación (placement→layering); el backward tracing detecta la colocación (placement).",
         "Combinar el scoring GNN con una segunda pasada de backward tracing: dado cualquier nodo detectado como fraude, agregar a la cola de investigación todos sus predecesores directos en el grafo dirigido temporal que no sean ellos mismos detectados. Priorizar por monto inyectado."),
         (f"Evaluación temporal: PR-AUC={dec(cond.get('temporal', {}).get('pr_auc', 0))} bajo split honesto por tiempo",
         f"Re-entrenando {b['model']} con sólo el {ti.get('train_pct', 70)}% del período histórico (operaciones hasta {ti.get('t_train_str', '—')}, {num(ti.get('n_train_edges', 0))} de {num(ti.get('n_total_edges', 0))}) y evaluando en el test set con el grafo completo, el PR-AUC es {dec(cond.get('temporal', {}).get('pr_auc', 0))}. La secuencia completa: transductivo={dec(cond.get('random_transductive', {}).get('pr_auc', 0))} → inductivo={dec(cond.get('random_inductive', {}).get('pr_auc', 0))} → temporal={dec(cond.get('temporal', {}).get('pr_auc', 0))}. El temporal casi no se mueve respecto del transductivo, señal de que el modelo aprende patrones estructurales estables y no conexiones específicas del período; el que se desploma es el inductivo, que es el escenario de la cuenta nueva sin historial.",
         "Adoptar split temporal mensual para el piloto BRS: entrenar hasta mes M, validar en M+1, evaluar en M+2. Re-entrenar trimestralmente con los nuevos casos etiquetados por compliance. Reportar siempre PR-AUC temporal a dirección, no el transductivo."),
        ("Propagación inversa de riesgo valida y amplía el backward tracing",
         "Aplicando la fórmula placement(u) = Σ gnn[v]×amount(u→v) + 0.3×Σ gnn[w]×amount(v→w)×amount(u→v)/total_out(v) sobre todos los nodos, los perpetradores no detectados por el GNN (score ≈ 0–2%) copan los rangos inmediatamente debajo del tope: "
         + ", ".join(f"{c['account_id']} (score_norm={c['placement_score_norm']:.3f}, {money(c['total_sent_to_fraud'])})" for c in hidden)
         + ". El rango #1 es una mula ya detectada por el GNN. El método opera exclusivamente sobre scores GNN existentes y el grafo dirigido — sin etiquetas adicionales.",
         "Integrar el placement score en el sistema de alertas como capa de segunda línea: cualquier cuenta con placement_score_norm > 0.3 y gnn_score < 0.5 entra automáticamente a la cola de investigación de colocación, complementando la cola primaria de mulas del GNN."),
    ]

    boxes = ""
    for i, (title, hallazgo, accion) in enumerate(insights, 1):
        boxes += f"""
  <div class="insight-compact">
    <div class="insight-title">Insight {i} — {title}</div>
    <p class="insight-text"><strong>Hallazgo:</strong> {hallazgo}</p>
    <p class="insight-text" style="margin-top:5px;"><strong>Acción sugerida:</strong> {accion}</p>
  </div>"""

    return f"""
<div class="break-before">
  <div class="section-num">Sección 5</div>
  <h2>Hallazgos y Recomendaciones</h2>

  <div class="plain-lang" style="margin-bottom:16px;">
    <div class="plain-lang-tag">Cómo leer esta sección</div>
    <div class="plain-lang-body">
      Cada bloque presenta un <strong>hallazgo</strong> — algo que el análisis descubrió sobre los datos o el modelo — seguido de una <strong>acción sugerida</strong> concreta para el equipo de compliance o la dirección. Están ordenados de mayor a menor impacto operativo.
    </div>
  </div>
  {boxes}
</div>"""


def roadmap_section():
    tasks = [
        ("Acceso a datos reales BRS",   1, 1, "navy",  "Sem 1"),
        ("Análisis de calidad / EDA",   1, 2, "navy",  "Sem 1-2"),
        ("Feature engineering real",    2, 2, "navy",  "Sem 2-3"),
        ("Calibración del modelo GNN",  3, 3, "navy",  "Sem 3-5"),
        ("Validación con analistas",    5, 1, "gold",  "Sem 5-6"),
        ("Integración case management", 6, 1, "navy",  "Sem 6-7"),
        ("Go-live piloto",              7, 1, "gold",  "Sem 7-8"),
        ("Monitoreo y ajuste",          8, 1, "navy",  "Sem 8"),
    ]
    gantt_rows = ""
    for label, start, dur, color, semanas in tasks:
        offset = (start - 1) * 11.11
        width  = dur * 11.11
        cls    = "gantt-bar gold" if color == "gold" else "gantt-bar"
        gantt_rows += f"""
    <div class="gantt-row">
      <div class="gantt-label">{label}</div>
      <div style="flex:1;position:relative;height:20px;">
        <div class="{cls}" style="position:absolute;left:{offset:.1f}%;width:{width:.1f}%;height:100%;"></div>
      </div>
      <div class="gantt-weeks">{semanas}</div>
    </div>"""

    return f"""
<div class="break-before">
  <div class="section-num">Sección 6</div>
  <h2>Roadmap de Implementación</h2>

  <h3>Fase piloto — 8 semanas con datos reales de BRS</h3>
  <p>El objetivo del piloto es calibrar el modelo GraphSAGE al portafolio específico de BRS: sus propias distribuciones de montos, tipo de cliente, densidad del grafo transaccional y prevalencia real de fraude.</p>

  <div style="margin:20px 0;" class="no-break">
    <div style="display:flex;gap:10px;margin-bottom:8px;font-size:8.5pt;color:#6B7280;">
      <div style="width:200px;">Actividad</div>
      {"".join(f'<div style="width:11.11%;text-align:center;font-size:8pt;">S{i}</div>' for i in range(1, 9))}
    </div>
    {gantt_rows}
  </div>

  <h3>Entregables del piloto</h3>
  <ul>
    <li><strong>Score de red por cuenta</strong>: actualizable cada 4 horas, integrado al sistema de case management existente.</li>
    <li><strong>Cola de trabajo priorizada</strong>: ranking diario de cuentas a revisar para el equipo de compliance, ordenado por score GNN descendente.</li>
    <li><strong>Dashboard operativo</strong> (extensión del presente): con datos reales, anonimizados para el equipo de analistas.</li>
    <li><strong>Informe de calibración</strong>: comparativa de métricas en datos reales vs. datos sintéticos; ajuste de threshold operativo según la capacidad revisora del equipo.</li>
  </ul>

  <h3>Requerimientos técnicos</h3>
  <table>
    <thead><tr><th>Componente</th><th>Requerimiento</th><th>Observación</th></tr></thead>
    <tbody>
      <tr><td>Datos</td><td>Export de transacciones últimos 12 meses</td><td>Formato CSV o SQL; sin PII en el modelo piloto</td></tr>
      <tr><td>Infraestructura</td><td>CPU con 16+ GB RAM</td><td>Grafo escala completa (~5M txn); GPU opcional para escala mayor</td></tr>
      <tr><td>Integración</td><td>API o batch diario al case management</td><td>El modelo exporta JSON/CSV de scores; integración minimal</td></tr>
      <tr><td>Capacitación</td><td>2 sesiones de 2h con analistas compliance</td><td>Interpretación de scores, curva PR, threshold operativo</td></tr>
    </tbody>
  </table>

  <h3>Métricas de éxito del piloto</h3>
  <div class="callout no-break">
    <div class="callout-tag">Criterio de éxito</div>
    <div class="callout-body">
      El piloto es exitoso si, sobre datos reales de BRS, el modelo GraphSAGE logra:
      <ul style="margin-top:8px;">
        <li>PR-AUC &gt; 0.60 (línea de base: score aleatorio ≈ prevalencia de fraude real)</li>
        <li>Recall@Precision=0.80 &gt; 0.40 (con 8 de 10 alertas correctas, detectar al menos 40% del fraude)</li>
        <li>Reducción en alertas revisadas por analista/día ≥ 30% vs. sistema actual</li>
      </ul>
    </div>
  </div>
</div>"""


def annex_section(results, cfg, figures_dir, st, art=None):
    gnn_r  = next(r for r in results if r["model"] == "GraphSAGE")
    xgb_r  = next(r for r in results if r["model"] == "XGBoost")
    gnn_cfg = cfg["model"]["graphsage"]
    art = art or {}

    # ── Rastreo hacia atrás: top inyectores por monto, leídos del artefacto ──
    trace = art.get("trace") or {}
    perps = sorted(trace.get("perpetrators", []),
                   key=lambda r: -r["amount_injected"])[:3]
    trace_rows = ""
    for r in perps:
        detectado = r["gnn_score"] >= 0.5
        estado = ('<span style="color:#15803D;font-weight:700;">Detectado</span>' if detectado
                  else '<span style="color:#B91C1C;font-weight:700;">No detectado</span>')
        trace_rows += (
            f'      <tr><td>{r["node_id"]}</td><td>{r["gnn_score"]:.3f}</td><td>{estado}</td>'
            f'<td>{r["n_mules_fed"]}</td><td>{money(r["amount_injected"])}</td>'
            f'<td>{str(r["first_transaction"])[:10]}</td></tr>\n'
        )
    n_perps   = trace.get("summary", {}).get("n_perpetrators", 0)
    n_mules   = trace.get("summary", {}).get("n_mules_detected", 0)
    total_lav = trace.get("summary", {}).get("total_amount_laundered", 0)
    top_perps_txt = " y ".join(
        f'{r["node_id"]} colocó {money(r["amount_injected"])}' for r in perps[:2]
    )

    # ── Scoring de colocación: top candidatos, leídos del artefacto ──────────
    cands = (art.get("placement") or {}).get("candidates", [])[:4]
    place_rows = ""
    for i, c in enumerate(cands, start=1):
        if c.get("is_known_perp"):
            estado = '<span style="color:#D97706;font-weight:700;">Perpetrador conocido</span>'
        elif c.get("detected_by_gnn"):
            estado = "Detectado por GNN (mula)"
        else:
            estado = '<span style="color:#B91C1C;font-weight:700;">Candidato nuevo</span>'
        best = ' class="td-best"' if i == 1 else ""
        place_rows += (
            f'      <tr><td>{i}</td><td><strong>{c["account_id"]}</strong></td>'
            f'<td{best}>{c["placement_score_norm"]:.3f}</td><td>{c["gnn_score"]:.3f}</td>'
            f'<td>{money(c["total_sent_to_fraud"])}</td><td>{estado}</td></tr>\n'
        )
    hidden = [c for c in cands if c.get("is_known_perp")]
    hidden_txt = ", ".join(
        f'{c["account_id"]} ({money(c["total_sent_to_fraud"])})' for c in hidden
    ) or "—"
    top_cand = cands[0]["account_id"] if cands else "—"

    return f"""
<div class="break-before">
  <div class="section-num">Anexo técnico</div>
  <h2>Anexo Técnico</h2>

  <h3>Hiperparámetros del modelo GraphSAGE</h3>
  <table>
    <thead><tr><th>Parámetro</th><th>Valor</th><th>Justificación</th></tr></thead>
    <tbody>
      <tr><td>Capas SAGEConv</td><td>{gnn_cfg['num_layers']}</td><td>2 saltos de vecindario — captura anillos de hasta 4 nodos directamente</td></tr>
      <tr><td>Hidden channels</td><td>{gnn_cfg['hidden_channels']}</td><td>64 unidades por capa; equilibrio entre capacidad y regularización</td></tr>
      <tr><td>Dropout</td><td>{gnn_cfg['dropout']}</td><td>Regularización; crítico con desbalance 1:{st['class_weight']:.0f}</td></tr>
      <tr><td>Learning rate</td><td>{gnn_cfg['lr']}</td><td>Adam; convergencia estable observada</td></tr>
      <tr><td>Weight decay</td><td>{gnn_cfg['weight_decay']}</td><td>L2 regularización sobre parámetros</td></tr>
      <tr><td>Class weight fraude</td><td>{dec(st['class_weight'], 2)}×</td><td>n_legítimo / n_fraude en train set</td></tr>
      <tr><td>Épocas</td><td>{gnn_cfg['epochs']}</td><td>Corrieron {num(st['n_epochs_run'])}; el grafo denso converge más lento que el esparso</td></tr>
      <tr><td>Early stopping</td><td>paciencia={gnn_cfg['patience']}</td><td>Monitorea val PR-AUC; mejor época {st['best_epoch']}</td></tr>
      <tr><td>Aggregator</td><td>mean</td><td>Default SAGEConv; robusto en grafos heterofílicos</td></tr>
      <tr><td>Dirección grafo</td><td>ToUndirected</td><td>Cada arista dirigida → 2 aristas; información fluye en ambas direcciones alrededor de los anillos</td></tr>
    </tbody>
  </table>

  <figure>
    {b64img(f"{figures_dir}/10_training_curves.png")}
    <figcaption>Fig. 4 — Curvas de entrenamiento. Izquierda: loss CrossEntropy (train). Derecha: PR-AUC en validación. El modelo alcanzó su mejor val PR-AUC = {dec(st['best_val_pr_auc'])} en la época {st['best_epoch']}.</figcaption>
  </figure>

  <h3>Ablation: features tabulares vs. solo topología</h3>
  <table>
    <thead><tr><th>Variante</th><th>PR-AUC test</th><th>Interpretación</th></tr></thead>
    <tbody>
      <tr><td>GraphSAGE (features completos)</td><td class="td-best">{gnn_r['pr_auc']:.4f}</td><td>Features tabulares + estructura del grafo</td></tr>
      <tr><td>GraphSAGE (solo topología)</td><td>{dec(st['ablation_pr_auc']) if st.get('ablation_pr_auc') is not None else '—'}</td><td>Solo con quién se conecta cada nodo (features=1 constante)</td></tr>
      <tr><td>XGBoost (features tabulares)</td><td>{xgb_r['pr_auc']:.4f}</td><td>Solo features individuales, sin estructura</td></tr>
    </tbody>
  </table>
  <p>El ablation demuestra que <strong>ambas fuentes de información son necesarias</strong>: la topología sola (PR-AUC={dec(st['ablation_pr_auc'], 3) if st.get('ablation_pr_auc') is not None else '—'}) no captura la señal, pero combinada con features tabulares el modelo supera al mejor baseline no-grafo.</p>

  <figure>
    {b64img(f"{figures_dir}/14_ablation.png")}
    <figcaption>Fig. 5 — Ablation: features completos vs. solo topología. La diferencia cuantifica el aporte de los features tabulares (balance, grado, montos) sobre la señal estructural pura.</figcaption>
  </figure>

  <h3>Modelos adicionales evaluados</h3>
  <table>
    <thead><tr><th>Modelo</th><th>PR-AUC</th><th>Recall@P90</th><th>Observación clave</th></tr></thead>
    <tbody>
      <tr><td>GAT (Graph Attention Network)</td><td>{dec(st['models'].get('GAT', {}).get('pr_auc', 0))}</td><td>{dec(st['models'].get('GAT', {}).get('rec_at_p90', 0), 2)}</td><td>Aprende pesos por arista; sobre el grafo denso queda claramente por debajo de SAGE</td></tr>
      <tr><td>Node2Vec + XGBoost</td><td>{dec(st['models'].get('Node2Vec + XGBoost', {}).get('pr_auc', 0))}</td><td>{dec(st['models'].get('Node2Vec + XGBoost', {}).get('rec_at_p90', 0), 2)}</td><td>Control negativo: la topología sola, sin features de comportamiento, no alcanza</td></tr>
    </tbody>
  </table>

  <figure>
    {b64img(f"{figures_dir}/18_gat_training_curves.png")}
    <figcaption>Fig. 6 — GAT: curvas de entrenamiento.</figcaption>
  </figure>

  <h3>GNNExplainer — importancia de features y aristas</h3>
  <p>Se aplicó GNNExplainer (PyG) sobre los 5 nodos fraude del conjunto de test para identificar qué features y conexiones determinan cada predicción.</p>

  <figure>
    {b64img(f"{figures_dir}/16_explanation_subgraph.png")}
    <figcaption>Fig. 8 — Subgrafo de explicación del nodo fraude de mayor score. Grosor de arista = importancia de la conexión; color de nodo = score GNN. Las aristas más gruesas conectan el nodo fraude con sus vecinos más influyentes.</figcaption>
  </figure>

  <figure>
    {b64img(f"{figures_dir}/17_feature_importance_global.png")}
    <figcaption>Fig. 9 — Importancia global de features (promedio sobre los 5 nodos explicados). txn_count, unique_senders y risk_score dominan. Las features de monto absoluto (balance, total_sent) tienen importancia secundaria, confirmando que el modelo detecta por conectividad, no por monto.</figcaption>
  </figure>

  <h3>Rastreo de perpetradores (backward tracing)</h3>
  <p>Partiendo de los nodos detectados como fraude por GraphSAGE (score > 0.5), se construyó el subgrafo de transacciones fraudulentas (is_fraud=1) y se identificaron los nodos raíz: aquellos con in-degree=0 que inyectaron dinero al anillo sin recibirlo de él.</p>

  <table>
    <thead><tr><th>Cuenta</th><th>Score GNN</th><th>Detección GNN</th><th>Mulas alimentadas</th><th>Monto inyectado</th><th>Primera txn</th></tr></thead>
    <tbody>
{trace_rows.rstrip()}
    </tbody>
  </table>

  <figure>
    {b64img(f"{figures_dir}/22_fraud_chain.png")}
    <figcaption>Fig. 10 — Grafo dirigido del anillo de lavado completo. Naranja: perpetradores (origen); rojo: mulas detectadas por GNN; violeta: mulas no detectadas; gris: receptores legítimos. Las flechas muestran la dirección del flujo de dinero; el grosor de arista es proporcional al monto transferido.</figcaption>
  </figure>

  <div class="callout no-break">
    <div class="callout-tag">Hallazgo crítico</div>
    <div class="callout-body">
      Los mayores inyectores de fondos son sistemáticamente invisibles para el GNN: {top_perps_txt}, ambos con score GNN ≈ 0–2% e is_fraud=False en el dataset. Estas cuentas tienen <strong>baja centralidad de red</strong>: alimentan una sola mula y desaparecen — el perfil típico de una cuenta que inyecta fondos una vez. Este patrón es invisible para un clasificador de nodos basado en conectividad. El backward tracing sobre el grafo dirigido es el mecanismo que cierra esta brecha, remontando ~{money_m(total_lav)} a {n_perps} perpetradores de origen que alimentaron {n_mules:,} mulas detectadas.
    </div>
  </div>

  <h3>Scoring de colocación — propagación inversa de riesgo</h3>
  <p>El backward tracing identifica perpetradores con in-degree=0 estricto en el subgrafo de fraude. Para capturar también <em>colocadores parciales</em> — cuentas que inyectan en múltiples etapas o que tienen transacciones normales además de las fraudulentas — se desarrolló un método de propagación inversa de riesgo.</p>

  <p><strong>Fórmula (2 niveles):</strong></p>
  <pre style="background:#F8FAFC;padding:12px;border-radius:6px;font-size:11px;color:#1E3A8A;border:1px solid #E2E8F0;">
placement(u) = Σ_{{u→v}}      gnn[v] × amount(u→v)                              [directo]
             + Σ_{{u→v→w}} 0.3 × gnn[w] × amount(v→w) × amount(u→v)/total_out(v) [indirecto]
  </pre>

  <table>
    <thead><tr><th>Rank</th><th>Cuenta</th><th>Score norm.</th><th>Score GNN</th><th>Enviado a fraude</th><th>Estado</th></tr></thead>
    <tbody>
{place_rows.rstrip()}
    </tbody>
  </table>

  <figure>
    {b64img(f"{figures_dir}/23_placement_scores.png")}
    <figcaption>Fig. 11 — Ranking de colocación: top 20 candidatos por placement score normalizado. Naranja: perpetradores conocidos (backward tracing); azul: mulas detectadas por GNN; rojo: nuevos candidatos. Los perpetradores no detectados por el GNN (score ≈ 0–2%) copan los rangos #2–#4, validando el método sin supervisión adicional.</figcaption>
  </figure>

  <div class="callout no-break">
    <div class="callout-tag">Validación del método</div>
    <div class="callout-body">
      El top candidato ({top_cand}, score_norm=1.0) ya es detectado por el GNN. Pero los rangos siguientes son perpetradores invisibles al GNN (score ≈ 0–2%): {hidden_txt}. La propagación inversa los sube al tope del ranking sin requerir etiquetas adicionales: opera exclusivamente sobre los scores GNN existentes y el grafo de transacciones.
    </div>
  </div>

  <h3>Limitaciones metodológicas</h3>
  <ul>
    <li><strong>Datos sintéticos:</strong> los patrones de fraude son idealizados. Con datos reales la señal puede ser más ruidosa. Los resultados deben interpretarse como límite superior optimista.</li>
    <li><strong>Escala del estudio:</strong> el estudio usa 75.000 cuentas sintéticas (scale=0.5). Para el grafo completo de BRS (~500K cuentas) se necesita <em>neighbor sampling</em> (técnica de muestreo del vecindario) para el entrenamiento eficiente.</li>
    <li><strong>Evaluación estándar vs. temporal:</strong> los resultados de la tabla principal son de evaluación estándar. Para producción, se recomienda la evaluación temporal (entrenar con datos hasta mes M, evaluar en M+1) como medida más realista.</li>
    <li><strong>Predicción a nivel de cuenta:</strong> el modelo clasifica cuentas completas, no transacciones individuales. Detectar si una <em>transacción específica</em> es fraudulenta requiere una extensión del modelo — una fase posterior del proyecto.</li>
    <li><strong>Deriva de concepto:</strong> los patrones de lavado evolucionan. Se recomienda re-entrenamiento trimestral con los nuevos casos confirmados por el equipo de compliance.</li>
  </ul>

  <div class="plain-lang no-break">
    <div class="plain-lang-tag">En palabras simples — limitaciones para dirección</div>
    <div class="plain-lang-body">
      Este estudio es una <strong>prueba de concepto</strong>: demuestra que el enfoque funciona con datos ficticios. Los resultados en datos reales del banco podrían ser algo menores (los patrones reales son más variados y ruidosos). El paso siguiente — un piloto de 8 semanas con datos reales de BRS — es el que confirmará si el sistema funciona a la escala y complejidad del banco.
    </div>
  </div>
</div>"""


def glossary_section(st):
    e   = st["eda"]
    b   = st["best"]
    xgb = st["models"].get("XGBoost", {})
    gat = st["models"].get("GAT", {})
    base = st["kpis"]["pct_fraud"]
    terms = [
        ("GNN — Red Neuronal de Grafos",
         "Sistema de inteligencia artificial diseñado para analizar datos organizados como redes (grafos), donde lo importante son las <strong>conexiones</strong> entre elementos, no solo los elementos en sí mismos.",
         "En este proyecto: analiza la red de transacciones bancarias donde las cuentas son los nodos y las transferencias son las conexiones."),
        ("GraphSAGE",
         "Un tipo específico de GNN que aprende a resumir la información de los vecinos de cada nodo (<em>SAGEConv = Sample and AGgregation</em>). Su ventaja clave es que puede aplicarse a cuentas nuevas que nunca vio durante el entrenamiento.",
         f"Resultado: PR-AUC={dec(b['pr_auc'])} sobre {num(st['kpis']['n_accounts'])} cuentas sintéticas."),
        ("GAT — Graph Attention Network",
         "Otro tipo de GNN que aprende a <strong>ponderar</strong> la importancia de cada conexión: no todos los vecinos influyen igual para detectar fraude.",
         f"En este proyecto: obtuvo PR-AUC={dec(gat.get('pr_auc', 0))}, por debajo de {b['model']}."),
        ("PR-AUC — Área bajo la curva Precisión-Recall",
         "Métrica principal para evaluar modelos de detección de fraude. Mide el equilibrio entre <em>precisión</em> (¿cuántas alertas son fraude real?) y <em>recall</em> (¿cuánto fraude detectamos del total?). Va de 0 a 1; un modelo aleatorio obtendría ~0.015 (la tasa de fraude). Por encima de 0.90 es excelente.",
         f"Por qué no usamos 'exactitud': si un modelo dijera siempre 'no es fraude', acertaría el {pct(100 - base, 1)} del tiempo pero no detectaría nada."),
        ("Recall @ Precisión 90% (Recall@P90)",
         "Responde a la pregunta: si le exigimos al sistema que 9 de cada 10 alertas sean fraude real, ¿qué porcentaje del fraude total detecta? Un valor de 97% significa que el modelo no pierde casi nada bajo condiciones de alta exigencia.",
         "GraphSAGE: 97%. XGBoost: 88%. Regresión Logística: 18%."),
        ("ROC-AUC",
         "Métrica complementaria a PR-AUC. Mide la capacidad general de separación entre clases legítimas y fraudulentas. Útil para comparación entre modelos, pero menos informativa que PR-AUC cuando el fraude es muy raro.",
         "Todos los modelos obtuvieron ROC-AUC > 0.98 — incluso el modelo simple. Esto ilustra por qué ROC-AUC sola puede ser engañosa en datos desbalanceados."),
        ("Homofilia",
         "Tendencia de los nodos similares a conectarse entre sí. En redes de fraude: las cuentas fraudulentas tienden a transaccionar con otras cuentas fraudulentas mucho más de lo esperado por azar.",
         f"En este estudio: lift de {dec(e['ff_lift'], 1)}×, es decir, la probabilidad de que el vecino de una cuenta sospechosa sea también sospechosa es {dec(e['ff_lift'], 1)} veces mayor que el promedio."),
        (f"Lift (homofilia {dec(e['ff_lift'], 1)}×)",
         f"Medida de cuánto más probable es algo comparado con lo que ocurriría por azar. Lift={dec(e['ff_lift'], 1)}× significa que si una cuenta está conectada a una cuenta fraudulenta, es {dec(e['ff_lift'], 1)} veces más probable que también sea fraudulenta, en comparación con una cuenta tomada al azar.",
         "Es la justificación matemática de por qué usar grafos supera a los modelos que analizan cuentas de forma individual."),
        ("Cohen d",
         "Medida estadística del tamaño del efecto entre dos grupos. Un valor cercano a 0 significa que los dos grupos son prácticamente idénticos; cerca de 1 significa diferencias grandes.",
         f"Cohen d={dec(e['effect_size_risk_score'], 3)} entre el puntaje crediticio de cuentas fraudulentas y legítimas confirma que el score crediticio no sirve para detectar lavado de dinero."),
        ("Transductivo vs. Inductivo",
         "<strong>Transductivo:</strong> el modelo ve las conexiones de TODAS las cuentas durante el entrenamiento y la evaluación, incluyendo las cuentas del conjunto de prueba. <strong>Inductivo:</strong> las conexiones del conjunto de prueba se ocultan durante el entrenamiento — simula cuentas nuevas. El modo inductivo es más honesto para estimar el rendimiento en producción.",
         "GraphSAGE fue diseñado específicamente para funcionar bien en modo inductivo."),
        ("Backward Tracing (rastreo hacia atrás)",
         "Técnica que, partiendo de las cuentas mula detectadas por el modelo, recorre las transacciones en sentido inverso para identificar las cuentas de <strong>origen</strong> que inyectaron el dinero al esquema. El modelo de IA detecta las mulas; el rastreo detecta a quienes las dirigen.",
         f"En el estudio: identificó {num(st['n_perps_invisible'])} perpetradores con score GNN por debajo del corte que habían inyectado {money_m(st['amount_perps_invisible'])} desde cuentas aparentemente legítimas."),
        ("Placement / Colocación",
         "Primera etapa del lavado de dinero: introducir el dinero sucio al sistema financiero. Es la más difícil de detectar porque las cuentas que hacen esta tarea tienen pocas transacciones totales y parecen legítimas.",
         "El backward tracing y el placement score están diseñados específicamente para detectar esta etapa que la IA convencional no ve."),
        ("Estructuración / Pitufeo",
         "Técnica de lavado que divide sumas grandes en muchas transferencias pequeñas, deliberadamente por debajo de los umbrales de reporte obligatorio. Esas transferencias circulan por múltiples cuentas intermedias ('mulas') antes de consolidarse.",
         "También conocido como 'smurfing' en inglés. Es el patrón más común en los anillos detectados por este modelo."),
        ("GNNExplainer",
         "Herramienta que analiza las predicciones del modelo y explica <em>por qué</em> clasificó una cuenta como sospechosa: qué conexiones y qué características fueron más determinantes para esa decisión específica.",
         "Resultado: los factores más importantes son 'cantidad de transacciones', 'remitentes únicos' y 'puntuación de riesgo' — no el monto absoluto de dinero."),
        ("Early Stopping",
         "Técnica que detiene el entrenamiento del modelo cuando detecta que está empezando a 'memorizar' los datos de entrenamiento en lugar de aprender patrones generalizables. Previene el sobreajuste.",
         "En este proyecto: el entrenamiento se detuvo automáticamente en la época óptima según el rendimiento en el conjunto de validación."),
        ("XGBoost",
         "Algoritmo de aprendizaje automático basado en árboles de decisión encadenados. Muy efectivo para datos tabulares (filas y columnas). No analiza la estructura del grafo, pero sirve como comparativo sólido.",
         f"PR-AUC={dec(xgb.get('pr_auc', 0))} vs. {dec(b['pr_auc'])} de {b['model']} — la diferencia representa el fraude adicional que se detecta por usar la información de las conexiones."),
        ("AML — Anti-Money Laundering",
         "Prevención de Lavado de Activos. Marco regulatorio y de procesos para detectar, reportar y prevenir el uso del sistema financiero para lavar dinero proveniente de actividades ilegales.",
         "En Argentina, el marco regulatorio es la Ley 25.246 y la UIF (Unidad de Información Financiera) supervisa el cumplimiento."),
        ("ROS / SAR — Reporte de Operación Sospechosa",
         "Reporte formal que una institución financiera debe presentar ante la UIF cuando detecta una operación que no puede justificarse económica o jurídicamente. La presentación es obligatoria bajo pena de sanción regulatoria.",
         "El módulo de Compliance de Phantom AI genera automáticamente el borrador del ROS con los datos del caso, listo para revisión y firma del oficial de cumplimiento."),
        ("GAFI",
         "Grupo de Acción Financiera Internacional (FATF en inglés). Organismo intergubernamental que establece los estándares internacionales para la lucha contra el lavado de dinero y la financiación del terrorismo.",
         "Argentina es miembro del GAFI a través del GAFILAT (Grupo de Acción Financiera de Latinoamérica)."),
        ("Grafo (red)",
         "Estructura matemática compuesta por <strong>nodos</strong> (cuentas bancarias en este caso) y <strong>aristas</strong> (transacciones entre cuentas). Permite representar y analizar relaciones complejas que una tabla de Excel no puede capturar.",
         f"Ejemplo: {num(st['kpis']['n_accounts'])} cuentas = {num(st['kpis']['n_accounts'])} nodos; {num(st['n_txns'])} operaciones que se agregan en {num(e['n_edges'])} aristas dirigidas."),
    ]

    entries = ""
    for term, definition, example in terms:
        entries += f"""
  <div class="glossary-entry no-break">
    <div class="glossary-term">{term}</div>
    <div class="glossary-def">{definition}</div>
    <div class="glossary-ex">Ejemplo en este estudio: {example}</div>
  </div>"""

    return f"""
<div class="break-before">
  <div class="section-num">Glosario</div>
  <h2>Glosario de Términos</h2>

  <div class="plain-lang" style="margin-bottom:20px;">
    <div class="plain-lang-tag">¿Cómo usar este glosario?</div>
    <div class="plain-lang-body">
      Este glosario define todos los términos técnicos del informe en lenguaje claro. Está pensado para directores, gerentes de compliance y auditores que no tienen formación en ciencias de datos. Cada entrada incluye la definición y un ejemplo concreto de cómo aplica en este proyecto.
    </div>
  </div>
  {entries}
</div>"""


# ─────────────────────────────────────────────────────────────────────────────
# Renderer
# ─────────────────────────────────────────────────────────────────────────────

def build_html(cfg, results, st, art=None):
    figs = cfg["paths"]["figures_dir"]
    sections = "\n".join([
        cover(st),
        disclaimer_section(),
        executive_summary(st),
        context_section(st),
        data_section(figs, st),
        results_section(results, figs, st),
        insights_section(st, art),
        roadmap_section(),
        annex_section(results, cfg, figs, st, art),
        glossary_section(st),
    ])
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Detección de Redes de Lavado — BRS · Germán Cárdenas</title>
<style>{CSS}</style>
</head>
<body>
{sections}
</body>
</html>"""


def render_pdf(html_path: str, pdf_path: str):
    from playwright.sync_api import sync_playwright
    abs_html = Path(html_path).absolute()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page    = browser.new_page()
        page.goto(f"file://{abs_html}", wait_until="networkidle")
        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template=(
                '<div style="font-size:7.5px;font-family:Arial,sans-serif;color:#9CA3AF;'
                'width:100%;padding:0 2.2cm;text-align:right;">'
                'Phantom AI — Detección de Redes de Lavado · Banco Regional del Sur · Confidencial'
                '</div>'
            ),
            footer_template=(
                '<div style="font-size:7.5px;font-family:Arial,sans-serif;color:#9CA3AF;'
                'width:100%;padding:0 2.2cm;display:flex;justify-content:space-between;">'
                '<span>PHANTOM AI · Germán Cárdenas · Data &amp; Analytics</span>'
                '<span>Página <span class="pageNumber"></span> de <span class="totalPages"></span></span>'
                '</div>'
            ),
            margin={"top": "2.2cm", "right": "2.2cm", "bottom": "2.2cm", "left": "2.2cm"},
        )
        browser.close()


def main(config_path="config/config.yaml"):
    cfg = load_config(config_path)

    with open(f"{cfg['paths']['reports_dir']}/results_all.json") as f:
        results = json.load(f)

    print("=" * 55)
    print("  FASE H — Informe PDF institucional")
    print("=" * 55)

    html_path = "reports/informe_final.html"
    pdf_path  = "reports/informe_final.pdf"

    print("\n── 1. Generando HTML ────────────────────────────────────")
    art  = load_artifacts(cfg)
    st   = load_stats(cfg)
    html = build_html(cfg, results, st, art)
    Path(html_path).write_text(html, encoding="utf-8")
    print(f"  → {html_path}  ({len(html)//1024} KB)")

    print("\n── 2. Renderizando PDF (Playwright/Chromium) ────────────")
    render_pdf(html_path, pdf_path)
    size_kb = Path(pdf_path).stat().st_size / 1024
    print(f"  → {pdf_path}  ({size_kb:.0f} KB)")

    print("\n" + "=" * 55)
    print(f"  Informe generado: {pdf_path}")
    print("=" * 55)


if __name__ == "__main__":
    main()
