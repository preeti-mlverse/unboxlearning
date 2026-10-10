import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, PURPOSES, type Json } from "../api";
import { ErrorNote, StatusBadge } from "../ui";

export function Home() {
  const [courses, setCourses] = useState<Json[] | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.courses().then(setCourses).catch((e) => setErr(String(e))); }, []);
  return (
    <main className="page">
      <div className="spread" style={{ marginBottom: 20 }}>
        <div>
          <h1>Courses</h1>
          <div className="muted">Turn trusted content into adaptive, evidence-backed learning.</div>
        </div>
        <div className="row">
          <label className="btn" style={{ margin: 0, color: "var(--ink)", fontSize: 14 }}>
            Import bundle
            <input type="file" accept=".json" hidden onChange={async (e) => {
              const f = e.target.files?.[0];
              if (!f) return;
              const fd = new FormData(); fd.append("file", f);
              const r = await fetch("/api/courses/import", { method: "POST", body: fd });
              if (r.ok) { const { course_id } = await r.json(); window.location.href = `/courses/${course_id}`; }
              else setErr((await r.json()).detail ?? "Import failed");
            }} />
          </label>
          <Link className="btn primary" to="/new">+ New course from content</Link>
        </div>
      </div>
      <ErrorNote error={err} />
      {courses && !courses.length && (
        <div className="card empty">
          <h3>No courses yet</h3>
          <p>Add a PDF, a web page, a docs site, a YouTube video or some notes — the engine works out what kind of
            knowledge it holds and how best to teach it.</p>
          <Link className="btn primary" to="/new">Create your first course</Link>
        </div>
      )}
      <div className="grid3">
        {courses?.map((c) => {
          const total = Object.values(c.activities as Record<string, number>).reduce((a, b) => a + b, 0);
          return (
            <div key={c.id} className="card col" style={{ gap: 8 }}>
              <div className="spread"><StatusBadge status={c.status} /><span className="badge">{PURPOSES[c.goal.purpose]?.label}</span></div>
              <h3 style={{ margin: 0 }}>{c.title}</h3>
              <div className="small muted">{total} activities · {c.activities.approved ?? 0} approved{c.activities.flagged ? ` · ${c.activities.flagged} flagged` : ""}</div>
              <div className="row" style={{ marginTop: "auto" }}>
                <Link className="btn sm" to={`/courses/${c.id}`}>Open studio</Link>
                {c.activities.approved ? <Link className="btn sm primary" to={`/classic/learn/${c.id}`}>Learn</Link> : null}
              </div>
            </div>
          );
        })}
      </div>
    </main>
  );
}
