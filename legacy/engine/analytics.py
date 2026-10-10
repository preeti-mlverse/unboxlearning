"""Post-launch item analytics (classical test theory) — how products retire weak questions.

For every graded activity:
* p-value (facility): share of learners answering correctly on their first attempt
* discrimination: point-biserial correlation between first-attempt score and the learner's overall
  course performance (excluding this item) — low/negative means the item does not separate strong
  from weak learners (ambiguous, mis-keyed or testing the wrong thing)
* distractor use for choice items: how often each option was picked; an option nobody picks is not
  doing any work, a wrong option picked more than the key suggests a mis-key or a real misconception
"""
from collections import defaultdict
from statistics import mean, pstdev

from . import db

MIN_N = 8  # below this, statistics are shown but never used to flag


def item_analysis(course_id: str) -> list[dict]:
    acts = {a["id"]: a for a in db.rows(db.conn().execute(
        "SELECT * FROM activities WHERE course_id=? AND stage!='model'", (course_id,)))}
    atts = db.rows(db.conn().execute(
        "SELECT * FROM attempts WHERE course_id=? AND score IS NOT NULL ORDER BY created_at", (course_id,)))
    first: dict[tuple, dict] = {}
    for a in atts:
        first.setdefault((a["learner_id"], a["activity_id"]), a)
    by_learner = defaultdict(list)
    for (lid, _aid), a in first.items():
        by_learner[lid].append(a["score"])
    totals = {lid: (sum(v), len(v)) for lid, v in by_learner.items()}

    out = []
    for aid, act in acts.items():
        rows = [a for (lid, x), a in first.items() if x == aid]
        n = len(rows)
        if not n:
            continue
        scores = [a["score"] for a in rows]
        p = mean(1.0 if s >= 0.8 else 0.0 for s in scores)
        rest = []
        for a in rows:
            tot, cnt = totals[a["learner_id"]]
            rest.append((tot - a["score"]) / (cnt - 1) if cnt > 1 else None)
        pairs = [(s, r) for s, r in zip(scores, rest) if r is not None]
        disc = None
        if len(pairs) >= 3:
            xs, ys = [s for s, _ in pairs], [r for _, r in pairs]
            sx, sy = pstdev(xs), pstdev(ys)
            if sx > 0 and sy > 0:
                mx, my = mean(xs), mean(ys)
                disc = round(sum((x - mx) * (y - my) for x, y in pairs) / (len(pairs) * sx * sy), 3)
        distractors = None
        payload = act["data"]["payload"]
        if act["type"] in ("mcq", "predict", "compare_table") and payload.get("options"):
            counts = [0] * len(payload["options"])
            for a in rows:
                for i in (a["response"] or {}).get("selected", []):
                    if 0 <= i < len(counts):
                        counts[i] += 1
            distractors = [{"text": o["text"][:80], "correct": o["correct"], "picked": c}
                           for o, c in zip(payload["options"], counts)]
        flags = []
        if n >= MIN_N:
            if p < 0.2:
                flags.append("very hard — check the answer key and wording")
            elif p > 0.95:
                flags.append("almost everyone gets it — too easy or gives the answer away")
            if disc is not None and disc < 0.1:
                flags.append("does not discriminate — strong and weak learners score alike" if disc >= 0
                             else "negative discrimination — likely mis-keyed or ambiguous")
            if distractors:
                key = max((d["picked"] for d in distractors if d["correct"]), default=0)
                for d in distractors:
                    if not d["correct"] and d["picked"] > key:
                        flags.append(f"wrong option chosen more than the key: “{d['text']}”")
                    if not d["correct"] and d["picked"] == 0:
                        flags.append(f"distractor never chosen: “{d['text']}”")
        out.append({"activity_id": aid, "objective_id": act["objective_id"], "type": act["type"],
                    "title": act["data"].get("title"), "n": n, "p_value": round(p, 3),
                    "mean_score": round(mean(scores), 3), "discrimination": disc,
                    "distractors": distractors, "flags": flags})
    out.sort(key=lambda r: (-len(r["flags"]), r["p_value"]))
    return out
