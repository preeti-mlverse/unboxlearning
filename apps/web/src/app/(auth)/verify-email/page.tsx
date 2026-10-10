"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { Alert, Loading } from "@/components/ui";
import { ApiError, post } from "@/lib/api";
import { HOME, useSession } from "@/lib/session";

function Verify() {
  const token = useSearchParams().get("token") ?? "";
  const { me, reload } = useSession();
  const [state, setState] = useState<"working" | "done" | "error">(token ? "working" : "error");
  const [message, setMessage] = useState(token ? "" : "This link is incomplete. Open it from your email again.");
  const once = useRef(false);

  useEffect(() => {
    if (!token || once.current) return;
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
      {me ? <Link className="font-bold text-violet hover:underline" href={HOME[me.home]}>Continue to UnboxEd →</Link>
          : <Link className="font-bold text-violet hover:underline" href="/login">Log in →</Link>}
      {state === "error" && me && <p className="text-muted">You can send a new link from your <Link className="text-violet underline" href="/account">account page</Link>.</p>}
    </div>
  );
}

export default function VerifyEmailPage() {
  return <Suspense><Verify /></Suspense>;
}
