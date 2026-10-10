"use client";
import type { Enrollment } from "@shared/index";

import { Card, EmptyState, ErrorState, LinkButton, Loading, PageHeader, ProgressBar, StatusBadge } from "@/components/ui";
import { timeAgo, useApi } from "@/lib/hooks";

export default function ProgressPage() {
  const list = useApi<Enrollment[]>("/enrollments");
  const items = list.data ?? [];
  const lessonsDone = items.reduce((n, e) => n + e.lessons_completed, 0);
  const finished = items.filter((e) => e.status === "completed").length;

  return (
    <>
      <PageHeader eyebrow="Progress" title="How you're doing" />
      {list.loading ? <Loading /> : list.error ? <ErrorState error={list.error} /> : items.length === 0 ? (
        <EmptyState title="No progress yet" action={<LinkButton href="/learn/catalog" variant="primary">Find a course</LinkButton>}>Join a course and your progress shows up here.</EmptyState>
      ) : (
        <div className="grid gap-6">
          <div className="grid gap-4 sm:grid-cols-3">
            {[["Courses joined", items.length], ["Courses finished", finished], ["Lessons completed", lessonsDone]].map(([l, n]) => (
              <Card key={l as string} className="grid gap-1"><span className="eyebrow text-muted">{l}</span><span className="font-display text-4xl font-extrabold">{n}</span></Card>
            ))}
          </div>
          <Card className="p-0">
            <ul className="divide-y-2 divide-line">
              {items.map((e) => (
                <li key={e.id} className="grid gap-2 px-5 py-4 sm:grid-cols-[minmax(0,1fr)_200px_auto] sm:items-center sm:gap-6">
                  <div className="grid gap-0.5">
                    <span className="font-bold">{e.course_title}</span>
                    <span className="text-sm text-muted">Joined {timeAgo(e.enrolled_at)}{e.completed_at ? ` · finished ${timeAgo(e.completed_at)}` : ""}</span>
                  </div>
                  <div className="grid gap-1"><ProgressBar value={e.percent} /><span className="font-mono text-xs text-muted">{e.lessons_completed}/{e.lessons_total} · {e.percent}%</span></div>
                  <StatusBadge status={e.status} />
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}
    </>
  );
}
