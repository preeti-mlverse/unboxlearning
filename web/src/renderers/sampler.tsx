import { useMemo, useState } from "react";
import type { Json } from "../api";
import { Md } from "../ui";
import { Choices, Feedback, SubmitBar, type RProps } from "./common";

export function probabilities(scores: number[], temperature: number | null): number[] {
  if (temperature == null) {
    const w = scores.map((s) => Math.max(0, s));
    const t = w.reduce((a, b) => a + b, 0) || 1;
    return w.map((x) => x / t);
  }
  const t = Math.max(1e-3, temperature);
  const m = Math.max(...scores);
  const e = scores.map((s) => Math.exp((s - m) / t));
  const z = e.reduce((a, b) => a + b, 0);
  return e.map((x) => x / z);
}

export function DistributionSampler({ a, reveal, result, locked, submit, busy }: RProps) {
  const p = a.data.payload;
  const outcomes = p.outcomes as { label: string; score: number }[];
  const [temp, setTemp] = useState<number>(p.temperature_default ?? 1);
  const [counts, setCounts] = useState<number[]>(outcomes.map(() => 0));
  const [last, setLast] = useState<number | null>(null);
  const [answers, setAnswers] = useState<Record<string, number[]>>({});
  const probs = useMemo(() => probabilities(outcomes.map((o) => o.score), p.uses_temperature ? temp : null), [outcomes, temp, p.uses_temperature]);
  const total = counts.reduce((x, y) => x + y, 0);
  const draw = (n: number) => {
    const c = [...counts];
    let pick = 0;
    for (let k = 0; k < n; k++) {
      let r = Math.random(), i = 0;
      while (i < probs.length - 1 && r > probs[i]) { r -= probs[i]; i++; }
      c[i]++; pick = i;
    }
    setCounts(c); setLast(pick);
  };
  const qs = (p.questions ?? []) as { prompt: string; options: Json[] }[];
  return (
    <div className="stack">
      <Md text={p.intro} />
      {p.uses_temperature && (
        <div>
          <label htmlFor={`t-${a.id}`}>Temperature: <strong>{temp.toFixed(2)}</strong></label>
          <input id={`t-${a.id}`} type="range" min={p.temperature_min} max={p.temperature_max} step={0.01} value={temp}
            onChange={(e) => { setTemp(parseFloat(e.target.value)); setCounts(outcomes.map(() => 0)); setLast(null); }} style={{ padding: 0 }} />
        </div>
      )}
      <div className="card flat stack" style={{ gap: 6 }}>
        {outcomes.map((o, i) => (
          <div key={i} className="row" style={{ flexWrap: "nowrap", gap: 10 }}>
            <span style={{ width: 150, flex: "none", fontWeight: last === i ? 700 : 400 }}>{last === i ? "▶ " : ""}{o.label}</span>
            <div style={{ flex: 1, position: "relative", height: 22, background: "var(--surface-2)", borderRadius: 6, overflow: "hidden" }}>
              <div style={{ position: "absolute", inset: 0, width: `${probs[i] * 100}%`, background: "var(--primary-soft)", transition: "width .3s" }} />
              <div style={{ position: "absolute", left: 0, top: 13, height: 9, width: `${total ? (counts[i] / total) * 100 : 0}%`, background: "var(--primary)", transition: "width .3s" }} />
            </div>
            <span className="mono small" style={{ width: 110, textAlign: "right" }}>{(probs[i] * 100).toFixed(1)}% · {counts[i]}</span>
          </div>
        ))}
        <div className="tiny faint">Light bar = probability · dark bar = share of your samples ({total} drawn)</div>
      </div>
      <div className="row">
        <button className="btn" onClick={() => draw(1)}>Sample 1</button>
        <button className="btn" onClick={() => draw(20)}>Sample 20</button>
        <button className="btn" onClick={() => draw(200)}>Sample 200</button>
        <button className="btn ghost sm" onClick={() => { setCounts(outcomes.map(() => 0)); setLast(null); }}>Reset</button>
      </div>
      {qs.map((q, i) => (
        <div key={i}>
          <strong><Md text={q.prompt} inline /></strong>
          <Choices options={q.options} selected={answers[String(i)] ?? []} multiple={false} locked={locked}
            setSelected={(s) => setAnswers((prev) => ({ ...prev, [String(i)]: s }))} reveal={reveal?.questions?.[i]?.options ?? null} />
        </div>
      ))}
      {(reveal || locked) && p.takeaway && <div className="notice good"><strong>Takeaway: </strong><Md text={p.takeaway} inline /></div>}
      {!locked && <SubmitBar onClick={() => submit({ answers })} disabled={qs.some((_, i) => !answers[String(i)])} busy={busy} />}
      <Feedback result={result} />
    </div>
  );
}
