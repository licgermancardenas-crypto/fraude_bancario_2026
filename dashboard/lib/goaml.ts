/**
 * Export goAML — genera el XML del ROS con el esquema goAML que consume la UIF
 * argentina (y la mayoría de las Unidades de Inteligencia Financiera del mundo,
 * estándar UNODC). Usa los nombres de elementos reales del report.xsd
 * (rentity_id, report_code, transaction, t_from/t_to, transmode_code…). Es una
 * versión ilustrativa poblada desde el caso — no una validación XSD completa.
 */
import type { Case, SARDraft } from "@/lib/types";

function esc(s: string | number | undefined | null): string {
  return String(s ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function iso(ts: number): string {
  return new Date(ts * 1000).toISOString().slice(0, 19);
}

/** Mapea el canal a un código de modo de transacción goAML (ilustrativo). */
function transmode(canal?: string): { code: string; comment: string } {
  const c = canal ?? "";
  if (c.includes("CBU")) return { code: "TCBU", comment: c };
  if (c.includes("CVU")) return { code: "TCVU", comment: c };
  if (c.includes("POS") || c.includes("débito")) return { code: "TDEB", comment: c };
  if (c.includes("efectivo") || c.includes("Efectivo")) return { code: "TEFE", comment: c };
  if (c.includes("MEP")) return { code: "TMEP", comment: c };
  return { code: "TOTR", comment: c || "Otro" };
}

const INST = "Banco Regional del Sur";

function txnXml(t: Case["recent_transactions"][number], idx: number, subjectName: string): string {
  const tm = transmode(t.canal);
  const fromName = t.direction === "entrada" ? "" : subjectName;
  const toName = t.direction === "salida" ? "" : subjectName;
  return `    <transaction>
      <transactionnumber>${esc(t.src)}-${esc(t.dst)}-${idx + 1}</transactionnumber>
      <transaction_location>${INST}</transaction_location>
      <date_transaction>${iso(t.timestamp)}</date_transaction>
      <transmode_code>${tm.code}</transmode_code>
      <transmode_comment>${esc(tm.comment)}</transmode_comment>
      <amount_local>${t.amount.toFixed(2)}</amount_local>
      <t_from>
        <from_funds_code>K</from_funds_code>
        <from_account>
          <institution_name>${INST}</institution_name>
          <account>${esc(t.src)}</account>
          <currency_code>${esc(t.moneda ?? "ARS")}</currency_code>${fromName ? `\n          <account_name>${esc(fromName)}</account_name>` : ""}
        </from_account>
      </t_from>
      <t_to>
        <to_funds_code>K</to_funds_code>
        <to_account>
          <institution_name>${INST}</institution_name>
          <account>${esc(t.dst)}</account>
          <currency_code>${esc(t.moneda ?? "ARS")}</currency_code>${toName ? `\n          <account_name>${esc(toName)}</account_name>` : ""}
        </to_account>
      </t_to>
      <comments>${esc(t.concepto ?? "")}</comments>
    </transaction>`;
}

export function buildGoamlXml(draft: SARDraft, c: Case): string {
  const oc = (draft.oficial_cumplimiento || "Oficial de Cumplimiento")
    .replace(/^(Lic\.?|Dr\.?|Dra\.?|Cr\.?|Cra\.?|Ab\.?)\s+/i, "")
    .trim().split(" ");
  const ocFirst = oc[0] ?? "";
  const ocLast = oc.slice(1).join(" ") || "";
  const subject = draft.reportado_nombre || c.account_id;
  const txns = c.recent_transactions.slice(0, 10)
    .map((t, i) => txnXml(t, i, subject)).join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>
<report xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <rentity_id>BRS-0001</rentity_id>
  <rentity_branch>Casa Central</rentity_branch>
  <submission_code>E</submission_code>
  <report_code>ROS</report_code>
  <entity_reference>${esc(draft.case_id)}</entity_reference>
  <submission_date>${esc(draft.fecha_reporte)}T00:00:00</submission_date>
  <currency_code_local>ARS</currency_code_local>
  <reporting_person>
    <first_name>${esc(ocFirst)}</first_name>
    <last_name>${esc(ocLast)}</last_name>
    <title>Oficial de Cumplimiento</title>
  </reporting_person>
  <location>
    <address>${INST} — ${esc(draft.sujeto_obligado)}</address>
    <city>Ciudad Autónoma de Buenos Aires</city>
    <country_code>AR</country_code>
  </location>
  <reason>${esc(draft.descripcion)}</reason>
  <action>Reporte de Operación Sospechosa elevado a la UIF conforme Ley 25.246.</action>
  <report_parties>
    <report_party>
      <account_my_client>t</account_my_client>
      <account>
        <institution_name>${INST}</institution_name>
        <account>${esc(c.account_id)}</account>
        <currency_code>ARS</currency_code>
        <account_name>${esc(subject)}</account_name>
        <signatory>
          <is_primary>t</is_primary>
          <t_person>
            <first_name>${esc(c.persona?.nombre ?? subject)}</first_name>
            <last_name>${esc(c.persona?.apellido ?? "")}</last_name>
            <ssn>${esc(draft.reportado_cuil)}</ssn>
            <nationality1>AR</nationality1>
          </t_person>
        </signatory>
      </account>
    </report_party>
  </report_parties>
  <transactions>
${txns}
  </transactions>
  <report_indicators>
    <indicator>${esc(draft.patron_detectado)}</indicator>
  </report_indicators>
</report>
`;
}

export function downloadGoaml(draft: SARDraft, c: Case) {
  const xml = buildGoamlXml(draft, c);
  const blob = new Blob([xml], { type: "application/xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `ROS_${c.case_id}_goAML.xml`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
