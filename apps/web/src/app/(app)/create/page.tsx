"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import type { CourseSummary, DocumentT } from "@shared/index";

import { CourseCard, NewCourseButton } from "@/components/courses";
import { Alert, Card, EmptyState, ErrorState, Loading, PageHeader, StatusBadge } from "@/components/ui";
import { fileSize, useApi } from "@/lib/hooks";
import { useSession } from "@/lib/session";

function Dashboard() {
  const { me, workspace } = useSession();
  const welcome = useSearchParams().get("welcome");
  const org = workspace?.organization_id;
  const courses = useApi<CourseSummary[]>(org ? `/courses?organization_id=${org}` : null);
  const docs = useApi<DocumentT[]>(org ? `/documents?organization_id=${org}` : null);
  const first = me?.profile.display_name.split(" ")[0];

  if (!workspace) return <EmptyState title="You don't have a workspace yet" action={<Link className="font-bold text-violet" href="/onboarding">Create one →</Link>} />;
  const list = courses.data ?? [];
  const published = list.filter((c) => c.status === "published").length;

  return (
    <>
      <PageHeader eyebrow={workspace.organization_name} title={`Hi ${first}. What will you unbox today?`} actions={<NewCourseButton />} />
      {welcome && <div className="mb-6"><Alert tone="good" title="Your workspace is ready">Start by creating a course. Add modules and lessons, then publish when it&apos;s ready.</Alert></div>}
      <div className="mb-8 grid gap-4 sm:grid-cols-3">
        {[["Courses", list.length], ["Published", published], ["Documents", docs.data?.length ?? 0]].map(([label, n]) => (
          <Card key={label as string} className="grid gap-1">
            <span className="eyebrow text-muted">{label}</span>
            <span className="font-display text-4xl font-extrabold">{courses.loading ? "…" : n}</span>
          </Card>
        ))}
      </div>
      <section className="grid gap-4">
        <div className="flex items-baseline justify-between gap-4">
          <h2 className="text-2xl font-extrabold">My courses</h2>
          {list.length > 6 && <Link href="/create/courses" className="font-bold text-violet hover:underline">See all →</Link>}
        </div>
        {courses.loading ? <Loading /> : courses.error ? <ErrorState error={courses.error} onRetry={() => courses.reload()} /> :
          list.length === 0 ? (
            <EmptyState icon="🧊" title="No courses yet" action={<NewCourseButton size="lg" />}>
              Build your first course by hand: a module, a lesson, some content. Once it reads well, publish it for learners.
            </EmptyState>
          ) : <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{list.slice(0, 6).map((c) => <CourseCard key={c.id} course={c} />)}</div>}
      </section>
      {(docs.data?.length ?? 0) > 0 && (
        <section className="mt-10 grid gap-3">
          <div className="flex items-baseline justify-between"><h2 className="text-2xl font-extrabold">Recent documents</h2>
            <Link href="/create/documents" className="font-bold text-violet hover:underline">All documents →</Link></div>
          <Card className="divide-y-2 divide-line p-0">
            {docs.data!.slice(0, 4).map((d) => (
              <div key={d.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
                <span className="font-semibold">{d.title}</span>
                <span className="flex items-center gap-3 font-mono text-xs text-muted">{fileSize(d.file_size)}<StatusBadge status={d.processing_status} /></span>
              </div>
            ))}
          </Card>
        </section>
      )}
    </>
  );
}

export default function CreatePage() {
  return <Suspense><Dashboard /></Suspense>;
}
