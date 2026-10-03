import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { ActivityPlayer } from "../ActivityPlayer";
import { api, LANGUAGES, type Activity, type Course, type Curriculum, type Json } from "../api";
import { CiteList, ErrorNote, Md, Progress, Spinner } from "../ui";

type Prog = Awaited<ReturnType<typeof api.progress>>;

export function Learn() {
  const { id = "" } = useParams();
  const key = `learner:${id}`;
  const [learner, setLearner] = useState<{ id: string; name: string } | null>(() => {
    try { return JSON.parse(localStorage.getItem(key) ?? "null"); } catch { return null; }
  });
  const [name, setName] = useState("");
  const [course, setCourse] = useState<Course | null>(null);
  const [prog, setProg] = useState<Prog | null>(null);
  const [step, setStep] = useState<Awaited<ReturnType<typeof api.next>> | null>(null);
  const [stepNo, setStepNo] = useState(0);
  const [answered, setAnswered] = useState(false);
  const [lastMastery, setLastMastery] = useState<Json | null>(null);
  const [tutorOpen, setTutorOpen] = useState(false);
  const [err, setErr] = useState("");
  const [lang, setLang] = useState<string>(() => { try { return localStorage.getItem(`lang:${id}`) ?? ""; } catch { return ""; } });
  const [cur, setCur] = useState<Curriculum | null>(null);
  const [langs, setLangs] = useState<string[]>([]);

  useEffect(() => { api.course(id).then(setCourse).catch((e) => setErr(String(e))); }, [id]);
  useEffect(() => {
    api.learnCurriculum(id, lang || undefined).then((r) => { setCur(r.curriculum); setLangs(r.languages); }).catch(() => {});
    try { localStorage.setItem(`lang:${id}`, lang); } catch { /* storage unavailable */ }
  }, [id, lang]);
  const refresh = useCallback(async () => {
    if (!learner) return;
    const [n, p] = await Promise.all([api.next(id, learner.id, lang || undefined), api.progress(id, learner.id)]);
    setStep(n); setProg(p); setAnswered(false); setLastMastery(null); setStepNo((k) => k + 1);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [id, learner, lang]);
  useEffect(() => { refresh().catch((e) => setErr(String(e))); }, [refresh]);

  if (err) return <main className="page"><ErrorNote error={err} /></main>;
  if (!course) return <main className="page"><Spinner /></main>;

  if (!learner) {
    return (
      <main className="page" style={{ maxWidth: 520 }}>
        <div className="card stack">
          <h1>{cur?.course_title ?? course.title}</h1>
          {cur?.learner_promise && <p className="muted" style={{ fontSize: 17 }}>{cur.learner_promise}</p>}
          <label htmlFor="nm">Your name</label>
          <input id="nm" value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && name.trim() && start()} autoFocus />
          <button className="btn primary" disabled={!name.trim()} onClick={start}>Start learning</button>
        </div>
      </main>
    );
  }
  async function start() {
    const l = await api.learner(name);
    localStorage.setItem(key, JSON.stringify(l));
    setLearner(l);
  }

  const mastered = prog?.objectives.filter((o) => o.state === "mastered" || o.state === "review_due").length ?? 0;
  const total = prog?.objectives.length ?? 0;
  const objective = cur?.objectives.find((o) => o.id === step?.objective_id);
  const banner = step?.mode === "review" ? "Spaced review — recalling this now makes it stick."
    : step?.mode === "remediate" ? "Let's try this one again — you're close. Use the tutor if you get stuck."
    : step?.mode === "reteach" ? "Let's look at the idea once more before trying again." : "";

  return (
    <main className="page">
      <div className="learn-layout">
        <aside className="stack" style={{ alignSelf: "start", position: "sticky", top: 70 }}>
          <div className="card stack">
            <strong>{cur?.course_title}</strong>
            <div className="small muted">{learner.name} · {mastered}/{total} mastered</div>
            <Progress value={total ? mastered / total : 0} />
          </div>
          <div className="card" style={{ padding: 10, maxHeight: "65vh", overflowY: "auto" }}>
            {cur?.modules.map((m) => (
              <div key={m.id} style={{ marginBottom: 8 }}>
                <div className="tiny faint" style={{ padding: "4px 8px", textTransform: "uppercase", letterSpacing: ".05em" }}>{m.title}</div>
                {m.objective_ids.map((oid) => {
                  const o = prog?.objectives.find((x) => x.objective_id === oid);
                  return (
                    <div key={oid} className={`path-obj ${oid === step?.objective_id ? "current" : ""}`} title={o ? `mastery ${Math.round(o.p * 100)}%` : ""}>
                      <span className={`dot ${o?.state ?? ""}`} /><span>{cur?.objectives.find((x) => x.id === oid)?.statement ?? o?.statement}</span>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
          {langs.length > 0 && (
            <select value={lang} onChange={(e) => setLang(e.target.value)} aria-label="Course language">
              <option value="">Original language</option>
              {langs.map((l) => <option key={l} value={l}>{LANGUAGES.find(([k]) => k === l)?.[1] ?? l}</option>)}
            </select>
          )}
          <button className="btn ghost sm" onClick={() => { localStorage.removeItem(key); setLearner(null); }}>Switch learner</button>
        </aside>
        <section className="stack">
          {!step ? <Spinner /> : step.mode === "assessment" && step.assessment ? (
            <AssessmentRunner courseId={id} learnerId={learner.id} a={step.assessment} onDone={refresh} />
          ) : step.mode === "done" || !step.activity ? (
            <div className="card empty">
              <h2>{total && mastered === total ? "🎉 You've mastered everything in this course" : "You're all caught up"}</h2>
              <p>Come back later — the engine will bring objectives back for review just before you'd forget them.</p>
              {!!step?.needs_help?.length && (
                <div className="notice warn" style={{ textAlign: "left" }}>
                  <strong>Worth a conversation with your teacher or the tutor:</strong>
                  <ul style={{ margin: "4px 0 0", paddingLeft: 20 }}>
                    {step.needs_help.map((oid) => <li key={oid}>{cur?.objectives.find((o) => o.id === oid)?.statement}</li>)}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <>
              {banner && <div className="notice">{banner}</div>}
              {objective && (
                <div className="small muted">Objective: <strong style={{ color: "var(--ink)" }}>{objective.statement}</strong></div>
              )}
              <ActivityPlayer key={`${step.activity.id}:${stepNo}:${lang}`} activity={step.activity} learnerId={learner.id} lang={lang || undefined}
                onResult={(r) => { setAnswered(true); setLastMastery(r.mastery); }} />
              <div className="spread">
                {step.arm !== "static" ? <button className="btn" onClick={() => setTutorOpen(true)}>💬 Ask the tutor</button> : <span />}
                {answered && (
                  <div className="row">
                    {lastMastery && <span className="small muted">Mastery of this objective: {Math.round(lastMastery.p * 100)}%</span>}
                    <button className="btn primary" onClick={refresh}>Continue →</button>
                  </div>
                )}
              </div>
            </>
          )}
        </section>
      </div>
      {tutorOpen && <Tutor courseId={id} learnerId={learner.id} activity={step?.activity ?? null} answered={answered} lang={lang || undefined} onClose={() => setTutorOpen(false)} />}
    </main>
  );
}

function Tutor({ courseId, learnerId, activity, answered, onClose, lang }: {
  courseId: string; learnerId: string; activity: Activity | null; answered: boolean; onClose: () => void; lang?: string;
}) {
  const [history, setHistory] = useState<{ role: string; text: string; move?: string; citations?: string[] }[]>([]);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [history, busy]);
  const send = async (text = msg) => {
    if (!text.trim()) return;
    const h = [...history, { role: "learner", text }];
    setHistory(h); setMsg(""); setBusy(true); setErr("");
    try {
      const r = await api.tutor(courseId, { learner_id: learnerId, message: text, history, activity_id: activity?.id, answered, lang });
      setHistory([...h, { role: "tutor", text: r.reply + (r.followup_question ? `\n\n*${r.followup_question}*` : ""), move: r.move, citations: r.citations }]);
    } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  };
  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label="Tutor">
        <div className="drawer-head"><strong>Tutor</strong><button className="btn ghost sm" onClick={onClose}>Close</button></div>
        <div className="drawer-body col" style={{ gap: 10 }}>
          {!history.length && (
            <div className="stack">
              <div className="small muted">I answer from this course's sources and help you reason it out rather than just giving answers.</div>
              {["I'm stuck — can you give me a hint?", "Can you explain this another way?", "Why does this matter in practice?"].map((q) => (
                <button key={q} className="opt" onClick={() => send(q)}>{q}</button>
              ))}
            </div>
          )}
          {history.map((m, i) => (
            <div key={i} className={`bubble ${m.role === "learner" ? "me" : "them"}`}>
              <Md text={m.text} />
              {m.role === "tutor" && !!m.citations?.length && <div style={{ marginTop: 4 }}><CiteList ids={m.citations} /></div>}
              {m.move === "not_in_sources" && <div className="tiny faint">Not covered by the course sources</div>}
            </div>
          ))}
          {busy && <div className="bubble them"><Spinner /></div>}
          <ErrorNote error={err} />
          <div ref={end} />
        </div>
        <div style={{ padding: 12, borderTop: "1px solid var(--line)", flexWrap: "nowrap" }} className="row">
          <MicButton onText={(t) => send(t)} />
          <input value={msg} onChange={(e) => setMsg(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} placeholder="Ask anything about this course…" aria-label="Message the tutor" style={{ flex: 1 }} />
          <button className="btn primary" onClick={() => send()} disabled={busy || !msg.trim()}>Send</button>
        </div>
      </aside>
    </>
  );
}

/** Speak to the tutor. Uses the browser's built-in speech recognition (Chrome/Edge); hidden where unsupported. */
function MicButton({ onText }: { onText: (t: string) => void }) {
  const [on, setOn] = useState(false);
  const w = window as unknown as { SpeechRecognition?: new () => Json; webkitSpeechRecognition?: new () => Json };
  const Rec = w.SpeechRecognition ?? w.webkitSpeechRecognition;
  if (!Rec) return null;
  const start = () => {
    const r = new Rec();
    r.lang = navigator.language || "en-US";
    r.interimResults = false;
    r.onresult = (e: Json) => onText(e.results[0][0].transcript);
    r.onend = () => setOn(false);
    r.onerror = () => setOn(false);
    setOn(true);
    r.start();
  };
  return <button className={`btn ${on ? "primary" : ""}`} onClick={start} disabled={on} title="Speak your question" aria-label="Speak your question">{on ? "● Listening" : "🎤"}</button>;
}


function AssessmentRunner({ courseId, learnerId, a, onDone }: { courseId: string; learnerId: string; a: Json; onDone: () => void }) {
  const [answers, setAnswers] = useState<Record<string, number[]>>({});
  const [result, setResult] = useState<Json | null>(null);
  const [err, setErr] = useState("");
  const label = { pre: "Before you start", post: "Final check", delayed: "Retention check" }[a.kind as string] ?? "Check";
  const send = async () => {
    try {
      const r = await fetch(`/api/courses/${courseId}/assessments/${a.id}/submit`, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ learner_id: learnerId, answers }) });
      if (!r.ok) throw new Error((await r.json()).detail);
      setResult(await r.json());
    } catch (e) { setErr(String(e)); }
  };
  if (result) return (
    <div className="card stack" style={{ textAlign: "center" }}>
      <h2>{label}: {result.correct} / {result.total}</h2>
      <p className="muted">{a.kind === "pre" ? "This just shows where you're starting from — no pressure. Your course adapts to you from here." : "Thanks — this helps measure how well the course works."}</p>
      <div><button className="btn primary" onClick={onDone}>Continue →</button></div>
    </div>
  );
  return (
    <div className="card stack">
      <div className="stage-pill">{label}</div>
      <h2 style={{ margin: 0 }}>{a.name}</h2>
      <div className="small muted">{a.items.length} questions. Answer on your own — no hints or feedback during this check.</div>
      {a.items.map((it: Json, i: number) => (
        <div key={it.id}>
          <strong>{i + 1}. {it.question}</strong>
          <div style={{ marginTop: 6 }}>
            {it.options.map((o: Json, j: number) => (
              <button key={j} className={`opt ${(answers[it.id] ?? []).includes(j) ? "sel" : ""}`}
                onClick={() => setAnswers((prev) => ({ ...prev, [it.id]: [j] }))}>
                <span className="opt-mark" /><span style={{ flex: 1 }}>{o.text}</span>
              </button>
            ))}
          </div>
        </div>
      ))}
      <ErrorNote error={err} />
      <div><button className="btn primary" disabled={Object.keys(answers).length < a.items.length} onClick={send}>Submit</button></div>
    </div>
  );
}
