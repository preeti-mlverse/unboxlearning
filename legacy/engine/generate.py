"""Activity generation (evidence-bound) and verification."""
import json
import time

from . import db, index
from .activities import GEN_RULES, REGISTRY, envelope
from .config import settings
from .knowledge import elements_by_ids, render
from .llm import gateway
from .models import Goal, VerifyOut

GEN_SYSTEM = """You create one learning activity for a specific objective, audience and lesson stage.
It must be accurate to the evidence, pedagogically purposeful and pleasant to do.

Stage meanings: activate = surface prior knowledge / create curiosity before teaching (low stakes);
model = teach/demonstrate clearly; practice = learner does it with feedback; check = evidence of mastery
(no hints in the question itself); transfer = apply in a new, realistic context.

""" + GEN_RULES

VERIFY_SYSTEM = """You are a meticulous reviewer checking a generated learning activity before a teacher sees it.

1. Facts: check each key claim and the answer key against the evidence (not your own knowledge).
   'yes' = stated or directly entailed (faithful paraphrase, or an obvious consequence such as "run the code to
   see the output"); 'partly' = plausible but goes beyond the evidence; 'no' = contradicted or clearly unsupported.
2. serious_issues — ONLY must-fix problems: a factual error; the answer key is wrong; more than one defensible
   answer (e.g. ordering items whose relative order does not matter); the answer is visible to the learner before
   responding (remember which fields are hidden until they answer); the activity cannot be completed as written;
   or it does not practise the stated objective at all.
3. pedagogy_issues — minor, optional improvements (clearer wording, more scaffolding, better examples, reading
   level, inclusiveness). Keep each to one concrete sentence; at most 3. Do not repeat serious issues here.
Be calibrated: a good, usable activity should come back with no serious issues."""


def evidence_for(course: dict, objective: dict, step: dict, extra_query: str = "") -> list[dict]:
    ids = list(objective["evidence"])
    q = f"{objective['statement']} {step.get('intent', '')} {extra_query}"
    for ch in index.search(q, course["source_ids"], k=5):
        ids += ch["element_ids"]
    els = elements_by_ids(list(dict.fromkeys(ids)))
    # keep headings for context, but put stated evidence first
    return els


def generate_activity(course: dict, goal: Goal, objective: dict, step: dict, concepts: list[dict],
                      assets: dict, instruction: str = "", tier: str = "standard") -> dict:
    t = REGISTRY[step["activity_type"]]
    els = evidence_for(course, objective, step)
    images = []
    fig_note = ""
    if t.key == "diagram_label":
        figs = [e for e in elements_by_ids(assets.get("figures", [])) if e["media_path"]]
        if figs:
            images = [settings.media_dir / figs[0]["media_path"]]
            fig_note = f"\nThe attached image is figure element {figs[0]['id']} ({figs[0]['text'] or 'no caption'})."
    miscon = "\n".join(f"- {m['misconception']} → {m['correction']}" for m in assets.get("misconceptions", []))
    concept_txt = "\n".join(f"- {c['name']}: {c['definition'][:240]}" for c in concepts)
    extras = ""
    if t.key in ("ordering", "process_stepper") and assets.get("procedures"):
        extras += "\nProcedures found in the source:\n" + json.dumps(assets["procedures"], ensure_ascii=False)[:2500]
    if t.key in ("timeline",) and assets.get("events_list"):
        extras += "\nEvents found in the source:\n" + json.dumps(assets["events_list"], ensure_ascii=False)[:2500]
    if t.key == "model_3d" and assets.get("assets_3d"):
        m = assets["assets_3d"][0]
        extras += (f"\n3D model asset_id={m['id']} ('{m['name']}'). Hotspots you may use: "
                   + "; ".join(m["hotspots"]))
    if t.key == "video_lesson":
        figs = [e for e in elements_by_ids(assets.get("figures", [])) if e["media_path"]]
        if figs:
            extras += "\nFigures with images you may show (figure scenes): " + "; ".join(
                f"{e['id']}: {e['text'] or 'figure'}" for e in figs)
    if t.key in ("parameter_explorer", "numeric_problem") and assets.get("formulas"):
        extras += "\nFormulas found in the source:\n" + json.dumps(assets["formulas"], ensure_ascii=False)[:2000]
    user = (
        f"## Activity type: {t.label} ({t.key})\nPurpose: {t.purpose}\nGuidance: {t.guidance}\n\n"
        f"## Lesson context\nStage: {step['stage']}\nIntent: {step.get('intent') or '-'}\n"
        f"Target misconception: {step.get('targets_misconception') or '-'}\nDifficulty: {step.get('difficulty', 0.5)}\n\n"
        f"## Objective\n{objective['statement']} (Bloom: {objective['bloom']}, type: {objective['knowledge_type']})\n"
        f"Success criteria: {'; '.join(objective['success_criteria'])}\n\n"
        f"## Learner\n{goal.audience_level}; {goal.audience_description or 'general audience'}; purpose: {goal.purpose}; "
        f"language: {goal.language}{'; exam format: ' + goal.exam_format if goal.exam_format else ''}\n\n"
        f"## Concepts\n{concept_txt or '-'}\n\n## Known misconceptions\n{miscon or '-'}\n{extras}\n"
        + (f"\n## Teacher instruction\n{instruction}\n" if instruction else "")
        + f"\n## Evidence{fig_note}\n{render(els, 3800)}"
    )
    out = gateway.structured(envelope(t.key), GEN_SYSTEM, user, tier=tier, purpose=f"generate:{t.key}",
                             course_id=course["id"], images=images or None)
    data = out.model_dump()
    valid = {e["id"] for e in els}
    data["evidence"] = [x for x in data["evidence"] if x in valid] or [e["id"] for e in els[:3]]
    data["context_ids"] = [e["id"] for e in els]  # what the author saw — the reviewer gets the same
    if t.key == "video_lesson":  # resolve figure scenes to real images; drop references we cannot show
        figs = {e["id"]: e for e in elements_by_ids([sc["figure_element_id"] for sc in data["payload"]["scenes"]
                                                     if sc["figure_element_id"]])}
        for sc in data["payload"]["scenes"]:
            f = figs.get(sc["figure_element_id"])
            if sc["visual"] == "figure" and not (f and f["media_path"]):
                sc["visual"], sc["figure_element_id"] = "bullets", ""
            sc["media_path"] = f["media_path"] if f and f["media_path"] else ""
    if t.key == "model_3d":
        from . import db as _db
        asset = _db.get_doc(course["id"], "asset", data["payload"]["asset_id"]) or             (_db.get_doc(course["id"], "asset", assets["assets_3d"][0]["id"]) if assets.get("assets_3d") else None)
        if asset:
            known = {h["label"] for h in asset["hotspots"]}
            data["payload"]["asset_id"] = asset["id"]
            data["payload"]["tour"] = [st for st in data["payload"]["tour"] if st["hotspot"] in known]
            data["payload"]["media_path"] = asset["media_path"]
            data["payload"]["hotspots"] = asset["hotspots"]
    if t.key == "diagram_label" and images:
        data["payload"]["figure_element_id"] = figs[0]["id"]
        data["payload"]["media_path"] = figs[0]["media_path"]
    return data


HIDDEN_UNTIL_ANSWERED = ("correct flags, rationale, explanation, reveal, model_answer, answers, bug_lines, "
                         "bug_explanation, fixed_code, solution, category, why, and the ORDER of ordering items (the "
                         "learner sees items shuffled)")


def verify_activity(course: dict, activity: dict, tier: str = "fast") -> dict:
    """Review against the same evidence the generator saw; the verdict is decided by rule, not by the model."""
    import re as _re
    t = REGISTRY[activity["type"]]
    blob = json.dumps(activity["data"], ensure_ascii=False)
    ids = list(dict.fromkeys(activity["data"].get("evidence", []) + _re.findall(r"\b(e\d+)\b", blob)
                             + activity["data"].get("context_ids", [])))
    els = elements_by_ids(ids)
    shown = {k: v for k, v in activity["data"].items() if k not in ("context_ids", "intent", "targets_misconception")}
    cur = db.get_doc(course["id"], "curriculum") or {"objectives": []}
    obj = next((o for o in cur["objectives"] if o["id"] == activity.get("objective_id")), None)
    goal = course["data"]["goal"]
    ctx = (f"Objective: {obj['statement']} (Bloom: {obj['bloom']})\n" if obj else "") + (
        f"Stage: {activity.get('stage', '-')}\n"
        f"Audience: {goal.get('audience_level')} — {goal.get('audience_description') or 'general'}\n\n")
    user = (ctx + f"Hidden from the learner until they answer: {HIDDEN_UNTIL_ANSWERED}.\n\n"
            f"Activity ({t.label}):\n{json.dumps(shown, ensure_ascii=False)[:7000]}\n\n"
            f"## Evidence (everything the author was given)\n{render(els, 5500)}")
    out = gateway.structured(VerifyOut, VERIFY_SYSTEM, user, tier=tier, purpose="verify", course_id=course["id"])
    v = out.model_dump()
    return finalize_verdict(v)


def finalize_verdict(v: dict, structural: list[str] | None = None) -> dict:
    """Flag only for must-fix problems; 'partly' claims and minor suggestions are shown but do not block."""
    if structural:
        v["serious_issues"] = [f"structure: {x}" for x in structural] + v.get("serious_issues", [])
    wrong_claims = [c for c in v.get("checks", []) if c["supported"] == "no"]
    v["verdict"] = "flagged" if (wrong_claims or v.get("answer_key_correct") == "no" or v.get("serious_issues")) \
        else "verified"
    return v


def save_activity(course_id: str, objective_id: str, step: dict, ord_: int, data: dict, verify: dict | None,
                  status: str, activity_id: str | None = None) -> str:
    aid = activity_id or db.new_id("act")
    now = time.time()
    with db.tx() as c:
        c.execute("INSERT OR REPLACE INTO activities VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                  (aid, course_id, objective_id, step["activity_type"], step["stage"], ord_,
                   db.dumps({**data, "intent": step.get("intent", ""),
                             "targets_misconception": step.get("targets_misconception", ""),
                             "reserve": bool(step.get("reserve"))}),
                   status, db.dumps(verify) if verify else None, now, now))
    return aid
