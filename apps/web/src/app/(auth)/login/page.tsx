"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import type { AuthResult } from "@shared/index";

import { Alert, Button, Input } from "@/components/ui";
import { ApiError, post } from "@/lib/api";
import { fieldErrors, loginSchema, safeNext } from "@/lib/forms";
import { HOME, useSession } from "@/lib/session";

function LoginForm() {
  const params = useSearchParams();
  const router = useRouter();
  const { reload } = useSession();
  const [form, setForm] = useState({ identifier: "", password: "", remember: true });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [show, setShow] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const parsed = loginSchema.safeParse(form);
    setErrors(fieldErrors(parsed));
    if (!parsed.success) return;
    setBusy(true);
    setError(null);
    try {
      const res = await post<AuthResult>("/auth/login", parsed.data);
      await reload();
      router.replace(safeNext(params.get("next")) ?? HOME[res.user.home]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className="grid gap-5">
      <div className="grid gap-2">
        <p className="eyebrow text-violet">Welcome back</p>
        <h1 className="text-4xl font-extrabold">Log in</h1>
      </div>
      {params.get("bye") && <Alert tone="good">You&apos;re logged out.</Alert>}
      {params.get("reset") && <Alert tone="good">Password changed. Log in with your new one.</Alert>}
      {error && <Alert tone="bad">{error}</Alert>}
      <Input label="Email or mobile" name="identifier" autoComplete="username" placeholder="you@example.com or 98765 43210"
             value={form.identifier} error={errors.identifier} onChange={(e) => setForm({ ...form, identifier: e.target.value })} autoFocus />
      <div className="relative">
        <Input label="Password" name="password" type={show ? "text" : "password"} autoComplete="current-password"
               value={form.password} error={errors.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        <button type="button" onClick={() => setShow(!show)} className="absolute right-3 top-[34px] text-sm font-bold text-violet"
                aria-label={show ? "Hide password" : "Show password"}>{show ? "Hide" : "Show"}</button>
      </div>
      <div className="flex items-center justify-between gap-3 text-sm">
        <label className="flex items-center gap-2 font-semibold">
          <input type="checkbox" className="size-4 accent-violet" checked={form.remember}
                 onChange={(e) => setForm({ ...form, remember: e.target.checked })} /> Keep me logged in
        </label>
        <Link href="/forgot-password" className="font-bold text-violet hover:underline">Forgot password?</Link>
      </div>
      <Button type="submit" variant="primary" size="lg" busy={busy}>Log in</Button>
      <p className="text-center text-muted">New to UnboxEd? <Link href="/signup" className="font-bold text-violet hover:underline">Create an account</Link></p>
    </form>
  );
}

export default function LoginPage() {
  return <Suspense><LoginForm /></Suspense>;
}
