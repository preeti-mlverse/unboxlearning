// Course set-up after upload: what we understood → who it's for → outline you can edit → generate.
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, type Json } from "../api";
import { mapi, type Blueprint } from "./mapi";

type Micro = Awaited<ReturnType<typeof mapi.get>>;
interface OutlineMod { title: string; goal: string; big_idea: string; minutes: number; concept_ids: string[] }

export const AUDIENCES: [string, string, string][] = [
  ["novice", "Kids", "8–12 years"], ["beginner", "School students", "13–16 years"], ["intermediate", "College / adults", "new to the topic"],
  ["advanced", "Professionals", "some background"],
];
export const PURPOSES: [string, string][] = [["understand", "Understand it"], ["apply", "Be able to do it"], ["exam_prep", "Prepare for an exam"],
  ["revision", "Quick revision"], ["onboarding", "Get up to speed at work"]];
const LANGS: [string, string][] = [["en", "English"], ["hi", "हिन्दी Hindi"], ["ta", "தமிழ் Tamil"], ["te", "తెలుగు Telugu"], ["bn", "বাংলা Bengali"],
  ["mr", "मराठी Marathi"], ["es", "Español"], ["fr", "Français"], ["de", "Deutsch"], ["ar", "العربية Arabic"]];

// How each kind of knowledge the engine detects turns into a learning experience.
const TEACH: Record<string, [string, string]> = {
  fact: ["🔗", "Match-ups, fill-the-blank and a memory deck for terms and names"],
  concept: ["🗂", "Sort games: what is and isn't an example, with pictures"],
  principle: ["⚡", "Cause-and-effect cards and quick true/false rounds"],
  process: ["🔄", "Step-by-step flow and cycle diagrams, then put-it-in-order games"],
  procedure: ["🎯", "Do-it-yourself steps and a hands-on task with feedback"],
  structure: ["🧩", "Labelled part diagrams and spot-the-odd-one-out"],
  chronology: ["🕰", "Timelines and order-the-events games"],
  argument: ["⚖️", "Compare-the-sides cards and a written 'what would you do'"],
  quantitative: ["➗", "Formula cards and worked examples to check"],
  code: ["💻", "Code cards with real snippets and fix-the-bug questions"],
  language: ["🗣", "Vocabulary match-ups, usage gaps and pronunciation"],
  data: ["📊", "Read-the-chart and compare cards"],
};
const GENRE: Record<string, string> = { textbook: "Textbook", technical_docs: "Technical documentation", research_paper: "Research paper",
  encyclopedic: "Reference article", how_to_manual: "How-to manual", policy_legal: "Policy / legal", narrative_history: "History / narrative",
  literature: "Literature", lecture_slides: "Lecture slides", transcript: "Talk / video transcript", question_bank: "Question bank",
  data_report: "Data report", business_case: "Business case", other: "Mixed material" };
const PLAN_STAGES: [string, string][] = [["read", "Reading your material"], ["understand", "Finding the key ideas"], ["design", "Designing the outline"]];
const toLevel = (l: string) => (l === "expert" ? "advanced" : l);

export function Setup() {
  const { cid = "" } = useParams();
  const nav = useNavigate();
  const [d, setD] = useState<Micro | null>(null);
  const [err, setErr] = useState("");
  const [editSettings, setEditSettings] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const load = async () => {
    try {
      const x = await mapi.get(cid);
      setD(x);
      window.clearTimeout(timer.current);
      if (x.job?.status === "running") timer.current = window.setTimeout(load, 1500);
      const st = x.blueprint?.status;
      if (st === "building" || st === "ready") nav(`/course/${cid}`, { replace: true });
    } catch (e) { setErr(String(e)); }
  };
  useEffect(() => { load(); return () => window.clearTimeout(timer.current); }, [cid]); // eslint-disable-line react-hooks/exhaustive-deps

  if (err) return <main className="m-page narrow"><div className="m-fb no">{err}</div></main>;
  if (!d) return <main className="m-page narrow"><div className="m-loading" /></main>;
  const job = d.job;
  const running = job?.status === "running";
  const failed = job?.status === "failed";
  const retry = async (fn: () => Promise<unknown>) => { setErr(""); try { await fn(); load(); } catch (e) { setErr(String(e)); } };

  return (
    <main className="m-page narrow">
      <Stepper at={!d.profile ? 1 : d.blueprint?.status === "outline" && !editSettings ? 3 : 2} />
      {failed && (
        <div className="m-fb no">
          <strong>That step didn't finish.</strong> {job.message}
          <div className="m-row" style={{ marginTop: 8 }}>
            <button className="m-btn sm" onClick={() => retry(() => (d.profile ? mapi.plan(cid) : api.analyse(cid)))}>Try again</button>
          </div>
        </div>
      )}
      {!d.profile && !failed && <Reading d={d} />}
      {d.profile && running && job?.kind === "micro_plan" && <Planning d={d} />}
      {d.profile && !running && (d.blueprint?.status !== "outline" || editSettings) && (
        <Understood d={d} onPlanned={() => { setEditSettings(false); load(); }} onOneClick={() => nav(`/course/${cid}`)} />
      )}
      {d.profile && !running && d.blueprint?.status === "outline" && !editSettings && (
        <Outline d={d} onBack={() => setEditSettings(true)} onGenerate={() => nav(`/course/${cid}`)} />
      )}
    </main>
  );
}

function Stepper({ at }: { at: number }) {
  const steps = ["Add content", "Understand & set goals", "Review outline", "Generate"];
  return (
    <ol className="m-stepper">
      {steps.map((s, i) => <li key={s} className={i < at ? "done" : i === at ? "now" : ""}><span>{i < at ? "✓" : i + 1}</span>{s}</li>)}
    </ol>
  );
}

function Reading({ d }: { d: Micro }) {
  return (
    <>
      <h1>Reading your material…</h1>
      <p className="m-sub">We're working out what kind of content this is, what's worth learning in it, and what goals it can support. Usually under a minute.</p>
      <div className="m-build">
        {d.sources.map((s) => (
          <div key={s.id} className="m-build-step now"><span className="m-dot"><span className="m-spin" /></span>{KIND_ICON[s.kind] ?? "📄"} {s.title}</div>
        ))}
      </div>
    </>
  );
}

function Planning({ d }: { d: Micro }) {
  const idx = Math.max(0, PLAN_STAGES.findIndex(([k]) => k === d.job?.stage));
  return (
    <>
      <h1>Designing your outline…</h1>
      <p className="m-sub">{d.job?.message}</p>
      <div className="m-build">
        {PLAN_STAGES.map(([k, label], i) => (
          <div key={k} className={`m-build-step ${i < idx ? "done" : i === idx ? "now" : ""}`}>
            <span className="m-dot">{i < idx ? "✓" : i === idx ? <span className="m-spin" /> : ""}</span>{label}
          </div>
        ))}
      </div>
      <div className="m-bar"><i style={{ width: `${Math.round((d.job?.progress ?? 0) / 0.35 * 100)}%` }} /></div>
    </>
  );
}

function Understood({ d, onPlanned, onOneClick }: { d: Micro; onPlanned: () => void; onOneClick: () => void }) {
  const p = d.profile as Json;
  const g = d.course.goal as Json;
  const [level, setLevel] = useState<string>(toLevel(g.audience_level ?? "beginner"));
  const [who, setWho] = useState<string>(g.audience_description ?? "");
  const [purpose, setPurpose] = useState<string>(g.purpose ?? "understand");
  const [goal, setGoal] = useState<string>((g.specific_goals ?? [])[0] ?? "");
  const [minutes, setMinutes] = useState<number>(g.time_budget_minutes && g.time_budget_minutes !== 60 ? g.time_budget_minutes : 20);
  const [lang, setLang] = useState<string>(g.language ?? "en");
  const units: Json[] = p.units ?? [];
  const defaultScope = units.filter((u) => u.role === "core" || u.role === "supporting").map((u) => u.id as string);
  const [scope, setScope] = useState<string[]>((d.course.settings as Json)?.scope_unit_ids ?? (defaultScope.length ? defaultScope : units.map((u) => u.id)));
  const [showAll, setShowAll] = useState(false);
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const mix: Json[] = (p.knowledge_mix ?? []).filter((k: Json) => k.weight >= 0.05);

  const pickGoal = (s: Json) => { setPurpose(PURPOSES.some(([k]) => k === s.purpose) ? s.purpose : "understand"); setLevel(toLevel(s.audience_level)); setGoal(s.title); };
  const save = async () => {
    await api.patchCourse(d.course.id, {
      goal: { purpose, audience_level: level, audience_description: who, time_budget_minutes: minutes, language: lang,
        specific_goals: goal ? [goal] : [], depth: "standard", hands_on: true },
      settings: { ...(d.course.settings as Json), scope_unit_ids: scope },
    });
  };
  const go = async (oneClick: boolean) => {
    setBusy(oneClick ? "Starting…" : "Designing…"); setErr("");
    try {
      await save();
      if (oneClick) { await mapi.build(d.course.id); onOneClick(); } else { await mapi.plan(d.course.id); onPlanned(); }
    } catch (e) { setErr(String(e)); setBusy(""); }
  };
  const shown = showAll ? units : units.slice(0, 12);
  const toggle = (id: string) => setScope((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  return (
    <>
      <h1>Here's what we found</h1>
      <section className="m-found">
        <div className="m-kicker">{GENRE[p.genre] ?? p.genre?.replace("_", " ")} · {p.subject_domain}</div>
        <strong className="m-found-title">{p.title}</strong>
        <p>{p.summary}</p>
        <div className="m-row">
          {d.sources.map((s) => <span key={s.id} className="m-tag">{KIND_ICON[s.kind] ?? "📄"} {s.title}</span>)}
          {(p.modalities ?? []).map((m: string) => <span key={m} className="m-tag soft">{m}</span>)}
        </div>
        {!!p.cautions?.length && <p className="m-sub small">⚠️ {p.cautions.join(" · ")}</p>}
      </section>

      {!!mix.length && (
        <section className="m-found">
          <div className="m-kicker">How we'll teach it</div>
          <p className="m-sub small">The mix of knowledge in your material decides the formats — not a fixed template.</p>
          <div className="m-teach">
            {mix.map((k) => {
              const [ic, how] = TEACH[k.type] ?? ["💡", "Visual explainer cards and quick checks"];
              return (
                <div key={k.type} className="m-teach-row">
                  <span className="m-teach-ic">{ic}</span>
                  <div><strong>{k.type}</strong> <span className="m-meta">{Math.round(k.weight * 100)}%</span><br /><span className="m-sub small">{how}</span></div>
                  <span className="m-teach-bar"><i style={{ width: `${Math.round(k.weight * 100)}%` }} /></span>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {!!p.suggested_goals?.length && (
        <section className="m-step">
          <div className="m-step-body">
            <h2>Pick a goal <span className="m-sub small">— or write your own below</span></h2>
            <div className="m-goal-grid">
              {p.suggested_goals.map((s: Json) => (
                <button key={s.title} className={`m-choice ${goal === s.title ? "on" : ""}`} onClick={() => pickGoal(s)}>
                  <strong>{s.title}</strong><span>{s.description}</span>
                </button>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="m-step">
        <div className="m-step-body">
          <h2>Who is it for?</h2>
          <div className="m-choice-row">
            {AUDIENCES.map(([k, t, s]) => <button key={k} className={`m-choice ${level === k ? "on" : ""}`} onClick={() => setLevel(k)}><strong>{t}</strong><span>{s}</span></button>)}
          </div>
          <input value={who} onChange={(e) => setWho(e.target.value)} placeholder="Anything else about them? e.g. first-year nursing students; new sales hires; Grade 9 science" aria-label="About the learners" />
          <h3>What should they get out of it?</h3>
          <div className="m-choice-row">{PURPOSES.map(([k, t]) => <button key={k} className={`m-choice sm ${purpose === k ? "on" : ""}`} onClick={() => setPurpose(k)}>{t}</button>)}</div>
          <input value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="Optional: a specific goal in your own words" aria-label="Specific goal" />
          <div className="m-row">
            <label className="m-sub">Time</label>
            {[10, 20, 30, 60].map((m) => <button key={m} className={`m-chip ${minutes === m ? "sel" : ""}`} onClick={() => setMinutes(m)}>{m} min</button>)}
            <span style={{ flex: 1 }} />
            <select value={lang} onChange={(e) => setLang(e.target.value)} aria-label="Language">
              {LANGS.map(([k, t]) => <option key={k} value={k}>{t}</option>)}
            </select>
          </div>
        </div>
      </section>

      {units.length > 1 && (
        <section className="m-step">
          <div className="m-step-body">
            <h2>What to include <span className="m-sub small">— {scope.length} of {units.length} sections</span></h2>
            <p className="m-sub small">{defaultScope.length < units.length
              ? "We've left out reference lists, contents pages and boilerplate. Tick anything you want back in."
              : "Untick any section you don't want taught."}</p>
            <div className="m-units">
              {shown.map((u) => (
                <label key={u.id} className={`m-unit ${scope.includes(u.id) ? "" : "off"}`}>
                  <input type="checkbox" checked={scope.includes(u.id)} onChange={() => toggle(u.id)} />
                  <span className="m-unit-t">{(u.path?.length ? u.path.join(" › ") : u.title) || u.id}</span>
                  <span className={`m-role ${u.role}`}>{u.role}</span>
                </label>
              ))}
            </div>
            <div className="m-row">
              {units.length > 12 && <button className="m-btn ghost sm" onClick={() => setShowAll(!showAll)}>{showAll ? "Show fewer" : `Show all ${units.length}`}</button>}
              <button className="m-btn ghost sm" onClick={() => setScope(units.map((u) => u.id))}>Include all</button>
              <button className="m-btn ghost sm" onClick={() => setScope(defaultScope)}>Recommended only</button>
            </div>
          </div>
        </section>
      )}

      <section className="m-step">
        <div className="m-step-body">
          <h2>Next: your outline</h2>
          <p className="m-sub">We'll propose about {Math.max(2, Math.round(minutes / 7))} short modules. You can rename, reorder, remove or add modules before anything is written.</p>
          <div className="m-row">
            <button className="m-btn big" disabled={!!busy || !scope.length} onClick={() => go(false)}>Design the outline →</button>
            <button className="m-btn ghost" disabled={!!busy || !scope.length} onClick={() => go(true)}>⚡ Skip review, create it all</button>
          </div>
          {busy && <div className="m-sub">⏳ {busy}</div>}
          {err && <div className="m-fb no">{err}</div>}
        </div>
      </section>
    </>
  );
}

function Outline({ d, onBack, onGenerate }: { d: Micro; onBack: () => void; onGenerate: () => void }) {
  const bp = d.blueprint as Blueprint;
  const [title, setTitle] = useState(bp.course_title);
  const [tagline, setTagline] = useState(bp.tagline);
  const [promise, setPromise] = useState(bp.learner_promise);
  const [mods, setMods] = useState<OutlineMod[]>(bp.modules.map((m) => ({ title: m.title, goal: m.goal, big_idea: m.big_idea ?? "",
    minutes: m.minutes, concept_ids: (m as unknown as { concept_ids?: string[] }).concept_ids ?? [] })));
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const set = (i: number, patch: Partial<OutlineMod>) => setMods(mods.map((m, k) => (k === i ? { ...m, ...patch } : m)));
  const move = (i: number, by: number) => { const x = [...mods]; const [m] = x.splice(i, 1); x.splice(i + by, 0, m); setMods(x); };
  const total = mods.reduce((n, m) => n + (m.minutes || 0), 0);
  const generate = async () => {
    setBusy("Starting…"); setErr("");
    try {
      await mapi.putOutline(d.course.id, { course_title: title, tagline, learner_promise: promise, modules: mods });
      await mapi.generate(d.course.id);
      onGenerate();
    } catch (e) { setErr(String(e)); setBusy(""); }
  };
  return (
    <>
      <h1>Your course outline</h1>
      <p className="m-sub">This is the learning journey we'd build. Change anything you like — nothing is written until you press Generate.</p>
      <section className="m-found m-outline-head">
        <label>Course title</label>
        <input value={title} onChange={(e) => setTitle(e.target.value)} />
        <label>Why it's worth learning</label>
        <input value={tagline} onChange={(e) => setTagline(e.target.value)} />
        <label>By the end, learners will be able to…</label>
        <input value={promise} onChange={(e) => setPromise(e.target.value)} />
      </section>
      <div className="m-outline">
        {mods.map((m, i) => (
          <div key={i} className="m-outline-mod">
            <span className="m-num">{i + 1}</span>
            <div className="m-outline-body">
              <input className="m-outline-title" value={m.title} onChange={(e) => set(i, { title: e.target.value })} aria-label={`Module ${i + 1} title`} />
              <input value={m.goal} onChange={(e) => set(i, { goal: e.target.value })} placeholder="You'll be able to…" aria-label={`Module ${i + 1} goal`} />
              {!!m.concept_ids.length && <div className="m-row">{m.concept_ids.slice(0, 6).map((c) => d.concepts[c] && <span key={c} className="m-tag soft">{d.concepts[c]}</span>)}</div>}
              {!m.concept_ids.length && <span className="m-sub small">New module — we'll find the matching parts of your material.</span>}
            </div>
            <div className="m-outline-ctl">
              <span className="m-meta">{m.minutes} min</span>
              <button className="m-icon" disabled={i === 0} onClick={() => move(i, -1)} aria-label="Move up">↑</button>
              <button className="m-icon" disabled={i === mods.length - 1} onClick={() => move(i, 1)} aria-label="Move down">↓</button>
              <button className="m-icon" disabled={mods.length < 2} onClick={() => setMods(mods.filter((_, k) => k !== i))} aria-label="Remove module">✕</button>
            </div>
          </div>
        ))}
        <button className="m-btn ghost" onClick={() => setMods([...mods, { title: "", goal: "", big_idea: "", minutes: 6, concept_ids: [] }])}>+ Add a module</button>
      </div>
      {!!bp.skipped?.length && <p className="m-sub small"><strong>Left out on purpose:</strong> {bp.skipped.join(" · ")}</p>}
      <section className="m-step">
        <div className="m-step-body">
          <h2>Generate the course</h2>
          <p className="m-sub">{mods.length} modules · about {total} minutes. Each module gets visual cards, 3+ games, a recap, narration and a memory deck. Takes 2–5 minutes.</p>
          <div className="m-row">
            <button className="m-btn big" disabled={!!busy || mods.some((m) => !m.title.trim())} onClick={generate}>✨ Generate course</button>
            <button className="m-btn ghost" disabled={!!busy} onClick={onBack}>← Change audience or goals</button>
          </div>
          {busy && <div className="m-sub">⏳ {busy}</div>}
          {err && <div className="m-fb no">{err}</div>}
        </div>
      </section>
    </>
  );
}

export const KIND_ICON: Record<string, string> = { pdf: "📕", docx: "📝", pptx: "📊", spreadsheet: "📈", epub: "📚", youtube: "▶️", audio: "🎧",
  image: "🖼", url: "🌐", site: "🗂", html: "🌐", text: "📄", markdown: "📄" };
