import { useRef, useState, type MouseEvent } from "react";
import { api } from "../api";
import { Md } from "../ui";
import { CodeView } from "./basic";
import { Feedback, SubmitBar, type RProps } from "./common";

type ScChoice = { text: string; next_node: string; feedback: string; quality: string };
type ScNode = { id: string; text: string; choices: ScChoice[] };

export function Scenario({ a, result, locked, review, submit, busy }: RProps) {
  const p = a.data.payload;
  const nodes = Object.fromEntries((p.nodes as ScNode[]).map((n) => [n.id, n]));
  const [path, setPath] = useState<{ node: string; choice: number }[]>([]);
  const [cur, setCur] = useState<string>(p.start_node in nodes ? p.start_node : (p.nodes[0]?.id ?? ""));
  const [ended, setEnded] = useState(false);
  const node = nodes[cur];
  const choose = (i: number) => {
    const c = node.choices[i];
    const np = [...path, { node: cur, choice: i }];
    setPath(np);
    if (c.next_node && nodes[c.next_node] && np.length < 8) setCur(c.next_node);
    else setEnded(true);
  };
  const qual = { best: "good", acceptable: "warn", poor: "bad" } as Record<string, string>;
  if (review) {
    return (
      <div className="stack">
        <Md text={p.context} />
        {(p.nodes as ScNode[]).map((n) => (
          <div key={n.id} className="card flat">
            <div className="tiny faint mono">{n.id}</div><Md text={n.text} />
            {n.choices.map((c, i) => (
              <div key={i} className="small" style={{ marginTop: 6 }}>
                <span className={`badge ${qual[c.quality]}`}>{c.quality}</span> {c.text} <span className="faint">→ {c.next_node || "end"}</span>
                <div className="rationale">{c.feedback}</div>
              </div>
            ))}
          </div>
        ))}
        <div className="notice"><strong>Debrief: </strong><Md text={p.debrief} inline /></div>
      </div>
    );
  }
  return (
    <div className="stack">
      <div className="card flat" style={{ background: "var(--surface-2)" }}><Md text={p.context} /></div>
      {path.map((st, i) => {
        const n = nodes[st.node], c = n.choices[st.choice];
        return (
          <div key={i} className="stack" style={{ opacity: 0.85 }}>
            <Md text={n.text} />
            <div className={`feedback ${c.quality === "best" ? "good" : c.quality === "poor" ? "bad" : "mid"}`}>
              <strong>You chose:</strong> {c.text}<div className="small"><Md text={c.feedback} inline /></div>
            </div>
          </div>
        );
      })}
      {!ended && node && (
        <div>
          <Md text={node.text} />
          {node.choices.map((c, i) => <button key={i} className="opt" onClick={() => choose(i)} disabled={locked}><span style={{ flex: 1 }}>{c.text}</span></button>)}
        </div>
      )}
      {ended && (
        <>
          <div className="notice"><strong>Debrief: </strong><Md text={p.debrief} inline /></div>
          {!locked && <SubmitBar label="Finish scenario" busy={busy}
            onClick={() => submit({ path, qualities: path.map((s) => nodes[s.node].choices[s.choice].quality) })} />}
        </>
      )}
      <Feedback result={result} />
    </div>
  );
}

export function Roleplay({ a, result, locked, review, submit, busy }: RProps) {
  const p = a.data.payload;
  const [history, setHistory] = useState<{ role: string; text: string }[]>([{ role: "character", text: p.opening_line }]);
  const [msg, setMsg] = useState("");
  const [state, setState] = useState<{ progress: number; met: string[]; finished: boolean; note: string }>({ progress: 0, met: [], finished: false, note: "" });
  const [sending, setSending] = useState(false);
  const [err, setErr] = useState("");
  const send = async () => {
    if (!msg.trim()) return;
    const h = [...history, { role: "learner", text: msg }];
    setHistory(h); setMsg(""); setSending(true); setErr("");
    try {
      const t = await api.roleplay(a.id, history, msg);
      setHistory([...h, { role: "character", text: t.reply }]);
      setState({ progress: t.goal_progress, met: t.criteria_met, finished: t.finished, note: t.coach_note });
    } catch (e) { setErr(String(e)); } finally { setSending(false); }
  };
  return (
    <div className="stack">
      <div className="card flat" style={{ background: "var(--surface-2)" }}>
        <div><strong>You're talking to:</strong> {p.persona}</div>
        <div className="small"><strong>Setting:</strong> {p.setting}</div>
        <div className="small"><strong>Your goal:</strong> {p.learner_goal}</div>
        {review && <div className="small muted"><strong>Brief:</strong> {p.persona_brief}<br /><strong>Success:</strong> {p.success_criteria.join("; ")}</div>}
      </div>
      <div className="col" style={{ gap: 8 }}>
        {history.map((m, i) => <div key={i} className={`bubble ${m.role === "learner" ? "me" : "them"}`}><Md text={m.text} /></div>)}
        {sending && <div className="bubble them faint">…</div>}
      </div>
      {state.note && <div className="small muted"><strong>Coach:</strong> {state.note}</div>}
      {err && <div className="notice bad">{err}</div>}
      {!locked && !review && (
        <>
          <div className="row" style={{ flexWrap: "nowrap" }}>
            <input value={msg} onChange={(e) => setMsg(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} placeholder="Your reply…" aria-label="Your reply" disabled={sending} />
            <button className="btn primary" onClick={send} disabled={sending || !msg.trim()}>Send</button>
          </div>
          <div className="spread small muted">
            <span>Goal progress {Math.round(state.progress * 100)}%{state.met.length ? ` · met: ${state.met.join("; ")}` : ""}</span>
            <button className="btn sm" onClick={() => submit({ score: state.progress, history })} disabled={busy || history.length < 3}>
              {state.finished ? "Finish conversation" : "End & get feedback"}</button>
          </div>
        </>
      )}
      <Feedback result={result} />
    </div>
  );
}

export function FindTheBug({ a, reveal, result, locked, submit, busy }: RProps) {
  const p = a.data.payload;
  const [sel, setSel] = useState<number[]>([]);
  const toggle = (n: number) => !locked && setSel(sel.includes(n) ? sel.filter((x) => x !== n) : [...sel, n]);
  return (
    <div className="stack">
      <Md text={p.question} />
      <div className="small muted">Click the line(s) that contain the bug.</div>
      <CodeView code={p.code} pick={toggle} selected={sel} bugs={reveal?.bug_lines ?? []} />
      {!locked && <SubmitBar onClick={() => submit({ lines: sel })} disabled={!sel.length} busy={busy} />}
      <Feedback result={result} />
      {reveal && (
        <>
          <div className="notice"><Md text={reveal.bug_explanation} /></div>
          <strong className="small">Fixed version</strong>
          <CodeView code={reveal.fixed_code} />
        </>
      )}
    </div>
  );
}

export function DiagramLabel({ a, reveal, result, locked, review, submit, busy }: RProps) {
  const p = a.data.payload;
  const labels = p.labels as { text: string; x?: number; y?: number; explanation?: string }[];
  const [placed, setPlaced] = useState<Record<string, [number, number]>>({});
  const [active, setActive] = useState(0);
  const img = useRef<HTMLDivElement>(null);
  const place = (e: MouseEvent) => {
    if (locked || !img.current) return;
    const r = img.current.getBoundingClientRect();
    const pt: [number, number] = [(e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height];
    const next = { ...placed, [String(active)]: pt };
    setPlaced(next);
    const free = labels.findIndex((_, i) => !next[String(i)]);
    if (free >= 0) setActive(free);
  };
  const truth = reveal?.labels ?? (review ? labels : null);
  return (
    <div className="stack">
      <Md text={p.prompt} />
      <div className="row">{labels.map((l, i) => <button key={i} className={`chip ${i === active ? "on" : ""}`} onClick={() => setActive(i)} disabled={locked}>{placed[String(i)] ? "✓ " : ""}{l.text}</button>)}</div>
      <div ref={img} onClick={place} style={{ position: "relative", cursor: locked ? "default" : "crosshair", display: "inline-block", maxWidth: "100%" }}>
        {p.media_path ? <img src={`/media/${p.media_path}`} alt="Diagram to label" style={{ maxWidth: "100%", display: "block", borderRadius: 8 }} />
          : <div className="notice warn">Figure image not available.</div>}
        {Object.entries(placed).map(([i, [x, y]]) => (
          <span key={i} className="badge primary" style={{ position: "absolute", left: `${x * 100}%`, top: `${y * 100}%`, transform: "translate(-50%,-50%)" }}>{labels[+i].text}</span>
        ))}
        {truth?.map((l: { text: string; x: number; y: number }, i: number) => (
          <span key={`t${i}`} className="badge good" style={{ position: "absolute", left: `${l.x * 100}%`, top: `${l.y * 100}%`, transform: "translate(-50%,-50%)", opacity: 0.9 }}>{l.text}</span>
        ))}
      </div>
      {!locked && <SubmitBar onClick={() => submit({ placed })} disabled={Object.keys(placed).length < labels.length} busy={busy} />}
      <Feedback result={result} />
    </div>
  );
}
