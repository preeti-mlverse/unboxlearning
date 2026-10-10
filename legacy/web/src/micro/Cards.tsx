import { useEffect, useMemo, useRef, useState } from "react";
import { Speaker } from "../speech";
import { mapi, type Card } from "./mapi";
import { Visual } from "./Visual";

export type Result = { score: number; response: Record<string, unknown> };

function shuffle<T>(a: T[], seed: string): T[] {
  let h = 0;
  for (const c of seed) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  const out = [...a];
  for (let i = out.length - 1; i > 0; i--) { h = (h * 1103515245 + 12345) >>> 0; const j = h % (i + 1); [out[i], out[j]] = [out[j], out[i]]; }
  return out;
}
const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();

export function Narrate({ text, auto }: { text: string; auto?: boolean }) {
  const sp = useRef(new Speaker());
  const [on, setOn] = useState(false);
  const play = async () => { setOn(true); await sp.current.say(text); setOn(false); };
  useEffect(() => { if (auto && text) play(); return () => sp.current.stop(); }, [text]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!text) return null;
  return (
    <button className={`m-listen ${on ? "on" : ""}`} onClick={() => (on ? (sp.current.stop(), setOn(false)) : play())} aria-label={on ? "Stop narration" : "Listen"}>
      {on ? <><span className="m-eq"><i /><i /><i /></span> Stop</> : <>🔊 Listen</>}
    </button>
  );
}

/** Renders one card. Calls done(result|null) when the learner may continue (null = nothing to score). */
export function CardView({ card, seed, done, autoVoice, ctx }: {
  card: Card; seed: string; done: (r: Result | null) => void; autoVoice?: boolean;
  ctx?: { cid: string; mid: string; index: number; learnerId?: string };
}) {
  const k = card.kind;
  if (k === "hook" || k === "concept" || k === "example")
    return <Teach card={card} done={done} autoVoice={autoVoice} />;
  if (k === "recap") return <Recap card={card} done={done} />;
  const body = {
    check: <Choice card={card} done={done} seed={seed} />, odd_one_out: <Choice card={card} done={done} seed={seed} odd />,
    true_false: <TrueFalse card={card} done={done} />, sort: <Sort card={card} done={done} seed={seed} />,
    reorder: <Reorder card={card} done={done} seed={seed} />, match: <Match card={card} done={done} seed={seed} />,
    fill_blank: <FillBlank card={card} done={done} />, apply: <Apply card={card} done={done} ctx={ctx} />,
  }[k];
  return (
    <div className="m-game">
      <div className="m-game-tag">{GAME_LABEL[k]}</div>
      <h2 className="m-title">{card.title}</h2>
      {card.text && k !== "apply" && <p className="m-prompt">{card.text}</p>}
      {card.visual?.kind !== "none" && <Visual v={card.visual} big={false} />}
      {body}
    </div>
  );
}

export const GAME_LABEL: Record<string, string> = {
  check: "Quick check", odd_one_out: "Odd one out", true_false: "True or false?", sort: "Sort it", reorder: "Put in order",
  match: "Match up", fill_blank: "Fill the gap", apply: "Your turn", recap: "Recap",
};

function Teach({ card, done, autoVoice }: { card: Card; done: (r: null) => void; autoVoice?: boolean }) {
  useEffect(() => { done(null); }, [card]); // eslint-disable-line react-hooks/exhaustive-deps
  const hook = card.kind === "hook";
  return (
    <div className={`m-teach ${hook ? "hook" : ""}`}>
      {card.visual?.kind !== "none" && <div className="m-visual"><Visual v={card.visual} /></div>}
      <div className="m-teach-text">
        {hook && <div className="m-kicker">Think about this</div>}
        {card.kind === "example" && <div className="m-kicker">For example</div>}
        <h2 className="m-title">{card.title}</h2>
        <p className="m-body">{card.text}</p>
        <Narrate text={card.narration || card.text} auto={autoVoice} />
      </div>
    </div>
  );
}

function Recap({ card, done }: { card: Card; done: (r: null) => void }) {
  useEffect(() => { done(null); }, [card]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className="m-recap">
      <div className="m-kicker">Remember</div>
      <h2 className="m-title">{card.title}</h2>
      <ul>{card.steps.map((s, i) => <li key={i} style={{ animationDelay: `${i * 0.15}s` }}>{s}</li>)}</ul>
    </div>
  );
}

function Feedback({ ok, text }: { ok: boolean | null; text: string }) {
  if (ok === null) return null;
  return <div className={`m-fb ${ok ? "ok" : "no"}`} role="status"><strong>{ok ? "Yes! " : "Not quite. "}</strong>{text}</div>;
}

function Choice({ card, done, seed, odd }: { card: Card; done: (r: Result) => void; seed: string; odd?: boolean }) {
  const opts = useMemo(() => shuffle(card.options.map((o, i) => ({ ...o, i })), seed), [card, seed]);
  const [pick, setPick] = useState<number | null>(null);
  const chosen = pick === null ? null : card.options[pick];
  const right = card.options.find((o) => o.correct);
  const choose = (i: number) => {
    if (pick !== null) return;
    setPick(i);
    done({ score: card.options[i].correct ? 1 : 0, response: { selected: i } });
  };
  return (
    <>
      <div className={`m-options ${odd ? "grid" : ""}`}>
        {opts.map((o) => {
          const st = pick === null ? "" : o.correct ? "right" : pick === o.i ? "wrong" : "dim";
          return <button key={o.i} className={`m-opt ${st}`} onClick={() => choose(o.i)} disabled={pick !== null}>{o.text}</button>;
        })}
      </div>
      {chosen && <Feedback ok={chosen.correct} text={chosen.correct ? chosen.why : `${chosen.why} ${right ? `→ ${right.text}` : ""}`} />}
    </>
  );
}

function TrueFalse({ card, done }: { card: Card; done: (r: Result) => void }) {
  const [i, setI] = useState(0);
  const [answers, setAnswers] = useState<boolean[]>([]);
  const [shown, setShown] = useState<boolean | null>(null);
  const [left, setLeft] = useState(12);
  const st = card.statements[i];
  const finished = answers.length === card.statements.length;
  useEffect(() => {
    if (finished || shown !== null) return;
    setLeft(12);
    const t = window.setInterval(() => setLeft((x) => {
      if (x <= 0.1) { window.clearInterval(t); answer(null); return 0; }
      return x - 0.1;
    }), 100);
    return () => window.clearInterval(t);
  }, [i, shown, finished]); // eslint-disable-line react-hooks/exhaustive-deps
  const answer = (v: boolean | null) => {
    if (shown !== null) return;
    const ok = v === st.is_true;
    setShown(ok);
    const next = [...answers, ok];
    setAnswers(next);
    if (next.length === card.statements.length) done({ score: next.filter(Boolean).length / next.length, response: { answers: next } });
  };
  if (finished && shown === null)
    return <div className="m-fb ok"><strong>{answers.filter(Boolean).length} / {answers.length} right.</strong> Nice and quick!</div>;
  return (
    <div className="m-tf">
      <div className="m-dots">{card.statements.map((_, k) => <span key={k} className={k < answers.length ? (answers[k] ? "ok" : "no") : k === i ? "cur" : ""} />)}</div>
      <div className="m-tf-card">{st.text}</div>
      {shown === null ? (
        <>
          <div className="m-timer"><div style={{ width: `${(left / 12) * 100}%` }} /></div>
          <div className="m-tf-btns">
            <button className="m-btn false" onClick={() => answer(false)}>✗ False</button>
            <button className="m-btn true" onClick={() => answer(true)}>✓ True</button>
          </div>
        </>
      ) : (
        <>
          <Feedback ok={shown} text={`${st.is_true ? "True" : "False"} — ${st.why}`} />
          {i + 1 < card.statements.length && <button className="m-btn ghost" onClick={() => { setI(i + 1); setShown(null); }}>Next statement →</button>}
          {i + 1 === card.statements.length && <button className="m-btn ghost" onClick={() => setShown(null)}>See score</button>}
        </>
      )}
    </div>
  );
}

function Sort({ card, done, seed }: { card: Card; done: (r: Result) => void; seed: string }) {
  const items = useMemo(() => shuffle(card.bucket_items.map((x, i) => ({ ...x, i })), seed), [card, seed]);
  const [sel, setSel] = useState<number | null>(null);
  const [put, setPut] = useState<Record<number, string>>({});
  const [checked, setChecked] = useState(false);
  const place = (b: string) => { if (sel === null || checked) return; setPut((p) => ({ ...p, [sel]: b })); setSel(null); };
  const check = () => {
    setChecked(true);
    const ok = card.bucket_items.filter((x, i) => put[i] === x.bucket).length;
    done({ score: ok / card.bucket_items.length, response: { put } });
  };
  const loose = items.filter((x) => put[x.i] === undefined);
  return (
    <div className="m-sort">
      <div className="m-chips">
        {loose.map((x) => <button key={x.i} className={`m-chip ${sel === x.i ? "sel" : ""}`} onClick={() => setSel(x.i)}>{x.text}</button>)}
        {!loose.length && !checked && <span className="m-hint">All placed — check your answer.</span>}
        {!!loose.length && <span className="m-hint">{sel === null ? "Tap an item, then a box." : "Now tap the box it belongs in."}</span>}
      </div>
      <div className="m-buckets">
        {card.buckets.map((b) => (
          <div key={b} className={`m-bucket ${sel !== null ? "target" : ""}`} onClick={() => place(b)} role="button" tabIndex={0}>
            <div className="m-bucket-title">{b}</div>
            {items.filter((x) => put[x.i] === b).map((x) => (
              <span key={x.i} className={`m-chip placed ${checked ? (x.bucket === b ? "right" : "wrong") : ""}`}
                onClick={(e) => { e.stopPropagation(); if (!checked) setPut((p) => { const n = { ...p }; delete n[x.i]; return n; }); }}>{x.text}</span>
            ))}
          </div>
        ))}
      </div>
      {!checked && <button className="m-btn" disabled={!!loose.length} onClick={check}>Check</button>}
      {checked && <Feedback ok={card.bucket_items.every((x, i) => put[i] === x.bucket)} text={card.bucket_items.every((x, i) => put[i] === x.bucket) ? "Every item is in the right place." : "The red ones belong in the other box."} />}
    </div>
  );
}

function Reorder({ card, done, seed }: { card: Card; done: (r: Result) => void; seed: string }) {
  const pool = useMemo(() => shuffle(card.steps.map((s, i) => ({ s, i })), seed + "r"), [card, seed]);
  const [seq, setSeq] = useState<number[]>([]);
  const [checked, setChecked] = useState(false);
  const check = () => {
    setChecked(true);
    const ok = seq.filter((v, i) => v === i).length;
    done({ score: ok / card.steps.length, response: { order: seq } });
  };
  const allRight = seq.every((v, i) => v === i);
  return (
    <div className="m-reorder">
      <ol className="m-seq">
        {card.steps.map((_, pos) => {
          const v = seq[pos];
          return (
            <li key={pos} className={v === undefined ? "empty" : checked ? (v === pos ? "right" : "wrong") : "filled"}
              onClick={() => !checked && v !== undefined && setSeq(seq.filter((x) => x !== v))}>
              <span className="m-num">{pos + 1}</span>{v === undefined ? <span className="m-hint">tap a step below</span> : card.steps[v]}
            </li>
          );
        })}
      </ol>
      <div className="m-chips">{pool.filter((p) => !seq.includes(p.i)).map((p) => <button key={p.i} className="m-chip" onClick={() => setSeq([...seq, p.i])}>{p.s}</button>)}</div>
      {!checked && <button className="m-btn" disabled={seq.length < card.steps.length} onClick={check}>Check order</button>}
      {checked && <Feedback ok={allRight} text={allRight ? "Perfect sequence." : `Correct order: ${card.steps.join(" → ")}`} />}
    </div>
  );
}

function Match({ card, done, seed }: { card: Card; done: (r: Result) => void; seed: string }) {
  const rights = useMemo(() => shuffle(card.pairs.map((p, i) => ({ t: p.right, i })), seed + "m"), [card, seed]);
  const [left, setLeft] = useState<number | null>(null);
  const [pairs, setPairs] = useState<Record<number, number>>({});
  const [checked, setChecked] = useState(false);
  const colors = ["#6c5ce7", "#00a884", "#ff7a59", "#f0a500", "#e84393"];
  const pickRight = (ri: number) => {
    if (left === null || checked) return;
    const n = { ...pairs };
    Object.keys(n).forEach((k) => { if (n[+k] === ri) delete n[+k]; });
    n[left] = ri;
    setPairs(n); setLeft(null);
  };
  const check = () => {
    setChecked(true);
    const ok = card.pairs.filter((_, i) => pairs[i] === i).length;
    done({ score: ok / card.pairs.length, response: { pairs } });
  };
  const colorOfRight = (ri: number) => { const l = Object.keys(pairs).find((k) => pairs[+k] === ri); return l === undefined ? undefined : colors[+l % colors.length]; };
  return (
    <div className="m-match">
      <div className="m-match-cols">
        <div>{card.pairs.map((p, i) => (
          <button key={i} className={`m-tile ${left === i ? "sel" : ""} ${checked ? (pairs[i] === i ? "right" : "wrong") : ""}`}
            style={pairs[i] !== undefined ? { borderColor: colors[i % colors.length], boxShadow: `inset 4px 0 0 ${colors[i % colors.length]}` } : undefined}
            onClick={() => !checked && setLeft(i)}>{p.left}</button>
        ))}</div>
        <div>{rights.map((r) => (
          <button key={r.i} className="m-tile" style={colorOfRight(r.i) ? { borderColor: colorOfRight(r.i), boxShadow: `inset 4px 0 0 ${colorOfRight(r.i)}` } : undefined}
            onClick={() => pickRight(r.i)}>{r.t}</button>
        ))}</div>
      </div>
      {!checked && <span className="m-hint">{left === null ? "Tap a left card, then its partner." : "Now tap its partner on the right."}</span>}
      {!checked && <button className="m-btn" disabled={Object.keys(pairs).length < card.pairs.length} onClick={check}>Check</button>}
      {checked && <Feedback ok={card.pairs.every((_, i) => pairs[i] === i)} text={card.pairs.map((p) => `${p.left} = ${p.right}`).join(" · ")} />}
    </div>
  );
}

function FillBlank({ card, done }: { card: Card; done: (r: Result) => void }) {
  const [v, setV] = useState("");
  const [ok, setOk] = useState<boolean | null>(null);
  const [before, after] = card.blank_sentence.split("___");
  const check = () => {
    const good = card.blank_answers.some((a) => norm(a) === norm(v) || (norm(v).length > 3 && norm(a).includes(norm(v)) && norm(v).length >= norm(a).length * 0.7));
    setOk(good);
    done({ score: good ? 1 : 0, response: { text: v } });
  };
  return (
    <div className="m-fill">
      <p className="m-sentence">{before}<input value={v} onChange={(e) => setV(e.target.value)} disabled={ok !== null} aria-label="Missing word"
        onKeyDown={(e) => e.key === "Enter" && v.trim() && ok === null && check()} style={{ width: Math.max(120, (card.blank_answers[0]?.length ?? 8) * 12) }} />{after}</p>
      {ok === null && <button className="m-btn" disabled={!v.trim()} onClick={check}>Check</button>}
      <Feedback ok={ok} text={ok ? "Exactly." : `The answer: ${card.blank_answers[0]}`} />
    </div>
  );
}

function Apply({ card, done, ctx }: { card: Card; done: (r: Result) => void; ctx?: { cid: string; mid: string; index: number; learnerId?: string } }) {
  const [v, setV] = useState("");
  const [fb, setFb] = useState<{ score: number; feedback: string; better_answer: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [listening, setListening] = useState(false);
  const w = window as unknown as { SpeechRecognition?: new () => any; webkitSpeechRecognition?: new () => any }; // eslint-disable-line @typescript-eslint/no-explicit-any
  const Rec = w.SpeechRecognition ?? w.webkitSpeechRecognition;
  const dictate = () => {
    if (!Rec) return;
    const r = new Rec(); r.lang = navigator.language || "en-IN"; r.interimResults = false;
    r.onresult = (e: any) => setV((x) => (x ? x + " " : "") + e.results[0][0].transcript); // eslint-disable-line @typescript-eslint/no-explicit-any
    r.onend = () => setListening(false); setListening(true); r.start();
  };
  const send = async () => {
    if (!ctx?.learnerId) { setFb({ score: 1, feedback: "Preview mode — here is the model answer.", better_answer: card.model_answer }); done({ score: 1, response: {} }); return; }
    setBusy(true); setErr("");
    try {
      const r = await mapi.feedback(ctx.cid, ctx.mid, ctx.index, ctx.learnerId, v);
      setFb(r); done({ score: r.score, response: { text: v } });
    } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  };
  return (
    <div className="m-apply">
      <p className="m-prompt">{card.question}</p>
      <textarea value={v} onChange={(e) => setV(e.target.value)} disabled={!!fb} rows={4} placeholder="Type or speak your answer in your own words…" aria-label="Your answer" />
      {!fb && (
        <div className="m-row">
          {Rec && <button className={`m-btn ghost ${listening ? "rec" : ""}`} onClick={dictate} disabled={listening}>{listening ? "● Listening…" : "🎤 Speak"}</button>}
          <button className="m-btn" disabled={v.trim().length < 8 || busy} onClick={send}>{busy ? "Reading your answer…" : "Get feedback"}</button>
        </div>
      )}
      {err && <div className="m-fb no">{err}</div>}
      {fb && (
        <div className={`m-fb ${fb.score >= 0.7 ? "ok" : "mid"}`}>
          <div className="m-stars" aria-label={`${Math.round(fb.score * 5)} of 5`}>{"★★★★★".slice(0, Math.max(1, Math.round(fb.score * 5)))}<span>{"★★★★★".slice(Math.max(1, Math.round(fb.score * 5)))}</span></div>
          <p>{fb.feedback}</p>
          <details><summary>A stronger version of your answer</summary><p>{fb.better_answer}</p></details>
        </div>
      )}
    </div>
  );
}
