import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { mapi, useLearner, type Journey as J, type Module } from "./mapi";
import { ServerDown } from "./Player";
import { AvatarTutor } from "./Tutor";

export function Journey() {
  const { cid = "" } = useParams();
  const nav = useNavigate();
  const store = useLearner(cid);
  const [learner, setLearner] = useState(store.read());
  const [j, setJ] = useState<J | null>(null);
  const [name, setName] = useState("");
  const [err, setErr] = useState("");
  useEffect(() => { if (learner) mapi.journey(cid, learner.id).then(setJ).catch((e) => setErr(String(e))); }, [cid, learner]);

  if (!learner) {
    return (
      <main className="m-page m-center">
        <div className="m-welcome">
          <div className="m-kicker">Welcome</div>
          <h1>What should we call you?</h1>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your first name" autoFocus
            onKeyDown={async (e) => { if (e.key === "Enter" && name.trim()) { const l = await api.learner(name.trim()); store.save(l); setLearner(l); } }} aria-label="Your name" />
          <button className="m-btn big" disabled={!name.trim()} onClick={async () => { const l = await api.learner(name.trim()); store.save(l); setLearner(l); }}>Start learning</button>
        </div>
      </main>
    );
  }
  if (err) return <main className="m-page"><ServerDown detail={err} /></main>;
  if (!j) return <main className="m-page"><div className="m-loading" /></main>;
  const cur = j.modules.find((m) => m.state === "review") ?? j.modules.find((m) => m.state === "current");
  const done = j.modules.filter((m) => m.state === "done" || m.state === "review").length;
  return (
    <main className="m-page">
      <section className="m-hero" style={j.cover ? { backgroundImage: `linear-gradient(90deg, rgba(20,16,50,.86), rgba(20,16,50,.35)), url(/media/${j.cover})` } : undefined}>
        <div>
          <div className="m-kicker light">Hi {learner.name} 👋</div>
          <h1>{j.title}</h1>
          <p>{j.promise}</p>
          <div className="m-row">
            {cur && <button className="m-btn big" onClick={() => nav(`/learn/${cid}/m/${cur.id}`)}>{cur.state === "review" ? "Review" : done ? "Continue" : "Start"}: {cur.title} →</button>}
            {!cur && <Link className="m-btn big" to={`/learn/${cid}/practice`}>Practise →</Link>}
          </div>
        </div>
        <div className="m-hero-stats">
          <div><strong>⭐ {j.xp}</strong><span>XP</span></div>
          <div><strong>🔥 {j.streak}</strong><span>day streak</span></div>
          <div><strong>{done}/{j.modules.length}</strong><span>modules</span></div>
        </div>
      </section>

      <div className="m-journey-grid">
        <section>
          <h2 className="m-h2">Your journey</h2>
          <ol className="m-path">
            {j.modules.map((m, k) => (
              <li key={m.id} className={`m-stop ${m.state}`} style={{ marginLeft: `${[0, 60, 110, 60][k % 4]}px` }}>
                <button className="m-node" disabled={m.state === "locked"} onClick={() => nav(`/learn/${cid}/m/${m.id}`)} aria-label={m.title}>
                  {m.state === "done" ? "✓" : m.state === "review" ? "↻" : m.state === "locked" ? "🔒" : k + 1}
                </button>
                <div className="m-stop-text">
                  <strong>{m.title}</strong>
                  <span>{m.goal}</span>
                  <span className="m-meta">{m.minutes} min · {m.cards} cards{m.score != null ? ` · ${Math.round(m.score * 100)}%` : ""}{m.state === "review" ? " · review due" : ""}</span>
                </div>
              </li>
            ))}
          </ol>
        </section>
        <aside className="m-side">
          <Link to={`/learn/${cid}/practice`} className="m-panel link">
            <div className="m-panel-icon">🧠</div>
            <div><strong>Memory deck</strong><span>{j.deck_due ? `${j.deck_due} cards ready to review` : "Nothing due — come back tomorrow"}</span></div>
          </Link>
          <Link to={`/learn/${cid}/practice?mode=time`} className="m-panel link">
            <div className="m-panel-icon">⚡</div>
            <div><strong>Time attack</strong><span>60 seconds of quick true / false</span></div>
          </Link>
          <div className="m-panel">
            <strong>What you know</strong>
            {j.modules.map((m) => (
              <div key={m.id} className="m-know">
                <span>{m.title}</span>
                <div className="m-bar"><div style={{ width: `${Math.round(m.mastery * 100)}%`, background: m.mastered ? "var(--m-good)" : "var(--m-primary)" }} /></div>
              </div>
            ))}
          </div>
        </aside>
      </div>
      <AvatarTutor cid={cid} learnerId={learner.id} />
    </main>
  );
}

export function Practice() {
  const { cid = "" } = useParams();
  const learner = useLearner(cid).read();
  const mode = new URLSearchParams(window.location.search).get("mode") === "time" ? "time" : "deck";
  if (!learner) return <main className="m-page"><div className="m-empty">Start from the <Link to={`/learn/${cid}`}>course page</Link>.</div></main>;
  return (
    <main className="m-page">
      <div className="m-row" style={{ marginBottom: 16 }}>
        <Link className="m-btn ghost" to={`/learn/${cid}`}>← Journey</Link>
        <Link className={`m-tab ${mode === "deck" ? "on" : ""}`} to={`/learn/${cid}/practice`}>🧠 Memory deck</Link>
        <Link className={`m-tab ${mode === "time" ? "on" : ""}`} to={`/learn/${cid}/practice?mode=time`}>⚡ Time attack</Link>
      </div>
      {mode === "deck" ? <Deck cid={cid} lid={learner.id} /> : <TimeAttack cid={cid} lid={learner.id} />}
    </main>
  );
}

function Deck({ cid, lid }: { cid: string; lid: string }) {
  const [cards, setCards] = useState<{ key: string; module: string; front: string; back: string }[] | null>(null);
  const [flip, setFlip] = useState(false);
  const [all, setAll] = useState(false);
  useEffect(() => { mapi.deck(cid, lid, all).then(setCards); }, [cid, lid, all]);
  if (!cards) return <div className="m-loading" />;
  if (!cards.length)
    return (
      <div className="m-empty">
        <h2>All caught up 🎉</h2>
        <p>Cards come back when you're about to forget them. Finish more modules to fill your deck.</p>
        <button className="m-btn ghost" onClick={() => setAll(true)}>Review all cards anyway</button>
      </div>
    );
  const c = cards[0];
  const rate = async (r: string) => { await mapi.rate(cid, lid, c.key, r); setFlip(false); setCards(cards.slice(1)); };
  return (
    <div className="m-deck">
      <div className="m-sub">{cards.length} to go · {c.module}</div>
      <div className={`m-flash ${flip ? "flip" : ""}`} onClick={() => setFlip(!flip)} role="button" tabIndex={0} onKeyDown={(e) => e.key === " " && setFlip(!flip)}>
        <div className="m-flash-in"><div className="m-face-front">{c.front}<small>tap to flip</small></div><div className="m-face-back">{c.back}</div></div>
      </div>
      {flip ? (
        <div className="m-row center">
          <button className="m-btn ghost" onClick={() => rate("again")}>Forgot</button>
          <button className="m-btn ghost" onClick={() => rate("hard")}>Hard</button>
          <button className="m-btn" onClick={() => rate("good")}>Got it</button>
          <button className="m-btn ghost" onClick={() => rate("easy")}>Easy</button>
        </div>
      ) : <div className="m-sub center">Say the answer in your head, then flip.</div>}
    </div>
  );
}

function TimeAttack({ cid, lid }: { cid: string; lid: string }) {
  const [pool, setPool] = useState<{ text: string; is_true: boolean; why: string }[] | null>(null);
  const [left, setLeft] = useState(60);
  const [i, setI] = useState(0);
  const [score, setScore] = useState(0);
  const [flash, setFlash] = useState<"" | "ok" | "no">("");
  const [started, setStarted] = useState(false);
  useEffect(() => {
    (async () => {
      const j = await mapi.journey(cid, lid);
      const mods: Module[] = await Promise.all(j.modules.filter((m) => m.state !== "locked").map((m) => mapi.module(cid, m.id)));
      const st = mods.flatMap((m) => m.cards.flatMap((c) => c.statements ?? []));
      setPool(st.sort(() => Math.random() - 0.5));
    })();
  }, [cid, lid]);
  useEffect(() => {
    if (!started || left <= 0) return;
    const t = window.setTimeout(() => setLeft(left - 1), 1000);
    return () => window.clearTimeout(t);
  }, [started, left]);
  const best = useMemo(() => Number(localStorage.getItem(`ta:${cid}`) ?? 0), [cid, left === 0]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!pool) return <div className="m-loading" />;
  if (!pool.length) return <div className="m-empty">Finish a module first — its quick facts become your time-attack questions.</div>;
  if (!started) return (
    <div className="m-empty"><h2>⚡ Time attack</h2><p>As many true/false as you can in 60 seconds.</p>
      <button className="m-btn big" onClick={() => setStarted(true)}>Go!</button></div>
  );
  if (left <= 0) {
    if (score > best) localStorage.setItem(`ta:${cid}`, String(score));
    return (
      <div className="m-empty"><h2>Time! {score} correct</h2><p>{score > best ? "New personal best 🎉" : `Best: ${best}`}</p>
        <button className="m-btn" onClick={() => { setLeft(60); setScore(0); setI(0); setPool([...pool].sort(() => Math.random() - 0.5)); }}>Play again</button></div>
    );
  }
  const s = pool[i % pool.length];
  const answer = (v: boolean) => {
    const ok = v === s.is_true;
    if (ok) setScore(score + 1);
    setFlash(ok ? "ok" : "no"); window.setTimeout(() => setFlash(""), 250);
    setI(i + 1);
  };
  return (
    <div className={`m-ta ${flash}`}>
      <div className="m-row spread"><strong>⏱ {left}s</strong><strong>✓ {score}</strong></div>
      <div className="m-timer"><div style={{ width: `${(left / 60) * 100}%` }} /></div>
      <div className="m-tf-card big">{s.text}</div>
      <div className="m-tf-btns"><button className="m-btn false" onClick={() => answer(false)}>✗ False</button><button className="m-btn true" onClick={() => answer(true)}>✓ True</button></div>
    </div>
  );
}
