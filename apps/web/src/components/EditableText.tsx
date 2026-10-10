"use client";
// Click a title to rename it; Enter saves, Escape cancels.
import { useEffect, useRef, useState } from "react";

import { cx } from "./ui";

export function EditableText({ value, onSave, className, label, disabled }: {
  value: string; onSave: (v: string) => Promise<void> | void; className?: string; label: string; disabled?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => setDraft(value), [value]);
  useEffect(() => { if (editing) ref.current?.select(); }, [editing]);

  if (disabled) return <span className={className}>{value}</span>;
  if (!editing) {
    return (
      <button type="button" onClick={() => setEditing(true)} title={`Rename ${label}`} aria-label={`Rename ${label}: ${value}`}
              className={cx("rounded-lg text-left decoration-violet/50 decoration-dashed underline-offset-4 hover:underline", className)}>
        {value}
      </button>
    );
  }
  const commit = async () => {
    setEditing(false);
    const v = draft.trim();
    if (v && v !== value) await onSave(v);
    else setDraft(value);
  };
  return (
    <input ref={ref} aria-label={label} value={draft} onChange={(e) => setDraft(e.target.value)} onBlur={commit} maxLength={200}
           onKeyDown={(e) => { if (e.key === "Enter") commit(); if (e.key === "Escape") { setDraft(value); setEditing(false); } }}
           className={cx("w-full rounded-lg border-2 border-violet bg-surface px-2 py-0.5 focus:outline-none", className)} />
  );
}
