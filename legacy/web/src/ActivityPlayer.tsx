import { useState } from "react";
import { api, type Activity, type AttemptResult, type Json } from "./api";
import { RENDERERS } from "./renderers";
import { CiteList, ErrorNote, Md, shortType } from "./ui";

export function ActivityPlayer({ activity, learnerId, review = false, onResult, lang }: {
  activity: Activity; learnerId?: string; review?: boolean; lang?: string;
  onResult?: (r: { result: AttemptResult; mastery: Json; solution: Json }) => void;
}) {
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [solution, setSolution] = useState<Json | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const R = RENDERERS[activity.type];

  const submit = async (response: Json, hints = 0) => {
    if (review || !learnerId) return;
    setBusy(true); setErr("");
    try {
      const r = await api.attempt(activity.id, learnerId, response, hints, lang);
      setResult(r.result); setSolution(r.solution); setSubmitted(true);
      onResult?.(r);
    } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  };

  return (
    <div className="card" style={{ padding: 22 }}>
      <div className="spread" style={{ marginBottom: 6 }}>
        <span className="stage-pill">{activity.stage} · {shortType(activity.type)}</span>
        <span className="row" style={{ gap: 6 }}>
          <span className="tiny faint">sources</span><CiteList ids={activity.data.evidence} />
        </span>
      </div>
      <h2 style={{ marginBottom: 4 }}>{activity.data.title}</h2>
      {activity.data.instructions && <div className="muted" style={{ marginBottom: 14 }}><Md text={activity.data.instructions} inline /></div>}
      {R ? (
        <R key={activity.id} a={activity} reveal={review ? activity.data.payload : solution} result={result}
          locked={review || submitted} review={review} submit={submit} busy={busy} />
      ) : <div className="notice warn">No renderer for “{activity.type}” yet.</div>}
      <ErrorNote error={err} />
    </div>
  );
}
