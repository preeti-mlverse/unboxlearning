import { useEffect, useRef, useState } from "react";
import { Speaker } from "../speech";
import { Md } from "../ui";
import { SubmitBar, type RProps } from "./common";

type Scene = { heading: string; narration: string; visual: string; bullets: string[]; code: string;
  figure_element_id: string; media_path?: string; seconds: number };

function Visual({ s, k }: { s: Scene; k: number }) {
  const anim = { animation: "sceneIn .5s ease both" };
  if (s.visual === "title")
    return <div key={k} style={{ ...anim, textAlign: "center", padding: "40px 20px" }}><div style={{ fontSize: 30, fontWeight: 700 }}>{s.heading}</div>
      {s.bullets[0] && <div className="muted" style={{ fontSize: 18, marginTop: 8 }}>{s.bullets[0]}</div>}</div>;
  if (s.visual === "flow")
    return (
      <div key={k} className="row" style={{ ...anim, justifyContent: "center", gap: 6, padding: 20 }}>
        {s.bullets.map((b, i) => (
          <span key={i} className="row" style={{ gap: 6, animation: `sceneIn .5s ${i * 0.35}s ease both` }}>
            <span className="card flat" style={{ padding: "10px 14px", fontWeight: 600, background: "var(--primary-soft)" }}>{b}</span>
            {i < s.bullets.length - 1 && <span style={{ fontSize: 20, color: "var(--primary)" }}>→</span>}
          </span>
        ))}
      </div>
    );
  if (s.visual === "code") return <div key={k} style={anim}><pre><code>{s.code}</code></pre></div>;
  if (s.visual === "figure" && s.media_path)
    return <div key={k} style={{ ...anim, textAlign: "center" }}><img src={`/media/${s.media_path}`} alt={s.heading} style={{ maxWidth: "100%", maxHeight: 300, borderRadius: 8 }} /></div>;
  if (s.visual === "quote")
    return <blockquote key={k} style={{ ...anim, fontSize: 20, fontStyle: "italic", padding: 20 }}>{s.bullets[0] ?? s.heading}</blockquote>;
  if (s.visual === "comparison")
    return (
      <table key={k} style={anim}><tbody>{s.bullets.map((b, i) => {
        const [l, r] = b.split("|").map((x) => x.trim());
        return <tr key={i} style={{ animation: `sceneIn .5s ${i * 0.3}s ease both` }}><td>{l}</td><td>{r ?? ""}</td></tr>;
      })}</tbody></table>
    );
  return (
    <ul key={k} style={{ fontSize: 18, lineHeight: 1.8, paddingLeft: 24 }}>
      {s.bullets.map((b, i) => <li key={i} style={{ animation: `sceneIn .5s ${i * 0.4}s ease both` }}><Md text={b} inline /></li>)}
    </ul>
  );
}

export function VideoLesson({ a, locked, review, submit, busy }: RProps) {
  const p = a.data.payload;
  const scenes = p.scenes as Scene[];
  const [i, setI] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [done, setDone] = useState(review);
  const [captions, setCaptions] = useState(true);
  const speaker = useRef(new Speaker());
  const run = useRef(0);

  useEffect(() => () => speaker.current.stop(), []);
  useEffect(() => {
    if (!playing) return;
    const token = ++run.current;
    const s = scenes[i];
    (async () => {
      const t0 = Date.now();
      await speaker.current.say(s.narration);
      const min = Math.max(2, Math.min(15, s.seconds || 5)) * 1000 * (speaker.current.providerOk || "speechSynthesis" in window ? 0.3 : 1);
      const wait = Math.max(0, min - (Date.now() - t0));
      await new Promise((r) => setTimeout(r, wait + 400));
      if (token !== run.current) return;
      if (i + 1 < scenes.length) setI(i + 1);
      else { setPlaying(false); setDone(true); }
    })();
  }, [playing, i]); // eslint-disable-line react-hooks/exhaustive-deps

  const go = (n: number) => { speaker.current.stop(); run.current++; setI(Math.max(0, Math.min(scenes.length - 1, n))); };
  const toggle = () => { if (playing) { speaker.current.stop(); run.current++; setPlaying(false); } else setPlaying(true); };
  const s = scenes[i];
  return (
    <div className="stack">
      <style>{`@keyframes sceneIn { from { opacity: 0; transform: translateY(10px) } to { opacity: 1; transform: none } }`}</style>
      <div className="card flat" style={{ minHeight: 280, display: "flex", flexDirection: "column", justifyContent: "center", background: "linear-gradient(180deg,#fff,#f4f3ff)" }}>
        {s.visual !== "title" && <div className="stage-pill" style={{ marginBottom: 6 }}>{s.heading}</div>}
        <Visual s={s} k={i} />
      </div>
      {captions && <div className="notice" style={{ fontSize: 15 }} aria-live="polite">{s.narration}</div>}
      <div className="spread">
        <div className="row" style={{ gap: 6 }}>
          <button className="btn sm" onClick={() => go(i - 1)} disabled={i === 0} aria-label="Previous scene">⏮</button>
          <button className="btn primary sm" onClick={toggle}>{playing ? "⏸ Pause" : i === 0 && !done ? "▶ Play" : "▶ Resume"}</button>
          <button className="btn sm" onClick={() => go(i + 1)} disabled={i === scenes.length - 1} aria-label="Next scene">⏭</button>
          <button className={`btn sm ${captions ? "" : "ghost"}`} onClick={() => setCaptions(!captions)}>CC</button>
        </div>
        <div className="row" style={{ gap: 4 }}>
          {scenes.map((_, k) => <span key={k} onClick={() => go(k)} style={{ width: 22, height: 6, borderRadius: 3, cursor: "pointer", background: k <= i ? "var(--primary)" : "var(--line)" }} />)}
        </div>
      </div>
      {(done || review) && p.summary && <div className="notice good"><strong>In short: </strong><Md text={p.summary} inline /></div>}
      {!locked && <SubmitBar label={done ? "Continue" : "Skip & continue"} onClick={() => { speaker.current.stop(); submit({ viewed: true, completed: done }); }} busy={busy} />}
    </div>
  );
}
