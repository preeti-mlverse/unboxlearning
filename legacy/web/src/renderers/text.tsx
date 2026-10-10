import { useState } from "react";
import { Md } from "../ui";
import { Feedback, SubmitBar, type RProps } from "./common";

export function Cloze({ a, reveal, result, locked, submit, busy }: RProps) {
  const p = a.data.payload;
  const [vals, setVals] = useState<Record<string, string>>({});
  const blanks = p.blanks as { id: number; hint: string; answers?: string[] }[];
  const truth = reveal ? Object.fromEntries(reveal.blanks.map((b: { id: number; answers: string[] }) => [String(b.id), b.answers])) : null;
  const detail = (result?.detail ?? {}) as Record<string, boolean>;
  const parts = String(p.passage).split(/(\[\[\d+\]\])/g);
  const isCode = /```/.test(p.passage) || /\n {2,}/.test(p.passage);
  const body = parts.map((part, i) => {
    const m = part.match(/^\[\[(\d+)\]\]$/);
    if (!m) return <span key={i} style={{ whiteSpace: isCode ? "pre-wrap" : undefined }}>{part.replace(/```\w*\n?/g, "")}</span>;
    const id = m[1];
    const b = blanks.find((x) => String(x.id) === id);
    const ok = detail[id];
    return (
      <span key={i} style={{ display: "inline-flex", flexDirection: "column", verticalAlign: "top", margin: "0 3px" }}>
        <input value={vals[id] ?? ""} onChange={(e) => { const v = e.target.value; setVals((prev) => ({ ...prev, [id]: v })); }} disabled={locked}
          placeholder={b?.hint ? `(${b.hint})` : `blank ${id}`} aria-label={`Blank ${id}`}
          style={{ width: Math.max(110, (truth?.[id]?.[0]?.length ?? 10) * 9), padding: "3px 8px", borderColor: result ? (ok ? "var(--good)" : "var(--bad)") : undefined }} />
        {truth && !ok && <span className="tiny" style={{ color: "var(--good)" }}>{truth[id]?.[0]}</span>}
      </span>
    );
  });
  // blanks the passage forgot to mark still get an input, so the learner is never stuck
  const orphan = blanks.filter((b) => !parts.includes(`[[${b.id}]]`));
  return (
    <div className="stack">
      <div className={isCode ? "mono small" : ""} style={{ lineHeight: 2.2, fontSize: isCode ? 13 : 16 }}>{body}</div>
      {orphan.map((b) => (
        <div key={b.id} className="row">
          <span className="small muted">Blank {b.id}{b.hint ? ` (${b.hint})` : ""}:</span>
          <input value={vals[String(b.id)] ?? ""} disabled={locked} style={{ width: 200 }} aria-label={`Blank ${b.id}`}
            onChange={(e) => { const v = e.target.value; setVals((prev) => ({ ...prev, [String(b.id)]: v })); }} />
          {truth && !detail[String(b.id)] && <span className="tiny" style={{ color: "var(--good)" }}>{truth[String(b.id)]?.[0]}</span>}
        </div>
      ))}
      {!locked && <SubmitBar onClick={() => submit({ blanks: vals })} disabled={Object.keys(vals).length < new Set(blanks.map((b) => String(b.id))).size} busy={busy} />}
      <Feedback result={result} />
    </div>
  );
}

function Hints({ hints, used, setUsed, locked }: { hints: string[]; used: number; setUsed: (n: number) => void; locked: boolean }) {
  if (!hints?.length) return null;
  return (
    <div className="stack">
      {hints.slice(0, used).map((h, i) => <div key={i} className="notice"><strong>Hint {i + 1}: </strong><Md text={h} inline /></div>)}
      {!locked && used < hints.length && (
        <button className="btn ghost sm" onClick={() => setUsed(used + 1)}>💡 {used ? "Another hint" : "Need a hint?"}</button>
      )}
    </div>
  );
}

function Rubric({ rubric }: { rubric: { criterion: string; points: number }[] }) {
  return (
    <ul className="small" style={{ margin: "4px 0", paddingLeft: 20 }}>
      {rubric.map((r, i) => <li key={i}>{r.criterion} <span className="faint">({r.points} pt)</span></li>)}
    </ul>
  );
}

export function ShortAnswer({ a, reveal, result, locked, review, submit, busy }: RProps) {
  const p = a.data.payload;
  const [text, setText] = useState("");
  const [used, setUsed] = useState(0);
  return (
    <div className="stack">
      <div style={{ fontSize: 17 }}><Md text={p.question} /></div>
      <textarea value={text} onChange={(e) => setText(e.target.value)} disabled={locked} placeholder="Answer in your own words…" rows={5} aria-label="Your answer" />
      <Hints hints={p.hints} used={used} setUsed={setUsed} locked={locked} />
      {!locked && <SubmitBar label="Submit answer" onClick={() => submit({ text }, used)} disabled={text.trim().length < 3} busy={busy} />}
      <Feedback result={result} />
      {reveal && (
        <div className="card flat">
          <strong>{review ? "Model answer" : "A strong answer"}</strong><Md text={reveal.model_answer} />
          {review && reveal.rubric && <><strong className="small">Rubric</strong><Rubric rubric={reveal.rubric} /></>}
        </div>
      )}
    </div>
  );
}

export function TeachBack({ a, reveal, result, locked, submit, busy }: RProps) {
  const p = a.data.payload;
  const [text, setText] = useState("");
  return (
    <div className="stack">
      <div style={{ fontSize: 17 }}><Md text={p.prompt} /></div>
      <div className="small muted">Explain it for: <strong>{p.audience}</strong></div>
      <textarea value={text} onChange={(e) => setText(e.target.value)} disabled={locked} rows={7} placeholder="Write your explanation…" aria-label="Your explanation" />
      {!locked && <SubmitBar label="Submit explanation" onClick={() => submit({ text })} disabled={text.trim().length < 20} busy={busy} />}
      <Feedback result={result} />
      {reveal && <div className="card flat"><strong>A good explanation includes</strong><ul className="small" style={{ margin: 0, paddingLeft: 20 }}>{reveal.must_include?.map((m: string, i: number) => <li key={i}>{m}</li>)}</ul></div>}
    </div>
  );
}

export function CaseStudy({ a, reveal, result, locked, submit, busy }: RProps) {
  const p = a.data.payload;
  const [q, setQ] = useState(0);
  const [text, setText] = useState("");
  const qs = p.questions as { question: string }[];
  return (
    <div className="stack">
      <div className="card flat"><Md text={p.case} /></div>
      <div className="row">{qs.map((_, i) => <button key={i} className={`chip ${i === q ? "on" : ""}`} onClick={() => setQ(i)} disabled={locked && !reveal}>Question {i + 1}</button>)}</div>
      <strong><Md text={qs[q].question} inline /></strong>
      <textarea value={text} onChange={(e) => setText(e.target.value)} disabled={locked} rows={6} placeholder="Your analysis…" aria-label="Your analysis" />
      {!locked && <SubmitBar label="Submit analysis" onClick={() => submit({ text, question: q })} disabled={text.trim().length < 10} busy={busy} />}
      <Feedback result={result} />
      {reveal && <div className="card flat"><strong>Model answer</strong><Md text={reveal.questions[q].model_answer} /></div>}
    </div>
  );
}

export function NumericProblem({ a, reveal, result, locked, submit, busy }: RProps) {
  const p = a.data.payload;
  const [v, setV] = useState("");
  const [used, setUsed] = useState(0);
  return (
    <div className="stack">
      <div style={{ fontSize: 17 }}><Md text={p.question} /></div>
      <div className="row">
        <input value={v} onChange={(e) => setV(e.target.value)} disabled={locked} inputMode="decimal" style={{ width: 180 }} aria-label="Your answer" />
        <span className="muted">{p.unit}</span>
      </div>
      <Hints hints={p.hints} used={used} setUsed={setUsed} locked={locked} />
      {!locked && <SubmitBar onClick={() => submit({ value: v }, used)} disabled={!v.trim()} busy={busy} />}
      <Feedback result={result} />
      {reveal && (
        <div className="card flat">
          <strong>Answer: {reveal.answer} {reveal.unit}</strong>
          <ol className="small" style={{ margin: "6px 0 0", paddingLeft: 20 }}>{reveal.solution?.map((s: string, i: number) => <li key={i}><Md text={s} inline /></li>)}</ol>
        </div>
      )}
    </div>
  );
}
