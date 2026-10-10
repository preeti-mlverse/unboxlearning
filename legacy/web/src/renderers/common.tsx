import type { Activity, AttemptResult, Json } from "../api";
import { Md } from "../ui";

export interface RProps {
  a: Activity;
  /** full payload with answers — present after an attempt, or in teacher review mode */
  reveal: Json | null;
  result: AttemptResult | null;
  /** true once submitted or in review mode */
  locked: boolean;
  review: boolean;
  submit: (response: Json, hints?: number) => void;
  busy: boolean;
}

export function SubmitBar({ onClick, disabled, label = "Check answer", busy }: { onClick: () => void; disabled?: boolean; label?: string; busy?: boolean }) {
  return (
    <div className="row" style={{ marginTop: 14 }}>
      <button className="btn primary" onClick={onClick} disabled={disabled || busy}>{busy ? "Checking…" : label}</button>
    </div>
  );
}

export function Feedback({ result }: { result: AttemptResult | null }) {
  if (!result || result.score == null) return null;
  const s = result.score;
  const cls = s >= 0.8 ? "good" : s >= 0.4 ? "mid" : "bad";
  const head = s >= 0.99 ? "Correct" : s >= 0.8 ? "Nearly perfect" : s >= 0.4 ? "Partly right" : "Not quite";
  return (
    <div className={`feedback ${cls}`} role="status">
      <strong>{head}</strong> <span className="small muted">· score {Math.round(s * 100)}%</span>
      {result.feedback && <Md text={result.feedback} />}
      {!!result.met?.length && <div className="small"><strong>You covered:</strong> {result.met.join("; ")}</div>}
      {!!result.missing?.length && <div className="small"><strong>Missing:</strong> {result.missing.join("; ")}</div>}
      {result.misconception && <div className="small"><strong>Watch out:</strong> {result.misconception}</div>}
    </div>
  );
}

export function Choices({ options, selected, setSelected, multiple, reveal, locked }: {
  options: { text: string; correct?: boolean; rationale?: string }[]; selected: number[]; setSelected: (s: number[]) => void;
  multiple: boolean; reveal: { correct: boolean; rationale: string }[] | null; locked: boolean;
}) {
  return (
    <div role={multiple ? "group" : "radiogroup"}>
      {options.map((o, i) => {
        const sel = selected.includes(i);
        const r = reveal?.[i];
        const cls = r ? (r.correct ? "right" : sel ? "wrong" : "") : sel ? "sel" : "";
        return (
          <button key={i} className={`opt ${cls}`} disabled={locked} aria-pressed={sel}
            onClick={() => setSelected(multiple ? (sel ? selected.filter((x) => x !== i) : [...selected, i]) : [i])}>
            <span className="opt-mark" style={multiple ? { borderRadius: 5 } : undefined} />
            <span style={{ flex: 1 }}>
              <Md text={o.text} inline />
              {r && (r.correct || sel) && <div className="rationale"><Md text={r.rationale} inline /></div>}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export function shuffleStable<T>(arr: T[], seed: string): T[] {
  let h = 0;
  for (const c of seed) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i--) {
    h = (h * 1103515245 + 12345) >>> 0;
    const j = h % (i + 1);
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}
