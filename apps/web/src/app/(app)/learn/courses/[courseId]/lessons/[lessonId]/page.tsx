"use client";
// The lesson player: read the lesson, mark it complete, move on. Opening a lesson marks it "in progress".
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { Enrollment, LearnLesson } from "@shared/index";

import { LessonBody } from "@/components/blocks/BlockView";
import { Alert, Button, ErrorState, LinkButton, Loading } from "@/components/ui";
import { ApiError, put } from "@/lib/api";
import { useApi } from "@/lib/hooks";

export default function LessonPlayerPage() {
  const { courseId, lessonId } = useParams<{ courseId: string; lessonId: string }>();
  const router = useRouter();
  const data = useApi<LearnLesson>(`/learn/courses/${courseId}/lessons/${lessonId}`);
  const [completing, setCompleting] = useState(false);
  const [finished, setFinished] = useState<Enrollment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const started = useRef<string | null>(null);

  useEffect(() => {
    const d = data.data;
    if (!d || started.current === d.lesson.id || d.progress.status !== "not_started") return;
    started.current = d.lesson.id;
    put(`/enrollments/${d.enrollment_id}/progress/${d.lesson.id}`, { status: "in_progress" }).catch(() => {});
  }, [data.data]);

  if (data.loading) return <Loading />;
  if (data.error?.code === "NOT_ENROLLED") return <Alert tone="info" title="Join this course first" action={<LinkButton size="sm" href="/learn/catalog">Find it</LinkButton>}>Lessons open once you&apos;ve joined.</Alert>;
  if (data.error || !data.data) return <ErrorState error={data.error!} onRetry={() => data.reload()} />;
  const d = data.data;
  const done = d.progress.status === "completed";

  async function complete() {
    setCompleting(true);
    setError(null);
    try {
      const e = await put<Enrollment>(`/enrollments/${d.enrollment_id}/progress/${d.lesson.id}`, { status: "completed" });
      if (d.next_lesson_id) router.push(`/learn/courses/${courseId}/lessons/${d.next_lesson_id}`);
      else { setFinished(e); await data.reload(true); }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save your progress. Try again.");
    } finally {
      setCompleting(false);
    }
  }

  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      <nav className="flex flex-wrap items-center justify-between gap-2 font-mono text-xs text-muted">
        <span><Link href={`/learn/courses/${courseId}`} className="hover:text-ink">{d.course_title}</Link> / {d.module_title}</span>
        <span>Lesson {d.position} of {d.total}</span>
      </nav>
      <div className="h-2 overflow-hidden rounded-full bg-line" aria-hidden><div className="h-full bg-violet" style={{ width: `${(d.position / d.total) * 100}%` }} /></div>
      <article className="grid gap-6 rounded-[26px] border-2 border-line bg-surface p-6 sm:p-10">
        <header className="grid gap-2 border-b-2 border-line pb-5">
          <p className="eyebrow text-violet">About {d.lesson.estimated_minutes} min{done ? " · completed" : ""}</p>
          <h1 className="text-3xl font-extrabold sm:text-4xl">{d.lesson.title}</h1>
        </header>
        <LessonBody blocks={d.lesson.blocks} />
      </article>
      {error && <Alert tone="bad">{error}</Alert>}
      {finished ? (
        <Alert tone="good" title={finished.status === "completed" ? "Course complete! 🎉" : "Lesson complete"}
               action={<LinkButton size="sm" href={`/learn/courses/${courseId}`}>See the course</LinkButton>}>
          {finished.status === "completed" ? `You finished all ${finished.lessons_total} lessons.` : `${finished.lessons_completed} of ${finished.lessons_total} lessons done.`}
        </Alert>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3">
          {d.previous_lesson_id ? <LinkButton variant="ghost" href={`/learn/courses/${courseId}/lessons/${d.previous_lesson_id}`}>← Previous</LinkButton> : <span />}
          {done && d.next_lesson_id
            ? <LinkButton variant="primary" href={`/learn/courses/${courseId}/lessons/${d.next_lesson_id}`}>Ready for what&apos;s next? →</LinkButton>
            : <Button variant="primary" size="lg" busy={completing} onClick={complete} disabled={done && !d.next_lesson_id}>
                {done ? "Completed ✓" : d.next_lesson_id ? "Complete and continue →" : "Complete lesson ✓"}
              </Button>}
        </div>
      )}
    </div>
  );
}
