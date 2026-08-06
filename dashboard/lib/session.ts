/**
 * Sesión y control de acceso (RBAC) — SIMULADO. Modela los tres roles del
 * proceso ALD con segregación de funciones: el analista investiga y arma el
 * ROS, el oficial de cumplimiento aprueba (control de cuatro ojos), y auditoría
 * sólo lee. Un rol no puede ejecutar acciones fuera de su alcance.
 *
 * NOTA: en producción la autorización DEBE aplicarse en el servidor (un usuario
 * no puede cambiar su propio rol desde el browser). Acá el switcher de rol es
 * una demostración del diseño de permisos, no un control real.
 */
export type Role = "analista" | "oficial" | "auditor";

export interface Session {
  nombre: string;
  role: Role;
}

export const ROLES: { role: Role; label: string; nombre: string }[] = [
  { role: "analista", label: "Analista ALD", nombre: "Lic. Tomás Ferreyra" },
  { role: "oficial", label: "Oficial de Cumplimiento", nombre: "Lic. María González" },
  { role: "auditor", label: "Auditoría Interna", nombre: "Cra. Paula Ríos" },
];

const KEY = "phantom_session";

export function getSession(): Session {
  if (typeof window === "undefined") return { role: "analista", nombre: ROLES[0].nombre };
  try {
    const s = JSON.parse(localStorage.getItem(KEY) || "null");
    if (s?.role) return s;
  } catch { /* ignore */ }
  return { role: "analista", nombre: ROLES[0].nombre };
}

export function setSessionRole(role: Role) {
  const nombre = ROLES.find(r => r.role === role)?.nombre ?? "";
  localStorage.setItem(KEY, JSON.stringify({ role, nombre }));
}

/** Matriz de permisos por rol. */
const PERMS: Record<Role, Set<string>> = {
  analista: new Set(["caso.tomar", "caso.desestimar", "ros.crear", "ros.enviar_revision", "nota.agregar", "cdd.revisar", "cliente.alta"]),
  oficial: new Set(["caso.tomar", "caso.desestimar", "ros.crear", "ros.enviar_revision", "ros.aprobar", "ros.rechazar", "nota.agregar", "cdd.revisar", "cliente.alta"]),
  auditor: new Set(["auditoria.ver"]),
};

export function can(role: Role, action: string): boolean {
  return PERMS[role]?.has(action) ?? false;
}

export function roleLabel(role: Role): string {
  return ROLES.find(r => r.role === role)?.label ?? role;
}
