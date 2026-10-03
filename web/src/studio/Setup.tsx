import { useEffect, useState } from "react";
import { api, KT_LABEL, PURPOSES, type Course, type Goal, type Json } from "../api";
import { ErrorNote, KT_COLOR, Progress, Spinner } from "../ui";

const LEVELS = ["novice", "beginner", "intermediate", "advanced", "expert"];
const LANGS: [string, string][] = [["en", "English"], ["hi", "Hindi"], ["ta", "Tamil"], ["te", "Telugu"], ["bn", "Bengali"],
  ["mr", "Marathi"], ["ar", "Arabic"], ["es", "Spanish"], ["fr", "French"], ["de", "German"], ["pt", "Portuguese"], ["ja", "Japanese"]];

export function JobPanel({ course }: { course: Course }) {
  const j = course.job;
  if (!j) return null;
  const running = j.status === "running";
  return (
    <div className="card stack">
      <div className="spread">
        <strong>{j.kind === "analyse" ? "Analysis" : "Build"} · {running ? j.stage : j.status}</strong>
        {running && <Spinner />}
      </div>
      <Progress value={j.progress} />
      <div className={`small ${j.status === "failed" ? "" : "muted"}`} style={j.status === "failed" ? { color: "var(--bad)" } : undefined}>{j.message}</div>
      {!!j.log?.length && (
        <details><summary className="small muted">Log</summary>
          <pre style={{ maxHeight: 200, overflow: "auto", fontSize: 12 }}>{j.log.join("\n")}</pre></details>
      )}
    </div>
  );
}

export function ProfileView({ course, onScope }: { course: Course; onScope: (ids: string[] | null) => void }) {
  const p = course.profile!;
  const scope = course.data.settings.scope_unit_ids;
  const inScope = (id: string, role: string) => (scope ? scope.includes(id) : role === "core" || role === "supporting");
  const toggle = (id: string, role: string) => {
    const base = scope ?? p.units.filter((u) => inScope(u.id, u.role)).map((u) => u.id);
    onScope(inScope(id, role) ? base.filter((x) => x !== id) : [...base, id]);
  };
  const selected = p.units.filter((u) => inScope(u.id, u.role));
  return (
    <div className="card stack">
      <div className="spread">
        <h2 style={{ margin: 0 }}>What the engine understood</h2>
        <span className="row" style={{ gap: 6 }}>
          <span className="badge primary">{p.genre.replace(/_/g, " ")}</span>
          <span className="badge">{p.subject_domain}</span>
          <span className="badge">source level: {p.source_level}</span>
        </span>
      </div>
      <p style={{ margin: 0 }}>{p.summary}</p>
      <div>
        <div className="small muted" style={{ marginBottom: 6 }}>Kinds of knowledge in this material — this decides how it will be taught</div>
        <div className="bar" aria-label="Knowledge mix">
          {p.knowledge_mix.map((k) => <div key={k.type} title={`${KT_LABEL[k.type]} ${Math.round(k.weight * 100)}%`} style={{ width: `${k.weight * 100}%`, background: KT_COLOR[k.type] }} />)}
        </div>
        <div className="row small" style={{ marginTop: 8, gap: 14 }}>
          {p.knowledge_mix.map((k) => (
            <span key={k.type} title={k.where}><span className="kt" style={{ background: KT_COLOR[k.type] }} />{KT_LABEL[k.type]} {Math.round(k.weight * 100)}%</span>
          ))}
        </div>
      </div>
      <div className="kv">
        <div>Modalities</div><div>{p.modalities.join(", ") || "—"}</div>
        <div>Assumes</div><div>{p.assumed_prerequisites.join("; ") || "—"}</div>
      </div>
      {!!p.cautions.length && <div className="notice warn"><strong>Cautions: </strong>{p.cautions.join(" · ")}</div>}
      <details>
        <summary><strong>Scope</strong> <span className="small muted">— {selected.length} of {p.units.length} sections will be taught
          ({selected.reduce((a, u) => a + u.tokens, 0).toLocaleString()} tokens). Reference and boilerplate are left out by default.</span></summary>
        <div style={{ maxHeight: 360, overflowY: "auto", marginTop: 8 }}>
          <table>
            <thead><tr><th style={{ width: 30 }}></th><th>Section</th><th>Role</th><th>Knowledge</th><th>Size</th></tr></thead>
            <tbody>
              {p.units.map((u) => (
                <tr key={u.id}>
                  <td><input type="checkbox" checked={inScope(u.id, u.role)} onChange={() => toggle(u.id, u.role)} style={{ width: "auto" }} aria-label={`Include ${u.title}`} /></td>
                  <td>{u.path.join(" › ") || u.title}<div className="tiny faint">{u.note}</div></td>
                  <td><span className={`badge ${u.role === "core" ? "good" : u.role === "supporting" ? "info" : ""}`}>{u.role}</span></td>
                  <td className="small">{u.knowledge_types.map((k) => <span key={k} style={{ marginRight: 6 }}><span className="kt" style={{ background: KT_COLOR[k] }} />{k}</span>)}</td>
                  <td className="small muted">{u.tokens.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {scope && <button className="btn sm" style={{ marginTop: 8 }} onClick={() => onScope(null)}>Reset to recommended scope</button>}
      </details>
    </div>
  );
}

export function GoalForm({ course, onBuild }: { course: Course; onBuild: () => void }) {
  const [g, setG] = useState<Goal>(course.data.goal);
  const [goalsText, setGoalsText] = useState(course.data.goal.specific_goals.join("\n"));
  const [quality, setQuality] = useState(course.data.settings.quality);
  const [auto, setAuto] = useState(course.data.settings.auto_approve);
  const [err, setErr] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => { setG(course.data.goal); setGoalsText(course.data.goal.specific_goals.join("\n")); }, [course.id]); // eslint-disable-line
  const set = <K extends keyof Goal>(k: K, v: Goal[K]) => setG({ ...g, [k]: v });
  const suggestions = course.profile?.suggested_goals ?? [];
  const [est, setEst] = useState<Json | null>(null);
  useEffect(() => { if (course.profile) api.estimate(course.id).then(setEst).catch(() => setEst(null)); },
    [course.id, course.profile, course.data.settings.quality, course.data.settings.scope_unit_ids, course.data.goal.time_budget_minutes]); // eslint-disable-line
  const building = course.job?.status === "running";

  const save = async () => {
    setSaving(true); setErr("");
    try {
      await api.patchCourse(course.id, {
        goal: { ...g, specific_goals: goalsText.split("\n").map((s) => s.trim()).filter(Boolean) },
        settings: { quality, auto_approve: auto },
      });
      await api.build(course.id);
      onBuild();
    } catch (e) { setErr(String(e)); } finally { setSaving(false); }
  };

  return (
    <div className="card stack">
      <h2 style={{ margin: 0 }}>Learning goal</h2>
      {!!suggestions.length && (
        <div>
          <div className="small muted" style={{ marginBottom: 6 }}>Goals this material can genuinely support — pick one to start from</div>
          <div className="grid2">
            {suggestions.map((s, i) => (
              <div key={i} className={`card flat pick ${g.purpose === s.purpose && goalsText === s.title ? "selected" : ""}`}
                onClick={() => { setG({ ...g, purpose: s.purpose, audience_level: s.audience_level }); setGoalsText(s.title); }}>
                <div className="spread"><strong>{s.title}</strong><span className="badge">{PURPOSES[s.purpose]?.label}</span></div>
                <div className="small">{s.description}</div>
                <div className="tiny faint" style={{ marginTop: 4 }}>{s.why_supported}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      <div>
        <label>Purpose</label>
        <div className="row" style={{ gap: 6 }}>
          {Object.entries(PURPOSES).map(([k, v]) => (
            <button key={k} className={`chip ${g.purpose === k ? "on" : ""}`} onClick={() => set("purpose", k)} title={v.blurb}>{v.label}</button>
          ))}
        </div>
        <div className="tiny faint" style={{ marginTop: 4 }}>{PURPOSES[g.purpose]?.blurb}</div>
      </div>
      <div className="grid2">
        <div><label htmlFor="lvl">Learner level</label>
          <select id="lvl" value={g.audience_level} onChange={(e) => set("audience_level", e.target.value)}>{LEVELS.map((l) => <option key={l}>{l}</option>)}</select></div>
        <div><label htmlFor="aud">Who are the learners?</label>
          <input id="aud" value={g.audience_description} onChange={(e) => set("audience_description", e.target.value)} placeholder="e.g. backend engineers new to agents; Class 10 students" /></div>
        <div><label htmlFor="tb">Time budget (minutes)</label>
          <input id="tb" type="number" min={10} max={1200} value={g.time_budget_minutes} onChange={(e) => set("time_budget_minutes", parseInt(e.target.value || "60", 10))} /></div>
        <div><label htmlFor="dp">Depth</label>
          <select id="dp" value={g.depth} onChange={(e) => set("depth", e.target.value)}>
            <option value="overview">Overview</option><option value="standard">Standard</option><option value="deep">Deep</option></select></div>
        <div><label htmlFor="lang">Language</label>
          <select id="lang" value={g.language} onChange={(e) => set("language", e.target.value)}>{LANGS.map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
        {g.purpose === "exam_prep" && (
          <div><label htmlFor="ex">Exam format</label>
            <input id="ex" value={g.exam_format ?? ""} onChange={(e) => set("exam_format", e.target.value)} placeholder="e.g. 40 MCQs + 2 short answers" /></div>
        )}
      </div>
      <div>
        <label htmlFor="sg">Specific goals (one per line)</label>
        <textarea id="sg" value={goalsText} onChange={(e) => setGoalsText(e.target.value)} rows={3}
          placeholder={"e.g. Build a research agent with subagents\nDecide which backend to use for production"} />
        <div className="tiny faint">Each goal is mapped to objectives. Goals the sources cannot support are reported, never invented.</div>
      </div>
      <div className="grid2">
        <label className="row" style={{ fontWeight: 400, gap: 6 }}>
          <input type="checkbox" checked={g.hands_on} onChange={(e) => set("hands_on", e.target.checked)} style={{ width: "auto" }} /> Hands-on (scenarios, roleplay, tasks)
        </label>
        <label className="row" style={{ fontWeight: 400, gap: 6 }}>
          <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} style={{ width: "auto" }} /> Auto-approve verified activities (personal use)
        </label>
      </div>
      <div className="row">
        <select value={quality} onChange={(e) => setQuality(e.target.value)} style={{ width: "auto" }} aria-label="Quality mode">
          <option value="economy">Economy</option><option value="balanced">Balanced</option><option value="best">Best</option>
        </select>
        <button className="btn primary" onClick={save} disabled={saving || building || !course.profile}>
          {building ? "Building…" : course.curriculum ? "Rebuild course for this goal" : "Build course →"}</button>
      </div>
      {est?.available && (
        <div className="small muted">
          Estimated build: ~{est.calls} AI calls over {est.units} sections{est.units_cached ? ` (${est.units_cached} already analysed)` : ""},
          ~{est.objectives_estimate} objectives / {est.activities_estimate} activities
          {est.usd != null && <> · about <strong>${est.usd}</strong></>} · ~{est.minutes_estimate} min
          <details><summary className="tiny">breakdown</summary>
            <table className="tiny"><tbody>{est.rows.map((r: Json) => (
              <tr key={r.stage}><td>{r.stage}</td><td className="mono">{r.model}</td><td>{r.calls} calls</td>
                <td>{(r.input_tokens / 1000).toFixed(0)}k in / {(r.output_tokens / 1000).toFixed(0)}k out</td><td>{r.usd != null ? `$${r.usd}` : "—"}</td></tr>
            ))}</tbody></table>
            <div className="tiny faint">Approximate list prices; the actual cost depends on content and model behaviour.</div>
          </details>
        </div>
      )}
      {est?.ai_status?.state && !["ok", "mock", "unknown"].includes(est.ai_status.state) && (
        <div className="notice bad">{est.ai_status.message}</div>
      )}
      <ErrorNote error={err} />
    </div>
  );
}
