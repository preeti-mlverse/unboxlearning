import { useEffect, useState } from "react";
import { api, type Course, type Json } from "../api";
import { ErrorNote } from "../ui";

async function call<T>(method: string, url: string, body?: unknown): Promise<T> {
  const init: RequestInit = { method };
  if (body instanceof FormData) init.body = body;
  else if (body) { init.body = JSON.stringify(body); init.headers = { "Content-Type": "application/json" }; }
  const r = await fetch(url, init);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail ?? r.statusText);
  return r.json();
}

type Item = { question: string; options: { text: string; correct: boolean }[] };

export function Evidence({ course, reload }: { course: Course; reload: () => void }) {
  const [assessments, setAssessments] = useState<Json[]>([]);
  const [report, setReport] = useState<Json | null>(null);
  const [err, setErr] = useState("");
  const [kind, setKind] = useState("pre");
  const [draft, setDraft] = useState<Item[]>([]);
  const exp = (course.data.settings as Json).experiment ?? { enabled: false };
  const load = () => {
    call<Json[]>("GET", `/api/courses/${course.id}/assessments`).then(setAssessments).catch((e) => setErr(String(e)));
    call<Json>("GET", `/api/courses/${course.id}/evidence`).then(setReport).catch(() => {});
  };
  useEffect(load, [course.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const importFile = async (f: File) => {
    const fd = new FormData(); fd.append("file", f); fd.append("kind", kind); fd.append("name", f.name);
    try { await call("POST", `/api/courses/${course.id}/assessments/import`, fd); load(); } catch (e) { setErr(String(e)); }
  };
  const saveDraft = async () => {
    try { await call("POST", `/api/courses/${course.id}/assessments`, { kind, items: draft, name: `${kind}-test`, source: "teacher" }); setDraft([]); load(); }
    catch (e) { setErr(String(e)); }
  };

  return (
    <div className="stack">
      <div className="notice">
        <strong>Evidence of learning.</strong> Measure learning with <em>independent</em> tests — imported from your item bank or written
        here — never with the course's own generated quizzes. Learners take the pre-test before starting, the post-test when they finish,
        and the delayed test after a gap to measure retention.
      </div>
      <ErrorNote error={err} />
      <div className="card stack">
        <strong>Tests</strong>
        {["pre", "post", "delayed"].map((k) => {
          const a = assessments.find((x) => x.kind === k);
          return (
            <div key={k} className="list-item">
              <span className="badge primary" style={{ width: 70, justifyContent: "center" }}>{k}</span>
              <div style={{ flex: 1 }}>{a ? <><strong>{a.name}</strong> · {a.items.length} items · {a.source}{k === "delayed" && ` · ${a.delay_days} days after post`}</> : <span className="faint">not set</span>}</div>
              {a && <button className="btn ghost sm danger" onClick={async () => { await call("DELETE", `/api/courses/${course.id}/assessments/${a.id}`); load(); }}>Remove</button>}
            </div>
          );
        })}
        <div className="row">
          <select value={kind} onChange={(e) => setKind(e.target.value)} style={{ width: "auto" }} aria-label="Test type">
            <option value="pre">Pre-test</option><option value="post">Post-test</option><option value="delayed">Delayed test</option>
          </select>
          <label className="btn" style={{ margin: 0, color: "var(--ink)", fontSize: 14 }}>Import QTI zip / JSON
            <input type="file" accept=".zip,.json" hidden onChange={(e) => e.target.files?.[0] && importFile(e.target.files[0])} /></label>
          <button className="btn" onClick={() => setDraft([...draft, { question: "", options: [{ text: "", correct: true }, { text: "", correct: false }] }])}>+ Write a question</button>
        </div>
        {draft.map((it, i) => (
          <div key={i} className="card flat stack">
            <input value={it.question} placeholder={`Question ${i + 1}`} aria-label={`Question ${i + 1}`}
              onChange={(e) => setDraft(draft.map((d, k) => (k === i ? { ...d, question: e.target.value } : d)))} />
            {it.options.map((o, j) => (
              <div key={j} className="row" style={{ flexWrap: "nowrap" }}>
                <input type="radio" name={`c${i}`} checked={o.correct} style={{ width: "auto" }} aria-label="Correct answer"
                  onChange={() => setDraft(draft.map((d, k) => (k === i ? { ...d, options: d.options.map((x, m) => ({ ...x, correct: m === j })) } : d)))} />
                <input value={o.text} placeholder={`Option ${j + 1}`} aria-label={`Option ${j + 1}`}
                  onChange={(e) => setDraft(draft.map((d, k) => (k === i ? { ...d, options: d.options.map((x, m) => (m === j ? { ...x, text: e.target.value } : x)) } : d)))} />
              </div>
            ))}
            <div><button className="btn ghost sm" onClick={() => setDraft(draft.map((d, k) => (k === i ? { ...d, options: [...d.options, { text: "", correct: false }] } : d)))}>+ option</button></div>
          </div>
        ))}
        {!!draft.length && <div><button className="btn primary" onClick={saveDraft}>Save as {kind}-test ({draft.length} questions)</button></div>}
      </div>

      <div className="card stack">
        <div className="spread">
          <strong>Controlled comparison</strong>
          <label className="row" style={{ fontWeight: 400, gap: 6, margin: 0 }}>
            <input type="checkbox" checked={!!exp.enabled} style={{ width: "auto" }}
              onChange={async (e) => { await api.patchCourse(course.id, { settings: { experiment: { enabled: e.target.checked } } }); reload(); }} />
            Randomly assign learners to adaptive vs static
          </label>
        </div>
        <div className="small muted">Static = the same approved activities in fixed order, no remediation, no spaced review, no tutor. The difference between arms is what the adaptive engine adds beyond the content.</div>
        {report && (
          <>
            <table>
              <thead><tr><th>Arm</th><th>Learners</th><th>Pre</th><th>Post</th><th>Gain (95% CI)</th><th>Normalised gain</th><th>Retention</th></tr></thead>
              <tbody>{Object.entries(report.arms as Record<string, Json>).map(([arm, v]) => (
                <tr key={arm}><td>{arm}</td><td>{v.learners} ({v.with_pre_and_post} paired)</td><td>{v.pre_mean ?? "—"}</td><td>{v.post_mean ?? "—"}</td>
                  <td>{v.gain_mean ?? "—"}{v.gain_ci95 ? ` [${v.gain_ci95.join(", ")}]` : ""}</td><td>{v.normalized_gain ?? "—"}</td><td>{v.retention ?? "—"}</td></tr>
              ))}</tbody>
            </table>
            <div className="small">Effect size (Cohen's d, adaptive vs static gain): <strong>{report.effect_size_d ?? "—"}</strong></div>
            {report.caveats.map((c: string, i: number) => <div key={i} className="tiny faint">{c}</div>)}
            <div><a className="btn sm" href={`/api/courses/${course.id}/evidence.csv`}>Download results (CSV)</a></div>
          </>
        )}
      </div>
    </div>
  );
}
