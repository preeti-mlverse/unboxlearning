"use client";
// Lesson editor: a lesson is an ordered list of typed blocks. Foundation has text and image blocks; each saves
// itself a moment after you stop typing.
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Block, CourseDetail, DocumentT, LessonDetail } from "@shared/index";

import { BlockView } from "@/components/blocks/BlockView";
import { Uploader } from "@/components/documents";
import { EditableText } from "@/components/EditableText";
import { Alert, Button, Card, ErrorState, Input, Loading, LinkButton, Select, Textarea, cx } from "@/components/ui";
import { ApiError, apiUrl, del, get, patch, post, put } from "@/lib/api";
import { useApi } from "@/lib/hooks";

type SaveState = "idle" | "saving" | "saved" | "error";

export default function LessonEditorPage() {
  const { courseId, lessonId } = useParams<{ courseId: string; lessonId: string }>();
  const course = useApi<CourseDetail>(`/courses/${courseId}`);
  const lesson = useApi<LessonDetail>(`/lessons/${lessonId}`);
  const [error, setError] = useState<string | null>(null);

  if (course.loading || lesson.loading) return <Loading />;
  if (lesson.error || !lesson.data || !course.data) return <ErrorState error={lesson.error ?? course.error!} onRetry={() => lesson.reload()} />;

  const c = course.data;
  const l = lesson.data;
  const inDraft = c.can_edit && c.modules.some((m) => m.lessons.some((x) => x.id === l.id));
  const all = c.modules.flatMap((m) => m.lessons.map((x) => ({ ...x, module: m.title })));
  const idx = all.findIndex((x) => x.id === l.id);
  const module = c.modules.find((m) => m.id === l.module_id);

  async function addBlock(type: "text" | "image", position?: number, config?: Record<string, unknown>) {
    setError(null);
    try {
      if (type === "text") await post(`/lessons/${lessonId}/blocks${position ? `?position=${position}` : ""}`, { block_type: "text", config: config ?? { heading: null, body: "" } });
      else if (config) await post(`/lessons/${lessonId}/blocks${position ? `?position=${position}` : ""}`, { block_type: "image", config });
      await lesson.reload(true);
    } catch (e) { setError(e instanceof ApiError ? e.message : "Couldn't add that block."); }
  }

  async function moveBlock(i: number, d: -1 | 1) {
    const ids = l.blocks.map((b) => b.id);
    [ids[i], ids[i + d]] = [ids[i + d], ids[i]];
    await put(`/lessons/${lessonId}/blocks/order`, { ids });
    await lesson.reload(true);
  }

  return (
    <div className="grid gap-6">
      <nav aria-label="Breadcrumb" className="font-mono text-xs text-muted">
        <Link href="/create/courses" className="hover:text-ink">Courses</Link> / <Link href={`/create/courses/${courseId}`} className="hover:text-ink">{c.title}</Link> / {module?.title}
      </nav>
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="grid gap-2">
          <p className="eyebrow text-violet">Lesson {idx + 1} of {all.length}</p>
          <h1 className="text-3xl font-extrabold">
            <EditableText label="lesson title" value={l.title} disabled={!inDraft}
                          onSave={async (title) => { await patch(`/lessons/${lessonId}`, { title }); await lesson.reload(true); }} />
          </h1>
          {inDraft ? (
            <label className="flex items-center gap-2 text-sm text-muted">About
              <input type="number" min={1} max={240} defaultValue={l.estimated_minutes} aria-label="Estimated minutes"
                     onBlur={(e) => { const v = Number(e.target.value); if (v >= 1 && v <= 240 && v !== l.estimated_minutes) patch(`/lessons/${lessonId}`, { estimated_minutes: v }); }}
                     className="w-16 rounded-lg border-2 border-line bg-surface px-2 py-0.5 text-ink" /> minutes
            </label>
          ) : <p className="text-sm text-muted">About {l.estimated_minutes} minutes</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          <LinkButton variant="ghost" href={`/create/courses/${courseId}/preview?lesson=${lessonId}`}>Preview</LinkButton>
          <LinkButton variant="violet" href={`/create/courses/${courseId}`}>Back to course</LinkButton>
        </div>
      </header>

      {!inDraft && <Alert tone="info" title="Read-only">This lesson belongs to a published version. Go back to the course and choose <b>Make changes</b> to edit it.</Alert>}
      {error && <Alert tone="bad">{error}</Alert>}

      <div className="grid gap-4">
        {l.blocks.map((b, i) => inDraft ? (
          <BlockEditor key={b.id} block={b} index={i} total={l.blocks.length} orgId={c.organization_id}
                       onMove={(d) => moveBlock(i, d)} onDelete={async () => { await del(`/blocks/${b.id}`); await lesson.reload(true); }}
                       onInsertText={() => addBlock("text", i + 2)} />
        ) : <Card key={b.id}><BlockView block={b} /></Card>)}
        {l.blocks.length === 0 && <Card className="text-muted">This lesson is empty.</Card>}
      </div>

      {inDraft && <AddBlockBar orgId={c.organization_id} onAdd={(type, config) => addBlock(type, undefined, config)} />}

      <nav className="flex flex-wrap justify-between gap-3 border-t-2 border-line pt-5">
        {idx > 0 ? <Link className="font-bold text-violet hover:underline" href={`/create/courses/${courseId}/lessons/${all[idx - 1].id}`}>← {all[idx - 1].title}</Link> : <span />}
        {idx < all.length - 1 && <Link className="font-bold text-violet hover:underline" href={`/create/courses/${courseId}/lessons/${all[idx + 1].id}`}>{all[idx + 1].title} →</Link>}
      </nav>
    </div>
  );
}

function useAutosave(block: Block) {
  const [state, setState] = useState<SaveState>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latest = useRef(block.config);
  const save = useCallback((config: Record<string, unknown>, delay = 700) => {
    latest.current = config;
    if (timer.current) clearTimeout(timer.current);
    setState("saving");
    timer.current = setTimeout(async () => {
      try {
        await patch(`/blocks/${block.id}`, { block_type: block.block_type, config: latest.current });
        setState("saved");
        setMessage(null);
      } catch (e) {
        setState("error");
        setMessage(e instanceof ApiError ? Object.values(e.fields)[0] ?? e.message : "Couldn't save.");
      }
    }, delay);
  }, [block.id, block.block_type]);
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);
  return { state, message, save };
}

function SaveIndicator({ state, message }: { state: SaveState; message: string | null }) {
  const text = { idle: "", saving: "Saving…", saved: "Saved", error: message ?? "Not saved" }[state];
  return <span aria-live="polite" className={cx("font-mono text-xs", state === "error" ? "text-bad" : "text-muted")}>{text}</span>;
}

function BlockEditor({ block, index, total, orgId, onMove, onDelete, onInsertText }: {
  block: Block; index: number; total: number; orgId: string; onMove: (d: -1 | 1) => void; onDelete: () => void; onInsertText: () => void;
}) {
  const { state, message, save } = useAutosave(block);
  const [config, setConfig] = useState<Record<string, unknown>>(block.config);
  const [preview, setPreview] = useState(false);
  const update = (patchCfg: Record<string, unknown>) => { const next = { ...config, ...patchCfg }; setConfig(next); save(next); };

  return (
    <Card className="grid gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="eyebrow text-violet">{block.block_type === "text" ? "Text" : "Image"} · block {index + 1}</span>
        <div className="flex items-center gap-2">
          <SaveIndicator state={state} message={message} />
          {block.block_type === "text" && <Button size="sm" variant="quiet" onClick={() => setPreview(!preview)}>{preview ? "Edit" : "Preview"}</Button>}
          <Button size="sm" variant="quiet" disabled={index === 0} onClick={() => onMove(-1)} aria-label="Move block up">↑</Button>
          <Button size="sm" variant="quiet" disabled={index === total - 1} onClick={() => onMove(1)} aria-label="Move block down">↓</Button>
          <Button size="sm" variant="quiet" onClick={() => { if (window.confirm("Delete this block?")) onDelete(); }} aria-label="Delete block">Delete</Button>
        </div>
      </div>
      {block.block_type === "text" ? (
        preview ? <BlockView block={{ ...block, config }} /> : (
          <>
            <Input label="Heading (optional)" value={(config.heading as string) ?? ""} onChange={(e) => update({ heading: e.target.value || null })} />
            <Textarea label="Text" rows={7} value={(config.body as string) ?? ""} onChange={(e) => update({ body: e.target.value })}
                      hint="**bold**, *italic*, lists with - or 1., links as [text](https://…). Leave a blank line between paragraphs." />
          </>
        )
      ) : (
        <ImageFields config={config} orgId={orgId} mediaPath={block.media_path ?? null} onChange={update} />
      )}
      <button type="button" onClick={onInsertText} className="justify-self-start text-sm font-bold text-violet hover:underline">+ Text below</button>
    </Card>
  );
}

function ImageFields({ config, mediaPath, onChange, orgId }: { config: Record<string, unknown>; mediaPath: string | null; orgId: string; onChange: (c: Record<string, unknown>) => void }) {
  return (
    <div className="grid gap-3 sm:grid-cols-[200px_minmax(0,1fr)]">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      {mediaPath ? <img src={apiUrl(mediaPath)} alt="" className="w-full rounded-xl border-2 border-line object-contain" /> : <div className="rounded-xl bg-lavender" />}
      <div className="grid gap-3">
        <Input label="Describe the image (alt text)" value={(config.alt as string) ?? ""} onChange={(e) => onChange({ alt: e.target.value })}
               hint="Read aloud to learners who can't see it. Say what matters, e.g. 'Two carts: the one pushed harder moves further'." />
        <Input label="Caption (optional)" value={(config.caption as string) ?? ""} onChange={(e) => onChange({ caption: e.target.value || null })} />
        <Select label="Size" value={(config.size as string) ?? "full"} onChange={(e) => onChange({ size: e.target.value })}>
          <option value="small">Small</option><option value="medium">Medium</option><option value="full">Full width</option>
        </Select>
        <input type="hidden" value={orgId} />
      </div>
    </div>
  );
}

function AddBlockBar({ orgId, onAdd }: { orgId: string; onAdd: (type: "text" | "image", config?: Record<string, unknown>) => Promise<void> }) {
  const [picking, setPicking] = useState(false);
  const [images, setImages] = useState<DocumentT[] | null>(null);
  const [alt, setAlt] = useState("");
  const [chosen, setChosen] = useState<DocumentT | null>(null);
  useEffect(() => { if (picking) get<DocumentT[]>(`/documents?purpose=asset&organization_id=${orgId}`).then(setImages); }, [picking, orgId]);

  return (
    <Card className="grid gap-4 border-dashed">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-bold">Add to this lesson:</span>
        <Button variant="ghost" size="sm" onClick={() => onAdd("text")}>+ Text</Button>
        <Button variant="ghost" size="sm" onClick={() => setPicking(!picking)}>+ Image</Button>
        <span className="text-sm text-muted">More block types (diagrams, practice, quizzes) arrive with the engine.</span>
      </div>
      {picking && (
        <div className="grid gap-4">
          <Uploader compact target={{ organizationId: orgId, purpose: "asset" }} onUploaded={(d) => { setImages((x) => [d, ...(x ?? [])]); setChosen(d); }} />
          {images && images.length > 0 && (
            <div className="grid gap-2">
              <p className="text-sm font-bold">Or pick one you&apos;ve uploaded</p>
              <div className="flex flex-wrap gap-2">
                {images.map((img) => (
                  <button key={img.id} type="button" onClick={() => setChosen(img)}
                          className={cx("rounded-xl border-2 px-3 py-1.5 text-sm font-semibold", chosen?.id === img.id ? "border-violet bg-lavender" : "border-line")}>
                    {img.title}
                  </button>
                ))}
              </div>
            </div>
          )}
          {chosen && (
            <form className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end" onSubmit={async (e) => {
              e.preventDefault();
              if (!alt.trim()) return;
              await onAdd("image", { document_id: chosen.id, alt, caption: null, size: "full" });
              setPicking(false); setChosen(null); setAlt("");
            }}>
              <Input label={`Describe “${chosen.title}” for people who can't see it`} value={alt} onChange={(e) => setAlt(e.target.value)} required />
              <Button type="submit" variant="violet" disabled={!alt.trim()}>Add image</Button>
            </form>
          )}
        </div>
      )}
    </Card>
  );
}
