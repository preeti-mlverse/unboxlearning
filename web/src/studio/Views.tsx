import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, KT_LABEL, LANGUAGES, PURPOSES, type Concept, type Course, type Element, type Json } from "../api";
import { Assets } from "./Assets";
import { CiteList, ElementView, ErrorNote, KT_COLOR, Spinner } from "../ui";

export function Overview({ course }: { course: Course }) {
  const c = course.curriculum!;
  const g = course.data.goal;
  const total = c.objectives.reduce((a, o) => a + o.estimated_minutes, 0);
  return (
    <div className="stack">
      <div className="card stack">
        <div className="row" style={{ gap: 6 }}>
          <span className="badge primary">{PURPOSES[g.purpose]?.label}</span>
          <span className="badge">{g.audience_level}</span><span className="badge">~{total} min</span>
          <span className="badge">{c.objectives.length} objectives</span>
        </div>
        <h2 style={{ margin: 0 }}>{c.course_title}</h2>
        <p style={{ fontSize: 17, margin: 0 }}>{c.learner_promise}</p>
        {!!c.uncovered_goals.length && <div className="notice warn"><strong>Not covered by these sources: </strong>{c.uncovered_goals.join(" · ")}</div>}
        <div className="row"><Link className="btn primary" to={`/classic/learn/${course.id}`}>Open classic learner view</Link></div>
      </div>
      <Languages course={course} />
      {c.modules.map((m, i) => (
        <div key={m.id} className="card">
          <div className="stage-pill">Module {i + 1}</div>
          <h3>{m.title}</h3>
          <div className="small muted" style={{ marginBottom: 8 }}>{m.why}</div>
          {m.objective_ids.map((oid) => {
            const o = c.objectives.find((x) => x.id === oid)!;
            return (
              <div key={oid} className="list-item">
                <span className="kt" style={{ background: KT_COLOR[o.knowledge_type], marginTop: 6 }} />
                <div style={{ flex: 1 }}>
                  {o.statement}
                  <div className="tiny faint">{KT_LABEL[o.knowledge_type]} · {o.bloom} · ~{o.estimated_minutes} min
                    {o.serves_goals.length ? ` · serves goal ${o.serves_goals.map((x) => x + 1).join(", ")}` : ""}</div>
                </div>
              </div>
            );
          })}
        </div>
      ))}
      {!!c.excluded.length && (
        <details className="card"><summary><strong>Deliberately left out</strong></summary>
          <ul className="small">{c.excluded.map((e, i) => <li key={i}>{e}</li>)}</ul></details>
      )}
    </div>
  );
}

export function Knowledge({ course }: { course: Course }) {
  const g = course.graph!;
  const [sel, setSel] = useState<Concept | null>(null);
  const [filter, setFilter] = useState("");
  const layout = useMemo(() => {
    const top = [...g.concepts].sort((a, b) => b.importance - a.importance || b.mentions - a.mentions).slice(0, 60);
    const ids = new Set(top.map((c) => c.id));
    const cols: Record<number, Concept[]> = {};
    top.forEach((c) => (cols[Math.min(c.depth, 5)] ??= []).push(c));
    const depths = Object.keys(cols).map(Number).sort((a, b) => a - b);
    const colW = 210, rowH = 34;
    const pos: Record<string, { x: number; y: number }> = {};
    let H = 0;
    depths.forEach((d, i) => cols[d].forEach((c, j) => { pos[c.id] = { x: 20 + i * colW, y: 24 + j * rowH }; H = Math.max(H, 24 + j * rowH); }));
    return { top, pos, W: 40 + depths.length * colW, H: H + 40, edges: g.edges.filter((e) => ids.has(e.source) && ids.has(e.target)) };
  }, [g]);
  const list = g.concepts.filter((c) => !filter || (c.name + c.definition).toLowerCase().includes(filter.toLowerCase()));
  return (
    <div className="stack">
      <div className="card" style={{ overflowX: "auto" }}>
        <div className="spread" style={{ marginBottom: 8 }}>
          <strong>Concept graph</strong>
          <span className="small muted">{g.concepts.length} concepts · {g.edges.length} relations · columns = prerequisite depth (top 60 shown)</span>
        </div>
        <svg width={layout.W} height={layout.H} role="img" aria-label="Concept graph">
          {layout.edges.map((e, i) => {
            const s = layout.pos[e.source], t = layout.pos[e.target];
            const on = !sel || sel.id === e.source || sel.id === e.target;
            return <path key={i} d={`M${s.x + 180},${s.y} C${s.x + 200},${s.y} ${t.x - 20},${t.y} ${t.x},${t.y}`} fill="none"
              stroke={e.type === "prerequisite" ? "#4b3fe0" : "#c9cedb"} strokeWidth={on ? 1.4 : 0.6} opacity={on ? 0.8 : 0.25} />;
          })}
          {layout.top.map((c) => (
            <g key={c.id} transform={`translate(${layout.pos[c.id].x},${layout.pos[c.id].y - 12})`} onClick={() => setSel(c)} style={{ cursor: "pointer" }}>
              <rect width={180} height={24} rx={7} fill={sel?.id === c.id ? KT_COLOR[c.knowledge_type] : "#fff"} stroke={KT_COLOR[c.knowledge_type]} strokeWidth={c.importance === 3 ? 2 : 1} />
              <text x={9} y={16} fontSize={12} fill={sel?.id === c.id ? "#fff" : "#151821"}>{c.name.length > 26 ? c.name.slice(0, 25) + "…" : c.name}</text>
            </g>
          ))}
        </svg>
      </div>
      {sel && <ConceptCard c={sel} course={course} />}
      <div className="card">
        <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Search concepts…" aria-label="Search concepts" style={{ marginBottom: 8 }} />
        {list.slice(0, 200).map((c) => (
          <div key={c.id} className="list-item" onClick={() => setSel(c)} style={{ cursor: "pointer" }}>
            <span className="kt" style={{ background: KT_COLOR[c.knowledge_type], marginTop: 6 }} />
            <div style={{ flex: 1 }}><strong>{c.name}</strong> <span className="tiny faint">{c.knowledge_type} · importance {c.importance} · depth {c.depth}</span>
              <div className="small">{c.definition}</div></div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ConceptCard({ c, course }: { c: Concept; course: Course }) {
  const g = course.graph!;
  const name = (id: string) => g.concepts.find((x) => x.id === id)?.name ?? id;
  const pre = g.edges.filter((e) => e.target === c.id && e.type === "prerequisite").map((e) => name(e.source));
  const leads = g.edges.filter((e) => e.source === c.id && e.type === "prerequisite").map((e) => name(e.target));
  const other = g.edges.filter((e) => e.type !== "prerequisite" && (e.source === c.id || e.target === c.id));
  return (
    <div className="card stack">
      <div className="spread"><h3 style={{ margin: 0 }}>{c.name}</h3><span className="badge" style={{ background: KT_COLOR[c.knowledge_type], color: "#fff" }}>{KT_LABEL[c.knowledge_type]}</span></div>
      <div>{c.definition}</div>
      {!!c.aliases.length && <div className="small muted">Also: {c.aliases.slice(0, 6).join(", ")}</div>}
      <div className="kv">
        <div>Needs first</div><div>{pre.join(", ") || "—"}</div>
        <div>Leads to</div><div>{leads.join(", ") || "—"}</div>
        <div>Related</div><div>{other.map((e) => `${e.type.replace("_", " ")} ${name(e.source === c.id ? e.target : e.source)}`).join("; ") || "—"}</div>
        <div>Evidence</div><div><CiteList ids={c.evidence} /></div>
      </div>
    </div>
  );
}

export function SourcesView({ course }: { course: Course }) {
  const [sid, setSid] = useState(course.sources[0]?.id ?? "");
  const [data, setData] = useState<{ elements: Element[]; total: number } | null>(null);
  const [offset, setOffset] = useState(0);
  useEffect(() => { if (sid) { setData(null); api.source(sid, offset).then(setData); } }, [sid, offset]);
  const s = course.sources.find((x) => x.id === sid);
  return (
    <div className="stack">
      <div className="row">{course.sources.map((x) => <button key={x.id} className={`chip ${x.id === sid ? "on" : ""}`} onClick={() => { setSid(x.id); setOffset(0); }}>{x.title}</button>)}</div>
      {s && (
        <div className="card stack">
          <div className="spread"><strong>{s.title}</strong><span className="small muted">{s.kind} · {data?.total ?? "…"} elements</span></div>
          {s.parse_notes.map((n, i) => <div key={i} className="tiny faint">{n}</div>)}
          {!data ? <Spinner /> : data.elements.map((e) => <ElementView key={e.id} e={e} />)}
          {data && data.total > 600 && (
            <div className="row">
              <button className="btn sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 600))}>← Previous</button>
              <span className="small muted">{offset + 1}–{Math.min(offset + 600, data.total)} of {data.total}</span>
              <button className="btn sm" disabled={offset + 600 >= data.total} onClick={() => setOffset(offset + 600)}>Next →</button>
            </div>
          )}
        </div>
      )}
      <Assets course={course} />
    </div>
  );
}

export function Learners({ course }: { course: Course }) {
  const [d, setD] = useState<Json | null>(null);
  const [items, setItems] = useState<Json[]>([]);
  const [err, setErr] = useState("");
  useEffect(() => {
    api.dashboard(course.id).then(setD).catch((e) => setErr(String(e)));
    api.items(course.id).then(setItems).catch(() => {});
  }, [course.id]);
  if (err) return <ErrorNote error={err} />;
  if (!d) return <Spinner />;
  const n = d.learners.length;
  return (
    <div className="stack">
      <div className="card"><strong>{n} learner{n === 1 ? "" : "s"}</strong> <span className="small muted">· mastery threshold {Math.round(d.threshold * 100)}%</span>
        {!n && <div className="small muted">No attempts yet. Share the learner view: <Link to={`/learn/${course.id}`}>/learn/{course.id}</Link></div>}</div>
      {!!n && (
        <div className="card" style={{ overflowX: "auto" }}>
          <table>
            <thead><tr><th>Objective</th><th>Mastered</th><th>Avg mastery</th><th>Attempts</th><th>Struggling</th><th>Common misconceptions</th></tr></thead>
            <tbody>{d.objectives.map((o: Json) => (
              <tr key={o.objective_id}>
                <td>{o.statement}</td>
                <td>{o.mastered}/{n}</td>
                <td>{o.avg_p == null ? "—" : `${Math.round(o.avg_p * 100)}%`}</td>
                <td>{o.attempts}</td>
                <td>{o.struggling.length || "—"}</td>
                <td className="small">{o.misconceptions.map(([m, k]: [string, number]) => `${m} (${k})`).join("; ") || "—"}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      {!!items.length && (
        <div className="card" style={{ overflowX: "auto" }}>
          <strong>Item analysis</strong>
          <div className="small muted" style={{ marginBottom: 8 }}>First attempts only. p = share correct; discrimination = how well the item separates stronger from weaker learners (≥0.2 is healthy). Flags appear once an item has 8+ responses.</div>
          <table>
            <thead><tr><th>Item</th><th>n</th><th>p</th><th>Discrimination</th><th>Flags</th></tr></thead>
            <tbody>{items.map((r) => (
              <tr key={r.activity_id}>
                <td><strong>{r.title}</strong><div className="tiny faint">{r.type}</div>
                  {r.distractors && <div className="tiny">{r.distractors.map((o: Json, i: number) => <span key={i} style={{ marginRight: 8, color: o.correct ? "var(--good)" : undefined }}>{o.correct ? "✓" : "✗"} {o.picked}</span>)}</div>}</td>
                <td>{r.n}</td><td>{r.p_value}</td><td>{r.discrimination ?? "—"}</td>
                <td className="small">{r.flags.length ? r.flags.map((f: string, i: number) => <div key={i} style={{ color: "var(--bad)" }}>{f}</div>) : <span className="faint">—</span>}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function Usage({ course }: { course: Course }) {
  const [rows, setRows] = useState<Json[] | null>(null);
  useEffect(() => { api.usage(course.id).then(setRows); }, [course.id]);
  if (!rows) return <Spinner />;
  const tin = rows.reduce((a, r) => a + (r.tin ?? 0), 0), tout = rows.reduce((a, r) => a + (r.tout ?? 0), 0);
  return (
    <div className="card" style={{ overflowX: "auto" }}>
      <div className="small muted" style={{ marginBottom: 8 }}>{tin.toLocaleString()} input · {tout.toLocaleString()} output tokens across {rows.reduce((a, r) => a + r.n, 0)} calls</div>
      <table>
        <thead><tr><th>Purpose</th><th>Model</th><th>Calls</th><th>Input tokens</th><th>Output tokens</th><th>Avg ms</th><th>Failed</th></tr></thead>
        <tbody>{rows.map((r, i) => (
          <tr key={i}><td>{r.purpose}</td><td className="mono small">{r.model}</td><td>{r.n}</td><td>{(r.tin ?? 0).toLocaleString()}</td>
            <td>{(r.tout ?? 0).toLocaleString()}</td><td>{Math.round(r.ms ?? 0)}</td><td>{r.failed}</td></tr>
        ))}</tbody>
      </table>
    </div>
  );
}


function Languages({ course }: { course: Course }) {
  const [langs, setLangs] = useState<string[]>([]);
  const [pick, setPick] = useState("hi");
  const [msg, setMsg] = useState("");
  const running = course.job?.status === "running" && course.job.kind === "translate";
  useEffect(() => { api.learnCurriculum(course.id).then((r) => setLangs(r.languages)).catch(() => {}); }, [course.id, course.job?.status]);
  const name = (l: string) => LANGUAGES.find(([k]) => k === l)?.[1] ?? l;
  return (
    <div className="card stack">
      <div className="spread"><strong>Languages</strong><span className="small muted">Original: {name(course.data.goal.language)}</span></div>
      <div className="small muted">Translations keep the same activities and answers, so a learner can switch language without losing progress. Terminology follows a per-language course glossary.</div>
      <div className="row">{langs.length ? langs.map((l) => <span key={l} className="badge good">{name(l)}</span>) : <span className="small faint">No translations yet.</span>}</div>
      <div className="row" style={{ flexWrap: "nowrap" }}>
        <select value={pick} onChange={(e) => setPick(e.target.value)} style={{ width: "auto" }} aria-label="Language to add">
          {LANGUAGES.filter(([k]) => k !== course.data.goal.language).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <button className="btn" disabled={running} onClick={async () => { try { await api.translate(course.id, pick); setMsg("Translation started — progress shows under Setup."); } catch (e) { setMsg(String(e)); } }}>
          {running ? "Translating…" : langs.includes(pick) ? "Re-translate" : "Translate approved content"}</button>
      </div>
      {running && <div className="small muted">{course.job?.message}</div>}
      {msg && <div className="small">{msg}</div>}
    </div>
  );
}
