import { useEffect, useMemo, useState } from "react";
import { ActivityPlayer } from "../ActivityPlayer";
import { api, type Activity, type CatalogEntry, type Course } from "../api";
import { CiteList, ErrorNote, KT_COLOR, Md, StatusBadge, shortType } from "../ui";

export function Lessons({ course, reload }: { course: Course; reload: () => void }) {
  const cur = course.curriculum!;
  const [acts, setActs] = useState<Activity[]>([]);
  const [sel, setSel] = useState(cur.objectives[0]?.id ?? "");
  const [catalog, setCatalog] = useState<CatalogEntry[]>([]);
  const [err, setErr] = useState("");
  const load = () => api.activities(course.id).then(setActs).catch((e) => setErr(String(e)));
  useEffect(() => { load(); api.catalog().then(setCatalog); }, [course.id]); // eslint-disable-line
  const byObj = useMemo(() => {
    const m: Record<string, Activity[]> = {};
    acts.forEach((a) => (m[a.objective_id] ??= []).push(a));
    return m;
  }, [acts]);
  const o = cur.objectives.find((x) => x.id === sel);
  const plan = course.plans[sel];
  const counts = acts.reduce<Record<string, number>>((m, a) => ({ ...m, [a.status]: (m[a.status] ?? 0) + 1 }), {});
  const replace = (a: Activity) => setActs((l) => l.map((x) => (x.id === a.id ? a : x)));

  return (
    <div className="stack">
      <div className="spread">
        <div className="row small">
          <StatusBadge status="approved" /> {counts.approved ?? 0}
          <StatusBadge status="draft" /> {counts.draft ?? 0}
          <StatusBadge status="flagged" /> {counts.flagged ?? 0}
        </div>
        <div className="row">
          <button className="btn" onClick={async () => { await api.approveAll(course.id); load(); reload(); }} disabled={!counts.draft}>Approve all verified drafts</button>
        </div>
      </div>
      <ErrorNote error={err} />
      <div className="learn-layout">
        <aside className="card" style={{ padding: 10, alignSelf: "start", position: "sticky", top: 70, maxHeight: "80vh", overflowY: "auto" }}>
          {cur.modules.map((m) => (
            <div key={m.id} style={{ marginBottom: 10 }}>
              <div className="tiny faint" style={{ padding: "4px 8px", textTransform: "uppercase", letterSpacing: ".05em" }}>{m.title}</div>
              {m.objective_ids.map((oid) => {
                const ob = cur.objectives.find((x) => x.id === oid)!;
                const list = byObj[oid] ?? [];
                const flagged = list.filter((a) => a.status === "flagged").length;
                const ok = list.length && list.every((a) => a.status === "approved");
                return (
                  <div key={oid} className={`path-obj ${oid === sel ? "current" : ""}`} onClick={() => setSel(oid)} style={{ cursor: "pointer" }}>
                    <span className="kt" style={{ background: KT_COLOR[ob.knowledge_type], marginTop: 5 }} />
                    <span style={{ flex: 1 }}>{ob.statement}</span>
                    {flagged ? <span className="badge bad">{flagged}</span> : ok ? <span className="badge good">✓</span> : null}
                  </div>
                );
              })}
            </div>
          ))}
        </aside>
        {o && (
          <div className="stack">
            <div className="card stack">
              <div className="row" style={{ gap: 6 }}>
                <span className="badge" style={{ background: KT_COLOR[o.knowledge_type], color: "#fff" }}>{o.knowledge_type}</span>
                <span className="badge">Bloom: {o.bloom}</span><span className="badge">~{o.estimated_minutes} min</span>
              </div>
              <h2 style={{ margin: 0 }}>{o.statement}</h2>
              <div className="small"><strong>Success criteria:</strong> {o.success_criteria.join(" · ")}</div>
              {plan && (
                <div className="notice">
                  <strong>Why this lesson design: </strong>{plan.rationale}
                  <div className="row small" style={{ marginTop: 6, gap: 6 }}>
                    {plan.steps.map((s, i) => <span key={i} className="badge primary">{i + 1}. {s.stage}: {shortType(s.activity_type)}</span>)}
                  </div>
                </div>
              )}
              <div className="small muted">Evidence: <CiteList ids={o.evidence} /></div>
            </div>
            {(byObj[o.id] ?? []).map((a) => (
              <ActivityReview key={a.id} a={a} course={course} catalog={catalog} allowed={plan?.allowed?.[a.stage] ?? []} onChange={(x) => { replace(x); reload(); }} />
            ))}
            {!(byObj[o.id] ?? []).length && <div className="card empty">No activities generated for this objective.</div>}
          </div>
        )}
      </div>
    </div>
  );
}

function ActivityReview({ a, course, catalog, allowed, onChange }: {
  a: Activity; course: Course; catalog: CatalogEntry[]; allowed: string[]; onChange: (a: Activity) => void;
}) {
  const [mode, setMode] = useState<"preview" | "edit" | "regen" | null>("preview");
  const [instr, setInstr] = useState("");
  const [type, setType] = useState(a.type);
  const [json, setJson] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const act = async (fn: () => Promise<Activity>) => {
    setBusy(true); setErr("");
    try { onChange(await fn()); setMode("preview"); } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  };
  const v = a.verify;
  const types = [...new Set([a.type, ...allowed, ...catalog.filter((c) => c.enabled && c.stages.includes(a.stage)).map((c) => c.key)])];
  return (
    <div className="card stack" style={{ borderColor: a.status === "flagged" ? "var(--bad)" : undefined }}>
      <div className="spread">
        <div className="row" style={{ gap: 6 }}>
          <StatusBadge status={a.status} />
          <span className="stage-pill">{a.stage}</span>
          {a.data.reserve && <span className="badge info" title="Held back: shown only to learners who need another try">reserve</span>}
          <strong>{shortType(a.type)}</strong>
          <span className="small muted">— {a.data.title}</span>
        </div>
        <div className="row" style={{ gap: 4 }}>
          {a.status !== "approved" && <button className="btn sm primary" disabled={busy} onClick={() => act(() => api.patchActivity(a.id, { status: "approved" }))}>Approve</button>}
          {a.status === "approved" && <button className="btn sm" disabled={busy} onClick={() => act(() => api.patchActivity(a.id, { status: "draft" }))}>Unapprove</button>}
          <button className="btn sm" onClick={() => setMode(mode === "regen" ? "preview" : "regen")}>Regenerate…</button>
          <button className="btn sm" onClick={() => { setJson(JSON.stringify(a.data, null, 2)); setMode(mode === "edit" ? "preview" : "edit"); }}>Edit</button>
        </div>
      </div>
      {a.data.intent && <div className="small muted"><strong>Intent:</strong> {a.data.intent}{a.data.targets_misconception ? ` · targets: ${a.data.targets_misconception}` : ""}</div>}
      {v && v.verdict === "flagged" && (
        <div className="notice bad">
          <strong>Must fix</strong>{v.answer_key_correct === "no" && " · answer key looks wrong"}
          <ul style={{ margin: "4px 0 0", paddingLeft: 20 }} className="small">
            {(v.serious_issues ?? []).map((p, i) => <li key={`s${i}`}>{p}</li>)}
            {v.checks.filter((c) => c.supported === "no").map((c, i) => <li key={i}>Unsupported: “{c.claim}” — {c.note}</li>)}
          </ul>
        </div>
      )}
      {v && v.verdict === "verified" && <div className="small" style={{ color: "var(--good)" }}>✓ Claims and answer key checked against the sources</div>}
      {v && (v.pedagogy_issues.length > 0 || v.checks.some((c) => c.supported === "partly")) && (
        <details className="small"><summary className="muted">Reviewer suggestions ({v.pedagogy_issues.length + v.checks.filter((c) => c.supported === "partly").length})</summary>
          <ul style={{ margin: "4px 0 0", paddingLeft: 20 }}>
            {v.pedagogy_issues.map((p, i) => <li key={`p${i}`}>{p}</li>)}
            {v.checks.filter((c) => c.supported === "partly").map((c, i) => <li key={`c${i}`}>Goes slightly beyond the source: “{c.claim}” — {c.note}</li>)}
          </ul>
        </details>
      )}
      {mode === "regen" && (
        <div className="card flat stack">
          <div className="grid2">
            <div><label>Activity type</label>
              <select value={type} onChange={(e) => setType(e.target.value)}>{types.map((t) => <option key={t} value={t}>{shortType(t)}</option>)}</select></div>
            <div><label>Instruction (optional)</label>
              <input value={instr} onChange={(e) => setInstr(e.target.value)} placeholder="e.g. make the example simpler; use a hospital context" /></div>
          </div>
          <div><button className="btn primary" disabled={busy} onClick={() => act(() => api.regenerate(course.id, a.id, instr, type !== a.type ? type : undefined))}>{busy ? "Regenerating…" : "Regenerate"}</button></div>
        </div>
      )}
      {mode === "edit" && (
        <div className="stack">
          <textarea className="mono" value={json} onChange={(e) => setJson(e.target.value)} rows={16} style={{ fontSize: 12 }} aria-label="Activity JSON" />
          <div className="row">
            <button className="btn primary" disabled={busy} onClick={() => act(() => api.patchActivity(a.id, { data: JSON.parse(json) }))}>Save</button>
            <span className="tiny faint">Validated against the activity schema before saving.</span>
          </div>
        </div>
      )}
      <ErrorNote error={err} />
      {mode === "preview" && <ActivityPlayer activity={a} review />}
      {a.data.key_claims && a.data.key_claims.length > 0 && (
        <details className="small"><summary className="muted">Key claims ({a.data.key_claims.length})</summary>
          <ul style={{ margin: "4px 0", paddingLeft: 20 }}>{a.data.key_claims.map((k, i) => <li key={i}><Md text={k} inline /></li>)}</ul></details>
      )}
    </div>
  );
}
