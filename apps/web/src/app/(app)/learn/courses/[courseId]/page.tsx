"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import type { LearnCourse } from "@shared/index";

import { Alert, Button, Card, ErrorState, LinkButton, Loading, ProgressBar, StatusBadge } from "@/components/ui";
import { post } from "@/lib/api";
import { useApi } from "@/lib/hooks";

export default function LearnCoursePage() {
  const { courseId } = useParams<{ courseId: string }>();
  const course = useApi<LearnCourse>(`/learn/courses/${courseId}`);
  const [switching, setSwitching] = useState(false);

  if (course.loading) return <Loading />;
  if (course.error?.code === "NOT_ENROLLED") {
    return <Alert tone="info" title="You haven't joined this course" action={<LinkButton href="/learn/catalog" size="sm">Find it in the catalog</LinkButton>}>Join it to start learning.</Alert>;
  }
  if (course.error || !course.data) return <ErrorState error={course.error!} onRetry={() => course.reload()} />;
  const c = course.data;
  const status = Object.fromEntries(c.progress.map((p) => [p.lesson_id, p.status]));
  let n = 0;

  return (
    <div className="grid gap-6">
      <nav className="font-mono text-xs text-muted"><Link href="/learn" className="hover:text-ink">My learning</Link> / {c.course_title}</nav>
      <header className="grid gap-4 rounded-[26px] border-2 border-line bg-surface p-6 sm:p-8">
        <div className="flex flex-wrap items-center gap-2"><StatusBadge status={c.status} /><span className="font-mono text-xs text-muted">Version {c.version_number}</span></div>
        <h1 className="text-3xl font-extrabold sm:text-4xl">{c.course_title}</h1>
        {c.description && <p className="max-w-2xl text-muted">{c.description}</p>}
        <div className="grid max-w-lg gap-1"><ProgressBar value={c.percent} /><p className="text-sm text-muted">{c.lessons_completed} of {c.lessons_total} lessons · {c.percent}%</p></div>
        {c.next_lesson_id && <div><LinkButton href={`/learn/courses/${courseId}/lessons/${c.next_lesson_id}`} variant="primary">{c.lessons_completed ? "Continue" : "Start the first lesson"} →</LinkButton></div>}
        {c.status === "completed" && <Alert tone="good" title="Course complete">You finished every lesson. Open any lesson to refresh it.</Alert>}
      </header>
      {c.newer_version_available && (
        <Alert tone="info" title="This course has been updated"
               action={<Button size="sm" variant="violet" busy={switching} onClick={async () => { setSwitching(true); await post(`/enrollments/${c.id}/switch-to-latest`); await course.reload(); setSwitching(false); }}>Switch to the new version</Button>}>
          Lessons you&apos;ve finished stay finished when you switch.
        </Alert>
      )}
      {c.modules.map((m, mi) => (
        <Card as="section" key={m.id} className="grid gap-2">
          <h2 className="text-xl font-extrabold"><span className="text-muted">Module {mi + 1} · </span>{m.title}</h2>
          <ol className="grid gap-1">
            {m.lessons.map((l) => {
              n += 1;
              const s = status[l.id] ?? "not_started";
              return (
                <li key={l.id}>
                  <Link href={`/learn/courses/${courseId}/lessons/${l.id}`} className="flex items-center gap-3 rounded-xl px-2 py-2.5 hover:bg-lavender">
                    <span aria-hidden className={`grid size-7 shrink-0 place-items-center rounded-full text-xs font-bold ${s === "completed" ? "bg-good text-white" : s === "in_progress" ? "bg-violet text-white" : "bg-line text-muted"}`}>
                      {s === "completed" ? "✓" : n}
                    </span>
                    <span className="flex-1 font-semibold">{l.title}</span>
                    <span className="font-mono text-xs text-muted">{l.estimated_minutes} min</span>
                    <span className="sr-only">{s.replace("_", " ")}</span>
                  </Link>
                </li>
              );
            })}
          </ol>
        </Card>
      ))}
    </div>
  );
}
