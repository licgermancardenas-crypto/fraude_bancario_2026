/**
 * Registro de auditoría inmutable (append-only) con encadenamiento por hash.
 * Cada evento incluye el hash del anterior (SHA-256), formando una cadena: si
 * alguien altera un evento pasado, la verificación de integridad lo detecta —
 * es la técnica de un audit log tamper-evident.
 *
 * NOTA: en esta demo la cadena vive en localStorage. En producción el registro
 * debe ser server-side, append-only real (WORM), firmado y fuera del alcance de
 * quien opera el sistema. Acá se demuestra el DISEÑO del control, no su
 * enforcement productivo.
 */
export interface AuditEvent {
  seq: number;
  timestamp: string;   // ISO
  actor: string;
  role: string;
  action: string;      // ej. "caso.desestimado", "ros.aprobado"
  target: string;      // case_id
  detail?: string;
  prevHash: string;
  hash: string;
}

const KEY = "phantom_audit_log";

function read(): AuditEvent[] {
  if (typeof window === "undefined") return [];
  try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; }
}
function write(list: AuditEvent[]) {
  localStorage.setItem(KEY, JSON.stringify(list));
}

async function sha256Hex(s: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
}

function payload(e: Omit<AuditEvent, "hash">): string {
  return `${e.seq}|${e.timestamp}|${e.actor}|${e.role}|${e.action}|${e.target}|${e.detail ?? ""}|${e.prevHash}`;
}

export async function appendAudit(
  e: { actor: string; role: string; action: string; target: string; detail?: string },
): Promise<AuditEvent> {
  const list = read();
  const prev = list[list.length - 1];
  const base = {
    seq: (prev?.seq ?? 0) + 1,
    timestamp: new Date().toISOString(),
    prevHash: prev?.hash ?? "GENESIS",
    ...e,
  };
  const hash = await sha256Hex(payload(base));
  const ev: AuditEvent = { ...base, hash };
  list.push(ev);
  write(list);
  return ev;
}

export function getAuditLog(target?: string): AuditEvent[] {
  const list = read();
  return target ? list.filter(e => e.target === target) : list;
}

/** Recalcula la cadena completa y detecta cualquier alteración. */
export async function verifyIntegrity(): Promise<{ ok: boolean; brokenAt?: number; total: number }> {
  const list = read();
  let prevHash = "GENESIS";
  for (const ev of list) {
    const recomputed = await sha256Hex(payload({ ...ev }));
    if (ev.prevHash !== prevHash || recomputed !== ev.hash) {
      return { ok: false, brokenAt: ev.seq, total: list.length };
    }
    prevHash = ev.hash;
  }
  return { ok: true, total: list.length };
}
