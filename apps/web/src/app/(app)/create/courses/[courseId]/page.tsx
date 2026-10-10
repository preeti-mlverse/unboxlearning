"use client";
// The manual course editor: details, modules and lessons, source documents, versions, preview and publish.
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import type { CourseDetail, DocumentT, ModuleT } from "@shared/index";

import { DocumentRow, Uploader, openDocument, useDocumentPolling } from "@/components/documents";
import { EditableText } from "@/components/EditableText";
import { Alert, Button, Card, ErrorState, Loading, LinkButton, Modal, Select, StatusBadge, Textarea, cx } from "@/components/ui";
import { ApiError, del, patch, post, put } from "@/lib/api";
import { timeAgo, useApi } from "@/lib/hooks";

export default function CourseEditorPage() {
  const { courseId } = useParams<{ courseId: string }>();
  const router = useRouter();
  const course = useApi<CourseDetail>(`/courses/${courseId}`);
  const docs = useApi<DocumentT[]>(`/documents?course_id=${courseId}&purpose=source`);
  useDocumentPolling(docs.data, docs.reload);
  const [problems, setProblems] = useState<string[]>([]);
  const [notice, setNotice] = useState<{ tone: "good" | "bad"; text: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  if (course.loading) return <Loading />;
  if (course.error || !course.data) {
    return course.error?.status === 404
      ? <Alert tone="bad" title="Course not found">It may have been deleted, or it belongs to another workspace. <Link className="underline" href="/create/courses">Back to courses</Link></Alert>
      : <ErrorState error={course.error!} onRetry={() => course.reload()} />;
  }
  const c = course.data;
  const editable = c.can_edit;
  const live = c.versions.find((v) => v.status === "published");

  async function run(key: string, fn: () => Promise<unknown>, ok?: string) {
    setBusy(key);
    setNotice(null);
    try {
      await fn();
      await course.reload(true);
      if (ok) setNotice({ tone: "good", text: ok });
    } catch (e) {
      if (e instanceof ApiError && e.code === "PUBLISH_BLOCKED") setProblems(e.problems);
      else setNotice({ tone: "bad", text: e instanceof ApiError ? e.message : "Something went wrong." });
    } finally {
      setBusy(null);
    }
  }

  const publish = () => { setProblems([]); return run("publish", () => post(`/courses/${courseId}/publish`), "Published. Learners can now find and join this version."); };

  return (
    <div className="grid gap-6">
      <nav aria-label="Breadcrumb" className="font-mono text-xs text-muted"><Link href="/create/courses" className="hover:text-ink">Courses</Link> / {c.title}</nav>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="grid gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={c.status} />
            {c.version && <span className="font-mono text-xs text-muted">Version {c.version.version_number} · {c.version.status === "draft" ? "draft" : "live"}</span>}
          </div>
          <h1 className="text-3xl font-extrabold sm:text-4xl">
            <EditableText label="course title" value={c.title} disabled={!editable && !c.current_published_version_id}
                          onSave={(title) => run("title", () => patch(`/courses/${courseId}`, { title }))} />
          </h1>
          <p className="text-sm text-muted">Last edited {timeAgo(c.updated_at)}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <LinkButton href={`/create/courses/${courseId}/preview`} variant="ghost">Preview</LinkButton>
          {editable ? (
            <Button variant="primary" busy={busy === "publish"} onClick={publish}>{live ? `Publish version ${c.version?.version_number}` : "Publish"}</Button>
          ) : (
            <Button variant="violet" busy={busy === "draft"} onClick={() => run("draft", () => post(`/courses/${courseId}/versions`), "New draft started. Learners keep seeing the live version until you publish.")}>
              Make changes
            </Button>
          )}
        </div>
      </header>

      {notice && <Alert tone={notice.tone}>{notice.text}</Alert>}
      {problems.length > 0 && (
        <Alert tone="warn" title="Almost. Here's what's missing before you can publish:">
          <ul className="mt-1 list-disc pl-5">{problems.map((p) => <li key={p}>{p}</li>)}</ul>
        </Alert>
      )}
      {!editable && live && (
        <Alert tone="info" title={`Version ${live.version_number} is live`}>
          This is what learners see, so it can&apos;t be changed directly. Choose <b>Make changes</b> to work on a new version; enrolled learners stay on theirs until they choose to update.
        </Alert>
      )}
      {editable && c.has_unpublished_changes && (
        <Alert tone="warn" title="You're editing a new draft"
               action={<Button size="sm" variant="ghost" busy={busy === "discard"} onClick={() => run("discard", () => del(`/courses/${courseId}/draft`), "Draft discarded.")}>Discard draft</Button>}>
          Changes here aren&apos;t visible to learners until you publish version {c.version?.version_number}.
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="grid content-start gap-6">
          <Structure course={c} editable={editable} run={run} busy={busy} />
        </div>
        <aside className="grid content-start gap-6">
          <Details course={c} run={run} busy={busy} />
          <Card className="grid gap-3">
            <h2 className="text-lg font-extrabold">Source material</h2>
            <p className="text-sm text-muted">The documents this course is built from. They stay private to your workspace.</p>
            <Uploader compact target={{ courseId: c.id }} onUploaded={() => docs.reload(true)} />
            {docs.data && docs.data.length > 0 && (
              <ul className="-mx-5 divide-y-2 divide-line border-t-2 border-line">
                {docs.data.map((d) => <DocumentRow key={d.id} doc={d} onOpen={() => openDocument(d)}
                                                   onRetry={d.job_id ? () => post(`/jobs/${d.job_id}/retry`).then(() => docs.reload(true)) : undefined} />)}
              </ul>
            )}
          </Card>
          <Card className="grid gap-3">
            <h2 className="text-lg font-extrabold">Versions</h2>
            <ol className="grid gap-2">
              {c.versions.map((v) => (
                <li key={v.id} className="flex items-center justify-between gap-2 text-sm">
                  <span className="font-semibold">Version {v.version_number}</span>
                  <span className="flex items-center gap-2 text-xs text-muted">{timeAgo(v.published_at ?? v.created_at)}<StatusBadge status={v.status} /></span>
                </li>
              ))}
            </ol>
            <p className="text-xs text-muted">Older versions are kept, so learners who enrolled earlier never lose their place.</p>
          </Card>
          <Card className="grid gap-3 border-bad/30">
            <h2 className="text-lg font-extrabold">Danger zone</h2>
            {c.status === "published" && (
              <Button variant="ghost" busy={busy === "unpublish"} onClick={() => run("unpublish", () => post(`/courses/${courseId}/unpublish`), "Taken out of the catalog. Enrolled learners keep access.")}>
                Stop new enrollments
              </Button>
            )}
            <Button variant="danger" onClick={() => setConfirmDelete(true)}>Delete course</Button>
          </Card>
        </aside>
      </div>

      <Modal open={confirmDelete} onClose={() => setConfirmDelete(false)} title="Delete this course?"
             footer={<><Button variant="ghost" onClick={() => setConfirmDelete(false)}>Keep it</Button>
                       <Button variant="danger" busy={busy === "delete"} onClick={async () => { setBusy("delete"); await del(`/courses/${courseId}`); router.replace("/create/courses"); }}>Delete course</Button></>}>
        <p>&ldquo;{c.title}&rdquo; will disappear from your courses and the catalog. Learners already enrolled keep their progress records, and a platform admin can restore it if this was a mistake.</p>
      </Modal>
    </div>
  );
}

type Run = (key: string, fn: () => Promise<unknown>, ok?: string) => Promise<void>;

function Details({ course, run, busy }: { course: CourseDetail; run: Run; busy: string | null }) {
  const [description, setDescription] = useState(course.description);
  const [visibility, setVisibility] = useState(course.visibility);
  const dirty = description !== course.description || visibility !== course.visibility;
  return (
    <Card className="grid gap-3">
      <h2 className="text-lg font-extrabold">Details</h2>
      <Textarea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Who it's for and what they'll learn" />
      <Select label="Who can join once it's published" value={visibility} onChange={(e) => setVisibility(e.target.value as typeof visibility)}>
        <option value="public">Anyone with an UnboxEd account</option>
        <option value="organization">Only members of this workspace</option>
      </Select>
      <Button variant="violet" disabled={!dirty} busy={busy === "details"}
              onClick={() => run("details", () => patch(`/courses/${course.id}`, { description, visibility }), "Saved.")}>Save</Button>
    </Card>
  );
}

function Structure({ course, editable, run, busy }: { course: CourseDetail; editable: boolean; run: Run; busy: string | null }) {
  const [newModule, setNewModule] = useState("");
  const modules = course.modules;
  const move = (ids: string[], i: number, d: -1 | 1) => { const next = [...ids]; [next[i], next[i + d]] = [next[i + d], next[i]]; return next; };

  return (
    <section className="grid gap-4" aria-label="Modules and lessons">
      <div className="flex items-baseline justify-between">
        <h2 className="text-2xl font-extrabold">Modules and lessons</h2>
        <span className="font-mono text-xs text-muted">{course.module_count} module{course.module_count === 1 ? "" : "s"} · {course.lesson_count} lesson{course.lesson_count === 1 ? "" : "s"}</span>
      </div>
      {modules.length === 0 && (
        <Card className="text-muted">{editable ? "Start with a module: a chapter or a big idea. Then add lessons inside it." : "This version has no modules."}</Card>
      )}
      {modules.map((m, i) => (
        <ModuleCard key={m.id} module={m} index={i} total={modules.length} editable={editable} run={run} courseId={course.id}
                    onMove={(d) => run("order", () => put(`/courses/${course.id}/modules/order`, { ids: move(modules.map((x) => x.id), i, d) }))} />
      ))}
      {editable && (
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (!newModule.trim()) return;
          run("module", () => post(`/courses/${course.id}/modules`, { title: newModule })).then(() => setNewModule("")); }}>
          <input aria-label="New module title" placeholder="New module title, e.g. Newton's Laws" value={newModule} onChange={(e) => setNewModule(e.target.value)}
                 className="flex-1 rounded-xl border-2 border-dashed border-line bg-surface px-3.5 py-2.5 focus:border-violet focus:outline-none" />
          <Button type="submit" variant="ghost" busy={busy === "module"}>+ Module</Button>
        </form>
      )}
    </section>
  );
}

function ModuleCard({ module: m, index, total, editable, run, courseId, onMove }: {
  module: ModuleT; index: number; total: number; editable: boolean; run: Run; courseId: string; onMove: (d: -1 | 1) => void;
}) {
  const [newLesson, setNewLesson] = useState("");
  const [confirm, setConfirm] = useState(false);
  const lessons = m.lessons;
  const reorder = (i: number, d: -1 | 1) => {
    const ids = lessons.map((l) => l.id);
    [ids[i], ids[i + d]] = [ids[i + d], ids[i]];
    return run("order", () => put(`/modules/${m.id}/lessons/order`, { ids }));
  };

  return (
    <Card as="section" className="grid gap-3 p-0">
      <div className="flex items-center gap-3 border-b-2 border-line px-5 py-3">
        <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-violet font-display font-extrabold text-white">{index + 1}</span>
        <h3 className="min-w-0 flex-1 text-lg font-extrabold">
          <EditableText label="module title" value={m.title} disabled={!editable} onSave={(title) => run("m", () => patch(`/modules/${m.id}`, { title }))} />
        </h3>
        {editable && (
          <div className="flex items-center gap-1">
            <IconBtn label="Move module up" disabled={index === 0} onClick={() => onMove(-1)}>↑</IconBtn>
            <IconBtn label="Move module down" disabled={index === total - 1} onClick={() => onMove(1)}>↓</IconBtn>
            <IconBtn label={`Delete module ${m.title}`} onClick={() => setConfirm(true)}>✕</IconBtn>
          </div>
        )}
      </div>
      <ol className="grid gap-1 px-3">
        {lessons.length === 0 && <li className="px-2 py-2 text-sm text-muted">No lessons yet.</li>}
        {lessons.map((l, i) => (
          <li key={l.id} className="group flex items-center gap-3 rounded-xl px-2 py-2 hover:bg-lavender/60">
            <span className="font-mono text-xs text-muted">{index + 1}.{i + 1}</span>
            <Link href={`/create/courses/${courseId}/lessons/${l.id}`} className="min-w-0 flex-1 truncate font-semibold hover:text-violet">{l.title}</Link>
            <span className="hidden font-mono text-xs text-muted sm:inline">{l.estimated_minutes} min · {l.block_count} block{l.block_count === 1 ? "" : "s"}</span>
            {editable && (
              <span className="flex gap-1 opacity-70 group-hover:opacity-100">
                <IconBtn label="Move lesson up" disabled={i === 0} onClick={() => reorder(i, -1)}>↑</IconBtn>
                <IconBtn label="Move lesson down" disabled={i === lessons.length - 1} onClick={() => reorder(i, 1)}>↓</IconBtn>
                <IconBtn label={`Delete lesson ${l.title}`} onClick={() => { if (confirmDelete(l.title)) run("l", () => del(`/lessons/${l.id}`)); }}>✕</IconBtn>
              </span>
            )}
          </li>
        ))}
      </ol>
      {editable && (
        <form className="flex gap-2 px-5 pb-4" onSubmit={(e) => { e.preventDefault(); if (!newLesson.trim()) return;
          run("lesson", () => post(`/modules/${m.id}/lessons`, { title: newLesson })).then(() => setNewLesson("")); }}>
          <input aria-label={`New lesson in ${m.title}`} placeholder="New lesson title" value={newLesson} onChange={(e) => setNewLesson(e.target.value)}
                 className="flex-1 rounded-xl border-2 border-dashed border-line bg-surface px-3 py-2 text-[15px] focus:border-violet focus:outline-none" />
          <Button type="submit" size="sm" variant="quiet">+ Lesson</Button>
        </form>
      )}
      <Modal open={confirm} onClose={() => setConfirm(false)} title="Delete this module?"
             footer={<><Button variant="ghost" onClick={() => setConfirm(false)}>Keep it</Button>
                       <Button variant="danger" onClick={() => { setConfirm(false); run("m", () => del(`/modules/${m.id}`)); }}>Delete module</Button></>}>
        <p>&ldquo;{m.title}&rdquo; and its {lessons.length} lesson{lessons.length === 1 ? "" : "s"} will be removed from this draft. Published versions aren&apos;t affected.</p>
      </Modal>
    </Card>
  );
}

function confirmDelete(title: string) {
  return window.confirm(`Delete the lesson "${title}" from this draft?`);
}

function IconBtn({ label, onClick, disabled, children }: { label: string; onClick: () => void; disabled?: boolean; children: React.ReactNode }) {
  return (
    <button type="button" aria-label={label} title={label} onClick={onClick} disabled={disabled}
            className={cx("grid size-7 place-items-center rounded-lg text-sm font-bold text-muted hover:bg-surface hover:text-ink disabled:opacity-30")}>
      {children}
    </button>
  );
}
