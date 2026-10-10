"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { CourseSummary } from "@shared/index";

import { ApiError, post } from "@/lib/api";
import { timeAgo } from "@/lib/hooks";
import { useSession } from "@/lib/session";

import { Alert, Button, Input, Modal, StatusBadge, Textarea } from "./ui";

export function CourseCard({ course }: { course: CourseSummary }) {
  return (
    <Link href={`/create/courses/${course.id}`}
          className="group grid content-start gap-3 rounded-[22px] border-2 border-line bg-surface p-5 shadow-[0_5px_0_var(--line)] transition hover:-translate-y-0.5 hover:border-violet">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={course.status} />
        {course.has_unpublished_changes && <StatusBadge status="draft" label="Unpublished changes" />}
      </div>
      <h3 className="text-xl font-extrabold leading-tight group-hover:text-violet">{course.title}</h3>
      {course.description && <p className="line-clamp-2 text-[15px] text-muted">{course.description}</p>}
      <p className="font-mono text-xs text-muted">
        {course.module_count} module{course.module_count === 1 ? "" : "s"} · {course.lesson_count} lesson{course.lesson_count === 1 ? "" : "s"}
        {" · "}edited {timeAgo(course.updated_at)}
      </p>
    </Link>
  );
}

export function NewCourseButton({ size = "md" }: { size?: "md" | "lg" }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const { workspace } = useSession();
  const router = useRouter();

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (title.trim().length < 2) { setError("Give the course a title."); return; }
    setBusy(true);
    try {
      const c = await post<CourseSummary>("/courses", { title, description, organization_id: workspace?.organization_id });
      router.push(`/create/courses/${c.id}?new=1`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setBusy(false);
    }
  }

  return (
    <>
      <Button variant="primary" size={size} onClick={() => setOpen(true)}>+ Create course</Button>
      <Modal open={open} onClose={() => setOpen(false)} title="Create a course"
             footer={<><Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
                       <Button variant="violet" busy={busy} onClick={create}>Create course</Button></>}>
        <form onSubmit={create} className="grid gap-4">
          {error && <Alert tone="bad">{error}</Alert>}
          <Input label="Course title" placeholder="e.g. Force and Laws of Motion" value={title} onChange={(e) => setTitle(e.target.value)} autoFocus />
          <Textarea label="Short description (optional)" placeholder="Who it's for and what they'll be able to do"
                    value={description} onChange={(e) => setDescription(e.target.value)} />
          <p className="text-sm text-muted">It starts as a private draft in {workspace?.organization_name ?? "your workspace"}. Nobody else sees it until you publish.</p>
        </form>
      </Modal>
    </>
  );
}
