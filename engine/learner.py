"""Learner model: grading, per-objective mastery (BKT-style, transparent), spaced review, next step."""
import json
import time

from . import db
from .activities import REGISTRY, grade_auto
from .knowledge import elements_by_ids, render
from .llm import gateway
from .models import RubricGrade

DAY = 86400.0
PRIOR = {"novice": 0.1, "beginner": 0.15, "intermediate": 0.3, "advanced": 0.45, "expert": 0.6}
P_LEARN = 0.18
REMEDIATION_LIMIT = 3  # extra graded attempts on an objective before moving on and flagging it for the teacher

RUBRIC_SYSTEM = """You grade a learner's written answer against a rubric and model answer, using the evidence.
Be fair: credit correct ideas in the learner's own words; do not require the model answer's wording.
Feedback is for the learner: specific, kind, second person, points to what to improve, and does not simply
paste the model answer. Name the likely misconception if the answer shows one."""


def learner(name: str) -> dict:
    r = db.conn().execute("SELECT * FROM learners WHERE name=?", (name,)).fetchone()
    if r:
        return dict(r)
    lid = db.new_id("lrn")
    with db.tx() as c:
        c.execute("INSERT INTO learners VALUES(?,?,?)", (lid, name, time.time()))
    return {"id": lid, "name": name}


def threshold(course: dict) -> float:
    return 0.9 if course["data"]["goal"].get("purpose") == "certification" else 0.8


def mastery_row(lid: str, course: dict, oid: str) -> dict:
    r = db.conn().execute("SELECT * FROM mastery WHERE learner_id=? AND objective_id=?", (lid, oid)).fetchone()
    if r:
        return dict(r)
    level = course["data"]["goal"].get("audience_level", "beginner")
    return {"learner_id": lid, "course_id": course["id"], "objective_id": oid, "p": PRIOR.get(level, 0.15),
            "attempts": 0, "correct": 0, "last_at": None, "next_review": None, "interval_days": 0.0}


def update_mastery(lid: str, course: dict, oid: str, score: float, difficulty: float, hints: int,
                   n_options: int | None) -> dict:
    m = mastery_row(lid, course, oid)
    p = m["p"]
    slip = min(0.3, 0.08 + 0.12 * difficulty)
    guess = (1 / n_options) if n_options else 0.12
    guess = min(0.4, guess + 0.05 * hints)
    # evidence weight falls with hints used (a hinted success says less about independent mastery)
    s = max(0.0, min(1.0, score)) * (0.6 ** hints)
    post_c = p * (1 - slip) / (p * (1 - slip) + (1 - p) * guess)
    post_w = p * slip / (p * slip + (1 - p) * (1 - guess))
    p = s * post_c + (1 - s) * post_w
    p = p + (1 - p) * P_LEARN * (0.5 + s / 2)
    now = time.time()
    good = score >= 0.8
    interval = max(1.0, (m["interval_days"] or 0.5) * 2.5) if good else 0.25
    m.update(p=round(p, 4), attempts=m["attempts"] + 1, correct=m["correct"] + int(good), last_at=now,
             next_review=now + interval * DAY, interval_days=interval)
    with db.tx() as c:
        c.execute("INSERT OR REPLACE INTO mastery VALUES(?,?,?,?,?,?,?,?,?)",
                  (lid, course["id"], oid, m["p"], m["attempts"], m["correct"], m["last_at"], m["next_review"],
                   m["interval_days"]))
    return m


def grade(course: dict, activity: dict, response: dict) -> dict:
    t = REGISTRY[activity["type"]]
    payload = activity["data"]["payload"]
    if t.grading in ("auto", "self"):
        return grade_auto(activity["type"], payload, response)
    if t.grading == "rubric":
        if activity["type"] == "case_study":
            qi = int(response.get("question", 0))
            q = payload["questions"][qi]
            question, model_answer, rubric = q["question"], q["model_answer"], q["rubric"]
        elif activity["type"] == "teach_back":
            question, model_answer, rubric = payload["prompt"], "; ".join(payload["must_include"]), payload["rubric"]
        else:
            question, model_answer, rubric = payload["question"], payload["model_answer"], payload["rubric"]
        ids = list(dict.fromkeys(activity["data"]["evidence"] + activity["data"].get("context_ids", [])))
        els = elements_by_ids(ids)
        user = (f"Question: {question}\nModel answer (one good answer, not the only one): {model_answer}\n"
                f"Rubric: {json.dumps(rubric)}\n\nLearner answer: {response.get('text', '')}\n\n"
                f"## Course evidence (a learner answer supported by any of this is correct)\n{render(els, 4500)}")
        g = gateway.structured(RubricGrade, RUBRIC_SYSTEM, user, tier="fast", purpose="grade", course_id=course["id"])
        return {"score": g.score, "correct": g.score >= 0.8, "feedback": g.feedback, "met": g.met,
                "missing": g.missing, "misconception": g.misconception}
    if t.grading == "dialogue":
        return {"score": response.get("score"), "correct": (response.get("score") or 0) >= 0.8}
    return {"score": None, "correct": None}


def record_attempt(course: dict, lid: str, activity: dict, response: dict, hints: int = 0) -> dict:
    result = grade(course, activity, response)
    aid = db.new_id("att")
    with db.tx() as c:
        c.execute("INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                  (aid, lid, course["id"], activity["id"], activity["objective_id"], db.dumps(response),
                   result.get("score"), None if result.get("correct") is None else int(result["correct"]), hints,
                   db.dumps(result), time.time()))
    m = None
    if result.get("score") is not None and activity["stage"] != "model":
        opts = activity["data"]["payload"].get("options")
        m = update_mastery(lid, course, activity["objective_id"], result["score"],
                           activity["data"].get("difficulty", 0.5), hints, len(opts) if opts else None)
    return {"attempt_id": aid, "result": result, "mastery": m}


def progress(course: dict, lid: str) -> dict:
    cur = db.get_doc(course["id"], "curriculum") or {"objectives": []}
    rows = {r["objective_id"]: dict(r) for r in db.conn().execute(
        "SELECT * FROM mastery WHERE learner_id=? AND course_id=?", (lid, course["id"]))}
    th = threshold(course)
    out = []
    for o in cur["objectives"]:
        m = rows.get(o["id"]) or mastery_row(lid, course, o["id"])
        state = "mastered" if m["p"] >= th else ("learning" if m["attempts"] else "new")
        if state == "mastered" and m["next_review"] and m["next_review"] <= time.time():
            state = "review_due"
        out.append({"objective_id": o["id"], "statement": o["statement"], "module_id": o["module_id"],
                    "p": m["p"], "attempts": m["attempts"], "state": state, "next_review": m["next_review"]})
    return {"threshold": th, "objectives": out}


def next_step(course: dict, lid: str) -> dict:
    from .evidence import arm_for, pending_assessment
    step = _next_activity(course, lid)
    course_done = step["mode"] == "done"
    if (pending := pending_assessment(course, lid, course_done)) and (pending["kind"] != "post" or course_done):
        return {"mode": "assessment", "objective_id": None, "activity": None, "assessment": pending,
                "arm": arm_for(course, lid)}
    step["arm"] = arm_for(course, lid)
    return step


def _static_next(course: dict, lid: str, acts: list[dict], done: dict) -> dict:
    """Control arm: every approved main activity once, in curriculum order; no adaptivity."""
    cur = db.get_doc(course["id"], "curriculum") or {"objectives": []}
    order = {o["id"]: i for i, o in enumerate(cur["objectives"])}
    seq = sorted((a for a in acts if not a["data"].get("reserve")), key=lambda a: (order.get(a["objective_id"], 999), a["ord"]))
    for a in seq:
        if a["id"] not in done:
            return {"mode": "learn", "objective_id": a["objective_id"], "activity": a}
    return {"mode": "done", "objective_id": None, "activity": None}


def _next_activity(course: dict, lid: str) -> dict:
    from .evidence import arm_for
    acts = db.rows(db.conn().execute(
        "SELECT * FROM activities WHERE course_id=? AND status='approved' ORDER BY objective_id, ord", (course["id"],)))
    by_obj: dict[str, list] = {}
    for a in acts:
        by_obj.setdefault(a["objective_id"], []).append(a)
    done = {r["activity_id"]: r for r in db.rows(db.conn().execute(
        "SELECT activity_id, max(COALESCE(score, 1)) AS best, count(*) AS n, max(created_at) AS last FROM attempts "
        "WHERE learner_id=? AND course_id=? GROUP BY activity_id", (lid, course["id"])))}
    if arm_for(course, lid) == "static":
        return _static_next(course, lid, acts, done)
    prog = progress(course, lid)

    # 1) spaced review of mastered objectives that are due
    for o in prog["objectives"]:
        if o["state"] == "review_due" and by_obj.get(o["objective_id"]):
            pool = [a for a in by_obj[o["objective_id"]] if a["stage"] in ("check", "practice")] or by_obj[o["objective_id"]]
            pick = min(pool, key=lambda a: (done.get(a["id"], {}).get("last") or 0))
            return {"mode": "review", "objective_id": o["objective_id"], "activity": pick}
    # 2) the first objective not yet mastered
    last = db.row(db.conn().execute("SELECT activity_id, score FROM attempts WHERE learner_id=? AND course_id=? "
                                    "ORDER BY created_at DESC LIMIT 1", (lid, course["id"])).fetchone())
    stuck = []
    for o in prog["objectives"]:
        if o["state"] in ("mastered", "review_due"):
            continue
        seq = by_obj.get(o["objective_id"], [])
        if not seq:
            continue
        main = [a for a in seq if not a["data"].get("reserve")]
        fresh = [a for a in main if a["id"] not in done]
        if fresh:
            return {"mode": "learn", "objective_id": o["objective_id"], "activity": fresh[0]}
        spare = [a for a in seq if a["data"].get("reserve") and a["id"] not in done]
        if spare:  # first remediation step: a fresh item the learner has not seen
            return {"mode": "remediate", "objective_id": o["objective_id"], "activity": spare[0]}
        # every activity done but not mastered → remediation, bounded so a learner is never trapped
        graded = [a for a in seq if a["stage"] != "model"]
        if not graded:  # nothing to assess (explanations only): completed, not stuck
            continue
        if o["attempts"] - len(graded) >= REMEDIATION_LIMIT:
            stuck.append(o["objective_id"])
            continue
        last_score = last["score"] if last and last["activity_id"] in {a["id"] for a in seq} else None
        teach = [a for a in seq if a["stage"] == "model"]
        if last_score is not None and last_score < 0.5 and teach and last["activity_id"] not in {a["id"] for a in teach}:
            return {"mode": "reteach", "objective_id": o["objective_id"], "activity": teach[0]}
        pool = [a for a in graded if not last or a["id"] != last["activity_id"]] or graded
        weakest = min(pool, key=lambda a: (done[a["id"]]["best"], done[a["id"]]["last"]))
        return {"mode": "remediate", "objective_id": o["objective_id"], "activity": weakest}
    return {"mode": "done", "objective_id": None, "activity": None, "needs_help": stuck}


def dashboard(course: dict) -> dict:
    cur = db.get_doc(course["id"], "curriculum") or {"objectives": []}
    th = threshold(course)
    learners = db.rows(db.conn().execute(
        "SELECT DISTINCT l.* FROM learners l JOIN attempts a ON a.learner_id=l.id WHERE a.course_id=?", (course["id"],)))
    ms = db.rows(db.conn().execute("SELECT * FROM mastery WHERE course_id=?", (course["id"],)))
    atts = db.rows(db.conn().execute("SELECT * FROM attempts WHERE course_id=?", (course["id"],)))
    objs = []
    for o in cur["objectives"]:
        rows = [m for m in ms if m["objective_id"] == o["id"]]
        miscon = {}
        for a in atts:
            if a["objective_id"] == o["id"] and isinstance(a["feedback"], dict) and a["feedback"].get("misconception"):
                k = a["feedback"]["misconception"]
                miscon[k] = miscon.get(k, 0) + 1
        objs.append({"objective_id": o["id"], "statement": o["statement"],
                     "mastered": sum(1 for m in rows if m["p"] >= th),
                     "struggling": [m["learner_id"] for m in rows if m["attempts"] >= 3 and m["p"] < 0.5],
                     "avg_p": round(sum(m["p"] for m in rows) / len(rows), 3) if rows else None,
                     "attempts": sum(1 for a in atts if a["objective_id"] == o["id"]),
                     "misconceptions": sorted(miscon.items(), key=lambda kv: -kv[1])[:3]})
    act_stats = {}
    for a in atts:
        s = act_stats.setdefault(a["activity_id"], {"n": 0, "correct": 0})
        s["n"] += 1
        s["correct"] += a["correct"] or 0
    hard = sorted(((k, v["correct"] / v["n"], v["n"]) for k, v in act_stats.items() if v["n"] >= 3),
                  key=lambda x: x[1])[:5]
    return {"learners": learners, "objectives": objs, "hard_items": hard, "threshold": th}
