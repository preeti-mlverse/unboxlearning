"""Evidence of learning: independent pre/post/delayed assessments and simple controlled experiments.

Principle (from the research base): never use the course's own generated quizzes as the primary evidence.
Assessments here are imported (QTI 2.1 / JSON) or written by the teacher, and are scored separately from
the adaptive course. An optional experiment randomly assigns learners to arms:

* adaptive — the full engine (remediation, reserve items, spaced review, tutor)
* static   — the same approved activities in a fixed order, no adaptivity and no tutor

so the report isolates what adaptivity adds beyond the content itself.
"""
import hashlib
import io
import math
import re
import time
import zipfile
from statistics import mean, pstdev
from xml.etree import ElementTree as ET

from . import db

KINDS = ("pre", "post", "delayed")


# ----------------------------------------------------------------------------- assessments

def list_assessments(course_id: str) -> list[dict]:
    return sorted(db.list_docs(course_id, "assessment").values(), key=lambda a: KINDS.index(a["kind"]))


def save_assessment(course_id: str, a: dict) -> dict:
    if a["kind"] not in KINDS:
        raise ValueError("kind must be pre, post or delayed")
    items = []
    for i, it in enumerate(a["items"]):
        opts = [{"text": str(o["text"]), "correct": bool(o.get("correct"))} for o in it["options"]]
        if len(opts) < 2 or not any(o["correct"] for o in opts):
            raise ValueError(f"item {i + 1} needs at least 2 options and a correct answer")
        items.append({"id": it.get("id") or f"q{i + 1}", "question": str(it["question"]), "options": opts})
    doc = {"id": a.get("id") or db.new_id("asm"), "kind": a["kind"], "name": a.get("name") or a["kind"].title() + "-test",
           "items": items, "source": a.get("source", "teacher"), "delay_days": int(a.get("delay_days", 21)),
           "updated_at": time.time()}
    for other in list_assessments(course_id):  # one assessment per kind
        if other["kind"] == doc["kind"] and other["id"] != doc["id"]:
            with db.tx() as c:
                c.execute("DELETE FROM course_docs WHERE course_id=? AND kind='assessment' AND key=?",
                          (course_id, other["id"]))
    db.put_doc(course_id, "assessment", doc, doc["id"])
    return doc


def parse_qti_zip(data: bytes) -> list[dict]:
    """Choice items from a QTI 2.x package (the common denominator across LMS item banks)."""
    items = []
    z = zipfile.ZipFile(io.BytesIO(data))
    for name in z.namelist():
        if not name.lower().endswith(".xml") or "manifest" in name.lower():
            continue
        try:
            root = ET.fromstring(z.read(name))
        except ET.ParseError:
            continue
        strip = lambda t: re.sub(r"^\{[^}]+\}", "", t)  # noqa: E731
        correct = {v.text for d in root.iter() if strip(d.tag) == "correctResponse" for v in d if v.text}
        for ci in (e for e in root.iter() if strip(e.tag) == "choiceInteraction"):
            prompt = next((" ".join(p.itertext()).strip() for p in ci if strip(p.tag) == "prompt"), "")
            if not prompt:
                body = next((e for e in root.iter() if strip(e.tag) == "itemBody"), None)
                prompt = " ".join(t.strip() for t in body.itertext() if t.strip())[:500] if body is not None else ""
            opts = [{"text": " ".join(c.itertext()).strip(), "correct": c.get("identifier") in correct}
                    for c in ci if strip(c.tag) == "simpleChoice"]
            if len(opts) >= 2 and any(o["correct"] for o in opts):
                items.append({"question": prompt, "options": opts})
    return items


# ----------------------------------------------------------------------------- learners

def arm_for(course: dict, learner_id: str) -> str:
    exp = course["data"]["settings"].get("experiment") or {}
    if not exp.get("enabled"):
        return "adaptive"
    h = int(hashlib.sha256(f"{course['id']}:{learner_id}".encode()).hexdigest(), 16)
    return "static" if h % 2 else "adaptive"


def results(course_id: str, learner_id: str | None = None) -> list[dict]:
    rows = db.list_docs(course_id, "assessment_result")
    return [r for r in rows.values() if learner_id is None or r["learner_id"] == learner_id]


def pending_assessment(course: dict, learner_id: str, course_done: bool) -> dict | None:
    """Which independent test (if any) the learner should take now."""
    assessments = {a["kind"]: a for a in list_assessments(course["id"])}
    taken = {r["kind"]: r for r in results(course["id"], learner_id)}
    if "pre" in assessments and "pre" not in taken:
        return assessments["pre"]
    if course_done and "post" in assessments and "post" not in taken:
        return assessments["post"]
    if "delayed" in assessments and "delayed" not in taken and "post" in taken:
        due = taken["post"]["at"] + assessments["delayed"]["delay_days"] * 86400
        if time.time() >= due:
            return assessments["delayed"]
    return None


def submit(course: dict, learner_id: str, assessment_id: str, answers: dict[str, list[int]]) -> dict:
    a = db.get_doc(course["id"], "assessment", assessment_id)
    if not a:
        raise ValueError("unknown assessment")
    per = {}
    for it in a["items"]:
        want = {i for i, o in enumerate(it["options"]) if o["correct"]}
        per[it["id"]] = set(answers.get(it["id"], [])) == want
    score = sum(per.values()) / len(per) if per else 0.0
    rec = {"learner_id": learner_id, "assessment_id": a["id"], "kind": a["kind"], "score": round(score, 4),
           "per_item": per, "arm": arm_for(course, learner_id), "at": time.time()}
    db.put_doc(course["id"], "assessment_result", rec, f"{learner_id}:{a['kind']}")
    return {"score": rec["score"], "kind": a["kind"], "correct": sum(per.values()), "total": len(per)}


def public_view(a: dict) -> dict:
    return {**a, "items": [{"id": it["id"], "question": it["question"], "options": [{"text": o["text"]} for o in it["options"]]}
                           for it in a["items"]]}


# ----------------------------------------------------------------------------- report

def _ci(xs: list[float]) -> list[float] | None:
    if len(xs) < 2:
        return None
    m, sd = mean(xs), pstdev(xs) * math.sqrt(len(xs) / (len(xs) - 1))
    half = 1.96 * sd / math.sqrt(len(xs))
    return [round(m - half, 3), round(m + half, 3)]


def report(course_id: str) -> dict:
    by_learner: dict[str, dict] = {}
    for r in results(course_id):
        d = by_learner.setdefault(r["learner_id"], {"arm": r["arm"]})
        d[r["kind"]] = r["score"]
    arms = {}
    for arm in ("adaptive", "static"):
        ls = [d for d in by_learner.values() if d["arm"] == arm]
        paired = [d for d in ls if "pre" in d and "post" in d]
        gains = [d["post"] - d["pre"] for d in paired]
        norm = [(d["post"] - d["pre"]) / (1 - d["pre"]) for d in paired if d["pre"] < 1]
        retained = [d for d in ls if "post" in d and "delayed" in d]
        arms[arm] = {
            "learners": len(ls), "with_pre_and_post": len(paired),
            "pre_mean": round(mean(d["pre"] for d in ls if "pre" in d), 3) if any("pre" in d for d in ls) else None,
            "post_mean": round(mean(d["post"] for d in ls if "post" in d), 3) if any("post" in d for d in ls) else None,
            "gain_mean": round(mean(gains), 3) if gains else None, "gain_ci95": _ci(gains),
            "normalized_gain": round(mean(norm), 3) if norm else None,
            "retention": round(mean(d["delayed"] / d["post"] for d in retained if d["post"] > 0), 3) if retained else None,
            "_gains": gains,
        }
    a, s = arms["adaptive"]["_gains"], arms["static"]["_gains"]
    effect = None
    if len(a) >= 2 and len(s) >= 2:
        pooled = math.sqrt(((len(a) - 1) * pstdev(a) ** 2 * len(a) / (len(a) - 1) +
                            (len(s) - 1) * pstdev(s) ** 2 * len(s) / (len(s) - 1)) / (len(a) + len(s) - 2))
        effect = round((mean(a) - mean(s)) / pooled, 3) if pooled > 0 else None
    for v in arms.values():
        v.pop("_gains")
    n_total = sum(v["with_pre_and_post"] for v in arms.values())
    caveats = []
    if n_total < 30:
        caveats.append(f"Only {n_total} learners have both pre and post scores — too few for firm conclusions.")
    caveats.append("Randomisation here is by learner; for classroom studies randomise by class or teacher to avoid "
                   "contamination, and fix the analysis plan before the pilot.")
    return {"arms": arms, "effect_size_d": effect, "caveats": caveats,
            "assessments": [{"kind": x["kind"], "name": x["name"], "items": len(x["items"]), "source": x["source"]}
                            for x in list_assessments(course_id)]}


def results_csv(course_id: str) -> str:
    lines = ["learner_id,arm,kind,score,at"]
    for r in sorted(results(course_id), key=lambda r: (r["learner_id"], r["kind"])):
        lines.append(f"{r['learner_id']},{r['arm']},{r['kind']},{r['score']},{int(r['at'])}")
    return "\n".join(lines) + "\n"
