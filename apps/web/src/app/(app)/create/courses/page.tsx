"use client";
import { useEffect, useState } from "react";
import type { CourseSummary } from "@shared/index";

import { CourseCard, NewCourseButton } from "@/components/courses";
import { EmptyState, ErrorState, Loading, PageHeader, cx } from "@/components/ui";
import { useApi } from "@/lib/hooks";
import { useSession } from "@/lib/session";

const FILTERS = [["", "All"], ["draft", "Drafts"], ["published", "Published"], ["archived", "Archived"]] as const;

export default function CoursesPage() {
  const { workspace } = useSession();
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  useEffect(() => { const t = setTimeout(() => setQuery(q), 250); return () => clearTimeout(t); }, [q]);
  const params = new URLSearchParams({ ...(workspace ? { organization_id: workspace.organization_id } : {}), ...(query ? { q: query } : {}),
                                       ...(status ? { status } : {}) });
  const courses = useApi<CourseSummary[]>(workspace ? `/courses?${params}` : null);

  return (
    <>
      <PageHeader eyebrow={workspace?.organization_name} title="Courses" actions={<NewCourseButton />} />
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <input type="search" placeholder="Search by title…" aria-label="Search courses" value={q} onChange={(e) => setQ(e.target.value)}
               className="min-w-60 flex-1 rounded-xl border-2 border-line bg-surface px-3.5 py-2.5 focus:border-violet focus:outline-none" />
        <div role="tablist" aria-label="Filter by status" className="flex gap-1 rounded-xl bg-lavender p-1">
          {FILTERS.map(([v, l]) => (
            <button key={v} role="tab" aria-selected={status === v} onClick={() => setStatus(v)}
                    className={cx("rounded-lg px-3 py-1.5 text-sm font-bold", status === v ? "bg-surface text-violet shadow" : "text-muted hover:text-ink")}>{l}</button>
          ))}
        </div>
      </div>
      {courses.loading ? <Loading /> : courses.error ? <ErrorState error={courses.error} onRetry={() => courses.reload()} /> :
        !courses.data?.length ? (
          <EmptyState title={query || status ? "Nothing matches" : "No courses yet"} action={!query && !status ? <NewCourseButton /> : undefined}>
            {query || status ? "Try a different search or filter." : "Create your first course to get started."}
          </EmptyState>
        ) : <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{courses.data.map((c) => <CourseCard key={c.id} course={c} />)}</div>}
    </>
  );
}
