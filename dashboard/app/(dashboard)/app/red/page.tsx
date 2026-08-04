"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";

interface Txn { src: string; dst: string; src_name: string; dst_name: string; src_type: string; dst_type: string; amount: number; is_fraud: number; }
interface Edge { src: string; dst: string; amount: number; is_fraud: number; }
interface NodeInfo { name: string; type: string; fraud: boolean; }

export default function RedPage() {
  const cyRef = useRef<HTMLDivElement>(null);
  const cyInst = useRef<any>(null);
  const adj = useRef<Map<string, Edge[]>>(new Map());
  const info = useRef<Map<string, NodeInfo>>(new Map());
  const expandRef = useRef<(id: string) => void>(() => {});

  const [ready, setReady] = useState(false);
  const [seed, setSeed] = useState("");
  const [visible, setVisible] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [fraudOnly, setFraudOnly] = useState(false);

  const neighborsOf = (id: string, cap = 12) =>
    Array.from(new Set(
      (adj.current.get(id) ?? [])
        .slice().sort((a, b) => b.amount - a.amount).slice(0, cap)
        .flatMap(e => [e.src, e.dst])
    ));

  // carga + adyacencia
  useEffect(() => {
    fetch("/data/transactions_sample.json").then(r => r.json()).then((txns: Txn[]) => {
      const a = new Map<string, Edge[]>(), inf = new Map<string, NodeInfo>(), deg = new Map<string, number>();
      const push = (k: string, e: Edge) => { if (!a.has(k)) a.set(k, []); a.get(k)!.push(e); };
      for (const t of txns) {
        const e: Edge = { src: t.src, dst: t.dst, amount: t.amount, is_fraud: t.is_fraud };
        push(t.src, e); push(t.dst, e);
        if (!inf.has(t.src)) inf.set(t.src, { name: t.src_name, type: t.src_type, fraud: false });
        if (!inf.has(t.dst)) inf.set(t.dst, { name: t.dst_name, type: t.dst_type, fraud: false });
        if (t.is_fraud) { inf.get(t.src)!.fraud = true; inf.get(t.dst)!.fraud = true; }
        deg.set(t.src, (deg.get(t.src) ?? 0) + 1); deg.set(t.dst, (deg.get(t.dst) ?? 0) + 1);
      }
      adj.current = a; info.current = inf;
      let best = "", bd = -1;
      Array.from(deg).forEach(([id, d]) => { if (inf.get(id)?.fraud && d > bd) { bd = d; best = id; } });
      setSeed(best); setSelected(best);
      setVisible(new Set([best, ...neighborsOf(best)]));
      setReady(true);
    });
  }, []);

  useEffect(() => {
    expandRef.current = (id: string) => setVisible(prev => {
      const next = new Set(prev); neighborsOf(id).forEach(n => next.add(n)); return next;
    });
  }, []);

  // (re)dibujar
  useEffect(() => {
    if (!ready || !cyRef.current) return;
    import("cytoscape").then(({ default: cytoscape }) => {
      if (cyInst.current) cyInst.current.destroy();
      const vis = visible;
      const nodes = Array.from(vis).map(id => {
        const ni = info.current.get(id);
        return { data: { id, label: (ni?.name || id).split(" ").slice(0, 2).join(" "), fraud: ni?.fraud ? 1 : 0, seed: id === seed ? 1 : 0 } };
      });
      const seen = new Set<string>(), edges: any[] = [];
      for (const id of Array.from(vis)) for (const e of adj.current.get(id) ?? []) {
        if (!vis.has(e.src) || !vis.has(e.dst)) continue;
        if (fraudOnly && !e.is_fraud) continue;
        const key = `${e.src}|${e.dst}|${e.amount}`;
        if (seen.has(key)) continue; seen.add(key);
        edges.push({ data: { id: key, source: e.src, target: e.dst, amount: "$" + Math.round(e.amount).toLocaleString("es-AR"), fraud: e.is_fraud } });
      }
      const cy = cytoscape({
        container: cyRef.current, elements: [...nodes, ...edges],
        style: [
          { selector: "node", style: { "width": 30, "height": 30, "background-color": "#5A6478", "label": "data(label)", "font-size": 9, "color": "#8A93A6", "text-valign": "bottom", "text-margin-y": 3 } },
          { selector: "node[fraud=1]", style: { "background-color": "#EF4444" } },
          { selector: "node[seed=1]", style: { "background-color": "#0A1226", "border-width": 3, "border-color": "#2E6BFF", "width": 42, "height": 42, "color": "#7AA2FF", "font-weight": "bold" } },
          { selector: "node:selected", style: { "border-width": 3, "border-color": "#F59E0B" } },
          { selector: "edge", style: { "width": 1.5, "line-color": "#2A3242", "target-arrow-color": "#2A3242", "target-arrow-shape": "triangle", "curve-style": "bezier", "label": "data(amount)", "font-size": 7, "color": "#5A6478", "text-rotation": "autorotate" } },
          { selector: "edge[fraud=1]", style: { "line-color": "#7F1D1D", "target-arrow-color": "#7F1D1D", "width": 2 } },
        ],
        layout: { name: "cose", animate: true, animationDuration: 500, nodeRepulsion: () => 9000, idealEdgeLength: () => 95, padding: 30 },
      });
      cy.on("tap", "node", (evt: any) => { const id = evt.target.id(); setSelected(id); expandRef.current(id); });
      if (selected) cy.getElementById(selected).select();
      cyInst.current = cy;
    });
    return () => { if (cyInst.current) cyInst.current.destroy(); };
  }, [visible, fraudOnly, ready, seed]);

  const doSearch = () => {
    const q = search.trim().toLowerCase();
    if (!q) return;
    let id = Array.from(info.current.keys()).find(k => k.toLowerCase() === q);
    if (!id) id = Array.from(info.current.entries()).find(([, v]) => v.name.toLowerCase().includes(q))?.[0];
    if (id) { setSeed(id); setSelected(id); setVisible(new Set([id, ...neighborsOf(id)])); }
  };
  const reset = () => { setVisible(new Set([seed, ...neighborsOf(seed)])); setSelected(seed); };

  const sel = selected ? info.current.get(selected) : null;
  const selDeg = selected ? new Set((adj.current.get(selected) ?? []).flatMap(e => [e.src, e.dst])).size - 1 : 0;
  const inp = "rounded-lg border border-[#1E2430] bg-[#12161F] px-2 min-h-[40px] text-sm outline-none";

  return (
    <div className="space-y-4">
      <PageHeader eyebrow="Investigación" title="Investigación de Redes"
        description="Explorá relaciones y seguí el flujo del dinero de forma interactiva: hacé clic en un nodo para expandir sus conexiones, buscá una entidad de partida y aislá el fraude. Grafo sobre la muestra transaccional." />

      <div className="rounded-xl p-3 flex flex-wrap gap-2 items-center" style={{ background: "#0E1219", border: "1px solid #1E2430" }}>
        <input value={search} onChange={e => setSearch(e.target.value)} onKeyDown={e => e.key === "Enter" && doSearch()}
          placeholder="Entidad de partida (cuenta o nombre)…" className={inp + " flex-1 min-w-[220px]"} style={{ color: "#EDEAE6" }} />
        <button onClick={doSearch} className="rounded-lg px-3 min-h-[40px] text-sm font-medium" style={{ background: "rgba(46,107,255,0.15)", color: "#7AA2FF", border: "1px solid #2E6BFF" }}>Explorar</button>
        <button onClick={reset} className="rounded-lg px-3 min-h-[40px] text-sm" style={{ color: "#5A6478", border: "1px solid #1E2430" }}>↺ Reiniciar</button>
        <label className="flex items-center gap-1.5 text-xs cursor-pointer ml-2" style={{ color: fraudOnly ? "#EF4444" : "#5A6478" }}>
          <input type="checkbox" checked={fraudOnly} onChange={e => setFraudOnly(e.target.checked)} /> Solo flujo fraudulento
        </label>
        <span className="text-xs ml-auto" style={{ color: "#5A6478" }}>{visible.size} nodos visibles</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-3 rounded-xl overflow-hidden" style={{ background: "#0A0D14", border: "1px solid #1E2430" }}>
          <div ref={cyRef} style={{ width: "100%", height: 560 }} />
          <div className="flex flex-wrap gap-x-4 gap-y-1 px-3 py-2 text-[10px]" style={{ color: "#5A6478", borderTop: "1px solid #1E2430" }}>
            <span className="flex items-center gap-1"><span style={{ width: 9, height: 9, borderRadius: "50%", background: "#0A1226", border: "2px solid #2E6BFF", display: "inline-block" }} /> Entidad de partida</span>
            <span className="flex items-center gap-1"><span style={{ width: 9, height: 9, borderRadius: "50%", background: "#EF4444", display: "inline-block" }} /> Cuenta de fraude</span>
            <span className="flex items-center gap-1"><span style={{ width: 9, height: 9, borderRadius: "50%", background: "#5A6478", display: "inline-block" }} /> Contraparte</span>
            <span>— arista roja = transacción fraudulenta · clic en un nodo = expandir</span>
          </div>
        </div>

        <div className="rounded-xl p-4" style={{ background: "#0E1219", border: "1px solid #1E2430" }}>
          <h3 className="text-sm font-bold mb-2" style={{ color: "#EDEAE6" }}>Entidad seleccionada</h3>
          {sel ? (
            <div className="space-y-2 text-xs">
              <div><span className="text-[#5A6478]">Nombre:</span> <span style={{ color: "#EDEAE6" }}>{sel.name || "—"}</span></div>
              <div><span className="text-[#5A6478]">Cuenta:</span> <span className="font-mono" style={{ color: "#EDEAE6" }}>{selected}</span></div>
              <div><span className="text-[#5A6478]">Tipo:</span> <span style={{ color: "#EDEAE6" }}>{sel.type}</span></div>
              <div><span className="text-[#5A6478]">Estado:</span> <span style={{ color: sel.fraud ? "#EF4444" : "#22C55E" }}>{sel.fraud ? "Vinculada a fraude" : "Sin marcar"}</span></div>
              <div><span className="text-[#5A6478]">Conexiones (muestra):</span> <span style={{ color: "#EDEAE6" }}>{selDeg}</span></div>
              <div className="pt-2 flex flex-col gap-1.5" style={{ borderTop: "1px solid #1E2430" }}>
                <button onClick={() => selected && expandRef.current(selected)} className="rounded-lg px-3 py-2 text-xs font-medium" style={{ background: "rgba(46,107,255,0.12)", color: "#7AA2FF", border: "1px solid rgba(46,107,255,0.35)" }}>+ Expandir conexiones</button>
                <Link href={`/app/clientes/${selected}`} className="rounded-lg px-3 py-2 text-xs text-center" style={{ color: "#7AA2FF", border: "1px solid #1E2430" }}>Ver legajo del cliente →</Link>
              </div>
            </div>
          ) : <p className="text-xs" style={{ color: "#5A6478" }}>Hacé clic en un nodo del grafo.</p>}
        </div>
      </div>
    </div>
  );
}
