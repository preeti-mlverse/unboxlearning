import { useEffect, useRef, useState, type DragEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, type SourceSummary } from "../api";
import { ErrorNote, Spinner } from "../ui";

const ACCEPT = ".pdf,.docx,.pptx,.md,.markdown,.txt,.html,.htm,.mp3,.wav,.m4a,.mp4,.webm,.png,.jpg,.jpeg,.webp";

export function SourceStats({ s }: { s: SourceSummary }) {
  const st = s.stats;
  const bits = [st.pages ? `${st.pages} pages` : null, `${st.heading} headings`, st.code ? `${st.code} code` : null,
    st.table ? `${st.table} tables` : null, st.figure ? `${st.figure} figures` : null, st.equation ? `${st.equation} equations` : null,
    st.transcript ? `${st.transcript} transcript segments` : null].filter(Boolean);
  return <span className="small muted">{s.kind} · {bits.join(" · ")}</span>;
}

export function NewCourse() {
  const nav = useNavigate();
  const [library, setLibrary] = useState<SourceSummary[]>([]);
  const [picked, setPicked] = useState<string[]>([]);
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const [url, setUrl] = useState("");
  const [crawl, setCrawl] = useState(false);
  const [text, setText] = useState("");
  const [textTitle, setTextTitle] = useState("");
  const [over, setOver] = useState(false);
  const [quality, setQuality] = useState("balanced");
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => { api.sources().then(setLibrary).catch(() => {}); }, []);

  const added = (list: SourceSummary[]) => {
    setLibrary((l) => [...list, ...l.filter((x) => !list.some((y) => y.id === x.id))]);
    setPicked((p) => [...new Set([...p, ...list.map((x) => x.id)])]);
  };
  const run = async (label: string, fn: () => Promise<void>) => {
    setBusy(label); setErr("");
    try { await fn(); } catch (e) { setErr(String(e)); } finally { setBusy(""); }
  };
  const onFiles = (files: File[]) => files.length && run(`Reading ${files.length} file(s)…`, async () => added(await api.upload(files)));
  const onDrop = (e: DragEvent) => { e.preventDefault(); setOver(false); onFiles([...e.dataTransfer.files]); };

  const create = () => run("Creating course…", async () => {
    const c = await api.createCourse(picked, "Untitled course", { quality });
    await api.analyse(c.id);
    nav(`/courses/${c.id}`);
  });

  return (
    <main className="page stack">
      <div>
        <h1>New course</h1>
        <div className="muted">Add the trusted material to learn from. Mix formats freely — everything becomes evidence the course can cite.</div>
      </div>
      <div className="grid2" style={{ alignItems: "start" }}>
        <div className="stack">
          <div className={`dropzone ${over ? "over" : ""}`} onDragOver={(e) => { e.preventDefault(); setOver(true); }}
            onDragLeave={() => setOver(false)} onDrop={onDrop} onClick={() => fileRef.current?.click()} role="button" tabIndex={0}>
            <strong>Drop files here</strong> or click to choose
            <div className="small">PDF · Word · PowerPoint · Markdown/text · HTML · audio/video · images</div>
            <input ref={fileRef} type="file" multiple accept={ACCEPT} hidden onChange={(e) => onFiles([...(e.target.files ?? [])])} />
          </div>
          <div className="card flat stack">
            <label htmlFor="url">Web page, docs site or YouTube URL</label>
            <div className="row" style={{ flexWrap: "nowrap" }}>
              <input id="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" />
              <button className="btn" disabled={!url.trim() || !!busy}
                onClick={() => run(crawl ? "Collecting pages…" : "Fetching…", async () => { added([await api.addUrl(url, crawl)]); setUrl(""); })}>Add</button>
            </div>
            <label className="row" style={{ fontWeight: 400, gap: 6 }}>
              <input type="checkbox" checked={crawl} onChange={(e) => setCrawl(e.target.checked)} style={{ width: "auto" }} />
              Include the whole docs section under this URL (up to 30 pages)
            </label>
          </div>
          <div className="card flat stack">
            <label htmlFor="txt">Paste text or notes</label>
            <input value={textTitle} onChange={(e) => setTextTitle(e.target.value)} placeholder="Title" aria-label="Title for pasted text" />
            <textarea id="txt" value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste Markdown or plain text…" rows={5} />
            <div><button className="btn" disabled={text.trim().length < 20 || !!busy}
              onClick={() => run("Reading text…", async () => { added([await api.addText(text, textTitle || "Pasted notes")]); setText(""); setTextTitle(""); })}>Add text</button></div>
          </div>
        </div>
        <div className="card stack">
          <div className="spread"><h3 style={{ margin: 0 }}>Sources for this course</h3><span className="badge primary">{picked.length} selected</span></div>
          {busy && <div className="notice row"><Spinner /> {busy}</div>}
          <ErrorNote error={err} />
          {!library.length && <div className="muted small">Nothing added yet.</div>}
          <div style={{ maxHeight: 420, overflowY: "auto" }}>
            {library.map((s) => (
              <label key={s.id} className="list-item" style={{ cursor: "pointer", fontWeight: 400, color: "inherit", margin: 0 }}>
                <input type="checkbox" checked={picked.includes(s.id)} style={{ width: "auto", marginTop: 4 }}
                  onChange={(e) => setPicked(e.target.checked ? [...picked, s.id] : picked.filter((x) => x !== s.id))} />
                <span style={{ flex: 1 }}>
                  <strong>{s.title}</strong><br /><SourceStats s={s} />
                  {s.parse_notes.slice(0, 2).map((n, i) => <div key={i} className="tiny faint">{n}</div>)}
                  {!!s.low_confidence_pages.length && <div className="tiny" style={{ color: "var(--warn)" }}>Low-confidence pages: {s.low_confidence_pages.slice(0, 10).join(", ")}</div>}
                </span>
              </label>
            ))}
          </div>
          <div>
            <label htmlFor="q">Quality mode</label>
            <select id="q" value={quality} onChange={(e) => setQuality(e.target.value)}>
              <option value="economy">Economy — fastest, lowest cost</option>
              <option value="balanced">Balanced — recommended</option>
              <option value="best">Best — strongest models for design and generation</option>
            </select>
          </div>
          <button className="btn primary" disabled={!picked.length || !!busy} onClick={create}>Analyse content →</button>
          <div className="tiny faint">Next, the engine profiles the material (what kind of knowledge it holds) and suggests goals it can genuinely support.</div>
        </div>
      </div>
    </main>
  );
}
