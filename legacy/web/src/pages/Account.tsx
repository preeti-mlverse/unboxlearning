// Log in, sign up, the role-based dashboard, and the signed-out welcome page.
import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { authApi, useAuth, type CourseCard, type Dashboard } from "../auth";

const ROLES: [string, string, string][] = [
  ["learner", "Learner", "I want to learn something"],
  ["educator", "Educator", "I teach or train people"],
  ["school", "School or university", "For our institution"],
  ["ngo", "NGO or public program", "For learners in the field"],
  ["organization", "Organization", "Training for our team or customers"],
];
const ROLE_LABEL: Record<string, string> = Object.fromEntries(ROLES.map(([k, t]) => [k, t]));

function safeNext(next: string | null) { return next && next.startsWith("/") && !next.startsWith("//") ? next : "/dashboard"; }

export function Login() {
  const { user, setUser } = useAuth();
  const nav = useNavigate();
  const [q] = useSearchParams();
  const [id, setId] = useState("");
  const [pw, setPw] = useState("");
  const [show, setShow] = useState(false);
  const [remember, setRemember] = useState(true);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [resetMode, setResetMode] = useState(false);
  const [resetMsg, setResetMsg] = useState("");
  if (user) return <Navigate to={safeNext(q.get("next"))} replace />;
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setErr("");
    if (!id.trim() || !pw) { setErr("Enter your email or mobile and your password."); return; }
    setBusy(true);
    try { const r = await authApi.login(id.trim(), pw, remember); setUser(r.user); nav(safeNext(q.get("next")), { replace: true }); }
    catch (x) { setErr(String((x as Error).message)); } finally { setBusy(false); }
  };
  if (resetMode) {
    return (
      <main className="m-page narrow auth-page">
        <form className="auth-box" onSubmit={async (e) => { e.preventDefault(); const r = await authApi.reset(id); setResetMsg(r.message); }}>
          <h1>Reset your password</h1>
          <label>Email<input type="email" value={id} onChange={(e) => setId(e.target.value)} required autoComplete="email" /></label>
          <button className="m-btn big" type="submit">Send reset link</button>
          {resetMsg && <div className="m-fb mid">{resetMsg}</div>}
          <button type="button" className="link-btn" onClick={() => setResetMode(false)}>← Back to log in</button>
        </form>
      </main>
    );
  }
  return (
    <main className="m-page narrow auth-page">
      <form className="auth-box" onSubmit={submit} noValidate>
        <h1>Log in</h1>
        <p className="m-sub">Welcome back to UnboxEd.</p>
        <label>Email or mobile<input value={id} onChange={(e) => setId(e.target.value)} autoComplete="username" placeholder="you@example.com or 98765 43210" /></label>
        <label>Password
          <span className="pw"><input type={show ? "text" : "password"} value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="current-password" />
            <button type="button" onClick={() => setShow(!show)}>{show ? "Hide" : "Show"}</button></span>
        </label>
        <div className="auth-row">
          <label className="check"><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} /> Keep me logged in</label>
          <button type="button" className="link-btn" onClick={() => setResetMode(true)}>Forgot password?</button>
        </div>
        {err && <div className="m-fb no">{err}</div>}
        <button className="m-btn big" type="submit" disabled={busy}>{busy ? "Logging in…" : "Log in"}</button>
        <p className="m-sub">New here? <Link to={`/signup${q.get("next") ? `?next=${encodeURIComponent(q.get("next")!)}` : ""}`}>Create an account</Link></p>
      </form>
    </main>
  );
}

export function Signup() {
  const { user, setUser } = useAuth();
  const nav = useNavigate();
  const [q] = useSearchParams();
  const [step, setStep] = useState(1);
  const [role, setRole] = useState("");
  const [f, setF] = useState({ name: "", email: "", phone: "", org: "", password: "", language: "en" });
  const [show, setShow] = useState(false);
  const [agree, setAgree] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to={safeNext(q.get("next"))} replace />;
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const strength = f.password.length >= 12 && /\d/.test(f.password) ? "Strong" : f.password.length >= 8 ? "OK" : f.password ? "Too short" : "";
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setErr("");
    if (!agree) { setErr("Please agree to the Terms and Privacy policy."); return; }
    setBusy(true);
    try { const r = await authApi.signup({ ...f, role }); setUser(r.user); nav(safeNext(q.get("next")), { replace: true }); }
    catch (x) { setErr(String((x as Error).message)); } finally { setBusy(false); }
  };
  return (
    <main className="m-page narrow auth-page">
      <div className="auth-box">
        <ol className="auth-steps"><li className={step === 1 ? "on" : "done"}>1 · You</li><li className={step === 2 ? "on" : ""}>2 · Details</li></ol>
        {step === 1 ? (
          <>
            <h1>Who's signing up?</h1>
            <div className="role-grid">
              {ROLES.map(([k, t, s]) => (
                <button key={k} type="button" className={`m-choice ${role === k ? "on" : ""}`} onClick={() => setRole(k)}><strong>{t}</strong><span>{s}</span></button>
              ))}
            </div>
            <button className="m-btn big" disabled={!role} onClick={() => setStep(2)}>Continue →</button>
            <p className="m-sub">Already have an account? <Link to="/login">Log in</Link></p>
          </>
        ) : (
          <form onSubmit={submit} className="auth-form" noValidate>
            <h1>Your details</h1>
            <p className="m-sub">Signing up as <b>{ROLE_LABEL[role]}</b> · <button type="button" className="link-btn" onClick={() => setStep(1)}>change</button></p>
            <label>Full name<input value={f.name} onChange={set("name")} autoComplete="name" required /></label>
            <label>Email<input type="email" value={f.email} onChange={set("email")} autoComplete="email" required /></label>
            <label>Mobile (optional)<span className="pw"><b className="cc">+91</b><input value={f.phone} onChange={set("phone")} inputMode="numeric" maxLength={11} placeholder="10-digit number" /></span></label>
            {role !== "learner" && <label>Organisation<input value={f.org} onChange={set("org")} placeholder="School, NGO or company name" /></label>}
            <label>Language
              <select value={f.language} onChange={set("language")}>
                <option value="en">English</option><option value="hi">हिन्दी Hindi</option><option value="ta">தமிழ் Tamil</option><option value="te">తెలుగు Telugu</option>
                <option value="bn">বাংলা Bengali</option><option value="mr">मराठी Marathi</option><option value="es">Español</option><option value="fr">Français</option><option value="ar">العربية Arabic</option>
              </select>
            </label>
            <label>Create a password
              <span className="pw"><input type={show ? "text" : "password"} value={f.password} onChange={set("password")} autoComplete="new-password" />
                <button type="button" onClick={() => setShow(!show)}>{show ? "Hide" : "Show"}</button></span>
              {strength && <small className={`pw-hint ${strength === "Too short" ? "bad" : "good"}`}>{strength === "Too short" ? "At least 8 characters" : `${strength} password`}</small>}
            </label>
            <label className="check"><input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} /> I agree to the <a href="https://unboxlearning.in/terms/" target="_blank" rel="noreferrer">Terms</a> and <a href="https://unboxlearning.in/privacy/" target="_blank" rel="noreferrer">Privacy policy</a></label>
            {err && <div className="m-fb no">{err}</div>}
            <button className="m-btn big" type="submit" disabled={busy}>{busy ? "Creating your account…" : "Create my account"}</button>
          </form>
        )}
      </div>
    </main>
  );
}

function Cover({ c }: { c: CourseCard }) {
  return <div className="dash-cover" style={c.cover ? { backgroundImage: `url(/media/${c.cover})` } : undefined}>{!c.cover && <span>{c.title.slice(0, 1)}</span>}</div>;
}

function statusOf(c: CourseCard) {
  if (c.status === "building" || c.status === "analysing") return ["Building…", "mid"];
  if (c.outline === "outline") return ["Outline ready", "mid"];
  if (c.published) return ["Published", "ok"];
  if (c.modules) return ["Ready · not published", ""];
  return ["Draft", ""];
}

export function DashboardPage() {
  const { user } = useAuth();
  const [d, setD] = useState<Dashboard | null>(null);
  const [err, setErr] = useState("");
  const load = () => authApi.dashboard().then(setD).catch((e) => setErr(String(e.message)));
  useEffect(() => { if (user) load(); }, [user]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!user) return <Navigate to="/login?next=/dashboard" replace />;
  if (err) return <main className="m-page"><div className="m-fb no">{err}</div></main>;
  if (!d) return <main className="m-page"><div className="m-loading" /></main>;
  const mine = d.my_courses ?? [];
  const learners = mine.reduce((n, c) => n + c.learners, 0);
  return (
    <main className="m-page dash">
      <section className="dash-head">
        <div>
          <p className="m-kicker">{ROLE_LABEL[user.role] ?? user.role}{user.org ? ` · ${user.org}` : ""}</p>
          <h1>Welcome, {user.name.split(" ")[0]}</h1>
          <p className="m-sub">{user.is_educator ? "Turn your material into courses, then see how your learners are doing." : "Pick up where you left off, or start something new."}</p>
        </div>
        {user.is_educator && <Link className="m-btn big" to="/create">+ Unbox a new course</Link>}
      </section>

      {user.is_educator && (
        <>
          <div className="dash-stats">
            <div><b>{mine.length}</b><span>Your courses</span></div>
            <div><b>{mine.filter((c) => c.published).length}</b><span>Published</span></div>
            <div><b>{learners}</b><span>Learners started</span></div>
            <div><b>{mine.reduce((n, c) => n + c.cards, 0)}</b><span>Cards created</span></div>
          </div>
          <h2 className="m-h2">Your courses</h2>
          {!mine.length && <div className="m-empty">You haven't created a course yet. <Link to="/create">Unbox your first one</Link> from a PDF, a deck, a web page or a video.</div>}
          <div className="dash-grid">
            {mine.map((c) => {
              const [label, tone] = statusOf(c);
              return (
                <article key={c.id} className="dash-card">
                  <Cover c={c} />
                  <div className="dash-body">
                    <span className={`dash-pill ${tone}`}>{label}</span>
                    <strong>{c.title}</strong>
                    <span className="m-meta">{c.modules} modules · {c.cards} cards · {c.learners} learner{c.learners === 1 ? "" : "s"}</span>
                    <div className="m-row">
                      <Link className="m-btn sm" to={c.outline === "outline" || !c.modules ? `/create/${c.id}` : `/course/${c.id}`}>Edit & review</Link>
                      {c.modules > 0 && <Link className="m-btn ghost sm" to={`/learn/${c.id}`}>Open as learner</Link>}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
          {!!d.unclaimed?.length && (
            <details className="dash-claim">
              <summary>Courses made before accounts existed ({d.unclaimed.length}) · add them to your dashboard</summary>
              {d.unclaimed.map((c) => (
                <div key={c.id} className="m-row dash-claim-row">
                  <span><b>{c.title}</b> <span className="m-meta">{c.modules} modules</span></span>
                  <button className="m-btn ghost sm" onClick={async () => { await authApi.claim(c.id); load(); }}>Add to my courses</button>
                </div>
              ))}
            </details>
          )}
        </>
      )}

      <h2 className="m-h2">{user.is_educator ? "Courses you're taking" : "Your learning"}</h2>
      {!d.learning.length && <div className="m-empty">Nothing started yet{d.available.length ? ": pick a course below." : "."}</div>}
      <div className="dash-grid">
        {d.learning.map((c) => (
          <article key={c.id} className="dash-card">
            <Cover c={c} />
            <div className="dash-body">
              <strong>{c.title}</strong>
              <div className="dash-bar"><i style={{ width: `${c.progress?.percent ?? 0}%` }} /></div>
              <span className="m-meta">{c.progress?.modules_done ?? 0} of {c.progress?.modules_total ?? c.modules} modules · ★ {c.progress?.xp ?? 0} XP</span>
              <Link className="m-btn sm" to={`/learn/${c.id}`}>Continue →</Link>
            </div>
          </article>
        ))}
      </div>

      {!!d.available.length && (
        <>
          <h2 className="m-h2">Explore courses</h2>
          <div className="dash-grid">
            {d.available.map((c) => (
              <article key={c.id} className="dash-card">
                <Cover c={c} />
                <div className="dash-body">
                  <strong>{c.title}</strong>
                  <span className="m-meta">{c.tagline || `${c.modules} modules`}</span>
                  <Link className="m-btn ghost sm" to={`/learn/${c.id}`}>Start</Link>
                </div>
              </article>
            ))}
          </div>
        </>
      )}
    </main>
  );
}

export function Welcome() {
  const { user } = useAuth();
  if (user) return <Navigate to="/dashboard" replace />;
  return (
    <main className="m-page narrow auth-page">
      <div className="auth-box welcome">
        <p className="m-kicker">UnboxEd</p>
        <h1>Any knowledge in. Real learning out.</h1>
        <p className="m-sub">Educators turn their material into short, visual, interactive courses. Learners learn until it makes sense.</p>
        <div className="m-row">
          <Link className="m-btn big" to="/signup">Create an account</Link>
          <Link className="m-btn ghost big" to="/login">Log in</Link>
        </div>
      </div>
    </main>
  );
}
