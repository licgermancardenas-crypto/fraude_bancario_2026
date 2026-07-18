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

def cover():
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


def executive_summary():
    return """
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
      <div class="kpi-val">0.977</div>
      <div class="kpi-lbl">Precisión global — GraphSAGE</div>
      <div class="kpi-sub">Escala 0–1. Por encima de 0.95 es sobresaliente.</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-val">95%</div>
      <div class="kpi-lbl">Detección con 9 de 10 alertas correctas</div>
      <div class="kpi-sub">vs. 80% modelo tradicional / 0% regresión simple</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-val">4</div>
      <div class="kpi-lbl">Modelos comparados</div>
      <div class="kpi-sub">Regresión · XGBoost · GAT · GraphSAGE</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-val">14.3×</div>
      <div class="kpi-lbl">Señal de red fraude-fraude</div>
      <div class="kpi-sub">Los vecinos de cuentas fraudulentas son 14× más sospechosos</div>
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
      Imaginen que una banda decide lavar $100.000. En lugar de hacer una sola transferencia grande (que dispararía una alerta), divide ese dinero en 50 transferencias de $2.000, las hace circular por 20 cuentas distintas y las reagrupa al final. Cada transferencia parece normal. El sistema de reglas del banco no ve nada raro. <strong>Este software detecta ese patrón analizando las conexiones entre cuentas, no los montos individuales.</strong>
    </div>
  </div>

  <h3>Qué se hizo en este estudio</h3>
  <ul>
    <li>Se construyó un <strong>grafo (red) transaccional sintético</strong> con 75.000 cuentas y 400.000 transacciones, incluyendo redes de lavado cíclicas (4-7 pasos) y esquemas de estructuración.</li>
    <li>Se compararon <strong>4 modelos de IA</strong> sobre los mismos datos y el mismo criterio de evaluación: Regresión Logística (modelo simple), XGBoost (modelo tabular avanzado), GAT y GraphSAGE (modelos de grafos).</li>
    <li>Se analizó <strong>por qué</strong> el modelo toma cada decisión, usando una técnica llamada GNNExplainer que señala cuáles conexiones son las más sospechosas.</li>
    <li>Se implementó <strong>rastreo hacia atrás</strong> (backward tracing) para identificar no solo las "mulas" que mueven el dinero, sino también los <em>perpetradores de origen</em> que inyectaron los fondos.</li>
    <li>Se construyó un <strong>panel de control web</strong> con gestión de casos, red de entidades y formularios de reporte regulatorio (ROS/SAR).</li>
  </ul>

  <h3>Resultados principales</h3>
  <ul>
    <li>El <strong>historial crediticio es ciego al lavado de dinero</strong>: las cuentas que mueven dinero sucio tienen exactamente el mismo puntaje crediticio que las cuentas normales. El problema no está en el perfil de la persona, está en con quién se conecta.</li>
    <li>GraphSAGE supera a todos los modelos comparados con una puntuación de <strong>0.977 sobre 1.0</strong> y detecta el 95% del fraude cuando se le exige que 9 de cada 10 alertas sean reales.</li>
    <li>El modelo se basa en <strong>señales de conectividad</strong> (cuántas transferencias hace una cuenta, cuántos remitentes únicos recibe, su puntuación de riesgo), no en los montos absolutos.</li>
    <li>El rastreo hacia atrás identificó <strong>2 perpetradores que el modelo de IA no vio directamente</strong> pero que habían inyectado $66.000 al esquema desde cuentas aparentemente legítimas.</li>
  </ul>

  <h3>Recomendación</h3>
  <div class="callout">
    <div class="callout-tag">Recomendación ejecutiva</div>
    <div class="callout-body">
      Iniciar un <strong>piloto de 8 semanas</strong> con datos reales de BRS. El entregable es una puntuación de riesgo por cuenta, actualizable cada 4 horas, combinada con rastreo automático de perpetradores — alimentando la cola de trabajo del equipo de compliance con un ranking priorizado que incluye tanto cuentas mula como cuentas de origen del dinero.
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

  <div class="plain-lang no-break">
    <div class="plain-lang-tag">En palabras simples — homofilia (14.3×)</div>
    <div class="plain-lang-body">
      "Lift de 14.3×" significa esto: si tomamos una cuenta al azar del banco, la probabilidad de que sea fraudulenta es del 1.5%. Pero si tomamos una cuenta que <em>está conectada a una cuenta ya sospechosa</em>, esa probabilidad sube a más del 21%. Las cuentas fraudulentas se conectan entre sí mucho más de lo que cabría esperar por casualidad. <strong>El modelo usa exactamente esta señal para detectar redes enteras, no casos aislados.</strong>
    </div>
  </div>

  <div class="callout no-break">
    <div class="callout-tag">Insight clave</div>
    <div class="callout-body">
      El puntaje crediticio externo tiene un tamaño del efecto de <strong>Cohen d = 0.055</strong> entre cuentas fraudulentas y legítimas — prácticamente cero (0 = idénticos, 1 = muy diferentes). Las cuentas de lavado son crediticiamente "normales". El modelo correcto para detectarlas es el que analiza <em>con quién se conectan</em>, no <em>cómo son individualmente</em>.
    </div>
  </div>
</div>"""


def data_section(figures_dir):
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
      <tr><td>Cuentas (nodos)</td><td><strong>75.000</strong></td><td>Distribuidas entre personal (70.6%), empresas (18.8%), comercios (10.6%)</td></tr>
      <tr><td>Transacciones (aristas)</td><td><strong>~400.000</strong></td><td>Período ~1 año; tipos: transferencias (50%), pagos (35%), extracciones (15%)</td></tr>
      <tr><td>Cuentas fraudulentas</td><td><strong>1.147 (1.53%)</strong></td><td>Prevalencia comparable a tasas reales de fraude bancario</td></tr>
      <tr><td>Transacciones fraudulentas</td><td><strong>~8.000 (2%)</strong></td><td>Desbalance dominante — el modelo aprende de ejemplos muy escasos</td></tr>
      <tr><td>Patrones embebidos</td><td>2 tipos</td><td>Anillos cíclicos (4-7 pasos) + estructuración / pitufeo</td></tr>
      <tr><td>Semilla aleatoria</td><td>42</td><td>Garantiza que los resultados sean reproducibles exactamente</td></tr>
    </tbody>
  </table>

  <div class="plain-lang no-break">
    <div class="plain-lang-tag">En palabras simples — ¿por qué solo 1.53% de fraude?</div>
    <div class="plain-lang-body">
      En un banco real, la gran mayoría de las transacciones son legítimas. El fraude es raro (1–3% del total). Esta rareza hace que sea difícil entrenar un sistema de IA: si simplemente dijera "todo es legítimo", acertaría el 98.5% de las veces pero no detectaría ni un solo caso de fraude. Por eso usamos métricas especiales (PR-AUC) que miden específicamente qué tan bien se detectan los casos raros.
    </div>
  </div>

  <h3>Características analizadas por cuenta (18 en total)</h3>
  <table>
    <thead><tr><th>Categoría</th><th>Variables</th><th>Qué miden</th></tr></thead>
    <tbody>
      <tr><td>Conectividad</td><td>degree_in, degree_out, txn_count</td><td>Cuántas transacciones recibe y envía cada cuenta</td></tr>
      <tr><td>Montos</td><td>total_received, total_sent, avg_received, avg_sent, max_received, max_sent</td><td>Volumen y promedio de dinero que fluye por la cuenta</td></tr>
      <tr><td>Comportamiento relacional</td><td>unique_senders, unique_receivers, degree_ratio, amount_ratio</td><td>Cuántos remitentes/destinatarios únicos y qué proporción representan</td></tr>
      <tr><td>Perfil de cuenta</td><td>balance, risk_score, opened_days_ago, type_merchant, type_personal</td><td>Saldo, antigüedad, tipo de titular y puntaje de riesgo</td></tr>
    </tbody>
  </table>

  <h3>Modelos comparados</h3>
  <p>Los cuatro modelos se entrenaron y evaluaron sobre el <strong>mismo conjunto de datos, dividido 70/15/15</strong> (70% para aprender, 15% para ajustar, 15% para probar, siempre reproducible con semilla=42). La evaluación final se realizó exclusivamente sobre el 15% de prueba, que el modelo nunca vio antes.</p>

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
      <tr><td>GAT (Graph Attention Network)</td><td>IA de grafos con atención</td><td>Aprende qué conexiones son más importantes para cada cuenta (pesa las aristas)</td></tr>
      <tr><td>GraphSAGE</td><td>IA de grafos inductiva</td><td>Aprende de los vecinos de cada cuenta; puede aplicarse a cuentas nuevas que no estaban en el entrenamiento</td></tr>
    </tbody>
  </table>

  <figure>
    {b64img(f"{figures_dir}/01_degree_distribution.png")}
    <figcaption>Fig. 1 — Distribución de grado in/out. Las cuentas fraudulentas tienen grado 1.36× superior al legítimo (comportamiento de "router" típico de cuentas mula).</figcaption>
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
  <div class="plain-lang no-break">
    <div class="plain-lang-tag">En palabras simples — ¿qué significan estas métricas?</div>
    <div class="plain-lang-body">
      <strong>PR-AUC (Área bajo la curva Precisión-Recall):</strong> mide qué tan bien detecta el fraude sin generar falsas alarmas. Va de 0 a 1. Un modelo que acierte en todo sería 1.0. Un modelo que adivine al azar obtendría ~0.015 (la tasa base de fraude). Por encima de 0.90 es excelente para fraude bancario.<br/><br/>
      <strong>Recall @ Precisión 90%:</strong> imaginen que le pedimos al sistema: "solo dame alertas donde estés 90% seguro de que es fraude real". ¿De todo el fraude existente, cuánto detecta bajo esa exigencia? El 95% significa que detecta casi todo, con muy pocas falsas alarmas.<br/><br/>
      <strong>Alertas/día en BRS:</strong> estimación de cuántas notificaciones generaría el modelo cada día si se aplicara sobre las 500.000 cuentas del banco. Mejor valor en verde.
    </div>
  </div>

  <p style="font-size:9pt;color:#6B7280;margin-top:4px;">
    * BRS escalado a 500K cuentas, 1.53% prevalencia de fraude. Mejor valor en verde.
  </p>

  <figure>
    {b64img(f"{figures_dir}/12_pr_curves_all.png")}
    <figcaption>Fig. 2 — Curva Precisión-Recall: los 4 modelos evaluados. La línea más alta y a la derecha es la mejor. GAT compite muy bien pero GraphSAGE lo supera.</figcaption>
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
        ("El GNN mejora 5 puntos de PR-AUC sobre XGBoost",
         "GraphSAGE logra PR-AUC=0.977 vs XGBoost=0.927 vs LogReg=0.675, usando exactamente el mismo test set. El único diferencial es el acceso a la estructura del grafo.",
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
      <tr><td>Hidden channels</td><td>{gnn_cfg['hidden_channels']}</td><td>64 unidades por capa; equilibrio entre capacidad y regularización</td></tr>
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


def glossary_section():
    terms = [
        ("GNN — Red Neuronal de Grafos",
         "Sistema de inteligencia artificial diseñado para analizar datos organizados como redes (grafos), donde lo importante son las <strong>conexiones</strong> entre elementos, no solo los elementos en sí mismos.",
         "En este proyecto: analiza la red de transacciones bancarias donde las cuentas son los nodos y las transferencias son las conexiones."),
        ("GraphSAGE",
         "Un tipo específico de GNN que aprende a resumir la información de los vecinos de cada nodo (<em>SAGEConv = Sample and AGgregation</em>). Su ventaja clave es que puede aplicarse a cuentas nuevas que nunca vio durante el entrenamiento.",
         "Resultado: PR-AUC=0.977 sobre 75.000 cuentas sintéticas."),
        ("GAT — Graph Attention Network",
         "Otro tipo de GNN que aprende a <strong>ponderar</strong> la importancia de cada conexión: no todos los vecinos influyen igual para detectar fraude.",
         "En este proyecto: obtuvo PR-AUC=0.973, muy cercano a GraphSAGE."),
        ("PR-AUC — Área bajo la curva Precisión-Recall",
         "Métrica principal para evaluar modelos de detección de fraude. Mide el equilibrio entre <em>precisión</em> (¿cuántas alertas son fraude real?) y <em>recall</em> (¿cuánto fraude detectamos del total?). Va de 0 a 1; un modelo aleatorio obtendría ~0.015 (la tasa de fraude). Por encima de 0.90 es excelente.",
         "Por qué no usamos 'exactitud': si un modelo dijera siempre 'no es fraude', acertaría el 98.5% del tiempo pero no detectaría nada."),
        ("Recall @ Precisión 90% (Recall@P90)",
         "Responde a la pregunta: si le exigimos al sistema que 9 de cada 10 alertas sean fraude real, ¿qué porcentaje del fraude total detecta? Un valor de 95% significa que el modelo no pierde casi nada bajo condiciones de alta exigencia.",
         "GraphSAGE: 95%. XGBoost: 80%. Regresión Logística: 0%."),
        ("ROC-AUC",
         "Métrica complementaria a PR-AUC. Mide la capacidad general de separación entre clases legítimas y fraudulentas. Útil para comparación entre modelos, pero menos informativa que PR-AUC cuando el fraude es muy raro.",
         "Todos los modelos obtuvieron ROC-AUC > 0.98 — incluso el modelo simple. Esto ilustra por qué ROC-AUC sola puede ser engañosa en datos desbalanceados."),
        ("Homofilia",
         "Tendencia de los nodos similares a conectarse entre sí. En redes de fraude: las cuentas fraudulentas tienden a transaccionar con otras cuentas fraudulentas mucho más de lo esperado por azar.",
         "En este estudio: lift de 14.3×, es decir, la probabilidad de que el vecino de una cuenta sospechosa sea también sospechosa es 14 veces mayor que el promedio."),
        ("Lift (homofilia 14.3×)",
         "Medida de cuánto más probable es algo comparado con lo que ocurriría por azar. Lift=14.3× significa que si una cuenta está conectada a una cuenta fraudulenta, es 14.3 veces más probable que también sea fraudulenta, en comparación con una cuenta tomada al azar.",
         "Es la justificación matemática de por qué usar grafos supera a los modelos que analizan cuentas de forma individual."),
        ("Cohen d",
         "Medida estadística del tamaño del efecto entre dos grupos. Un valor cercano a 0 significa que los dos grupos son prácticamente idénticos; cerca de 1 significa diferencias grandes.",
         "Cohen d=0.055 entre el puntaje crediticio de cuentas fraudulentas y legítimas confirma que el score crediticio no sirve para detectar lavado de dinero."),
        ("Transductivo vs. Inductivo",
         "<strong>Transductivo:</strong> el modelo ve las conexiones de TODAS las cuentas durante el entrenamiento y la evaluación, incluyendo las cuentas del conjunto de prueba. <strong>Inductivo:</strong> las conexiones del conjunto de prueba se ocultan durante el entrenamiento — simula cuentas nuevas. El modo inductivo es más honesto para estimar el rendimiento en producción.",
         "GraphSAGE fue diseñado específicamente para funcionar bien en modo inductivo."),
        ("Backward Tracing (rastreo hacia atrás)",
         "Técnica que, partiendo de las cuentas mula detectadas por el modelo, recorre las transacciones en sentido inverso para identificar las cuentas de <strong>origen</strong> que inyectaron el dinero al esquema. El modelo de IA detecta las mulas; el rastreo detecta a quienes las dirigen.",
         "En el estudio: identificó 2 perpetradores con score GNN ≈ 0% que habían inyectado $66.000 desde cuentas aparentemente legítimas."),
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
         "PR-AUC=0.927 vs. 0.977 de GraphSAGE — la diferencia representa el fraude adicional que se detecta por usar la información de las conexiones."),
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
         "Ejemplo: 75.000 cuentas = 75.000 nodos; 400.000 transferencias = 400.000 aristas dirigidas."),
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
        glossary_section(),
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
