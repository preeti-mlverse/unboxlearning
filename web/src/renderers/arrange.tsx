import { useState } from "react";
import { Md } from "../ui";
import { Feedback, SubmitBar, type RProps } from "./common";

function Reorder({ items, setItems, locked, correct }: { items: string[]; setItems: (x: string[]) => void; locked: boolean; correct?: string[] }) {
  const move = (i: number, d: number) => {
    const j = i + d;
    if (j < 0 || j >= items.length) return;
    const n = [...items];
    [n[i], n[j]] = [n[j], n[i]];
    setItems(n);
  };
  const [drag, setDrag] = useState<number | null>(null);
  return (
    <ol style={{ listStyle: "none", padding: 0, margin: 0 }}>
      {items.map((it, i) => (
        <li key={it} draggable={!locked} onDragStart={() => setDrag(i)} onDragOver={(e) => e.preventDefault()}
          onDrop={() => { if (drag === null) return; const n = [...items]; const [x] = n.splice(drag, 1); n.splice(i, 0, x); setItems(n); setDrag(null); }}
          className={`drag-item ${correct ? (correct[i] === it ? "right" : "wrong") : ""}`}>
          <span className="badge">{i + 1}</span>
          <span style={{ flex: 1 }}><Md text={it} inline /></span>
          {!locked && (
            <span className="row" style={{ gap: 2 }}>
              <button className="btn ghost sm" onClick={() => move(i, -1)} aria-label="Move up" disabled={i === 0}>↑</button>
              <button className="btn ghost sm" onClick={() => move(i, 1)} aria-label="Move down" disabled={i === items.length - 1}>↓</button>
            </span>
          )}
        </li>
      ))}
    </ol>
  );
}

export function Ordering({ a, reveal, result, locked, review, submit, busy }: RProps) {
  const p = a.data.payload;
  const [items, setItems] = useState<string[]>(p.items);
  return (
    <div className="stack">
      <Md text={p.prompt} />
      <div className="small muted">Drag or use the arrows to put these in the right order.</div>
      <Reorder items={review ? reveal.items : items} setItems={setItems} locked={locked} correct={reveal && !review ? reveal.items : undefined} />
      {!locked && <SubmitBar onClick={() => submit({ order: items })} busy={busy} />}
      <Feedback result={result} />
      {reveal?.explanation && <div className="notice"><Md text={reveal.explanation} /></div>}
    </div>
  );
}

export function Timeline({ a, reveal, result, locked, review, submit, busy }: RProps) {
  const p = a.data.payload;
  const events = p.events as { when?: string; label: string; detail: string; sort_key?: number }[];
  const [order, setOrder] = useState<string[]>(events.map((e) => e.label));
  const full = (reveal?.events ?? events) as typeof events;
  const sorted = [...full].sort((x, y) => (x.sort_key ?? 0) - (y.sort_key ?? 0));
  const explore = p.task !== "order" || review || !!reveal;
  return (
    <div className="stack">
      <Md text={p.intro} />
      {explore ? (
        <div style={{ borderLeft: "3px solid var(--primary-soft)", paddingLeft: 16 }}>
          {sorted.map((e, i) => (
            <div key={i} style={{ position: "relative", marginBottom: 14 }}>
              <span style={{ position: "absolute", left: -23, top: 6, width: 11, height: 11, borderRadius: 99, background: "var(--primary)" }} />
              <div className="stage-pill">{e.when}</div>
              <strong>{e.label}</strong>
              <div className="small"><Md text={e.detail} inline /></div>
            </div>
          ))}
        </div>
      ) : (
        <>
          <div className="small muted">Put the events in chronological order (earliest first).</div>
          <Reorder items={order} setItems={setOrder} locked={locked} />
        </>
      )}
      {!locked && <SubmitBar label={p.task === "order" ? "Check order" : "Continue"} onClick={() => submit({ order })} busy={busy} />}
      <Feedback result={result} />
    </div>
  );
}

export function Matching({ a, reveal, result, locked, submit, busy }: RProps) {
  const p = a.data.payload;
  const lefts: string[] = p.pairs.map((x: { left: string }) => x.left);
  const rights: string[] = p.rights ?? p.pairs.map((x: { right: string }) => x.right);
  const [pairs, setPairs] = useState<Record<string, string>>({});
  const truth: Record<string, string> | null = reveal ? Object.fromEntries(reveal.pairs.map((x: { left: string; right: string }) => [x.left, x.right])) : null;
  return (
    <div className="stack">
      <Md text={p.prompt} />
      {lefts.map((l) => (
        <div key={l} className="grid2" style={{ alignItems: "center", gap: 10 }}>
          <div className={`drag-item ${truth ? (pairs[l] === truth[l] ? "right" : "wrong") : ""}`} style={{ cursor: "default", marginBottom: 0 }}><Md text={l} inline /></div>
          {truth && locked && !pairs[l] ? <div className="small"><strong>{truth[l]}</strong></div> : (
            <select value={pairs[l] ?? ""} disabled={locked} onChange={(e) => { const v = e.target.value; setPairs((prev) => ({ ...prev, [l]: v })); }} aria-label={`Match for ${l}`}>
              <option value="">Choose…</option>
              {rights.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          )}
          {truth && pairs[l] && pairs[l] !== truth[l] && <div className="small muted" style={{ gridColumn: "2" }}>Correct: {truth[l]}</div>}
        </div>
      ))}
      {!locked && <SubmitBar onClick={() => submit({ pairs })} disabled={Object.keys(pairs).length < lefts.length} busy={busy} />}
      <Feedback result={result} />
      {reveal?.explanation && <div className="notice"><Md text={reveal.explanation} /></div>}
    </div>
  );
}

export function Categorize({ a, reveal, result, locked, submit, busy }: RProps) {
  const p = a.data.payload;
  const items = p.items as { text: string }[];
  const [assign, setAssign] = useState<Record<string, string>>({});
  const truth = reveal ? (reveal.items as { text: string; category: string; why: string }[]) : null;
  return (
    <div className="stack">
      <Md text={p.prompt} />
      {items.map((it, idx) => {
        const t = truth?.[idx];
        const k = String(idx);
        return (
          <div key={idx} className={`drag-item ${t ? (assign[k] === t.category ? "right" : "wrong") : ""}`} style={{ cursor: "default", flexWrap: "wrap" }}>
            <span style={{ flex: "1 1 240px" }}><Md text={it.text} inline /></span>
            <span className="row" style={{ gap: 6 }}>
              {p.categories.map((c: string) => (
                <button key={c} className={`chip ${assign[k] === c ? "on" : ""}`} disabled={locked}
                  onClick={() => setAssign((prev) => ({ ...prev, [k]: c }))}>{c}</button>
              ))}
            </span>
            {t && <div className="rationale" style={{ flexBasis: "100%" }}><strong>{t.category}:</strong> <Md text={t.why} inline /></div>}
          </div>
        );
      })}
      {!locked && <SubmitBar onClick={() => submit({ assign })} disabled={Object.keys(assign).length < items.length} busy={busy} />}
      <Feedback result={result} />
    </div>
  );
}
