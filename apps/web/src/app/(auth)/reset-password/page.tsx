"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { Alert, Button, Input } from "@/components/ui";
import { ApiError, post } from "@/lib/api";
import { password as passwordRule } from "@/lib/forms";

function ResetForm() {
  const token = useSearchParams().get("token") ?? "";
  const router = useRouter();
  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const r = passwordRule.safeParse(pw);
    const errs: Record<string, string> = {};
    if (!r.success) errs.password = r.error.issues[0].message;
    if (pw !== confirm) errs.confirm = "The two passwords don't match.";
    setErrors(errs);
    if (Object.keys(errs).length) return;
    setBusy(true);
    try {
      await post("/auth/reset-password", { token, password: pw });
      router.replace("/login?reset=1");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setBusy(false);
    }
  }

  if (!token) {
    return <Alert tone="bad" title="This link is incomplete">Open the reset link from your email again, or <Link className="underline" href="/forgot-password">ask for a new one</Link>.</Alert>;
  }
  return (
    <form onSubmit={submit} noValidate className="grid gap-5">
      <div className="grid gap-2">
        <p className="eyebrow text-violet">Almost there</p>
        <h1 className="text-4xl font-extrabold">Choose a new password</h1>
      </div>
      {error && <Alert tone="bad" action={<Link href="/forgot-password" className="font-bold underline">Get a new link</Link>}>{error}</Alert>}
      <Input label="New password" type="password" autoComplete="new-password" value={pw} error={errors.password}
             hint="At least 8 characters, with letters and numbers." onChange={(e) => setPw(e.target.value)} autoFocus />
      <Input label="Type it again" type="password" autoComplete="new-password" value={confirm} error={errors.confirm}
             onChange={(e) => setConfirm(e.target.value)} />
      <Button type="submit" variant="primary" size="lg" busy={busy}>Save new password</Button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return <Suspense><ResetForm /></Suspense>;
}
