import { useEffect, useState } from "react";
import type { Course, Json } from "../api";
import { ModelView, type Hotspot } from "../model3d";
import { ErrorNote } from "../ui";

type Asset = { id: string; name: string; description: string; tags: string[]; media_path: string; hotspots: Hotspot[] };

async function call<T>(method: string, url: string, body?: unknown): Promise<T> {
  const init: RequestInit = { method };
  if (body instanceof FormData) init.body = body;
  else if (body) { init.body = JSON.stringify(body); init.headers = { "Content-Type": "application/json" }; }
  const r = await fetch(url, init);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail ?? r.statusText);
  return r.json();
}

export function Assets({ course }: { course: Course }) {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [sel, setSel] = useState<string | null>(null);
  const [err, setErr] = useState("");
  const [form, setForm] = useState({ name: "", description: "", tags: "" });
  const [file, setFile] = useState<File | null>(null);
  const load = () => call<Asset[]>("GET", `/api/courses/${course.id}/assets`).then(setAssets).catch((e) => setErr(String(e)));
  useEffect(() => { load(); }, [course.id]); // eslint-disable-line

  const upload = async () => {
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file); fd.append("name", form.name || file.name); fd.append("description", form.description); fd.append("tags", form.tags);
    try { const a = await call<Asset>("POST", `/api/courses/${course.id}/assets`, fd); setForm({ name: "", description: "", tags: "" }); setFile(null); await load(); setSel(a.id); }
    catch (e) { setErr(String(e)); }
  };
  const asset = assets.find((a) => a.id === sel);
  return (
    <div className="card stack">
      <div className="spread"><strong>3D models</strong><span className="small muted">{assets.length} attached</span></div>
      <div className="small muted">
        Attach licensed 3D models (.glb) for things learners should explore spatially — anatomy, machines, molecules, buildings.
        Place labelled hotspots by clicking on the model. Lessons whose concepts match a model's name, description or tags will use it
        (rebuild, or regenerate an activity as “Explore in 3D”). Sources for models: your own, Sketchfab (check licence), NIH 3D, Smithsonian 3D.
      </div>
      <div className="grid2">
        <div><label>Model file (.glb)</label><input type="file" accept=".glb,.gltf" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></div>
        <div><label>Name</label><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Human heart" /></div>
        <div><label>Description</label><input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="what it shows" /></div>
        <div><label>Tags (comma separated)</label><input value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} placeholder="ventricle, atrium, valve" /></div>
      </div>
      <div><button className="btn" disabled={!file} onClick={upload}>Attach model</button></div>
      <ErrorNote error={err} />
      <div className="row">{assets.map((a) => <button key={a.id} className={`chip ${a.id === sel ? "on" : ""}`} onClick={() => setSel(a.id)}>{a.name} · {a.hotspots.length} hotspots</button>)}</div>
      {asset && <HotspotEditor key={asset.id} course={course} asset={asset} onSaved={load} />}
    </div>
  );
}

function HotspotEditor({ course, asset, onSaved }: { course: Course; asset: Asset; onSaved: () => void }) {
  const [hs, setHs] = useState<Hotspot[]>(asset.hotspots);
  const [pending, setPending] = useState<{ position: string; normal: string } | null>(null);
  const [label, setLabel] = useState("");
  const [msg, setMsg] = useState("");
  const save = async (list: Hotspot[]) => {
    await call<Json>("PUT", `/api/courses/${course.id}/assets/${asset.id}`, { hotspots: list });
    setMsg("Saved"); onSaved();
  };
  return (
    <div className="stack">
      <ModelView src={`/media/${asset.media_path}`} hotspots={hs} onPick={(p) => { setPending(p); setLabel(""); }} />
      <div className="small muted">Click a point on the model to add a hotspot.</div>
      {pending && (
        <div className="row" style={{ flexWrap: "nowrap" }}>
          <input autoFocus value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Label, e.g. Left ventricle" aria-label="Hotspot label"
            onKeyDown={(e) => { if (e.key === "Enter" && label.trim()) { const n = [...hs, { ...pending, label: label.trim() }]; setHs(n); setPending(null); save(n); } }} />
          <button className="btn primary" disabled={!label.trim()} onClick={() => { const n = [...hs, { ...pending, label: label.trim() }]; setHs(n); setPending(null); save(n); }}>Add</button>
          <button className="btn ghost" onClick={() => setPending(null)}>Cancel</button>
        </div>
      )}
      {hs.map((h, i) => (
        <div key={i} className="row small">
          <span className="badge primary">{i + 1}</span> {h.label}
          <button className="btn ghost sm danger" onClick={() => { const n = hs.filter((_, k) => k !== i); setHs(n); save(n); }}>Remove</button>
        </div>
      ))}
      {msg && <div className="tiny faint">{msg}</div>}
    </div>
  );
}
