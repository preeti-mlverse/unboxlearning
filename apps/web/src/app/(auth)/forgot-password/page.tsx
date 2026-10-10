"use client";
import Link from "next/link";
import { useState } from "react";

import { Alert, Button, Input } from "@/components/ui";
import { ApiError, post } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!/^\S+@\S+\.\S+$/.test(email)) { setError("Enter the email you signed up with."); return; }
    setBusy(true);
    setError(null);
    try {
      await post("/auth/forgot-password", { email });
      setSent(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-5">
      <div className="grid gap-2">
        <p className="eyebrow text-violet">Forgot password</p>
        <h1 className="text-4xl font-extrabold">Reset your password</h1>
      </div>
      {sent ? (
        <Alert tone="good" title="Check your inbox">
          If an account uses {email}, we&apos;ve sent a link to choose a new password. It works for one hour.
        </Alert>
      ) : (
        <form onSubmit={submit} noValidate className="grid gap-4">
          <p className="text-muted">Enter the email you signed up with and we&apos;ll send you a link to set a new password.</p>
          {error && <Alert tone="bad">{error}</Alert>}
          <Input label="Email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
          <Button type="submit" variant="primary" size="lg" busy={busy}>Send reset link</Button>
        </form>
      )}
      <Link href="/login" className="font-bold text-violet hover:underline">← Back to log in</Link>
    </div>
  );
}
