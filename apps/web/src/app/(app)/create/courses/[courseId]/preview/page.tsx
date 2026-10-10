"use client";
// Preview: the course exactly as a learner will see it (the draft if there is one, otherwise the live version).
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import type { CourseDetail, LessonDetail } from "@shared/index";

import { LessonBody } from "@/components/blocks/BlockView";
import { Alert, Button, ErrorState, Loading, cx } from "@/components/ui";
import { useApi } from "@/lib/hooks";

function Preview() {
  const { courseId } = useParams<{ courseId: string }>();
  const params = useSearchParams();
  const router = useRouter();
  const course = useApi<CourseDetail>(`/courses/${courseId}`);
  const all = course.data?.modules.flatMap((m) => m.lessons) ?? [];
  const lessonId = params.get("lesson") ?? all[0]?.id ?? null;
  const lesson = useApi<LessonDetail>(lessonId ? `/lessons/${lessonId}` : null);

  if (course.loading) return <Loading />;
  if (course.error || !course.data) return <ErrorState error={course.error!} />;
  const c = course.data;
  const idx = all.findIndex((l) => l.id === lessonId);
  const go = (id: string) => router.replace(`/create/courses/${courseId}/preview?lesson=${id}`);

  return (
    <div className="grid gap-5">
      <Alert tone="warn" title={`Preview · version ${c.version?.version_number ?? "?"} (${c.version?.status === "draft" ? "draft" : "live"})`}
             action={<Link className="font-bold underline" href={lessonId ? `/create/courses/${courseId}/lessons/${lessonId}` : `/create/courses/${courseId}`}>Back to editing</Link>}>
        This is what learners will see. Progress isn&apos;t recorded in preview.
      </Alert>
      <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
        <nav aria-label="Lessons" className="grid content-start gap-4">
          <h2 className="text-xl font-extrabold">{c.title}</h2>
          {c.modules.map((m, mi) => (
            <div key={m.id} className="grid gap-1">
              <p className="eyebrow text-muted">Module {mi + 1} · {m.title}</p>
              {m.lessons.map((l) => (
                <button key={l.id} onClick={() => go(l.id)} aria-current={l.id === lessonId ? "page" : undefined}
                        className={cx("rounded-lg px-3 py-1.5 text-left text-[15px] font-semibold", l.id === lessonId ? "bg-violet text-white" : "hover:bg-lavender")}>
                  {l.title}
                </button>
              ))}
            </div>
          ))}
        </nav>
        <article className="grid content-start gap-6 rounded-[24px] border-2 border-line bg-surface p-6 sm:p-10">
          {!lessonId ? <p className="text-muted">Add a lesson to preview it.</p> : lesson.loading ? <Loading /> : lesson.data && (
            <>
              <header className="grid gap-2 border-b-2 border-line pb-5">
                <p className="eyebrow text-violet">Lesson {idx + 1} of {all.length} · about {lesson.data.estimated_minutes} min</p>
                <h1 className="text-3xl font-extrabold sm:text-4xl">{lesson.data.title}</h1>
              </header>
              <LessonBody blocks={lesson.data.blocks} />
              <div className="flex justify-between gap-3 border-t-2 border-line pt-5">
                <Button variant="ghost" disabled={idx <= 0} onClick={() => go(all[idx - 1].id)}>← Previous</Button>
                {idx < all.length - 1 ? <Button variant="primary" onClick={() => go(all[idx + 1].id)}>Ready for what&apos;s next? →</Button>
                                      : <Button variant="primary" disabled>Complete lesson ✓</Button>}
              </div>
            </>
          )}
        </article>
      </div>
    </div>
  );
}

export default function PreviewPage() {
  return <Suspense><Preview /></Suspense>;
}
