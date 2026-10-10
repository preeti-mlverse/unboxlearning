import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Course } from "../api";
import { GoalForm, JobPanel, ProfileView } from "../studio/Setup";
import { Evidence } from "../studio/Evidence";
import { Lessons } from "../studio/Lessons";
import { Knowledge, Learners, Overview, SourcesView, Usage } from "../studio/Views";
import { ErrorNote, Spinner, StatusBadge, Tabs } from "../ui";

type Tab = "setup" | "overview" | "lessons" | "knowledge" | "sources" | "learners" | "evidence" | "usage";

export function Studio() {
  const { id = "" } = useParams();
  const [course, setCourse] = useState<Course | null>(null);
  const [tab, setTab] = useState<Tab | null>(null);
  const [err, setErr] = useState("");
  const timer = useRef<number | undefined>(undefined);

  const load = useCallback(async () => {
    try {
      const c = await api.course(id);
      setCourse(c);
      setTab((t) => t ?? (c.curriculum ? "lessons" : "setup"));
      window.clearTimeout(timer.current);
      if (c.job?.status === "running") timer.current = window.setTimeout(load, 1500);
    } catch (e) { setErr(String(e)); }
  }, [id]);
  useEffect(() => { load(); return () => window.clearTimeout(timer.current); }, [load]);

  if (err) return <main className="page"><ErrorNote error={err} /></main>;
  if (!course || !tab) return <main className="page"><Spinner /></main>;
  const ready = !!course.curriculum && !!course.graph;
  const tabs: [Tab, string][] = [["setup", "Setup & goal"], ...(ready ? [["overview", "Path"], ["lessons", "Lessons"], ["knowledge", "Knowledge"]] as [Tab, string][] : []),
    ["sources", "Sources"], ...(ready ? [["learners", "Learners"], ["evidence", "Evidence"]] as [Tab, string][] : []), ["usage", "AI usage"]];

  return (
    <main className="page">
      <div className="spread" style={{ marginBottom: 12 }}>
        <div>
          <div className="row" style={{ gap: 8 }}><StatusBadge status={course.status} /><span className="small muted">{course.sources.length} source(s)</span></div>
          <h1 style={{ margin: "4px 0 0" }}>{course.title}</h1>
        </div>
        <div className="row">
          {ready && (
            <details style={{ position: "relative" }}>
              <summary className="btn sm" style={{ listStyle: "none" }}>Export ▾</summary>
              <div className="card" style={{ position: "absolute", right: 0, zIndex: 30, width: 260, padding: 10 }}>
                <a className="btn ghost sm" href={`/api/courses/${course.id}/export/qti`}>Question bank (QTI 2.1 zip)</a>
                <div className="tiny faint" style={{ padding: "0 10px 6px" }}>Approved items, for Moodle / Canvas / Blackboard</div>
                <a className="btn ghost sm" href={`/api/courses/${course.id}/export/bundle`}>Full course bundle (.json)</a>
                <div className="tiny faint" style={{ padding: "0 10px" }}>Everything incl. evidence — import on another install</div>
              </div>
            </details>
          )}
          {course.activity_counts.approved ? <Link className="btn primary" to={`/classic/learn/${course.id}`}>Classic learner view →</Link> : null}
        </div>
      </div>
      <Tabs tabs={tabs} value={tab} onChange={setTab} />
      {tab === "setup" && (
        <div className="stack">
          <JobPanel course={course} />
          {course.profile ? (
            <>
              <ProfileView course={course} onScope={async (ids) => { await api.patchCourse(course.id, { settings: { scope_unit_ids: ids } }); load(); }} />
              <GoalForm course={course} onBuild={load} />
            </>
          ) : course.job?.status !== "running" && (
            <div className="card empty">
              <p>The content has not been analysed yet.</p>
              <button className="btn primary" onClick={async () => { await api.analyse(course.id); load(); }}>Analyse content</button>
            </div>
          )}
        </div>
      )}
      {tab === "overview" && ready && <Overview course={course} />}
      {tab === "lessons" && ready && <Lessons course={course} reload={load} />}
      {tab === "knowledge" && ready && <Knowledge course={course} />}
      {tab === "sources" && <SourcesView course={course} />}
      {tab === "learners" && ready && <Learners course={course} />}
      {tab === "evidence" && ready && <Evidence course={course} reload={load} />}
      {tab === "usage" && <Usage course={course} />}
    </main>
  );
}
