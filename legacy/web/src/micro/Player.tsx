import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { CardView, GAME_LABEL, type Result } from "./Cards";
import { mapi, useLearner, type Module } from "./mapi";
import { AvatarTutor } from "./Tutor";

export function Player() {
  const { cid = "", mid = "" } = useParams();
  const nav = useNavigate();
  const learner = useLearner(cid).read();
  const [m, setM] = useState<Module | null>(null);
  const [i, setI] = useState(0);
  const [ready, setReady] = useState(false);
  const [xp, setXp] = useState<number | null>(null);
  const [gain, setGain] = useState(0);
  const [summary, setSummary] = useState<{ score: number | null; xp: number; mastery: number; streak: number } | null>(null);
  const [scores, setScores] = useState<number[]>([]);
  const [voice, setVoice] = useState(() => localStorage.getItem("autoVoice") === "1");
  const [next, setNext] = useState<string | null>(null);

  const [loadErr, setLoadErr] = useState("");
  useEffect(() => {
    setLoadErr("");
    mapi.module(cid, mid).then((x) => { setM(x); setI(0); setSummary(null); setScores([]); })
      .catch((e) => setLoadErr(String(e)));
  }, [cid, mid]);
  useEffect(() => {
    if (!learner) return;
    mapi.journey(cid, learner.id).then((j) => {
      setXp(j.xp);
      const k = j.modules.findIndex((x) => x.id === mid);
      setNext(j.modules[k + 1]?.id ?? null);
    }).catch(() => {});
  }, [cid, mid]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!learner) return <main className="m-page"><div className="m-empty">Please start from the <Link to={`/learn/${cid}`}>course page</Link>.</div></main>;
  if (loadErr) return <main className="m-page"><ServerDown detail={loadErr} /></main>;
  if (!m) return <main className="m-page"><div className="m-loading" /></main>;
  const card = m.cards[i];

  const done = async (r: Result | null) => {
    setReady(true);
    if (!r) return;
    setScores((s) => [...s, r.score]);
    try {
      const p = await mapi.progress(cid, { learner_id: learner.id, module_id: mid, card_index: i, score: r.score, response: r.response });
      setXp(p.xp); if (p.gained) { setGain(p.gained); window.setTimeout(() => setGain(0), 1200); }
    } catch { /* offline: keep going */ }
  };
  const advance = async () => {
    setReady(false);
    if (i + 1 < m.cards.length) { setI(i + 1); window.scrollTo({ top: 0 }); return; }
    setSummary(await mapi.complete(cid, mid, learner.id));
  };

  if (summary) {
    const pct = summary.score == null ? null : Math.round(summary.score * 100);
    return (
      <main className="m-page m-center">
        <div className="m-summary">
          <div className="m-confetti" aria-hidden>{Array.from({ length: 24 }, (_, k) => <i key={k} style={{ left: `${(k * 37) % 100}%`, animationDelay: `${(k % 8) * 0.12}s` }} />)}</div>
          <div className="m-trophy">🏅</div>
          <h1>Module complete!</h1>
          <p className="m-sub">{m.goal}</p>
          <div className="m-stats">
            {pct !== null && <div><strong>{pct}%</strong><span>score</span></div>}
            <div><strong>{summary.xp}</strong><span>XP</span></div>
            <div><strong>{summary.streak}🔥</strong><span>day streak</span></div>
          </div>
          <p className="m-sub small">{m.flashcards.length} memory cards added — we'll bring them back just before you'd forget.</p>
          <div className="m-row center">
            <Link className="m-btn ghost" to={`/learn/${cid}`}>Back to journey</Link>
            {next ? <button className="m-btn" onClick={() => nav(`/learn/${cid}/m/${next}`)}>Next module →</button>
              : <Link className="m-btn" to={`/learn/${cid}/practice`}>Practise what you learned →</Link>}
          </div>
        </div>
      </main>
    );
  }

  const isGame = !["hook", "concept", "example", "recap"].includes(card.kind);
  return (
    <main className="m-player">
      <header className="m-player-top">
        <Link to={`/learn/${cid}`} className="m-x" aria-label="Close">✕</Link>
        <div className="m-progress" aria-label={`Card ${i + 1} of ${m.cards.length}`}><div style={{ width: `${((i + (ready ? 1 : 0)) / m.cards.length) * 100}%` }} /></div>
        <button className={`m-voice ${voice ? "on" : ""}`} onClick={() => { const v = !voice; setVoice(v); localStorage.setItem("autoVoice", v ? "1" : "0"); }}
          title="Read cards aloud automatically" aria-pressed={voice}>{voice ? "🔊" : "🔈"}</button>
        <div className="m-xp">⭐ {xp ?? 0}{gain > 0 && <span className="m-gain">+{gain}</span>}</div>
      </header>
      <section className={`m-card ${isGame ? "game" : ""}`} key={i}>
        <CardView card={card} seed={`${mid}-${i}`} done={done} autoVoice={voice} ctx={{ cid, mid, index: i, learnerId: learner.id }} />
      </section>
      <footer className="m-player-foot">
        <span className="m-foot-label">{m.title} · {isGame ? GAME_LABEL[card.kind] : `${i + 1} / ${m.cards.length}`}</span>
        <button className="m-btn big" disabled={!ready} onClick={advance}>{i + 1 === m.cards.length ? "Finish" : "Continue"}</button>
      </footer>
      <AvatarTutor cid={cid} learnerId={learner.id} context={`${m.title} — card: ${card.title}. ${card.text}`} />
      {scores.length === 0 && <span hidden />}
    </main>
  );
}

export function ServerDown({ detail }: { detail: string }) {
  return (
    <div className="m-empty">
      <h2>Can't reach the course server</h2>
      <p>UnboxEd isn't responding. Start it with <strong>start.bat</strong> in the platform folder, then reload this page.</p>
      <p className="m-sub small">{detail}</p>
      <button className="m-btn" onClick={() => location.reload()}>Try again</button>
    </div>
  );
}
