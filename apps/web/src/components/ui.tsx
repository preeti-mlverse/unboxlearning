"use client";
// The UnboxEd component set: typography, buttons, inputs, cards, modal, alerts, loading and empty states, and
// status badges. Status styles are defined once here and used everywhere.
import Link from "next/link";
import { forwardRef, useEffect, useId, useRef } from "react";

const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");
export { cx };

// ---------------------------------------------------------------- brand
export function Logo({ size = 32, light = false, label = true }: { size?: number; light?: boolean; label?: boolean }) {
  return (
    <span className={cx("inline-flex items-center gap-2 font-display font-extrabold tracking-tight", light ? "text-white" : "text-ink")}
          style={{ fontSize: size * 0.62 }}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/brand/logo.svg" width={size} height={size} alt="" />
      {label && <span>Unbox<span className="text-mustard">Ed</span></span>}
    </span>
  );
}

// ---------------------------------------------------------------- buttons
type Variant = "primary" | "violet" | "ghost" | "quiet" | "danger";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-mustard text-uv shadow-[0_4px_0_#B98600] hover:-translate-y-px hover:shadow-[0_5px_0_#B98600] active:translate-y-0.5 active:shadow-[0_1px_0_#B98600]",
  violet: "bg-violet text-white shadow-[0_4px_0_var(--violet-deep)] hover:-translate-y-px active:translate-y-0.5 active:shadow-none",
  ghost: "border-2 border-line bg-surface text-ink hover:border-violet",
  quiet: "text-violet hover:bg-lavender",
  danger: "border-2 border-bad/40 bg-surface text-bad hover:bg-bad-soft",
};
const SIZES = { sm: "px-3 py-1.5 text-sm rounded-xl", md: "px-4 py-2.5 text-[15px] rounded-2xl", lg: "px-6 py-3.5 text-base rounded-2xl" };

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: keyof typeof SIZES; busy?: boolean };

export function Button({ variant = "violet", size = "md", busy, className, children, disabled, ...rest }: ButtonProps) {
  return (
    <button {...rest} disabled={disabled || busy} aria-busy={busy || undefined}
            className={cx("inline-flex items-center justify-center gap-2 font-bold transition disabled:cursor-not-allowed disabled:opacity-55",
                          VARIANTS[variant], SIZES[size], className)}>
      {busy && <Spinner small />}
      {children}
    </button>
  );
}

export function LinkButton({ href, variant = "violet", size = "md", className, children }:
  { href: string; variant?: Variant; size?: keyof typeof SIZES; className?: string; children: React.ReactNode }) {
  return <Link href={href} className={cx("inline-flex items-center justify-center gap-2 font-bold transition", VARIANTS[variant], SIZES[size], className)}>{children}</Link>;
}

// ---------------------------------------------------------------- form fields
const inputCls = "w-full rounded-xl border-2 border-line bg-surface px-3.5 py-2.5 text-[15px] text-ink placeholder:text-muted/70 focus:border-violet focus:outline-none aria-[invalid=true]:border-bad";

export function Field({ label, error, hint, children, id }: { label: string; error?: string; hint?: string; children: React.ReactNode; id: string }) {
  return (
    <div className="grid gap-1.5">
      <label htmlFor={id} className="text-sm font-bold">{label}</label>
      {children}
      {error ? <p id={`${id}-err`} className="text-sm font-semibold text-bad">{error}</p>
             : hint ? <p className="text-sm text-muted">{hint}</p> : null}
    </div>
  );
}

type InputProps = React.InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: string };
export const Input = forwardRef<HTMLInputElement, InputProps>(function Input({ label, error, hint, id, className, ...rest }, ref) {
  const auto = useId();
  const fid = id ?? auto;
  return (
    <Field label={label} error={error} hint={hint} id={fid}>
      <input ref={ref} id={fid} aria-invalid={error ? true : undefined} aria-describedby={error ? `${fid}-err` : undefined}
             className={cx(inputCls, className)} {...rest} />
    </Field>
  );
});

type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; error?: string; hint?: string };
export function Textarea({ label, error, hint, id, className, ...rest }: TextareaProps) {
  const auto = useId();
  const fid = id ?? auto;
  return (
    <Field label={label} error={error} hint={hint} id={fid}>
      <textarea id={fid} aria-invalid={error ? true : undefined} className={cx(inputCls, "min-h-28 leading-relaxed", className)} {...rest} />
    </Field>
  );
}

type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement> & { label: string; error?: string; hint?: string };
export function Select({ label, error, hint, id, className, children, ...rest }: SelectProps) {
  const auto = useId();
  const fid = id ?? auto;
  return (
    <Field label={label} error={error} hint={hint} id={fid}>
      <select id={fid} aria-invalid={error ? true : undefined} className={cx(inputCls, className)} {...rest}>{children}</select>
    </Field>
  );
}

// ---------------------------------------------------------------- surfaces
export function Card({ className, children, as: As = "div" }: { className?: string; children: React.ReactNode; as?: "div" | "section" | "article" | "li" }) {
  return <As className={cx("rounded-[22px] border-2 border-line bg-surface p-5 shadow-[0_5px_0_var(--line)]", className)}>{children}</As>;
}

export function PageHeader({ eyebrow, title, children, actions }: { eyebrow?: string; title: string; children?: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <header className="mb-7 flex flex-wrap items-end justify-between gap-4">
      <div className="grid max-w-3xl gap-2">
        {eyebrow && <p className="eyebrow text-violet">{eyebrow}</p>}
        <h1 className="text-3xl font-extrabold sm:text-4xl">{title}</h1>
        {children && <div className="text-muted">{children}</div>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

// ---------------------------------------------------------------- feedback
type Tone = "info" | "good" | "bad" | "warn";
const TONES: Record<Tone, string> = { info: "bg-lavender text-ink", good: "bg-good-soft text-good", bad: "bg-bad-soft text-bad", warn: "bg-warn-soft text-warn-ink" };

export function Alert({ tone = "info", title, children, action }: { tone?: Tone; title?: string; children?: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div role={tone === "bad" ? "alert" : "status"} className={cx("flex flex-wrap items-start justify-between gap-3 rounded-2xl px-4 py-3 text-[15px] font-medium", TONES[tone])}>
      <div className="grid gap-0.5">
        {title && <p className="font-bold">{title}</p>}
        {children && <div>{children}</div>}
      </div>
      {action}
    </div>
  );
}

export function Spinner({ small, label }: { small?: boolean; label?: string }) {
  return (
    <span className="inline-flex items-center gap-2" role={label ? "status" : undefined}>
      <span aria-hidden className={cx("inline-block animate-spin rounded-full border-current border-r-transparent", small ? "size-4 border-2" : "size-6 border-[3px]")} />
      {label && <span>{label}</span>}
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cx("animate-pulse rounded-xl bg-line/70", className)} />;
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return <div className="grid min-h-40 place-items-center text-muted"><Spinner label={label} /></div>;
}

export function EmptyState({ title, children, action, icon = "📦" }: { title: string; children?: React.ReactNode; action?: React.ReactNode; icon?: string }) {
  return (
    <div className="grid justify-items-center gap-3 rounded-[22px] border-2 border-dashed border-line bg-surface/60 px-6 py-12 text-center">
      <span className="text-4xl" aria-hidden>{icon}</span>
      <h2 className="text-xl font-bold">{title}</h2>
      {children && <div className="max-w-md text-muted">{children}</div>}
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: { message: string; requestId?: string | null }; onRetry?: () => void }) {
  return (
    <Alert tone="bad" title="That didn't load" action={onRetry && <Button size="sm" variant="ghost" onClick={onRetry}>Try again</Button>}>
      {error.message}
      {error.requestId && <span className="block font-mono text-xs opacity-70">Reference: {error.requestId}</span>}
    </Alert>
  );
}

// ---------------------------------------------------------------- status badges (one definition for every status)
const STATUS: Record<string, { label: string; cls: string; pulse?: boolean }> = {
  draft: { label: "Draft", cls: "bg-lavender text-violet" },
  review: { label: "In review", cls: "bg-warn-soft text-warn-ink" },
  published: { label: "Published", cls: "bg-good-soft text-good" },
  archived: { label: "Archived", cls: "bg-line text-muted" },
  uploaded: { label: "Uploaded", cls: "bg-lavender text-violet" },
  queued: { label: "Waiting", cls: "bg-warn-soft text-warn-ink", pulse: true },
  pending: { label: "Waiting", cls: "bg-warn-soft text-warn-ink", pulse: true },
  processing: { label: "Processing", cls: "bg-warn-soft text-warn-ink", pulse: true },
  running: { label: "Processing", cls: "bg-warn-soft text-warn-ink", pulse: true },
  ready: { label: "Ready", cls: "bg-good-soft text-good" },
  completed: { label: "Completed", cls: "bg-good-soft text-good" },
  failed: { label: "Failed", cls: "bg-bad-soft text-bad" },
  cancelled: { label: "Cancelled", cls: "bg-line text-muted" },
  active: { label: "In progress", cls: "bg-lavender text-violet" },
  not_started: { label: "Not started", cls: "bg-line text-muted" },
  in_progress: { label: "In progress", cls: "bg-lavender text-violet" },
  disabled: { label: "Disabled", cls: "bg-bad-soft text-bad" },
};

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  const s = STATUS[status] ?? { label: status, cls: "bg-line text-muted" };
  return (
    <span className={cx("inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wider", s.cls)}>
      {s.pulse && <span aria-hidden className="size-1.5 animate-pulse rounded-full bg-current" />}
      {label ?? s.label}
    </span>
  );
}

export function ProgressBar({ value, label }: { value: number; label?: string }) {
  return (
    <div className="grid gap-1">
      <div role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100} aria-label={label ?? "Progress"}
           className="h-2.5 overflow-hidden rounded-full bg-line">
        <div className="h-full rounded-full bg-gradient-to-r from-good to-[#53D3A6] transition-[width] duration-500" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- modal
export function Modal({ open, onClose, title, children, footer }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode; footer?: React.ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) {
      d.showModal();
      // land on the first field, not the close button
      d.querySelector<HTMLElement>("input:not([type=hidden]), textarea, select")?.focus();
    }
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog ref={ref} onClose={onClose} onClick={(e) => { if (e.target === ref.current) onClose(); }}
            className="m-auto w-[min(560px,calc(100vw-32px))] rounded-[24px] border-2 border-line bg-surface p-0 text-ink shadow-2xl backdrop:bg-uv/60 backdrop:backdrop-blur-sm">
      <div className="grid gap-4 p-6">
        <div className="flex items-start justify-between gap-4">
          <h2 className="text-2xl font-extrabold">{title}</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-lg px-2 text-2xl leading-none text-muted hover:text-ink">×</button>
        </div>
        {children}
        {footer && <div className="flex flex-wrap justify-end gap-2 pt-2">{footer}</div>}
      </div>
    </dialog>
  );
}
