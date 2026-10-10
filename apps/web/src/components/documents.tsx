"use client";
// Upload with progress, plus a list that keeps checking documents that are still being processed.
import { useCallback, useRef, useState } from "react";
import type { ApiErrorBody, DocumentT } from "@shared/index";

import { post } from "@/lib/api";
import { fileSize, timeAgo, usePoll } from "@/lib/hooks";

import { Alert, Button, StatusBadge, cx } from "./ui";

const SOURCE_EXT = ["pdf", "docx", "pptx", "txt", "md"];
const IMAGE_EXT = ["png", "jpg", "jpeg", "webp"];
const MAX_MB = 50;

export type UploadTarget = { organizationId?: string; courseId?: string; purpose?: "source" | "asset" };

export function uploadFile(file: File, target: UploadTarget, onProgress: (pct: number) => void): Promise<DocumentT> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file);
    form.append("purpose", target.purpose ?? "source");
    if (target.organizationId) form.append("organization_id", target.organizationId);
    if (target.courseId) form.append("course_id", target.courseId);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/documents");
    xhr.withCredentials = true;
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(Math.round((e.loaded / e.total) * 100));
    xhr.onload = () => {
      let body: unknown = null;
      try { body = JSON.parse(xhr.responseText); } catch { /* not JSON */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as DocumentT);
      else reject(new Error((body as ApiErrorBody | null)?.error?.message ?? "We couldn't upload this file."));
    };
    xhr.onerror = () => reject(new Error("The upload was interrupted. Check your connection and try again."));
    xhr.send(form);
  });
}

function check(file: File, purpose: "source" | "asset"): string | null {
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  const allowed = purpose === "asset" ? IMAGE_EXT : [...SOURCE_EXT, ...IMAGE_EXT];
  if (!allowed.includes(ext)) return `${file.name}: that kind of file isn't supported yet (use ${allowed.join(", ").toUpperCase()}).`;
  if (file.size === 0) return `${file.name} is empty.`;
  if (file.size > MAX_MB * 1024 * 1024) return `${file.name} is larger than ${MAX_MB} MB.`;
  return null;
}

export function Uploader({ target, onUploaded, compact }: { target: UploadTarget; onUploaded: (d: DocumentT) => void; compact?: boolean }) {
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [uploading, setUploading] = useState<{ name: string; pct: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const purpose = target.purpose ?? "source";

  const handle = useCallback(async (files: FileList | null) => {
    if (!files?.length) return;
    setError(null);
    for (const file of Array.from(files)) {
      const problem = check(file, purpose);
      if (problem) { setError(problem); continue; }
      setUploading({ name: file.name, pct: 0 });
      try {
        onUploaded(await uploadFile(file, target, (pct) => setUploading({ name: file.name, pct })));
      } catch (e) {
        setError(`${file.name}: ${(e as Error).message}`);
      }
    }
    setUploading(null);
    if (input.current) input.current.value = "";
  }, [onUploaded, purpose, target]);

  return (
    <div className="grid gap-2">
      <div onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
           onDrop={(e) => { e.preventDefault(); setDrag(false); handle(e.dataTransfer.files); }}
           className={cx("grid justify-items-center gap-2 rounded-[22px] border-2 border-dashed text-center transition",
                         compact ? "px-4 py-5" : "px-6 py-10", drag ? "border-violet bg-lavender" : "border-line bg-surface")}>
        {uploading ? (
          <div className="grid w-full max-w-sm gap-2" role="status">
            <p className="font-semibold">Uploading {uploading.name}… {uploading.pct}%</p>
            <div className="h-2 overflow-hidden rounded-full bg-line"><div className="h-full bg-violet transition-[width]" style={{ width: `${uploading.pct}%` }} /></div>
          </div>
        ) : (
          <>
            {!compact && <span className="text-3xl" aria-hidden>⇪</span>}
            <p className="font-display text-lg font-bold">{purpose === "asset" ? "Drop an image here" : "Drop a file here"}</p>
            <p className="font-mono text-xs text-muted">{purpose === "asset" ? "PNG · JPG · WEBP" : "PDF · DOCX · PPTX · TXT · MD · images"} · up to {MAX_MB} MB</p>
            <Button size="sm" variant="ghost" onClick={() => input.current?.click()}>Choose a file</Button>
          </>
        )}
        <input ref={input} type="file" hidden multiple={purpose !== "asset"} onChange={(e) => handle(e.target.files)}
               accept={(purpose === "asset" ? IMAGE_EXT : [...SOURCE_EXT, ...IMAGE_EXT]).map((e) => "." + e).join(",")} />
      </div>
      {error && <Alert tone="bad">{error}</Alert>}
    </div>
  );
}

export function DocumentRow({ doc, onRetry, onDelete, onOpen }: { doc: DocumentT; onRetry?: () => void; onDelete?: () => void; onOpen?: () => void }) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
      <div className="grid min-w-0 gap-0.5">
        <span className="truncate font-semibold">{doc.title}</span>
        <span className="font-mono text-xs text-muted">
          {doc.original_filename} · {fileSize(doc.file_size)}{doc.page_count ? ` · ${doc.page_count} pages` : ""} · {timeAgo(doc.created_at)}
        </span>
        {doc.processing_status === "failed" && doc.error && <span className="text-sm text-bad">{doc.error}</span>}
      </div>
      <div className="flex items-center gap-2">
        <StatusBadge status={doc.processing_status} />
        {doc.processing_status === "failed" && onRetry && <Button size="sm" variant="ghost" onClick={onRetry}>Retry</Button>}
        {onOpen && <Button size="sm" variant="quiet" onClick={onOpen}>Open</Button>}
        {onDelete && <Button size="sm" variant="quiet" onClick={onDelete} aria-label={`Delete ${doc.title}`}>Delete</Button>}
      </div>
    </li>
  );
}

/** Keep a document list fresh while any item is still waiting or processing. */
export function useDocumentPolling(docs: DocumentT[] | null, reload: (quiet?: boolean) => void) {
  const busy = (docs ?? []).some((d) => d.processing_status === "queued" || d.processing_status === "processing" || d.processing_status === "uploaded");
  usePoll(useCallback(() => reload(true), [reload]), busy, 2000);
}

export async function openDocument(doc: DocumentT) {
  const { url } = await post<{ url: string }>(`/documents/${doc.id}/download-url`);
  window.open(`/api${url}`, "_blank", "noopener");
}
