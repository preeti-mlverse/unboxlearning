"use client";
// Confirm an email address, either by typing the 6-digit code from the email (signed in) or by opening the
// link in the email (?token=…, works signed in or out).
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { Alert, Button, Loading } from "@/components/ui";
import { ApiError, post } from "@/lib/api";
import { HOME, useSession } from "@/lib/session";

function ByLink({ token }: { token: string }) {
  const { me, reload } = useSession();
  const [state, setState] = useState<"working" | "done" | "error">("working");
  const [message, setMessage] = useState("");
  const once = useRef(false);

  useEffect(() => {
    if (once.current) return;
    once.current = true;
    post("/auth/verify-email", { token })
      .then(() => { setState("done"); reload(); })
      .catch((e) => { setState("error"); setMessage(e instanceof ApiError ? e.message : "Something went wrong."); });
  }, [token, reload]);

  if (state === "working") return <Loading label="Confirming your email…" />;
  return (
    <div className="grid gap-5">
      <h1 className="text-4xl font-extrabold">{state === "done" ? "Email confirmed" : "That link didn't work"}</h1>
      {state === "done" ? <Alert tone="good">Thanks. Your email address is confirmed.</Alert> : <Alert tone="bad">{message}</Alert>}
      {me ? <Link className="font-bold text-violet hover:underline" href={state === "done" ? HOME[me.home] : "/verify-email"}>
              {state === "done" ? "Continue to UnboxEd →" : "Use a code instead →"}</Link>
          : <Link className="font-bold text-violet hover:underline" href="/login">Log in →</Link>}
    </div>
  );
}

function ByCode() {
  const { me, loading, reload, logout } = useSession();
  const router = useRouter();
  const [digits, setDigits] = useState<string[]>(Array(6).fill(""));
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const boxes = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    if (loading) return;
    if (!me) router.replace("/login?next=/verify-email");
    else if (me.email_verified) router.replace(HOME[me.home]);
  }, [me, loading, router]);

  async function submit(code: string) {
    setBusy(true);
    setError(null);
    try {
      await post("/auth/verify-email-code", { code });
      const fresh = await reload();
      router.replace(fresh ? `${HOME[fresh.home]}?welcome=1` : "/");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong.");
      setDigits(Array(6).fill(""));
      boxes.current[0]?.focus();
      setBusy(false);
    }
  }

  function setAt(i: number, value: string) {
    const clean = value.replace(/\D/g, "");
    if (clean.length > 1) { // pasted the whole code
      const all = clean.slice(0, 6).split("");
      const next = Array(6).fill("").map((_, k) => all[k] ?? "");
      setDigits(next);
      if (all.length === 6) submit(all.join(""));
      else boxes.current[all.length]?.focus();
      return;
    }
    const next = [...digits];
    next[i] = clean;
    setDigits(next);
    if (clean && i < 5) boxes.current[i + 1]?.focus();
    if (next.every(Boolean)) submit(next.join(""));
  }

  if (loading || !me || me.email_verified) return <Loading />;
  return (
    <div className="grid gap-5">
      <div className="grid gap-2">
        <p className="eyebrow text-violet">One last step</p>
        <h1 className="text-4xl font-extrabold">Check your email</h1>
        <p className="text-muted">We sent a 6-digit code to <b className="text-ink">{me.email}</b>. Type it here to confirm it&apos;s you.</p>
      </div>
      {error && <Alert tone="bad">{error}</Alert>}
      {notice && <Alert tone="good">{notice}</Alert>}
      <form onSubmit={(e) => { e.preventDefault(); if (digits.every(Boolean)) submit(digits.join("")); }} className="grid gap-5">
        <fieldset className="flex justify-between gap-2" disabled={busy}>
          <legend className="sr-only">6-digit code</legend>
          {digits.map((d, i) => (
            <input key={i} ref={(el) => { boxes.current[i] = el; }} value={d} inputMode="numeric" autoComplete={i === 0 ? "one-time-code" : "off"}
                   aria-label={`Digit ${i + 1}`} maxLength={i === 0 ? 6 : 1} autoFocus={i === 0}
                   onChange={(e) => setAt(i, e.target.value)}
                   onKeyDown={(e) => { if (e.key === "Backspace" && !digits[i] && i > 0) boxes.current[i - 1]?.focus(); }}
                   className="size-12 rounded-xl border-2 border-line bg-surface text-center font-mono text-2xl font-bold focus:border-violet focus:outline-none sm:size-14" />
          ))}
        </fieldset>
        <Button type="submit" variant="primary" size="lg" busy={busy} disabled={!digits.every(Boolean)}>Confirm email</Button>
      </form>
      <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
        <button type="button" className="font-bold text-violet hover:underline" onClick={async () => {
          setError(null);
          try { await post("/auth/resend-verification"); setNotice("New code sent. It works for 30 minutes."); }
          catch (e) { setError(e instanceof ApiError ? e.message : "Couldn't send a new code."); }
        }}>Send a new code</button>
        <button type="button" className="text-muted hover:text-ink" onClick={logout}>Use a different account</button>
      </div>
      <p className="text-sm text-muted">Can&apos;t find it? Check your spam folder, or open the link in the same email.</p>
    </div>
  );
}

function Verify() {
  const token = useSearchParams().get("token");
  return token ? <ByLink token={token} /> : <ByCode />;
}

export default function VerifyEmailPage() {
  return <Suspense><Verify /></Suspense>;
}
