"use client";

import { ROLES, type Role, roleLabel } from "@/lib/session";

const COLORS: Record<Role, string> = { analista: "#7AA2FF", oficial: "#22C55E", auditor: "#F59E0B" };

export default function SessionSwitcher({ role, nombre, onChange }: { role: Role; nombre: string; onChange: (r: Role) => void }) {
  return (
    <div className="flex items-center gap-2 rounded-lg px-2.5 py-1.5" style={{ background: "#0A0D14", border: "1px solid #1E2430" }}>
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: COLORS[role] }} />
      <div className="leading-tight">
        <div className="text-[11px] font-semibold" style={{ color: "#EDEAE6" }}>{nombre}</div>
        <div className="text-[9px]" style={{ color: "#5A6478" }}>sesión simulada</div>
      </div>
      <select value={role} onChange={e => onChange(e.target.value as Role)}
        className="ml-1 rounded-md bg-[#12161F] px-2 py-1 text-[11px] outline-none" style={{ color: COLORS[role], border: "1px solid #1E2430" }}>
        {ROLES.map(r => <option key={r.role} value={r.role} style={{ color: "#EDEAE6" }}>{roleLabel(r.role)}</option>)}
      </select>
    </div>
  );
}
