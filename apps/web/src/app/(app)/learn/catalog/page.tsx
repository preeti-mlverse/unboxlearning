"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { CatalogCourse, Enrollment } from "@shared/index";

import { Alert, Button, Card, EmptyState, ErrorState, LinkButton, Loading, PageHeader } from "@/components/ui";
import { ApiError, post } from "@/lib/api";
import { useApi } from "@/lib/hooks";

export default function CatalogPage() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { const t = setTimeout(() => setQuery(q), 250); return () => clearTimeout(t); }, [q]);
  const list = useApi<CatalogCourse[]>(`/catalog${query ? `?q=${encodeURIComponent(query)}` : ""}`);

  async function join(c: CatalogCourse) {
    setBusy(c.id);
    setError(null);
    try {
      const e = await post<Enrollment>(`/courses/${c.id}/enroll`);
      router.push(e.next_lesson_id ? `/learn/courses/${c.id}/lessons/${e.next_lesson_id}` : `/learn/courses/${c.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setBusy(null);
    }
  }

  return (
    <>
      <PageHeader eyebrow="Find a course" title="What do you want to understand?" />
      <input type="search" placeholder="Search courses…" aria-label="Search courses" value={q} onChange={(e) => setQ(e.target.value)}
             className="mb-6 w-full rounded-xl border-2 border-line bg-surface px-3.5 py-3 focus:border-violet focus:outline-none" />
      {error && <div className="mb-4"><Alert tone="bad">{error}</Alert></div>}
      {list.loading ? <Loading /> : list.error ? <ErrorState error={list.error} onRetry={() => list.reload()} /> : !list.data?.length ? (
        <EmptyState icon="🔍" title={query ? "No courses match" : "No courses published yet"}>
          {query ? "Try a different word." : "When creators publish courses, they appear here."}
        </EmptyState>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {list.data.map((c) => (
            <Card key={c.id} className="grid content-start gap-3">
              <p className="eyebrow text-muted">{c.organization_name}</p>
              <h2 className="text-xl font-extrabold leading-tight">{c.title}</h2>
              {c.description && <p className="line-clamp-3 text-[15px] text-muted">{c.description}</p>}
              <p className="font-mono text-xs text-muted">{c.module_count} module{c.module_count === 1 ? "" : "s"} · {c.lesson_count} lesson{c.lesson_count === 1 ? "" : "s"} · about {c.estimated_minutes} min</p>
              {c.enrollment_id
                ? <LinkButton href={`/learn/courses/${c.id}`} variant="ghost">Continue</LinkButton>
                : <Button variant="primary" busy={busy === c.id} onClick={() => join(c)}>Join course</Button>}
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
