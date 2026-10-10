import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Speaker } from "../speech";
import { Md } from "../ui";

/** A friendly talking tutor: floating avatar, voice in and out, answers from the course sources, hints first. */
export function AvatarTutor({ cid, learnerId, context }: { cid: string; learnerId: string; context?: string }) {
  const [open, setOpen] = useState(false);
  const [talking, setTalking] = useState(false);
  const [msgs, setMsgs] = useState<{ role: string; text: string }[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [speak, setSpeak] = useState(true);
  const sp = useRef(new Speaker());
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);
  useEffect(() => () => sp.current.stop(), []);

  const ask = async (q: string) => {
    if (!q.trim()) return;
    const history = msgs.map((m) => ({ role: m.role === "me" ? "learner" : "tutor", text: m.text }));
    setMsgs((m) => [...m, { role: "me", text: q }]); setText(""); setBusy(true);
    try {
      const r = await api.tutor(cid, { learner_id: learnerId, message: context ? `(I'm looking at: ${context})\n${q}` : q, history });
      const reply = r.reply.replace(/\[e\d+\]/g, "");
      setMsgs((m) => [...m, { role: "tutor", text: reply + (r.followup_question ? `\n\n*${r.followup_question}*` : "") }]);
      if (speak) { setTalking(true); await sp.current.say(reply); setTalking(false); }
    } catch (e) {
      setMsgs((m) => [...m, { role: "tutor", text: `Sorry — I couldn't answer just now (${String(e).slice(0, 80)}).` }]);
    } finally { setBusy(false); }
  };
  const w = window as unknown as { SpeechRecognition?: new () => any; webkitSpeechRecognition?: new () => any }; // eslint-disable-line @typescript-eslint/no-explicit-any
  const Rec = w.SpeechRecognition ?? w.webkitSpeechRecognition;
  const listen = () => {
    if (!Rec) return;
    const r = new Rec(); r.lang = navigator.language || "en-IN";
    r.onresult = (e: any) => ask(e.results[0][0].transcript); // eslint-disable-line @typescript-eslint/no-explicit-any
    r.onend = () => setListening(false); setListening(true); r.start();
  };

  return (
    <>
      {!open && (
        <button className="m-tutor-fab" onClick={() => setOpen(true)} aria-label="Ask Mira, your tutor">
          <Face talking={false} size={52} /><span>Ask Mira</span>
        </button>
      )}
      {open && (
        <aside className="m-tutor" role="dialog" aria-label="Tutor">
          <header>
            <Face talking={talking || busy} size={56} />
            <div><strong>Mira</strong><div className="m-sub small">{busy ? "thinking…" : talking ? "speaking…" : "your study buddy"}</div></div>
            <span style={{ flex: 1 }} />
            <button className="m-icon" onClick={() => { sp.current.stop(); setSpeak(!speak); setTalking(false); }} title="Voice replies" aria-pressed={speak}>{speak ? "🔊" : "🔇"}</button>
            <button className="m-icon" onClick={() => { sp.current.stop(); setOpen(false); }} aria-label="Close">✕</button>
          </header>
          <div className="m-tutor-body">
            {!msgs.length && (
              <div className="m-tutor-intro">
                <p>Hi! I only use your course material, and I'll help you think it through rather than just giving answers.</p>
                {["I don't get this card — explain it simply", "Give me an everyday example", "Quiz me on this"].map((q) => (
                  <button key={q} className="m-chip" onClick={() => ask(q)}>{q}</button>
                ))}
              </div>
            )}
            {msgs.map((m, k) => <div key={k} className={`m-bubble ${m.role === "me" ? "me" : ""}`}><Md text={m.text} /></div>)}
            {busy && <div className="m-bubble"><span className="m-eq"><i /><i /><i /></span></div>}
            <div ref={end} />
          </div>
          <footer>
            {Rec && <button className={`m-icon big ${listening ? "rec" : ""}`} onClick={listen} aria-label="Speak">🎤</button>}
            <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask(text)} placeholder="Ask anything…" aria-label="Message Mira" />
            <button className="m-btn" onClick={() => ask(text)} disabled={busy || !text.trim()}>Send</button>
          </footer>
        </aside>
      )}
    </>
  );
}

export function Face({ talking, size = 48 }: { talking: boolean; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" className={`m-face ${talking ? "talk" : ""}`} aria-hidden>
      <defs><linearGradient id="mf" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#8b7bff" /><stop offset="1" stopColor="#ff8a6b" /></linearGradient></defs>
      <circle cx="32" cy="32" r="30" fill="url(#mf)" />
      <circle cx="32" cy="34" r="21" fill="#fff6ee" />
      <ellipse className="m-eye" cx="24.5" cy="31" rx="2.6" ry="3.2" fill="#2d2350" />
      <ellipse className="m-eye" cx="39.5" cy="31" rx="2.6" ry="3.2" fill="#2d2350" />
      <circle cx="19" cy="38" r="3" fill="#ffb4a2" opacity=".7" /><circle cx="45" cy="38" r="3" fill="#ffb4a2" opacity=".7" />
      <ellipse className="m-mouth" cx="32" cy="42" rx="5" ry="2" fill="#2d2350" />
      <path d="M14 22c4-10 14-14 22-12s12 6 14 12c-8-4-20-6-36 0z" fill="#3b2f7a" />
    </svg>
  );
}
