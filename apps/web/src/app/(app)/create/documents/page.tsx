"use client";
import { useEffect, useState } from "react";
import type { DocumentT } from "@shared/index";

import { DocumentRow, Uploader, openDocument, useDocumentPolling } from "@/components/documents";
import { Alert, Card, EmptyState, ErrorState, Loading, PageHeader } from "@/components/ui";
import { ApiError, del, post } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useSession } from "@/lib/session";

export default function DocumentsPage() {
  const { workspace } = useSession();
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { const t = setTimeout(() => setQuery(q), 250); return () => clearTimeout(t); }, [q]);
  const org = workspace?.organization_id;
  const docs = useApi<DocumentT[]>(org ? `/documents?organization_id=${org}${query ? `&q=${encodeURIComponent(query)}` : ""}` : null);
  useDocumentPolling(docs.data, docs.reload);

  const act = async (fn: () => Promise<unknown>) => {
    setError(null);
    try { await fn(); await docs.reload(true); } catch (e) { setError(e instanceof ApiError ? e.message : "Something went wrong."); }
  };

  return (
    <>
      <PageHeader eyebrow={workspace?.organization_name} title="Documents">
        Textbooks, slide decks, policies and notes your courses are built from. Files are stored privately; only people in this workspace can open them.
      </PageHeader>
      <div className="grid gap-5">
        {org && <Uploader target={{ organizationId: org }} onUploaded={() => docs.reload(true)} />}
        {error && <Alert tone="bad">{error}</Alert>}
        <input type="search" placeholder="Search by name…" aria-label="Search documents" value={q} onChange={(e) => setQ(e.target.value)}
               className="rounded-xl border-2 border-line bg-surface px-3.5 py-2.5 focus:border-violet focus:outline-none" />
        {docs.loading ? <Loading /> : docs.error ? <ErrorState error={docs.error} onRetry={() => docs.reload()} /> :
          !docs.data?.length ? (
            <EmptyState icon="📄" title={query ? "No documents match" : "No documents yet"}>
              {query ? "Try another name." : "Upload a chapter, deck or handbook. We check it and get it ready for the next steps."}
            </EmptyState>
          ) : (
            <Card className="p-0">
              <ul className="divide-y-2 divide-line">
                {docs.data.map((d) => (
                  <DocumentRow key={d.id} doc={d} onOpen={() => act(() => openDocument(d))}
                               onRetry={d.job_id ? () => act(() => post(`/jobs/${d.job_id}/retry`)) : undefined}
                               onDelete={() => { if (window.confirm(`Delete “${d.title}”?`)) act(() => del(`/documents/${d.id}`)); }} />
                ))}
              </ul>
            </Card>
          )}
      </div>
    </>
  );
}
