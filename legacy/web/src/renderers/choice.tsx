import { useState } from "react";
import type { Json } from "../api";
import { Md } from "../ui";
import { Choices, Feedback, SubmitBar, type RProps } from "./common";

export function MCQ({ a, reveal, result, locked, submit, busy }: RProps) {
  const p = a.data.payload;
  const [sel, setSel] = useState<number[]>([]);
  return (
    <div>
      <div style={{ fontSize: 17, marginBottom: 12 }}><Md text={p.question} /></div>
      {p.multiple && <div className="small muted" style={{ marginBottom: 8 }}>Select all that apply.</div>}
      <Choices options={p.options} selected={sel} setSelected={setSel} multiple={!!p.multiple} reveal={reveal?.options ?? null} locked={locked} />
      {!locked && <SubmitBar onClick={() => submit({ selected: sel })} disabled={!sel.length} busy={busy} />}
      <Feedback result={result} />
      {reveal?.explanation && <div className="notice" style={{ marginTop: 10 }}><Md text={reveal.explanation} /></div>}
    </div>
  );
}

export function Predict({ a, reveal, result, locked, submit, busy }: RProps) {
  const p = a.data.payload;
  const [sel, setSel] = useState<number[]>([]);
  return (
    <div>
      <div className="card flat" style={{ marginBottom: 12 }}><Md text={p.setup} /></div>
      <div style={{ fontSize: 17, marginBottom: 10 }}><strong>Your prediction: </strong><Md text={p.question} inline /></div>
      <Choices options={p.options} selected={sel} setSelected={setSel} multiple={false} reveal={reveal?.options ?? null} locked={locked} />
      {!locked && <SubmitBar label="Lock in prediction" onClick={() => submit({ selected: sel })} disabled={!sel.length} busy={busy} />}
      <Feedback result={result} />
      {reveal?.reveal && <div className="notice good" style={{ marginTop: 10 }}><strong>What actually happens</strong><Md text={reveal.reveal} /></div>}
    </div>
  );
}

export function CompareTable({ a, reveal, result, locked, submit, busy }: RProps) {
  const p = a.data.payload;
  const [sel, setSel] = useState<number[]>([]);
  return (
    <div className="stack">
      <Md text={p.prompt} />
      <div style={{ overflowX: "auto" }}>
        <table>
          <thead><tr><th></th>{p.subjects.map((s: string) => <th key={s}>{s}</th>)}</tr></thead>
          <tbody>{p.rows.map((r: { dimension: string; cells: string[] }, i: number) => (
            <tr key={i}><th>{r.dimension}</th>{r.cells.map((c, j) => <td key={j}><Md text={c} inline /></td>)}</tr>
          ))}</tbody>
        </table>
      </div>
      {p.takeaway && <div className="notice"><strong>Takeaway: </strong><Md text={p.takeaway} inline /></div>}
      {p.question && (
        <>
          <strong><Md text={p.question} inline /></strong>
          <Choices options={p.options} selected={sel} setSelected={setSel} multiple={false} reveal={reveal?.options ?? null} locked={locked} />
          {!locked && <SubmitBar onClick={() => submit({ selected: sel })} disabled={!sel.length} busy={busy} />}
        </>
      )}
      <Feedback result={result} />
    </div>
  );
}

export function ProcessStepper({ a, reveal, result, locked, review, submit, busy }: RProps) {
  const p = a.data.payload;
  const stages = p.stages as { name: string; description: string; what_changes: string }[];
  const preds = (p.predictions ?? []) as { after_stage: number; question: string; options: Json[] }[];
  const [at, setAt] = useState(review ? stages.length - 1 : 0);
  const [answers, setAnswers] = useState<Record<string, number[]>>({});
  const gate = preds.findIndex((q) => q.after_stage === at && !answers[String(preds.indexOf(q))]);
  const pending = !review && !locked && gate >= 0;
  return (
    <div className="stack">
      <Md text={p.intro} />
      <div className="row" style={{ gap: 6 }}>
        {stages.map((s, i) => (
          <span key={i} className={`badge ${i <= at ? "primary" : ""}`}>{i + 1}. {s.name}</span>
        ))}
      </div>
      {stages.slice(0, at + 1).map((s, i) => (
        <div key={i} className="card flat">
          <div className="stage-pill">Stage {i + 1}</div>
          <h3>{s.name}</h3>
          <Md text={s.description} />
          <div className="small"><strong>What changes: </strong><Md text={s.what_changes} inline /></div>
          {preds.map((q, qi) => q.after_stage === i && (
            <div key={qi} className="card flat" style={{ marginTop: 10, background: "var(--surface-2)" }}>
              <strong>What happens next? </strong><Md text={q.question} inline />
              <div style={{ marginTop: 8 }}>
                <Choices options={q.options} selected={answers[String(qi)] ?? []} multiple={false} locked={locked || !!answers[String(qi)]}
                  setSelected={(s) => setAnswers({ ...answers, [String(qi)]: s })} reveal={reveal?.predictions?.[qi]?.options ?? null} />
              </div>
            </div>
          ))}
        </div>
      ))}
      {at < stages.length - 1 && (
        <button className="btn" onClick={() => setAt(at + 1)} disabled={pending}>{pending ? "Answer the prediction to continue" : "Next stage →"}</button>
      )}
      {at === stages.length - 1 && !locked && <SubmitBar label="Finish" onClick={() => submit({ answers })} busy={busy} />}
      <Feedback result={result} />
    </div>
  );
}

export function ConceptMap({ a, reveal, result, locked, submit, busy }: RProps) {
  const p = a.data.payload;
  const nodes = p.nodes as { id: string; label: string; note: string }[];
  const edges = p.edges as { source: string; target: string; label: string }[];
  const [focus, setFocus] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, number[]>>({});
  const W = 640, H = 360, R = 140;
  const pos = Object.fromEntries(nodes.map((n, i) => {
    const t = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
    return [n.id, { x: W / 2 + R * 1.6 * Math.cos(t), y: H / 2 + R * Math.sin(t) }];
  }));
  const qs = (p.questions ?? []) as { prompt: string; options: Json[] }[];
  return (
    <div className="stack">
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", background: "var(--surface-2)", borderRadius: 12 }} role="img" aria-label="Concept map">
        <defs><marker id="arr" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0L10,5L0,10z" fill="#8a91a3" /></marker></defs>
        {edges.map((e, i) => {
          const s = pos[e.source], t = pos[e.target];
          if (!s || !t) return null;
          const on = !focus || focus === e.source || focus === e.target;
          return (
            <g key={i} opacity={on ? 1 : 0.15}>
              <line x1={s.x} y1={s.y} x2={t.x} y2={t.y} stroke="#8a91a3" strokeWidth={1.5} markerEnd="url(#arr)" />
              <text x={(s.x + t.x) / 2} y={(s.y + t.y) / 2 - 4} fontSize={11} textAnchor="middle" fill="#5d6475">{e.label}</text>
            </g>
          );
        })}
        {nodes.map((n) => pos[n.id] && (
          <g key={n.id} onClick={() => setFocus(focus === n.id ? null : n.id)} style={{ cursor: "pointer" }}>
            <rect x={pos[n.id].x - 62} y={pos[n.id].y - 16} width={124} height={32} rx={9}
              fill={focus === n.id ? "#4b3fe0" : "#fff"} stroke="#4b3fe0" />
            <text x={pos[n.id].x} y={pos[n.id].y + 4} fontSize={12} textAnchor="middle" fill={focus === n.id ? "#fff" : "#151821"}>
              {n.label.length > 20 ? n.label.slice(0, 19) + "…" : n.label}</text>
          </g>
        ))}
      </svg>
      {focus && <div className="notice"><strong>{nodes.find((n) => n.id === focus)?.label}: </strong>{nodes.find((n) => n.id === focus)?.note}</div>}
      {qs.map((q, i) => (
        <div key={i}>
          <strong><Md text={q.prompt} inline /></strong>
          <Choices options={q.options} selected={answers[String(i)] ?? []} multiple={false} locked={locked}
            setSelected={(s) => setAnswers({ ...answers, [String(i)]: s })} reveal={reveal?.questions?.[i]?.options ?? null} />
        </div>
      ))}
      {!locked && <SubmitBar onClick={() => submit({ answers })} disabled={qs.some((_, i) => !answers[String(i)])} busy={busy} />}
      <Feedback result={result} />
    </div>
  );
}
