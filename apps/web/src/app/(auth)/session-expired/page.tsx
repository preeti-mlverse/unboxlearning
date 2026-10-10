"use client";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { LinkButton } from "@/components/ui";
import { safeNext } from "@/lib/forms";

function Expired() {
  const next = safeNext(useSearchParams().get("next"));
  return (
    <div className="grid gap-5">
      <span className="text-5xl" aria-hidden>⏳</span>
      <h1 className="text-4xl font-extrabold">Your session has ended</h1>
      <p className="text-muted">For your security we log you out after a while. Log in again and we&apos;ll take you back to where you were.</p>
      <LinkButton href={next ? `/login?next=${encodeURIComponent(next)}` : "/login"} variant="primary" size="lg">Log in again</LinkButton>
    </div>
  );
}

export default function SessionExpiredPage() {
  return <Suspense><Expired /></Suspense>;
}
