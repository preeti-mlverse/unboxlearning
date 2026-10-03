import { useState } from "react";
import type { Json } from "../api";
import { ModelView, type Hotspot } from "../model3d";
import { Md } from "../ui";
import { Choices, Feedback, SubmitBar, type RProps } from "./common";

export function Model3D({ a, reveal, result, locked, submit, busy }: RProps) {
  const p = a.data.payload;
  const hotspots = (p.hotspots ?? []) as Hotspot[];
  const tour = (p.tour ?? []) as { hotspot: string; explanation: string }[];
  const [stop, setStop] = useState<number | null>(null);
  const [answers, setAnswers] = useState<Record<string, number[]>>({});
  const qs = (p.questions ?? []) as { prompt: string; options: Json[] }[];
  if (!p.media_path) return <div className="notice warn">The 3D model for this activity is missing — attach one in the studio (Sources → 3D models).</div>;
  const hsIndex = (label: string) => hotspots.findIndex((h) => h.label === label);
  const current = stop != null ? tour[stop] : null;
  return (
    <div className="stack">
      <Md text={p.intro} />
      <ModelView src={`/media/${p.media_path}`} hotspots={hotspots} active={current ? hsIndex(current.hotspot) : undefined}
        onHotspot={(i) => { const k = tour.findIndex((t) => t.hotspot === hotspots[i].label); if (k >= 0) setStop(k); }} />
      <div className="small muted">Drag to rotate · scroll to zoom · on a phone, tap the AR icon to place it in your room.</div>
      <div className="row">
        <button className="btn sm" onClick={() => setStop(stop == null ? 0 : Math.max(0, stop - 1))} disabled={stop === 0}>◀</button>
        <span className="small">Guided tour {stop == null ? "" : `· stop ${stop + 1} of ${tour.length}`}</span>
        <button className="btn sm primary" onClick={() => setStop(stop == null ? 0 : Math.min(tour.length - 1, stop + 1))} disabled={stop === tour.length - 1}>{stop == null ? "Start tour ▶" : "▶"}</button>
      </div>
      {current && <div className="notice"><strong>{current.hotspot}: </strong><Md text={current.explanation} inline /></div>}
      {qs.map((q, i) => (
        <div key={i}>
          <strong><Md text={q.prompt} inline /></strong>
          <Choices options={q.options} selected={answers[String(i)] ?? []} multiple={false} locked={locked}
            setSelected={(s) => setAnswers((prev) => ({ ...prev, [String(i)]: s }))} reveal={reveal?.questions?.[i]?.options ?? null} />
        </div>
      ))}
      {!locked && <SubmitBar label={qs.length ? "Check answers" : "Continue"} onClick={() => submit({ answers })} disabled={qs.some((_, i) => !answers[String(i)])} busy={busy} />}
      <Feedback result={result} />
    </div>
  );
}
