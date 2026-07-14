---
name: informe-gc
description: Generación de informes PDF institucionales con la identidad
  personal de Germán Cárdenas. Usar cuando se pida crear el informe final,
  el PDF entregable, o documentos para cliente.
---

# Informes institucionales — Germán Cárdenas

Pipeline: markdown/HTML con CSS print → render con Playwright/Chromium
a PDF A4. NUNCA generar PDF con librerías de bajo nivel (reportlab/fpdf).

Identidad visual:
- Paleta: navy #0A1F44 (principal), gold #C9A227 (acentos), gris #F4F5F7
- Tipografía: serif para títulos (Georgia), sans para cuerpo (Inter/Arial)
- Portada: título, cliente, fecha, wordmark "GERMÁN CÁRDENAS · Data & Analytics"
- Header/footer en cada página: nombre del documento + paginación
- Callout boxes gold para hallazgos clave ("Insight" / "Recomendación")

Estructura obligatoria (estilo consultoría):
1. Portada  2. Disclaimer de confidencialidad y datos sintéticos
3. Resumen ejecutivo (1 página, cero jerga)  4. Contexto y problema
5. Datos y metodología  6. Resultados  7. Insights y recomendaciones
8. Roadmap de implementación  9. Anexo técnico

Tono: consultor senior escribiendo para un directorio de banco.
Cada gráfico con título, fuente y una lectura en una línea.
