import { useEffect, useRef, useState } from "react";
import { Speaker } from "../speech";
import { Md } from "../ui";
import { SubmitBar, type RProps } from "./common";

function Listen({ text }: { text: string }) {
  const [on, setOn] = useState(false);
  const sp = useRef(new Speaker());
  useEffect(() => () => sp.current.stop(), []);
  const toggle = async () => {
    if (on) { sp.current.stop(); setOn(false); return; }
    setOn(true);
    await sp.current.say(text);
    setOn(false);
  };
  return <button className="btn ghost sm" onClick={toggle} title="Read aloud">{on ? "■ Stop" : "🔊 Listen"}</button>;
}

export function Explainer({ a, locked, submit, busy }: RProps) {
  const p = a.data.payload;
  const [showCheck, setShowCheck] = useState(false);
  const all = p.sections.map((s: { heading: string; markdown: string }) => `${s.heading}. ${s.markdown}`).join("\n");
  return (
    <div className="stack">
      <div className="row" style={{ justifyContent: "flex-end" }}><Listen text={all} /></div>
      {p.sections.map((s: { heading: string; markdown: string }, i: number) => (
        <section key={i}><h3>{s.heading}</h3><Md text={s.markdown} /></section>
      ))}
      {p.analogy && <div className="notice"><strong>Think of it like this: </strong><Md text={p.analogy} inline /></div>}
      {!!p.key_points?.length && (
        <div className="card flat"><h4>Key points</h4><ul style={{ margin: 0, paddingLeft: 20 }}>
          {p.key_points.map((k: string, i: number) => <li key={i}><Md text={k} inline /></li>)}</ul></div>
      )}
      {p.check_question && (
        <div className="card flat">
          <strong>Quick self-check: </strong><Md text={p.check_question} inline />
          <div style={{ marginTop: 8 }}>
            {showCheck ? <div className="notice good"><Md text={p.check_answer} /></div>
              : <button className="btn sm" onClick={() => setShowCheck(true)}>Show answer</button>}
          </div>
        </div>
      )}
      {!locked && <SubmitBar label="Got it — continue" onClick={() => submit({ viewed: true })} busy={busy} />}
    </div>
  );
}

export function WorkedExample({ a, locked, review, submit, busy }: RProps) {
  const p = a.data.payload;
  const [shown, setShown] = useState(review ? p.steps.length : 1);
  return (
    <div className="stack">
      <div className="card flat"><strong>Problem</strong><Md text={p.problem} /></div>
      {p.steps.slice(0, shown).map((s: { explanation: string; work: string; why: string }, i: number) => (
        <div key={i} className="card flat">
          <div className="stage-pill">Step {i + 1}</div>
          <Md text={s.explanation} />
          <Md text={s.work} />
          <div className="small muted"><strong>Why: </strong><Md text={s.why} inline /></div>
        </div>
      ))}
      {shown < p.steps.length ? (
        <div className="row">
          <button className="btn" onClick={() => setShown(shown + 1)}>Next step</button>
          <span className="small muted">Try predicting the next step before revealing it.</span>
        </div>
      ) : (
        <>
          <div className="notice good"><strong>Result: </strong><Md text={p.answer} inline /></div>
          {!!p.common_errors?.length && (
            <div className="notice warn"><strong>Common errors</strong>
              <ul style={{ margin: "4px 0 0", paddingLeft: 20 }}>{p.common_errors.map((e: string, i: number) => <li key={i}><Md text={e} inline /></li>)}</ul></div>
          )}
          {!locked && <SubmitBar label="Continue" onClick={() => submit({ viewed: true })} busy={busy} />}
        </>
      )}
    </div>
  );
}

function parseRange(r: string): number[] {
  const out: number[] = [];
  for (const part of String(r).split(",")) {
    const [a, b] = part.split("-").map((x) => parseInt(x, 10));
    if (!isNaN(a)) for (let i = a; i <= (isNaN(b) ? a : b); i++) out.push(i);
  }
  return out;
}

export function CodeView({ code, highlight = [], pick, selected = [], bugs = [] }: {
  code: string; highlight?: number[]; pick?: (n: number) => void; selected?: number[]; bugs?: number[];
}) {
  return (
    <div className="codeview" role={pick ? "listbox" : undefined}>
      {code.split("\n").map((line, i) => {
        const n = i + 1;
        const cls = [bugs.includes(n) ? "bug" : selected.includes(n) ? "sel" : highlight.includes(n) ? "hl" : "", pick ? "pick" : ""].join(" ");
        return (
          <div key={i} className={`codeline ${cls}`} onClick={pick ? () => pick(n) : undefined}
            role={pick ? "option" : undefined} aria-selected={pick ? selected.includes(n) : undefined}>
            <span className="ln">{n}</span><span>{line || " "}</span>
          </div>
        );
      })}
    </div>
  );
}

export function CodeWalkthrough({ a, locked, submit, busy }: RProps) {
  const p = a.data.payload;
  const [active, setActive] = useState(0);
  const ann = p.annotations ?? [];
  return (
    <div className="grid2" style={{ alignItems: "start" }}>
      <CodeView code={p.code} highlight={ann[active] ? parseRange(ann[active].lines) : []} />
      <div className="stack">
        {ann.map((x: { lines: string; note: string }, i: number) => (
          <button key={i} className={`opt ${i === active ? "sel" : ""}`} onClick={() => setActive(i)}>
            <span className="badge mono">L{x.lines}</span><span style={{ flex: 1 }}><Md text={x.note} inline /></span>
          </button>
        ))}
        <div className="notice good"><strong>Takeaway: </strong><Md text={p.takeaway} inline /></div>
        {p.try_it && <div className="notice"><strong>Try it: </strong><Md text={p.try_it} inline /></div>}
        {!locked && <SubmitBar label="Continue" onClick={() => submit({ viewed: true })} busy={busy} />}
      </div>
    </div>
  );
}

export function Flashcards({ a, locked, submit, busy }: RProps) {
  const cards = a.data.payload.cards as { front: string; back: string; hint: string }[];
  const [i, setI] = useState(0);
  const [flip, setFlip] = useState(false);
  const [ratings, setRatings] = useState<Record<string, string>>({});
  const rate = (r: string) => {
    const next = { ...ratings, [String(i)]: r };
    setRatings(next);
    setFlip(false);
    if (i + 1 < cards.length) setI(i + 1);
    else if (!locked) submit({ ratings: next });
  };
  const c = cards[Math.min(i, cards.length - 1)];
  return (
    <div className="stack">
      <div className="small muted">Card {Math.min(i + 1, cards.length)} of {cards.length} — recall the answer before flipping.</div>
      <div className={`flash ${flip ? "flip" : ""}`} onClick={() => setFlip(!flip)} role="button" tabIndex={0}
        onKeyDown={(e) => e.key === " " && setFlip(!flip)} aria-label="Flip card">
        <div className="flash-inner">
          <div className="flash-face"><Md text={c.front} /></div>
          <div className="flash-face flash-back"><Md text={c.back} /></div>
        </div>
      </div>
      {c.hint && !flip && <div className="small muted">Hint: {c.hint}</div>}
      {flip && !locked && (
        <div className="row">
          <span className="small muted">How well did you know it?</span>
          {["again", "hard", "good", "easy"].map((r) => <button key={r} className="btn sm" onClick={() => rate(r)} disabled={busy}>{r}</button>)}
        </div>
      )}
      {locked && <div className="row">{cards.map((_, k) => <button key={k} className={`chip ${k === i ? "on" : ""}`} onClick={() => { setI(k); setFlip(false); }}>{k + 1}</button>)}</div>}
    </div>
  );
}
