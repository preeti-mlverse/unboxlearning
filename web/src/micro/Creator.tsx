import { useEffect, useRef, useState, type DragEvent } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { api, type Json, type SourceSummary } from "../api";
import { CardView } from "./Cards";
import { mapi, type Card, type Module } from "./mapi";
import { KIND_ICON as SRC_ICON } from "./Setup";

// ------------------------------------------------------------------ home

export function CreatorHome() {
  const [courses, setCourses] = useState<Json[] | null>(null);
  const [covers, setCovers] = useState<Record<string, Json>>({});
  useEffect(() => {
    api.courses().then(async (cs) => {
      setCourses(cs);
      const out: Record<string, Json> = {};
      await Promise.all(cs.map(async (c: Json) => { try { const d = await mapi.get(c.id); if (d.blueprint) out[c.id] = d.blueprint; } catch { /* old course */ } }));
      setCovers(out);
    });
  }, []);
  const micro = (courses ?? []).filter((c) => covers[c.id] && covers[c.id].status !== "outline");
  const drafts = (courses ?? []).filter((c) => covers[c.id]?.status === "outline"
    || (!covers[c.id] && ["analysing", "analysed", "outlined"].includes(c.status) && !Object.keys(c.activities ?? {}).length));
  return (
    <main className="m-page">
      <section className="m-create-hero">
        <div>
          <h1>Turn any material into a course people enjoy.</h1>
          <p>Drop in a PDF, slides, a spreadsheet, an e-book, a web page, a video or notes. You get short visual modules, quick games, a talking tutor and a memory deck — ready in minutes.</p>
          <Link className="m-btn big" to="/create">+ Create a course</Link>
        </div>
        <div className="m-steps-mini">
          <div><span>1</span>Add any material</div><div><span>2</span>We read it, you set the goal</div><div><span>3</span>Approve the outline</div><div><span>4</span>Review & share</div>
        </div>
      </section>
      {!!drafts.length && (
        <>
          <h2 className="m-h2">Drafts</h2>
          <div className="m-drafts">
            {drafts.map((c) => (
              <Link key={c.id} className="m-draft" to={`/create/${c.id}`}>
                <strong>{covers[c.id]?.course_title ?? c.title}</strong>
                <span className="m-meta">{covers[c.id] ? "Outline ready — review and generate" : c.status === "analysing" ? "Reading your material…" : "Understood — set goals"}</span>
                <span className="m-draft-go">Continue →</span>
              </Link>
            ))}
          </div>
        </>
      )}
      <h2 className="m-h2">Your courses</h2>
      {courses && !micro.length && <div className="m-empty">No courses yet — create your first one above.</div>}
      <div className="m-course-grid">
        {micro.map((c) => {
          const bp = covers[c.id];
          return (
            <div key={c.id} className="m-course">
              <Link to={`/course/${c.id}`} className="m-course-cover" style={bp.cover_media ? { backgroundImage: `url(/media/${bp.cover_media})` } : undefined} />
              <div className="m-course-body">
                <strong>{bp.course_title}</strong>
                <span>{bp.tagline}</span>
                <span className="m-meta">{bp.modules.length} modules · {c.status}</span>
                <div className="m-row">
                  <Link className="m-btn ghost sm" to={`/course/${c.id}`}>Edit & review</Link>
                  <Link className="m-btn sm" to={`/learn/${c.id}`}>Open as learner</Link>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      {courses && courses.length > micro.length + drafts.length && (
        <details className="m-older"><summary>Older courses (classic format)</summary>
          {courses.filter((c) => !covers[c.id] && !drafts.includes(c)).map((c) => <div key={c.id}><Link to={`/studio/${c.id}`}>{c.title}</Link> <span className="m-meta">{c.status}</span></div>)}
        </details>
      )}
    </main>
  );
}

// ------------------------------------------------------------------ create: step 1, add content

const ACCEPT = ".pdf,.docx,.pptx,.xlsx,.xlsm,.csv,.tsv,.epub,.md,.markdown,.txt,.html,.htm,.png,.jpg,.jpeg,.webp,.gif,.mp3,.wav,.m4a,.mp4,.mov,.webm,.ogg";
const TYPES: [string, string][] = [["📕", "PDF"], ["📝", "Word"], ["📊", "PowerPoint"], ["📈", "Excel / CSV"], ["📚", "E-book"], ["🌐", "Web page"],
  ["🗂", "Docs site"], ["▶️", "YouTube"], ["🎧", "Audio / video"], ["🖼", "Images"], ["📄", "Text / notes"]];
const STEPS = ["Add content", "Understand & set goals", "Review outline", "Generate"];

export function Create() {
  const nav = useNavigate();
  const [sources, setSources] = useState<SourceSummary[]>([]);
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const [url, setUrl] = useState("");
  const [crawl, setCrawl] = useState(false);
  const [text, setText] = useState("");
  const [over, setOver] = useState(false);
  const file = useRef<HTMLInputElement>(null);
  const run = async (label: string, fn: () => Promise<void>) => { setBusy(label); setErr(""); try { await fn(); } catch (e) { setErr(String(e)); } finally { setBusy(""); } };
  const add = (s: SourceSummary[]) => setSources((x) => [...x, ...s.filter((n) => !x.some((o) => o.id === n.id))]);
  const onFiles = (fs: File[]) => fs.length && run(`Reading ${fs.length === 1 ? fs[0].name : `${fs.length} files`}…`, async () => add(await api.upload(fs)));
  const onDrop = (e: DragEvent) => { e.preventDefault(); setOver(false); onFiles([...e.dataTransfer.files]); };
  const isYt = /youtu\.?be/.test(url);
  const addLink = () => run(crawl ? "Collecting the pages…" : isYt ? "Fetching the video transcript…" : "Fetching the link…",
    async () => { add([await api.addUrl(url.trim(), crawl && !isYt, 30)]); setUrl(""); setCrawl(false); });
  const analyse = () => run("Starting…", async () => {
    const c = await api.createCourse(sources.map((s) => s.id), "Untitled course", { quality: "balanced" });
    await api.patchCourse(c.id, { goal: { time_budget_minutes: 20 } });
    await api.analyse(c.id);
    nav(`/create/${c.id}`);
  });
  return (
    <main className="m-page narrow">
      <ol className="m-stepper">{STEPS.map((s, i) => <li key={s} className={i === 0 ? "now" : ""}><span>{i + 1}</span>{s}</li>)}</ol>
      <h1>Add your material</h1>
      <p className="m-sub">Anything you'd teach from. Mix and match — a textbook chapter, a video and your own notes can become one course.</p>
      <section className="m-step">
        <div className="m-step-body">
          <div className={`m-drop ${over ? "over" : ""}`} onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={onDrop}
            onClick={() => file.current?.click()} role="button" tabIndex={0} onKeyDown={(e) => e.key === "Enter" && file.current?.click()}>
            <strong>Drop files here</strong> or click to choose
            <div className="m-types">{TYPES.map(([i, t]) => <span key={t}>{i} {t}</span>)}</div>
            <input ref={file} type="file" multiple hidden accept={ACCEPT} onChange={(e) => { onFiles([...(e.target.files ?? [])]); e.target.value = ""; }} />
          </div>
          <div className="m-row">
            <input value={url} onChange={(e) => setUrl(e.target.value)} onKeyDown={(e) => e.key === "Enter" && url.trim() && !busy && addLink()}
              placeholder="…or paste a link: web page, YouTube video, or a file URL" aria-label="Link" style={{ flex: 1 }} />
            <button className="m-btn ghost" disabled={!url.trim() || !!busy} onClick={addLink}>Add link</button>
          </div>
          {!!url.trim() && !isYt && (
            <label className="m-sub small m-row"><input type="checkbox" checked={crawl} onChange={(e) => setCrawl(e.target.checked)} /> It's a documentation site — also collect the linked pages in this section (up to 30)</label>
          )}
          <details><summary className="m-sub">…or paste text</summary>
            <textarea value={text} onChange={(e) => setText(e.target.value)} rows={5} placeholder="Paste notes, a chapter, a transcript…" aria-label="Pasted text" />
            <button className="m-btn ghost" disabled={text.trim().length < 50 || !!busy}
              onClick={() => run("Reading…", async () => { add([await api.addText(text, text.trim().split("\n")[0].slice(0, 60) || "Pasted notes")]); setText(""); })}>Add text</button>
          </details>
          {sources.map((s) => (
            <div key={s.id} className="m-source"><span className="m-source-ic">{SRC_ICON[s.kind] ?? "📄"}</span>
              <div><strong>{s.title}</strong><span className="m-meta">{s.kind}{s.stats.pages ? ` · ${s.stats.pages} pages` : ""} · {s.stats.heading} sections{s.stats.figure ? ` · ${s.stats.figure} figures` : ""}{s.stats.table ? ` · ${s.stats.table} tables` : ""}</span></div>
              <button className="m-icon" onClick={() => setSources(sources.filter((x) => x.id !== s.id))} aria-label="Remove">✕</button></div>
          ))}
          {busy && <div className="m-sub">⏳ {busy}</div>}
          {err && <div className="m-fb no">{err}</div>}
        </div>
      </section>
      <div className="m-row" style={{ marginTop: 18 }}>
        <button className="m-btn big" disabled={!sources.length || !!busy} onClick={analyse}>Analyse my content →</button>
        <span className="m-sub small">{sources.length ? `${sources.length} source${sources.length > 1 ? "s" : ""} ready` : "Add at least one source"}</span>
      </div>
    </main>
  );
}

// ------------------------------------------------------------------ build progress + review/edit

const STAGES: [string, string][] = [["read", "Reading your material"], ["understand", "Finding the key ideas"], ["design", "Designing the journey"],
  ["create", "Writing modules & games"], ["visualise", "Drawing illustrations"], ["done", "Ready"]];

export function CoursePreview() {
  const { cid = "" } = useParams();
  const [d, setD] = useState<Awaited<ReturnType<typeof mapi.get>> | null>(null);
  const [mi, setMi] = useState(0);
  const [ci, setCi] = useState(0);
  const [err, setErr] = useState("");
  const timer = useRef<number | undefined>(undefined);
  const load = async () => {
    try {
      const x = await mapi.get(cid);
      setD(x);
      window.clearTimeout(timer.current);
      if (x.job?.status === "running") timer.current = window.setTimeout(load, 2000);
    } catch (e) { setErr(String(e)); }
  };
  useEffect(() => { load(); return () => window.clearTimeout(timer.current); }, [cid]); // eslint-disable-line react-hooks/exhaustive-deps
  if (err) return <main className="m-page"><div className="m-fb no">{err}</div></main>;
  if (!d) return <main className="m-page"><div className="m-loading" /></main>;
  const job = d.job;
  if ((!d.blueprint || d.blueprint.status === "outline") && !(job?.kind === "micro" && job.status === "running")) {
    return <Navigate to={`/create/${cid}`} replace />;
  }
  const building = job?.status === "running" || (!d.blueprint && job?.status !== "failed");
  if (building || !d.modules.length) return <Building d={d} />;
  const bp = d.blueprint!;
  const m = d.modules[mi];
  const setCard = (card: Card) => { const mods = [...d.modules]; mods[mi] = { ...m, cards: m.cards.map((c, k) => (k === ci ? card : c)) }; setD({ ...d, modules: mods }); };
  const flagged = d.modules.reduce((n, x) => n + Object.keys(x.flags ?? {}).length, 0);
  return (
    <main className="m-page wide">
      <section className="m-cover-head" style={bp.cover_media ? { backgroundImage: `linear-gradient(90deg, rgba(20,16,50,.88), rgba(20,16,50,.3)), url(/media/${bp.cover_media})` } : undefined}>
        <div>
          <div className="m-kicker light">Course ready · {d.modules.length} modules · {d.modules.reduce((n, x) => n + x.cards.length, 0)} cards</div>
          <h1>{bp.course_title}</h1>
          <p>{bp.learner_promise}</p>
          <div className="m-row">
            <Link className="m-btn big" to={`/learn/${cid}`}>▶ Try it as a learner</Link>
            <button className="m-btn ghost light" onClick={async () => { await mapi.publish(cid, !d.course.published); load(); }}>{d.course.published ? "✓ Published" : "Publish"}</button>
            <button className="m-btn ghost light" onClick={() => navigator.clipboard?.writeText(`${location.origin}/learn/${cid}`)}>Copy learner link</button>
          </div>
        </div>
      </section>
      {flagged > 0 && <div className="m-fb mid">⚠️ {flagged} card{flagged > 1 ? "s" : ""} flagged by the fact-check — marked below. Open them and rewrite or edit.</div>}
      <HowMade d={d} />
      <div className="m-editor">
        <nav className="m-mod-list">
          {d.modules.map((x, k) => (
            <button key={x.id} className={`m-mod ${k === mi ? "on" : ""}`} onClick={() => { setMi(k); setCi(0); }}>
              <span className="m-num">{k + 1}</span><span><strong>{x.title}</strong><small>{x.goal}</small></span>
              {Object.keys(x.flags ?? {}).length > 0 && <span className="m-flag">⚠️</span>}
            </button>
          ))}
          <Link className="m-sub small" to={`/studio/${cid}`}>Advanced (sources, analytics, exports) →</Link>
        </nav>
        <div>
          {!!m.rule_issues?.length && (
            <div className="m-fb mid small"><strong>Style check:</strong> {m.rule_issues.join(" · ")}</div>
          )}
          <div className="m-strip">
            {m.cards.map((c, k) => (
              <button key={k} className={`m-thumb ${k === ci ? "on" : ""} ${m.flags?.[String(k)] ? "flag" : ""}`} onClick={() => setCi(k)} title={c.title}>
                <span className="m-thumb-kind">{KIND_ICON[c.kind]}</span><span>{c.title}</span>
              </button>
            ))}
          </div>
          <div className="m-edit-grid">
            <div className="m-phone"><div className="m-phone-in" key={`${mi}-${ci}-${c2s(m.cards[ci])}`}>
              <CardView card={m.cards[ci]} seed={`p${mi}-${ci}`} done={() => {}} ctx={{ cid, mid: m.id, index: ci }} />
            </div></div>
            <CardEditor cid={cid} m={m} i={ci} onChange={setCard} />
          </div>
        </div>
      </div>
    </main>
  );
}

const c2s = (c: Card) => (c.title + c.text).length + (c.visual.media ?? "");
const KIND_ICON: Record<string, string> = { hook: "✨", concept: "💡", example: "🔎", check: "❓", true_false: "⚡", sort: "🗂", reorder: "🔢",
  match: "🔗", odd_one_out: "🧩", fill_blank: "✏️", apply: "🎯", recap: "📌" };

function Building({ d }: { d: Awaited<ReturnType<typeof mapi.get>> }) {
  const job = d.job;
  const stage = job?.stage ?? "read";
  const idx = Math.max(0, STAGES.findIndex(([k]) => k === stage));
  return (
    <main className="m-page narrow">
      <h1>Creating your course…</h1>
      <p className="m-sub">{job?.message}</p>
      <div className="m-build">
        {STAGES.map(([k, label], i) => (
          <div key={k} className={`m-build-step ${i < idx ? "done" : i === idx ? "now" : ""}`}>
            <span className="m-dot">{i < idx ? "✓" : i === idx ? <span className="m-spin" /> : ""}</span>{label}
          </div>
        ))}
      </div>
      {job?.status === "failed" && <div className="m-fb no">{job.message}</div>}
      {d.profile && (
        <div className="m-found">
          <div className="m-kicker">What we found</div>
          <strong>{d.profile.title}</strong>
          <p>{d.profile.summary}</p>
        </div>
      )}
      {d.blueprint && (
        <div className="m-found">
          <div className="m-kicker">Your journey</div>
          <ol>{d.blueprint.modules.map((m: Module) => <li key={m.id}><strong>{m.title}</strong> — {m.goal}</li>)}</ol>
        </div>
      )}
    </main>
  );
}

function HowMade({ d }: { d: Awaited<ReturnType<typeof mapi.get>> }) {
  const p = d.profile, bp = d.blueprint!;
  return (
    <details className="m-howmade">
      <summary>How this course was made from your material</summary>
      <div className="m-flowline">
        <div><span>📄</span><strong>Your material</strong><small>{p?.title}</small></div>
        <div>→</div>
        <div><span>🔍</span><strong>Understood as</strong><small>{p?.genre?.replace("_", " ")} · {(p?.knowledge_mix ?? []).slice(0, 2).map((k: Json) => k.type).join(", ")}</small></div>
        <div>→</div>
        <div><span>🧭</span><strong>{bp.modules.length} big ideas</strong><small>{bp.modules.map((m) => m.title).join(" · ")}</small></div>
        <div>→</div>
        <div><span>🃏</span><strong>{d.modules.reduce((n, m) => n + m.cards.length, 0)} cards</strong><small>visual teaching + games + a tutor</small></div>
      </div>
      {!!bp.skipped?.length && <p className="m-sub small"><strong>Left out on purpose:</strong> {bp.skipped.join(" · ")}</p>}
      <p className="m-sub small">Every card is checked for length, reading level and a working answer key, then fact-checked against your material.</p>
    </details>
  );
}

function CardEditor({ cid, m, i, onChange }: { cid: string; m: Module; i: number; onChange: (c: Card) => void }) {
  const card = m.cards[i];
  const [draft, setDraft] = useState(card);
  const [instr, setInstr] = useState("");
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState("");
  useEffect(() => { setDraft(card); setMsg(""); }, [card, i, m.id]);
  const act = async (label: string, fn: () => Promise<Card>) => { setBusy(label); setMsg(""); try { const c = await fn(); onChange(c); setMsg("Saved ✓"); } catch (e) { setMsg(String(e)); } finally { setBusy(""); } };
  const flags = m.flags?.[String(i)];
  const teach = ["hook", "concept", "example"].includes(card.kind);
  return (
    <div className="m-card-editor">
      <div className="m-kicker">{KIND_ICON[card.kind]} {card.kind.replace("_", " ")} · card {i + 1} of {m.cards.length}</div>
      {flags && <div className="m-fb mid"><strong>Fact-check:</strong> {flags.join(" ")}</div>}
      <label>Title</label>
      <input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
      {card.kind !== "recap" && <><label>{teach ? "Text" : "Prompt"}</label><textarea rows={3} value={draft.text} onChange={(e) => setDraft({ ...draft, text: e.target.value })} /></>}
      {teach && <><label>What the narrator says</label><textarea rows={3} value={draft.narration} onChange={(e) => setDraft({ ...draft, narration: e.target.value })} /></>}
      {card.kind === "apply" && <><label>Task</label><textarea rows={3} value={draft.question} onChange={(e) => setDraft({ ...draft, question: e.target.value })} /></>}
      <div className="m-row">
        <button className="m-btn" disabled={!!busy || JSON.stringify(draft) === JSON.stringify(card)} onClick={() => act("Saving…", () => mapi.putCard(cid, m.id, i, draft))}>Save edits</button>
        {card.visual.kind === "illustration" && <button className="m-btn ghost" disabled={!!busy} onClick={() => act("Drawing…", () => mapi.redraw(cid, m.id, i))}>🎨 New picture</button>}
      </div>
      <label>Or ask AI to rewrite this card</label>
      <div className="m-row">
        <input value={instr} onChange={(e) => setInstr(e.target.value)} placeholder="e.g. simpler words; an Indian example; make it a sort game" />
        <button className="m-btn ghost" disabled={!!busy} onClick={() => act("Rewriting…", () => mapi.regen(cid, m.id, i, instr))}>Rewrite</button>
      </div>
      {busy && <div className="m-sub">⏳ {busy}</div>}
      {msg && <div className="m-sub">{msg}</div>}
      {card.visual.kind !== "none" && card.visual.kind !== "illustration" && card.visual.kind !== "figure" && (
        <div className="m-sub small">Diagram drawn from data: {card.visual.kind}</div>
      )}
    </div>
  );
}
