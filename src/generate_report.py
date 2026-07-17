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
"""


# ─────────────────────────────────────────────────────────────────────────────
# Sections
# ─────────────────────────────────────────────────────────────────────────────

def cover():
    return """
<div class="cover">
  <div>
    <div class="cover-wordmark">GERMÁN CÁRDENAS · Data &amp; Analytics</div>
    <div class="cover-tag">Informe de resultados · Prueba de concepto</div>
    <h1 class="cover-title">Detección de Redes de Lavado mediante Inteligencia de Grafos</h1>
    <p class="cover-subtitle">Graph Neural Networks aplicadas a la detección de estructuras cíclicas de lavado de activos en redes transaccionales financieras</p>
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


def executive_summary():
    return """
<div class="break-before">
  <div class="section-num">Sección 1</div>
  <h2>Resumen Ejecutivo</h2>

  <div class="kpi-row no-break">
    <div class="kpi-card">
      <div class="kpi-val">1.000</div>
      <div class="kpi-lbl">PR-AUC — GraphSAGE</div>
      <div class="kpi-sub">0.835 en evaluación inductiva (producción)</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-val">100%</div>
      <div class="kpi-lbl">Recall @ Precisión 90%</div>
      <div class="kpi-sub">vs. 80% XGBoost / 0% LogReg</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-val">4</div>
      <div class="kpi-lbl">Modelos evaluados</div>
      <div class="kpi-sub">LogReg · XGBoost · GAT · GraphSAGE</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-val">14.3×</div>
      <div class="kpi-lbl">Lift homofilia fraude-fraude</div>
      <div class="kpi-sub">Justificación cuantitativa del GNN</div>
    </div>
  </div>

  <h3>El problema</h3>
  <ul>
    <li>BRS opera con ~500K cuentas activas y un equipo de compliance de 6 analistas.</li>
    <li>El sistema de alertas actual basado en reglas de umbral genera un <strong>~90% de falsos positivos</strong>: los analistas revisan alertas que en su mayoría no son fraude real.</li>
    <li>Los esquemas de <strong>lavado estructurado</strong> (pitufeo y anillos cíclicos) fragmentan el flujo de dinero en transacciones pequeñas que pasan por debajo de los umbrales, haciendo que el problema sea <em>invisible</em> para las reglas actuales.</li>
  </ul>

  <h3>Qué se hizo en este estudio</h3>
  <ul>
    <li>Se construyó un <strong>grafo transaccional sintético</strong> con 1 500 cuentas y 8 050 transacciones, incluyendo anillos cíclicos (4-7 saltos) y estructuración.</li>
    <li>Se evaluaron <strong>4 modelos</strong> sobre el mismo split estratificado: Logistic Regression, XGBoost, GAT y GraphSAGE.</li>
    <li>Se aplicó <strong>GNNExplainer</strong> para identificar qué features y conexiones explican cada predicción de fraude.</li>
    <li>Se implementó <strong>backward tracing</strong> sobre el grafo dirigido de transacciones para identificar las cuentas origen (perpetradores) a partir de las mulas detectadas.</li>
    <li>Se construyó un <strong>dashboard interactivo</strong> con 5 secciones, desplegado en la web, para que el equipo de compliance explore resultados, anillos, perpetradores y cola de trabajo.</li>
  </ul>

  <h3>Resultados principales</h3>
  <ul>
    <li>El <strong>score crediticio externo es ciego al lavado</strong> (Cohen d = 0.055): las cuentas mula son crediticiamente normales. El problema es de red, no de perfil.</li>
    <li>GraphSAGE supera a todos los modelos evaluados: PR-AUC=1.000 transductivo, <strong>0.835 inductivo</strong> (el número correcto para producción con cuentas nuevas), y detecta el 100% del fraude a precisión 90%.</li>
    <li>GNNExplainer revela que el modelo se basa en <strong>features de conectividad</strong> (txn_count, unique_senders, risk_score), no en montos absolutos.</li>
    <li>El backward tracing identificó <strong>2 perpetradores no detectados por el GNN</strong> (score ≈ 0%) que inyectaron $66K al anillo desde cuentas aparentemente legítimas. El GNN detecta la estratificación; el tracing detecta la colocación.</li>
  </ul>

  <h3>Recomendación</h3>
  <div class="callout">
    <div class="callout-tag">Recomendación ejecutiva</div>
    <div class="callout-body">
      Iniciar un <strong>piloto de 8 semanas</strong> con datos reales de BRS. El entregable es un score GNN por cuenta, actualizable cada 4 horas, combinado con backward tracing automático sobre el grafo dirigido — alimentando la cola de trabajo del equipo de compliance con un ranking priorizado que incluye tanto mulas como perpetradores de origen.
    </div>
  </div>
</div>"""


def context_section():
    return """
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
  <p>La señal de fraude <em>emerge</em> del patrón de conexiones: los vecinos de una cuenta fraudulenta tienden fuertemente a ser fraudulentos. Medido en los datos de este estudio: <strong>lift fraude-fraude = 14.3×</strong> sobre el nivel esperado por azar. Esta señal es, por definición, invisible para modelos que analizan cuentas de forma individual.</p>

  <div class="callout no-break">
    <div class="callout-tag">Insight clave</div>
    <div class="callout-body">
      El risk score crediticio externo tiene un tamaño del efecto de <strong>Cohen d = 0.055</strong> entre cuentas fraudulentas y legítimas — prácticamente cero. Las cuentas de lavado son crediticiamente "normales". El modelo correcto para detectarlas es el que analiza <em>con quién se conectan</em>, no <em>cómo son individualmente</em>.
    </div>
  </div>
</div>"""


def data_section(figures_dir):
    return f"""
<div class="break-before">
  <div class="section-num">Sección 3</div>
  <h2>Datos y Metodología</h2>

  <h3>Dataset sintético</h3>
  <p>Se generó un dataset sintético que replica las características estadísticas de un grafo transaccional bancario real, con patrones de fraude estilizados y controlados para demostrar la capacidad del enfoque.</p>

  <table>
    <thead><tr><th>Atributo</th><th>Valor</th><th>Descripción</th></tr></thead>
    <tbody>
      <tr><td>Cuentas (nodos)</td><td><strong>1 500</strong></td><td>Distribuidas entre personal (70.6%), business (18.8%), merchant (10.6%)</td></tr>
      <tr><td>Transacciones (aristas)</td><td><strong>8 050</strong></td><td>Período ~1 año; tipos: transfer (50%), payment (35%), withdrawal (15%)</td></tr>
      <tr><td>Nodos fraude</td><td><strong>29 (1.93%)</strong></td><td>Prevalencia comparable a tasas reales de fraude bancario</td></tr>
      <tr><td>Aristas fraude</td><td><strong>50 (0.62%)</strong></td><td>Desbalance dominante — justifica uso de PR-AUC como métrica</td></tr>
      <tr><td>Patrones embebidos</td><td>2 tipos</td><td>Anillos cíclicos (4-7 saltos) + estructuración / pitufeo</td></tr>
      <tr><td>Seed</td><td>42</td><td>Reproducibilidad total</td></tr>
    </tbody>
  </table>

  <h3>Features por nodo (18 en total)</h3>
  <table>
    <thead><tr><th>Categoría</th><th>Features</th></tr></thead>
    <tbody>
      <tr><td>Grado</td><td>degree_in, degree_out, txn_count</td></tr>
      <tr><td>Montos</td><td>total_received, total_sent, avg_received, avg_sent, max_received, max_sent</td></tr>
      <tr><td>Conectividad</td><td>unique_senders, unique_receivers, degree_ratio, amount_ratio</td></tr>
      <tr><td>Perfil de cuenta</td><td>balance, risk_score, opened_days_ago, type_merchant, type_personal</td></tr>
    </tbody>
  </table>

  <h3>Modelos evaluados</h3>
  <p>Los cuatro modelos se entrenaron y evaluaron sobre el <strong>mismo split estratificado 70/15/15</strong> (seed=42). La evaluación final se realizó exclusivamente sobre el conjunto de test.</p>

  <table>
    <thead><tr><th>Modelo</th><th>Tipo</th><th>Hiperparámetros clave</th></tr></thead>
    <tbody>
      <tr><td>Logistic Regression</td><td>Tabular lineal</td><td>class_weight='balanced', C=1.0</td></tr>
      <tr><td>XGBoost</td><td>Tabular no lineal</td><td>n_estimators=300, max_depth=6, lr=0.05, scale_pos_weight=51.5</td></tr>
      <tr><td>GAT</td><td>GNN con atención</td><td>2 capas GATConv(18→64, 4 heads), dropout=0.3, Adam lr=0.005</td></tr>
      <tr><td>GraphSAGE</td><td>GNN inductivo</td><td>2 capas SAGEConv(18→64→64), dropout=0.3, Adam lr=0.005, wd=5e-4</td></tr>
    </tbody>
  </table>

  <figure>
    {b64img(f"{figures_dir}/01_degree_distribution.png")}
    <figcaption>Fig. 1 — Distribución de grado in/out. Las cuentas fraudulentas tienen grado 1.36× superior al legítimo (comportamiento de "router" típico de cuentas mula).</figcaption>
  </figure>

  <h3>Capa de identidad sintética</h3>
  <p>Para replicar fielmente un entorno bancario operativo, cada una de las 1 500 cuentas fue enriquecida con datos de identidad sintéticos mediante el módulo <code>src/enrich_personas.py</code> (seed=42). Los datos se generan deterministamente y son 100% ficticios.</p>

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

  <p>El impacto en el dashboard es inmediato: la tabla de cuentas muestra <strong>"Rodrigo Pérez Fernández — DNI 28.456.789 · Comerciante · La Plata"</strong> en lugar de <em>ACC0000051</em>. Los nodos del grafo de origen muestran apellidos reales; la ficha expandida de cada perpetrador incluye CUIL, condición AFIP y sucursal BRS. Esta capa convierte el demo técnico en una demostración ejecutiva directamente comprensible por el equipo de compliance.</p>
</div>"""


def results_section(results, figures_dir):
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
  <p style="font-size:9pt;color:#6B7280;margin-top:4px;">
    * BRS escalado a 500K cuentas, 1.93% prevalencia de fraude. Mejor valor en verde.
    PR-AUC = área bajo curva precisión-recall (métrica principal para clases desbalanceadas).
  </p>

  <figure>
    {b64img(f"{figures_dir}/12_pr_curves_all.png")}
    <figcaption>Fig. 2 — Curva Precisión-Recall: los 4 modelos evaluados. GAT compite bien pero sin alcanzar a GraphSAGE.</figcaption>
  </figure>

  <h3>Nota metodológica — tres condiciones de evaluación</h3>
  <table>
    <thead><tr><th>Condición</th><th>PR-AUC</th><th>Qué simula</th><th>Uso recomendado</th></tr></thead>
    <tbody>
      <tr><td>Transductivo</td><td>1.000</td><td>Modelo ve todas las aristas en inferencia, incluyendo conexiones de test a train</td><td>Límite superior teórico — no reportar a dirección</td></tr>
      <tr><td>Inductivo</td><td>0.835</td><td>Aristas de test ocultadas durante inferencia — simula cuentas nuevas</td><td>Cota conservadora para cuentas sin historia</td></tr>
      <tr><td class="td-best"><strong>Temporal</strong></td><td class="td-best"><strong>0.810</strong></td><td>Reentrenado con transacciones hasta 2024-07-25 (70% del período); evaluado en últimos 4 meses</td><td><strong>Número a presentar a dirección</strong></td></tr>
    </tbody>
  </table>

  <div class="callout no-break">
    <div class="callout-tag">Número operativo</div>
    <div class="callout-body">
      <strong>PR-AUC=0.810</strong> es el resultado de la evaluación temporal: el modelo entrenado sobre los primeros 8 meses de historia transaccional mantiene su capacidad de detección en los 4 meses siguientes, con una caída de solo <strong>-0.025</strong> respecto al inductivo. Esto confirma que los patrones de lavado aprendidos son estables en el tiempo — condición necesaria para un sistema AML en producción.
    </div>
  </div>

  <figure>
    {b64img(f"{figures_dir}/24_temporal_eval.png")}
    <figcaption>Fig. 3 — Evaluación temporal: izquierda, curvas PR para las tres condiciones (transductiva, inductiva, temporal); derecha, comparativa de PR-AUC. La caída del 1.000 al 0.810 representa el costo real de la evaluación honesta. El delta temporal (-0.025 vs inductivo) es pequeño, indicando robustez al shift temporal.</figcaption>
  </figure>

  <h3>Traducción operativa para BRS</h3>
  <div class="highlight no-break">
    <p>Con el <strong>sistema actual de reglas</strong>: ~90% de falsos positivos, los analistas revisan alertas que en su mayoría no son fraude.</p>
    <p style="margin-top:8px;">Con <strong>GraphSAGE + backward tracing</strong>: a escala de BRS (500K cuentas), el modelo generaría ~26 alertas/día de mulas detectadas, más una cola de perpetradores candidatos derivados por tracing — con 0% de fraude no detectado en el conjunto sintético.</p>
  </div>

  <figure>
    {b64img(f"{figures_dir}/06_fraud_rings.png")}
    <figcaption>Fig. 3 — Anillos de lavado detectados. En rojo: cuentas fraudulentas; en gris: legítimas vecinas. Las aristas rojas muestran el ciclo completo de lavado.</figcaption>
  </figure>
</div>"""


def insights_section():
    insights = [
        ("La señal de fraude es estructural, no de monto individual",
         "Las transacciones fraudulentas tienen una mediana 13.7× mayor que las legítimas, pero dentro de cada anillo el monto se reduce progresivamente (85-98% por salto). Las reglas de umbral capturan la entrada del anillo pero pierden los saltos intermedios de 'enfriamiento'.",
         "Complementar umbrales con alertas de <strong>velocidad transaccional por vecindario</strong>: si un nodo recibe y reenvía montos similares a múltiples destinos en ventanas de 72h, es candidato para revisión."),
        ("El risk score crediticio es ciego al lavado (Cohen d = 0.055)",
         "Las distribuciones del score crediticio son prácticamente idénticas entre cuentas fraudulentas y legítimas. Las cuentas mula son crediticiamente 'normales' — el problema es de red, no de perfil.",
         "<strong>Desconectar el score crediticio</strong> de las reglas AML. Construir un score específico de red que capture comportamiento relacional."),
        ("Homofilia fraude-fraude: lift de 14.3×",
         "Los vecinos de nodos fraudulentos son 14.3× más propensos a ser fraudulentos que el azar. Esto es la justificación cuantitativa para usar GNNs sobre baselines tabulares.",
         "Usar este lift como argumento interno: 'cada transacción con una cuenta de riesgo aumenta 14× la probabilidad de que el origen también sea riesgo'."),
        ("El grafo forma una sola componente conexa",
         "Todos los 1 500 nodos están interconectados (1 componente débilmente conexa, 17 fuertemente conexas). Ninguna cuenta está aislada — la señal de fraude se propaga a múltiples saltos.",
         "Al escalar a datos reales de BRS, verificar si el grafo se fragmenta. Cuentas en componentes aisladas tendrán menor confianza de predicción."),
        ("Grado de cuentas de lavado: 1.36× superior al legítimo",
         "Las cuentas mula tienen alta conectividad bidireccional (in ≈ out): actúan como 'routers'. Este es el fingerprint topológico del pitufeo.",
         "Implementar regla de velocidad: cuentas con más de N contrapartes únicas en 30 días y grado in ≈ grado out van a cola de segunda revisión."),
        ("El fraude es uniforme por tipo de cuenta (1.8-2.0%)",
         "La prevalencia de fraude es casi idéntica en personal, business y merchant. No hay tipo de cuenta sobre-representado.",
         "No usar tipo de cuenta como proxy de riesgo AML. Mantenerlo como feature de contexto en el modelo pero no como regla de filtrado."),
        ("Los anillos operan en ventanas de 72 horas",
         "Los 3 anillos detectados completan sus ciclos en 600 segundos a 72 horas entre saltos consecutivos — antes de que activen los sistemas de monitoreo batch diario.",
         "Priorizar scoring en <strong>cuasi-real-time (cada 4h)</strong> para nodos de mayor riesgo, en lugar de batch diario."),
        ("Pico de actividad fraudulenta: 20:00h y jueves",
         "Las transacciones de fraude se concentran fuera del horario bancario. Si el equipo de compliance opera de 9-18h, los anillos iniciados a las 20:00 completan 2-3 saltos antes de la apertura del día siguiente.",
         "Configurar alertas automáticas de alta prioridad para transacciones >$5.000 en horario nocturno, combinadas con el score de red del modelo."),
        ("El GNN mejora 7.5 puntos de PR-AUC sobre XGBoost",
         "GraphSAGE logra PR-AUC=1.000 vs XGBoost=0.925 vs LogReg=0.555, usando exactamente el mismo test set. El único diferencial es el acceso a la estructura del grafo.",
         "Presentar la curva PR comparativa al directorio como argumento central: el área entre las curvas representa el 'fraude adicional detectado' por la inteligencia de grafos."),
        ("La topología sola (ablation) logra PR-AUC=0.036",
         "Un GraphSAGE entrenado con features constantes (solo estructura del grafo) alcanza PR-AUC=0.036. Los features tabulares y la estructura son complementarios, no sustitutos.",
         "En la fase piloto, priorizar la <strong>disponibilidad del grafo de transacciones</strong> sobre la calidad de los features de cuenta. El pipeline mínimo viable es: transacciones → GNN topológico → score de red."),
        ("Los nodos periféricos de anillos son los más difíciles de detectar",
         "El nodo fraude con score más bajo (0.243) tiene degree bajo (in=3, out=4) y pocos vecinos fraude directos (2/7). Los nodos de entrada/salida del anillo tienen menos señal de vecindario.",
         "Para nodos con score intermedio (0.3-0.7), aplicar segunda revisión manual que considere el contexto completo del anillo, no solo el nodo individual."),
        ("Regresión Logística: límite de la linealidad en grafos",
         "LogReg logra ROC-AUC=0.926 (alta separabilidad global) pero PR-AUC=0.555 y Recall@P90=0. La frontera de decisión lineal no puede separar fraude de legítimo en el punto operativo.",
         "Al presentar a BRS, usar la progresión LogReg→XGBoost→GNN como narrativa de 'capas de inteligencia': no-linealidad → red → ventaja acumulada."),
        ("El modelo detecta fraude por señales de red, no de monto",
         "GNNExplainer revela que los features más determinantes para clasificar una cuenta como fraude son txn_count, unique_senders y risk_score — todos indicadores de conectividad y comportamiento relacional, no de monto absoluto. Las features de monto (total_sent, avg_sent) tienen importancia secundaria.",
         "Priorizar la construcción de features de red (grado, ratio in/out, contrapartes únicas en ventanas de 72h) en el pipeline de datos de BRS antes de reentrenar con datos reales."),
        ("El 13% de los vecinos influyentes son también de alto riesgo",
         "Para los 5 nodos fraude explicados, el 13% (3/23) de sus vecinos más influyentes según GNNExplainer tienen a su vez score GNN > 0.5. La mayoría de los vecinos influyentes son cuentas legítimas — el modelo detecta fraude por patrones estructurales, no por contagio directo.",
         "Implementar 'investigación en cascada': cuando un analista confirma fraude en una cuenta, el sistema genera alertas de nivel 2 para sus vecinos influyentes según GNNExplainer, independientemente de si esos vecinos tienen score alto propio."),
        ("PR-AUC=1.0 refleja evaluación transductiva, no inductiva",
         "En evaluación estándar (transductiva), el GNN ve durante el entrenamiento todas las aristas incluyendo las que conectan nodos de test con nodos fraude de train. Al aislar el test set (inductivo, simula cuentas nuevas), el PR-AUC cae de 1.000 a 0.835. Un nodo fraude pasa de score=0.997 a score=0.007: su única señal era la conexión directa a 2 nodos fraude de train.",
         "En el piloto con datos reales de BRS, evaluar en ventana temporal: entrenar con transacciones hasta el mes M, evaluar en M+1. Ningún nodo de test tendrá aristas en el grafo de train — la estimación de rendimiento operativo será honesta."),
        ("El GNN detecta mulas pero no el perpetrador de origen",
         "Rastreando hacia atrás desde los nodos detectados en el grafo dirigido de transacciones, se identificaron 3 cuentas raíz (in-degree=0 en el subgrafo de fraude): ACC0001330 (detectada, 13 mulas alimentadas), ACC0000210 y ACC0001046 (no detectadas, score GNN ≈ 0%, is_fraud=False en el dataset). Estas dos cuentas inyectaron $66.422 al anillo desde cuentas aparentemente legítimas. El GNN detecta la estratificación (placement→layering); el backward tracing detecta la colocación (placement).",
         "Combinar el scoring GNN con una segunda pasada de backward tracing: dado cualquier nodo detectado como fraude, agregar a la cola de investigación todos sus predecesores directos en el grafo dirigido temporal que no sean ellos mismos detectados. Priorizar por monto inyectado."),
        ("Evaluación temporal: PR-AUC=0.810 es el número operativo real",
         "Re-entrenando GraphSAGE con solo el 70% del período histórico (transacciones hasta 2024-07-25, 5.636 de 8.050 aristas) y evaluando en el test set con el grafo completo, el PR-AUC es 0.810. La secuencia completa: transductivo=1.000 → inductivo=0.835 → temporal=0.810. El delta temporal vs inductivo es solo -0.025, confirmando que el modelo aprende patrones estructurales estables, no conexiones específicas del período de entrenamiento.",
         "Adoptar split temporal mensual para el piloto BRS: entrenar hasta mes M, validar en M+1, evaluar en M+2. Re-entrenar trimestralmente con los nuevos casos etiquetados por compliance. Reportar siempre PR-AUC temporal a dirección, no el transductivo."),
        ("Propagación inversa de riesgo valida y amplía el backward tracing",
         "Aplicando la fórmula placement(u) = Σ gnn[v]×amount(u→v) + 0.3×Σ gnn[w]×amount(v→w)×amount(u→v)/total_out(v) sobre todos los nodos, ACC0000210 (perpetrador no detectado por GNN) rankea #1 con score_norm=1.0 y ACC0001046 rankea #9. Los rangos 2-8 están ocupados por mulas con GNN=100%, coherente porque se transfieren entre sí. El método opera exclusivamente sobre scores GNN existentes y el grafo dirigido — sin etiquetas adicionales.",
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
  <h2>Insights y Recomendaciones</h2>
  <p>Dieciséis insights derivados del análisis exploratorio, los modelos, GNNExplainer y el rastreo de perpetradores. Formato operativo para el equipo de compliance y la dirección de BRS.</p>
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


def annex_section(results, cfg, figures_dir):
    gnn_r  = next(r for r in results if r["model"] == "GraphSAGE")
    xgb_r  = next(r for r in results if r["model"] == "XGBoost")
    gnn_cfg = cfg["model"]["graphsage"]

    return f"""
<div class="break-before">
  <div class="section-num">Anexo técnico</div>
  <h2>Anexo Técnico</h2>

  <h3>Hiperparámetros del modelo GraphSAGE</h3>
  <table>
    <thead><tr><th>Parámetro</th><th>Valor</th><th>Justificación</th></tr></thead>
    <tbody>
      <tr><td>Capas SAGEConv</td><td>{gnn_cfg['num_layers']}</td><td>2 saltos de vecindario — captura anillos de hasta 4 nodos directamente</td></tr>
      <tr><td>Hidden channels</td><td>{gnn_cfg['hidden_channels']}</td><td>Suficiente para el tamaño del grafo (scale=0.01)</td></tr>
      <tr><td>Dropout</td><td>{gnn_cfg['dropout']}</td><td>Regularización; crítico con desbalance 1:51</td></tr>
      <tr><td>Learning rate</td><td>{gnn_cfg['lr']}</td><td>Adam; convergencia estable observada</td></tr>
      <tr><td>Weight decay</td><td>{gnn_cfg['weight_decay']}</td><td>L2 regularización sobre parámetros</td></tr>
      <tr><td>Class weight fraude</td><td>51.45×</td><td>n_legítimo / n_fraude en train set</td></tr>
      <tr><td>Early stopping</td><td>paciencia={gnn_cfg['patience']}</td><td>Monitorea val PR-AUC; detuvo en época 78</td></tr>
      <tr><td>Aggregator</td><td>mean</td><td>Default SAGEConv; robusto en grafos heterofílicos</td></tr>
      <tr><td>Dirección grafo</td><td>ToUndirected</td><td>Cada arista dirigida → 2 aristas; información fluye en ambas direcciones alrededor de los anillos</td></tr>
    </tbody>
  </table>

  <figure>
    {b64img(f"{figures_dir}/10_training_curves.png")}
    <figcaption>Fig. 4 — Curvas de entrenamiento. Izquierda: loss CrossEntropy (train). Derecha: PR-AUC en validación. El modelo detuvo por early stopping en época 78 con val PR-AUC = 0.9167.</figcaption>
  </figure>

  <h3>Ablation: features tabulares vs. solo topología</h3>
  <table>
    <thead><tr><th>Variante</th><th>PR-AUC test</th><th>Interpretación</th></tr></thead>
    <tbody>
      <tr><td>GraphSAGE (features completos)</td><td class="td-best">{gnn_r['pr_auc']:.4f}</td><td>Features tabulares + estructura del grafo</td></tr>
      <tr><td>GraphSAGE (solo topología)</td><td>0.0357</td><td>Solo con quién se conecta cada nodo (features=1 constante)</td></tr>
      <tr><td>XGBoost (features tabulares)</td><td>{xgb_r['pr_auc']:.4f}</td><td>Solo features individuales, sin estructura</td></tr>
    </tbody>
  </table>
  <p>El ablation demuestra que <strong>ambas fuentes de información son necesarias</strong>: la topología sola (PR-AUC=0.036) no captura la señal, pero combinada con features tabulares el modelo supera al mejor baseline no-grafo.</p>

  <figure>
    {b64img(f"{figures_dir}/14_ablation.png")}
    <figcaption>Fig. 5 — Ablation: features completos vs. solo topología. La diferencia cuantifica el aporte de los features tabulares (balance, grado, montos) sobre la señal estructural pura.</figcaption>
  </figure>

  <h3>Modelos adicionales evaluados</h3>
  <table>
    <thead><tr><th>Modelo</th><th>PR-AUC</th><th>Recall@P90</th><th>Observación clave</th></tr></thead>
    <tbody>
      <tr><td>GAT (Graph Attention Network)</td><td>0.973</td><td>0.93</td><td>Aprende pesos por arista; compite bien pero inferior a SAGE en este grafo</td></tr>
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
    <thead><tr><th>Cuenta</th><th>Score GNN</th><th>Etiqueta real</th><th>Mulas alimentadas</th><th>Monto inyectado</th><th>Primera txn</th></tr></thead>
    <tbody>
      <tr><td>ACC0001330</td><td>1.000</td><td class="td-best">Fraude (detectado)</td><td>13</td><td>$14.502</td><td>2024-05-27</td></tr>
      <tr><td>ACC0000210</td><td>0.000</td><td style="color:#B91C1C;font-weight:700;">No fraude (no detectado)</td><td>1</td><td>$48.411</td><td>2024-04-14</td></tr>
      <tr><td>ACC0001046</td><td>0.000</td><td style="color:#B91C1C;font-weight:700;">No fraude (no detectado)</td><td>1</td><td>$18.011</td><td>2023-12-14 ← primera</td></tr>
    </tbody>
  </table>

  <figure>
    {b64img(f"{figures_dir}/22_fraud_chain.png")}
    <figcaption>Fig. 10 — Grafo dirigido del anillo de lavado completo. Naranja: perpetradores (origen); rojo: mulas detectadas por GNN; violeta: mulas no detectadas; gris: receptores legítimos. Las flechas muestran la dirección del flujo de dinero; el grosor de arista es proporcional al monto transferido.</figcaption>
  </figure>

  <div class="callout no-break">
    <div class="callout-tag">Hallazgo crítico</div>
    <div class="callout-body">
      ACC0001046 inició la cadena en diciembre 2023 (primera transacción del anillo) con score GNN ≈ 0%. ACC0000210 inyectó $48.411 en una sola transacción con score GNN ≈ 0%. Ambas cuentas tienen <strong>baja centralidad de red</strong>: pocas transacciones totales, grado bajo — el perfil típico de una cuenta que inyecta fondos una vez y desaparece. Este patrón es invisible para un clasificador de nodos basado en conectividad. El backward tracing sobre el grafo dirigido es el mecanismo que cierra esta brecha.
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
      <tr><td>1</td><td><strong>ACC0000210</strong></td><td class="td-best">1.000</td><td>0.000</td><td>$48.411</td><td style="color:#D97706;font-weight:700;">Perpetrador conocido</td></tr>
      <tr><td>2</td><td>ACC0001309</td><td>0.966</td><td>1.000</td><td>—</td><td>Detectado por GNN (mula)</td></tr>
      <tr><td>3</td><td>ACC0000228</td><td>0.913</td><td>1.000</td><td>—</td><td>Detectado por GNN (mula)</td></tr>
      <tr><td>9</td><td><strong>ACC0001046</strong></td><td>0.365</td><td>0.000</td><td>$18.011</td><td style="color:#D97706;font-weight:700;">Perpetrador conocido</td></tr>
    </tbody>
  </table>

  <figure>
    {b64img(f"{figures_dir}/23_placement_scores.png")}
    <figcaption>Fig. 11 — Ranking de colocación: top 20 candidatos por placement score normalizado. Naranja: perpetradores conocidos (backward tracing); azul: mulas detectadas por GNN; rojo: nuevos candidatos. Los dos perpetradores no detectados por el GNN aparecen en rank #1 y #9, validando el método sin supervisión adicional.</figcaption>
  </figure>

  <div class="callout no-break">
    <div class="callout-tag">Validación del método</div>
    <div class="callout-body">
      ACC0000210 (perpetrador no detectado por GNN, score GNN ≈ 0%) rankea <strong>#1</strong> en placement score (score_norm=1.0). ACC0001046 rankea <strong>#9</strong>. Los rangos intermedios están ocupados por mulas con GNN=100% — coherente porque también transfieren entre sí. La propagación inversa no requiere etiquetas adicionales: opera exclusivamente sobre los scores GNN existentes y el grafo de transacciones.
    </div>
  </div>

  <h3>Limitaciones metodológicas</h3>
  <ul>
    <li><strong>Datos sintéticos:</strong> los patrones de fraude son idealizados. Con datos reales la señal puede ser más ruidosa. Los resultados deben interpretarse como límite superior optimista.</li>
    <li><strong>Escala reducida:</strong> el estudio usa scale=0.01 (1 500 cuentas). Para el grafo completo de BRS (~500K cuentas) se necesita neighbor sampling para el entrenamiento.</li>
    <li><strong>Evaluación transductiva:</strong> el PR-AUC=1.000 reportado para GraphSAGE es transductivo. El número operativo correcto es PR-AUC=0.835 (evaluación inductiva).</li>
    <li><strong>Etiquetas de nodo únicamente:</strong> el modelo predice fraude a nivel de cuenta. Clasificación a nivel de transacción requiere edge classification — extensión de fase 2.</li>
    <li><strong>Deriva de concepto:</strong> los patrones de lavado evolucionan. Se recomienda re-entrenamiento trimestral con validación de expertos de compliance.</li>
  </ul>
</div>"""


# ─────────────────────────────────────────────────────────────────────────────
# Renderer
# ─────────────────────────────────────────────────────────────────────────────

def build_html(cfg, results):
    figs = cfg["paths"]["figures_dir"]
    sections = "\n".join([
        cover(),
        disclaimer_section(),
        executive_summary(),
        context_section(),
        data_section(figs),
        results_section(results, figs),
        insights_section(),
        roadmap_section(),
        annex_section(results, cfg, figs),
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
                'Detección de Redes de Lavado — Banco Regional del Sur · Confidencial'
                '</div>'
            ),
            footer_template=(
                '<div style="font-size:7.5px;font-family:Arial,sans-serif;color:#9CA3AF;'
                'width:100%;padding:0 2.2cm;display:flex;justify-content:space-between;">'
                '<span>GERMÁN CÁRDENAS · Data &amp; Analytics</span>'
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
    html = build_html(cfg, results)
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
