"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import type { Enrollment } from "@shared/index";

import { Alert, Card, EmptyState, ErrorState, LinkButton, Loading, PageHeader, ProgressBar, StatusBadge } from "@/components/ui";
import { timeAgo, useApi } from "@/lib/hooks";
import { useSession } from "@/lib/session";

function EnrollmentCard({ e }: { e: Enrollment }) {
  const href = e.next_lesson_id ? `/learn/courses/${e.course_id}/lessons/${e.next_lesson_id}` : `/learn/courses/${e.course_id}`;
  return (
    <Card className="grid content-start gap-3">
      <div className="flex items-center justify-between gap-2">
        <StatusBadge status={e.status} />
        <span className="font-mono text-xs text-muted">{e.lessons_completed}/{e.lessons_total} lessons</span>
      </div>
      <Link href={`/learn/courses/${e.course_id}`} className="text-xl font-extrabold leading-tight hover:text-violet">{e.course_title}</Link>
      <ProgressBar value={e.percent} label={`${e.course_title} progress`} />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm text-muted">{e.last_activity_at ? `Last studied ${timeAgo(e.last_activity_at)}` : "Not started yet"}</span>
        <LinkButton href={href} size="sm" variant={e.status === "completed" ? "ghost" : "primary"}>
          {e.status === "completed" ? "Refresh this" : e.lessons_completed ? "Continue" : "Start"}
        </LinkButton>
      </div>
      {e.newer_version_available && <p className="text-xs font-semibold text-violet">An updated version of this course is available.</p>}
    </Card>
  );
}

function MyLearning() {
  const { me } = useSession();
  const welcome = useSearchParams().get("welcome");
  const list = useApi<Enrollment[]>("/enrollments");
  const items = list.data ?? [];
  const current = items.find((e) => e.status === "active" && e.lessons_completed > 0) ?? items.find((e) => e.status === "active");

  return (
    <>
      <PageHeader eyebrow="My learning" title={`Welcome${welcome ? "" : " back"}, ${me?.profile.display_name.split(" ")[0]}`}
                  actions={<LinkButton href="/learn/catalog" variant="ghost">Find a course</LinkButton>} />
      {welcome && <div className="mb-6"><Alert tone="good" title="You're in">Pick a course to start. Your progress saves as you go.</Alert></div>}
      {list.loading ? <Loading /> : list.error ? <ErrorState error={list.error} onRetry={() => list.reload()} /> : items.length === 0 ? (
        <EmptyState icon="🌱" title="Nothing here yet" action={<LinkButton href="/learn/catalog" variant="primary">Browse courses</LinkButton>}>
          Join a course and it shows up here, with where you left off.
        </EmptyState>
      ) : (
        <div className="grid gap-8">
          {current && (
            <section className="relative overflow-hidden rounded-[26px] bg-uv p-6 text-white sm:p-8">
              <div aria-hidden className="cube-field pointer-events-none absolute inset-0 opacity-[0.07]" />
              <div className="relative grid gap-3">
                <p className="eyebrow text-[#A99EF0]">Continue learning</p>
                <h2 className="text-3xl font-extrabold">{current.course_title}</h2>
                <div className="max-w-md"><ProgressBar value={current.percent} /></div>
                <p className="text-[#D9D2FF]">{current.lessons_completed} of {current.lessons_total} lessons done</p>
                <div><LinkButton variant="primary" href={current.next_lesson_id ? `/learn/courses/${current.course_id}/lessons/${current.next_lesson_id}` : `/learn/courses/${current.course_id}`}>
                  Ready for what&apos;s next? →</LinkButton></div>
              </div>
            </section>
          )}
          <section className="grid gap-4">
            <h2 className="text-2xl font-extrabold">My courses</h2>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{items.map((e) => <EnrollmentCard key={e.id} e={e} />)}</div>
          </section>
        </div>
      )}
    </>
  );
}

export default function LearnPage() {
  return <Suspense><MyLearning /></Suspense>;
}
