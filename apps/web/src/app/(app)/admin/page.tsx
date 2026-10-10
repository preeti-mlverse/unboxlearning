"use client";
// A deliberately plain platform admin view: users, organizations, courses, jobs and failed jobs.
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { AdminOrg, AdminStats, AdminUser, CourseSummary, Job } from "@shared/index";

import { Alert, Button, Card, ErrorState, Loading, PageHeader, StatusBadge, cx } from "@/components/ui";
import { ApiError, post } from "@/lib/api";
import { timeAgo, useApi } from "@/lib/hooks";
import { useSession } from "@/lib/session";

const TABS = ["Users", "Organizations", "Courses", "Jobs", "Failed jobs"] as const;
type Tab = (typeof TABS)[number];

function Table({ head, rows }: { head: string[]; rows: React.ReactNode[][] }) {
  return (
    <div className="overflow-x-auto rounded-[22px] border-2 border-line bg-surface">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="bg-lavender/60"><tr>{head.map((h) => <th key={h} className="px-4 py-3 font-display font-bold">{h}</th>)}</tr></thead>
        <tbody className="divide-y divide-line">
          {rows.length ? rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j} className="px-4 py-3 align-top">{c}</td>)}</tr>)
                       : <tr><td colSpan={head.length} className="px-4 py-8 text-center text-muted">Nothing here.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

export default function AdminPage() {
  const { me } = useSession();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("Users");
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => { if (me && !me.is_platform_admin) router.replace("/unauthorized"); }, [me, router]);
  const stats = useApi<AdminStats>(me?.is_platform_admin ? "/admin/stats" : null);
  const path = { Users: "/admin/users", Organizations: "/admin/organizations", Courses: "/admin/courses?include_deleted=true",
                 Jobs: "/admin/jobs", "Failed jobs": "/admin/jobs?status=failed" }[tab];
  const list = useApi<unknown[]>(me?.is_platform_admin ? path : null);
  if (!me?.is_platform_admin) return null;

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    try { await fn(); setMsg(ok); await list.reload(true); await stats.reload(true); }
    catch (e) { setMsg(e instanceof ApiError ? e.message : "Something went wrong."); }
  };

  let body: React.ReactNode = null;
  if (list.loading) body = <Loading />;
  else if (list.error) body = <ErrorState error={list.error} onRetry={() => list.reload()} />;
  else if (tab === "Users") {
    body = <Table head={["Person", "Status", "Workspaces", "Joined", "Last login", ""]} rows={(list.data as AdminUser[]).map((u) => [
      <span key="p" className="grid"><b>{u.display_name}{u.is_platform_admin ? " ⛭" : ""}</b><span className="text-muted">{u.email}{u.email_verified ? " ✓" : ""}</span></span>,
      <StatusBadge key="s" status={u.status === "active" ? "ready" : "disabled"} label={u.status} />, u.organizations, timeAgo(u.created_at), timeAgo(u.last_login_at) || "never",
      u.id === me.id ? null : <Button key="a" size="sm" variant="ghost" onClick={() => act(() => post(`/admin/users/${u.id}/status?status=${u.status === "active" ? "disabled" : "active"}`),
        `${u.email} is now ${u.status === "active" ? "disabled" : "active"}.`)}>{u.status === "active" ? "Disable" : "Enable"}</Button>])} />;
  } else if (tab === "Organizations") {
    body = <Table head={["Workspace", "Type", "Members", "Courses", "Created"]} rows={(list.data as AdminOrg[]).map((o) => [
      <span key="n" className="grid"><b>{o.name}</b><span className="font-mono text-xs text-muted">{o.slug}</span></span>, o.type.replace("_", " "), o.members, o.courses, timeAgo(o.created_at)])} />;
  } else if (tab === "Courses") {
    body = <Table head={["Course", "Status", "Lessons", "Updated", ""]} rows={(list.data as CourseSummary[]).map((c) => [
      <b key="t">{c.title}</b>, c.deleted_at ? <StatusBadge key="s" status="failed" label="Deleted" /> : <StatusBadge key="s" status={c.status} />, c.lesson_count, timeAgo(c.updated_at),
      c.deleted_at ? <Button key="r" size="sm" variant="ghost" onClick={() => act(() => post(`/admin/courses/${c.id}/restore`), `Restored “${c.title}”.`)}>Restore</Button> : null])} />;
  } else {
    body = <Table head={["Job", "Status", "For", "Attempts", "Created", "Error", ""]} rows={(list.data as Job[]).map((j) => [
      <span key="j" className="font-mono text-xs">{j.job_type}<br /><span className="text-muted">{j.id}</span></span>, <StatusBadge key="s" status={j.status} />,
      <span key="e" className="font-mono text-xs">{j.entity_type} {j.entity_id}</span>, `${j.attempt_count}/${j.max_attempts}`, timeAgo(j.created_at),
      <span key="err" className="line-clamp-3 max-w-xs text-xs text-bad">{j.error}</span>,
      j.status === "failed" ? <Button key="r" size="sm" variant="ghost" onClick={() => act(() => post(`/admin/jobs/${j.id}/retry`), "Job queued again.")}>Retry</Button> : null])} />;
  }

  const s = stats.data;
  return (
    <>
      <PageHeader eyebrow="Platform" title="Admin" />
      {s && (
        <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
          {[["Users", s.users], ["Workspaces", s.organizations], ["Courses", `${s.courses} (${s.published_courses} live)`], ["Enrollments", s.enrollments],
            ["Documents", s.documents], ["Jobs waiting", s.jobs_pending], ["Jobs failed", s.jobs_failed]].map(([l, n]) => (
            <Card key={l as string} className={cx("grid gap-0.5 p-4", l === "Jobs failed" && Number(n) > 0 && "border-bad/50")}>
              <span className="eyebrow text-muted">{l}</span><span className="font-display text-2xl font-extrabold">{n}</span>
            </Card>
          ))}
        </div>
      )}
      <div role="tablist" className="mb-4 flex flex-wrap gap-1 rounded-xl bg-lavender p-1">
        {TABS.map((t) => <button key={t} role="tab" aria-selected={tab === t} onClick={() => { setTab(t); setMsg(null); }}
                                 className={cx("rounded-lg px-3 py-1.5 text-sm font-bold", tab === t ? "bg-surface text-violet shadow" : "text-muted hover:text-ink")}>{t}</button>)}
      </div>
      {msg && <div className="mb-4"><Alert>{msg}</Alert></div>}
      {body}
    </>
  );
}
