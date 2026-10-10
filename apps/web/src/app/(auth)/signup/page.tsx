"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import type { AuthResult } from "@shared/index";

import { GoogleButton } from "@/components/GoogleButton";
import { Alert, Button, Input, Select, cx } from "@/components/ui";
import { ApiError, post } from "@/lib/api";
import { SITE_URL } from "@/lib/config";
import { fieldErrors, signupSchema } from "@/lib/forms";
import { landing, useSession } from "@/lib/session";

const ROLES = [
  { value: "learner", title: "Learner", sub: "I want to learn something" },
  { value: "educator", title: "Educator", sub: "I teach or train people" },
  { value: "school", title: "School or university", sub: "For our institution" },
  { value: "ngo", title: "NGO or public program", sub: "For our learners in the field" },
  { value: "organization", title: "Organization", sub: "Training for our team or customers" },
] as const;
type RoleValue = (typeof ROLES)[number]["value"];

const LANGS: [string, string][] = [["en", "English"], ["hi", "हिन्दी Hindi"], ["ta", "தமிழ் Tamil"], ["te", "తెలుగు Telugu"],
  ["bn", "বাংলা Bengali"], ["mr", "मराठी Marathi"], ["es", "Español"], ["fr", "Français"], ["ar", "العربية Arabic"]];

function SignupForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { reload } = useSession();
  const initialRole = ROLES.find((r) => r.value === params.get("role"))?.value;
  const [step, setStep] = useState<1 | 2>(initialRole ? 2 : 1);
  const [form, setForm] = useState({ role: (initialRole ?? "") as RoleValue | "", name: "", email: "", phone: "", org: "",
                                     language: "en", password: "", agree: false });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof form, v: string | boolean) => setForm((f) => ({ ...f, [k]: v }));
  const needsOrg = form.role === "school" || form.role === "ngo" || form.role === "organization";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const parsed = signupSchema.safeParse({ ...form, phone: form.phone.replace(/\D/g, "").slice(-10) || "" });
    const errs = fieldErrors(parsed);
    if (needsOrg && !form.org.trim()) errs.org = "Enter your organisation's name";
    setErrors(errs);
    if (!parsed.success || errs.org) return;
    setBusy(true);
    setError(null);
    try {
      const res = await post<AuthResult>("/auth/signup", { ...parsed.data, phone: parsed.data.phone || null, org: form.org || null });
      await reload();
      const dest = landing(res.user);
      router.replace(dest === "/verify-email" ? dest : `${dest}?welcome=1`);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrors(err.fields);
        setError(err.code === "EMAIL_TAKEN" ? null : err.message);
        if (err.code === "EMAIL_TAKEN") setErrors({ email: err.message });
      } else setError("Something went wrong.");
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-5">
      <div className="grid gap-2">
        <p className="eyebrow text-violet">Join UnboxEd · step {step} of 2</p>
        <h1 className="text-4xl font-extrabold">{step === 1 ? "Who's signing up?" : "Your details"}</h1>
      </div>
      {step === 1 ? (
        <div className="grid gap-3">
          <div role="radiogroup" aria-label="I am signing up as" className="grid gap-2.5">
            {ROLES.map((r) => (
              <button key={r.value} type="button" role="radio" aria-checked={form.role === r.value}
                      onClick={() => { set("role", r.value); setErrors({}); }}
                      className={cx("flex items-center justify-between gap-3 rounded-2xl border-2 px-4 py-3 text-left transition",
                                    form.role === r.value ? "border-violet bg-lavender" : "border-line bg-surface hover:border-violet/60")}>
                <span className="grid"><b className="font-display text-lg">{r.title}</b><small className="text-muted">{r.sub}</small></span>
                <span aria-hidden className={cx("size-5 rounded-full border-2", form.role === r.value ? "border-violet bg-violet shadow-[inset_0_0_0_3px_var(--lavender)]" : "border-line")} />
              </button>
            ))}
          </div>
          {errors.role && <p className="text-sm font-semibold text-bad">{errors.role}</p>}
          <Button variant="violet" size="lg" onClick={() => form.role ? setStep(2) : setErrors({ role: "Choose the option that fits you best." })}>
            Continue →
          </Button>
        </div>
      ) : (
        <form onSubmit={submit} noValidate className="grid gap-4">
          {error && <Alert tone="bad">{error}</Alert>}
          <GoogleButton role={form.role || undefined} />
          <Input label="Full name" autoComplete="name" value={form.name} error={errors.name} onChange={(e) => set("name", e.target.value)} autoFocus />
          <div className="grid gap-4 sm:grid-cols-2">
            <Input label="Email" type="email" autoComplete="email" value={form.email} error={errors.email} onChange={(e) => set("email", e.target.value)} />
            <Input label="Mobile (optional)" type="tel" inputMode="numeric" autoComplete="tel-national" placeholder="10-digit number"
                   value={form.phone} error={errors.phone} onChange={(e) => set("phone", e.target.value)} />
          </div>
          {form.role !== "learner" && (
            <Input label={needsOrg ? "Organisation name" : "Workspace name (optional)"} autoComplete="organization"
                   placeholder={needsOrg ? "School, NGO or company name" : "Leave blank and we'll use your name"}
                   value={form.org} error={errors.org} onChange={(e) => set("org", e.target.value)} />
          )}
          <Select label="Language you'd like to learn or teach in" value={form.language} onChange={(e) => set("language", e.target.value)}>
            {LANGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </Select>
          <Input label="Create a password" type="password" autoComplete="new-password" value={form.password} error={errors.password}
                 hint="At least 8 characters, with letters and numbers." onChange={(e) => set("password", e.target.value)} />
          <label className="flex items-start gap-2 text-sm font-semibold">
            <input type="checkbox" className="mt-0.5 size-4 accent-violet" checked={form.agree} onChange={(e) => set("agree", e.target.checked)} />
            <span>I agree to the <a className="text-violet underline" href={`${SITE_URL}/terms/`}>Terms</a> and{" "}
              <a className="text-violet underline" href={`${SITE_URL}/privacy/`}>Privacy policy</a></span>
          </label>
          {errors.agree && <p className="-mt-2 text-sm font-semibold text-bad">{errors.agree}</p>}
          <div className="flex items-center justify-between gap-3">
            <button type="button" className="font-bold text-violet hover:underline" onClick={() => setStep(1)}>← Back</button>
            <Button type="submit" variant="primary" size="lg" busy={busy}>Create my account</Button>
          </div>
        </form>
      )}
      <p className="text-center text-muted">Already have an account? <Link href="/login" className="font-bold text-violet hover:underline">Log in</Link></p>
    </div>
  );
}

export default function SignupPage() {
  return <Suspense><SignupForm /></Suspense>;
}
