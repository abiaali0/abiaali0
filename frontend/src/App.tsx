import { FormEvent, useEffect, useMemo, useState } from "react";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
type Rule = { attribute:string; operator:"equals"|"in"|"starts_with"; value:string; enabled:boolean };
type Flag = { key:string; name:string; description:string; environment:string; enabled:boolean; rollout:number; rules:Rule[]; updated_at:string };
type AuditEvent = { id:number; event_type:string; flag_key:string; detail:string; created_at:string };

export default function App() {
  const [flags,setFlags] = useState<Flag[]>([]);
  const [audit,setAudit] = useState<AuditEvent[]>([]);
  const [status,setStatus] = useState("Connecting…");
  const [name,setName] = useState("");
  const [key,setKey] = useState("");

  const refresh = async () => {
    const [flagRes,auditRes] = await Promise.all([fetch(`${API}/api/flags`),fetch(`${API}/api/audit?limit=8`)]);
    if (!flagRes.ok || !auditRes.ok) throw new Error("API request failed");
    setFlags(await flagRes.json()); setAudit(await auditRes.json());
  };

  useEffect(() => {
    refresh().then(()=>setStatus("Live")).catch(()=>setStatus("API unavailable"));
    const ws = new WebSocket(API.replace(/^http/,"ws") + "/ws");
    ws.onopen=()=>setStatus("Live"); ws.onmessage=()=>refresh(); ws.onclose=()=>setStatus("Reconnecting on refresh");
    return ()=>ws.close();
  },[]);

  const enabledCount = useMemo(()=>flags.filter(f=>f.enabled).length,[flags]);
  const prodCount = useMemo(()=>flags.filter(f=>f.environment==="production").length,[flags]);
  const avgRollout = useMemo(()=>flags.length?Math.round(flags.reduce((sum,f)=>sum+f.rollout,0)/flags.length):0,[flags]);

  const patch = async (flag:Flag, changes:Partial<Flag>) => {
    const response = await fetch(`${API}/api/flags/${flag.key}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify(changes)});
    if (!response.ok) throw new Error("Update failed");
    await refresh();
  };

  const createFlag = async (event:FormEvent) => {
    event.preventDefault(); if (!name.trim() || !key.trim()) return;
    const response = await fetch(`${API}/api/flags`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name,key,environment:"development",enabled:false,rollout:0,rules:[]})});
    if (response.ok) { setName(""); setKey(""); await refresh(); }
  };

  return <main className="shell">
    <header className="hero"><div><div className="eyebrow">FEATURE DELIVERY CONTROL PLANE</div><h1>FlagForge</h1><p>Ship gradually. Target safely. See every change.</p></div><div className="live"><span/>{status}</div></header>
    <section className="metrics"><Metric label="Feature flags" value={flags.length}/><Metric label="Enabled" value={enabledCount}/><Metric label="Production" value={prodCount}/><Metric label="Avg. rollout" value={`${avgRollout}%`}/></section>
    <section className="grid">
      <div className="panel flags-panel"><span className="section-label">CONTROL PLANE</span><h2>Feature flags</h2><div className="flag-list">{flags.map(flag=><article className="flag-card" key={flag.key}>
        <div className="flag-top"><div><h3>{flag.name}</h3><code>{flag.key}</code></div><label className="switch"><input type="checkbox" checked={flag.enabled} onChange={()=>patch(flag,{enabled:!flag.enabled})}/><span className="slider"/></label></div>
        <p>{flag.description || "No description yet."}</p><div className="flag-meta"><span>{flag.environment}</span><strong>{flag.rollout}% rollout</strong></div>
        <input className="range" type="range" min="0" max="100" value={flag.rollout} onChange={e=>setFlags(prev=>prev.map(f=>f.key===flag.key?{...f,rollout:Number(e.target.value)}:f))} onMouseUp={e=>patch(flag,{rollout:Number((e.target as HTMLInputElement).value)})}/>
      </article>)}</div></div>
      <aside className="side"><div className="panel"><span className="section-label">CREATE</span><h2>New flag</h2><form onSubmit={createFlag}><input placeholder="Flag name" value={name} onChange={e=>setName(e.target.value)}/><input placeholder="flag-key" value={key} onChange={e=>setKey(e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g,"-"))}/><button type="submit">Create feature flag</button></form></div>
      <div className="panel"><span className="section-label">AUDIT LOG</span><h2>Recent activity</h2><div className="audit-list">{audit.map(event=><div className="audit-row" key={event.id}><div className="dot"/><div><strong>{event.flag_key}</strong><p>{event.detail}</p></div></div>)}</div></div></aside>
    </section>
  </main>;
}
function Metric({label,value}:{label:string;value:string|number}) { return <div className="metric"><span>{label}</span><strong>{value}</strong></div>; }
