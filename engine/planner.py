"""Pedagogy planner: for each objective decide HOW it is taught.

Rule-based eligibility (knowledge type × stage × goal × available evidence × renderer capability),
then the model chooses within the eligible set and explains why. The stage sequence follows the
research base: activate → model → practise (hints) → check → transfer; spaced review is scheduled
later by the mastery engine.
"""
from typing import Literal

from pydantic import BaseModel, Field, create_model

from .activities import REGISTRY
from .llm import gateway
from .models import Goal

PREFERRED = {
    "fact": {"activate": ["flashcards", "mcq"], "model": ["explainer"], "practice": ["matching", "cloze", "flashcards"],
             "check": ["mcq", "cloze"], "transfer": ["mcq", "short_answer"]},
    "concept": {"activate": ["predict", "mcq"], "model": ["explainer", "video_lesson", "compare_table", "concept_map"],
                "practice": ["categorize", "mcq", "matching"], "check": ["mcq", "short_answer"],
                "transfer": ["scenario", "short_answer", "teach_back"]},
    "principle": {"activate": ["predict"], "model": ["explainer", "parameter_explorer", "distribution_sampler", "video_lesson", "worked_example"],
                  "practice": ["predict", "parameter_explorer", "distribution_sampler", "mcq"], "check": ["short_answer", "mcq"],
                  "transfer": ["scenario", "case_study"]},
    "process": {"activate": ["predict", "ordering"], "model": ["process_stepper", "video_lesson", "explainer"],
                "practice": ["ordering", "process_stepper", "diagram_label", "matching"], "check": ["ordering", "mcq"],
                "transfer": ["short_answer", "scenario"]},
    "procedure": {"activate": ["mcq", "predict"], "model": ["worked_example", "process_stepper", "explainer"],
                  "practice": ["ordering", "cloze", "scenario"], "check": ["ordering", "mcq", "short_answer"],
                  "transfer": ["scenario", "short_answer"]},
    "structure": {"activate": ["mcq"], "model": ["explainer", "concept_map", "model_3d"],
                  "practice": ["diagram_label", "matching", "categorize"], "check": ["mcq", "matching"],
                  "transfer": ["short_answer"]},
    "chronology": {"activate": ["predict", "mcq"], "model": ["timeline", "video_lesson", "explainer"],
                   "practice": ["timeline", "ordering", "matching"], "check": ["mcq", "short_answer"],
                   "transfer": ["roleplay", "case_study", "short_answer"]},
    "argument": {"activate": ["predict", "mcq"], "model": ["explainer", "compare_table", "case_study"],
                 "practice": ["scenario", "categorize"], "check": ["short_answer", "mcq"],
                 "transfer": ["roleplay", "case_study", "teach_back"]},
    "quantitative": {"activate": ["predict"], "model": ["worked_example", "parameter_explorer", "explainer"],
                     "practice": ["numeric_problem", "parameter_explorer", "distribution_sampler"], "check": ["numeric_problem", "mcq"],
                     "transfer": ["numeric_problem", "short_answer"]},
    "code": {"activate": ["predict", "mcq"], "model": ["code_walkthrough", "worked_example", "explainer"],
             "practice": ["predict", "find_the_bug", "cloze"], "check": ["mcq", "find_the_bug", "short_answer"],
             "transfer": ["scenario", "short_answer"]},
    "language": {"activate": ["flashcards"], "model": ["explainer", "flashcards"],
                 "practice": ["flashcards", "cloze", "matching"], "check": ["cloze", "mcq"],
                 "transfer": ["roleplay", "short_answer"]},
    "data": {"activate": ["predict", "mcq"], "model": ["explainer", "compare_table"],
             "practice": ["mcq", "numeric_problem"], "check": ["mcq", "short_answer"], "transfer": ["short_answer"]},
}

STAGES_BY_PURPOSE = {
    "understand": ["activate", "model", "practice", "check"],
    "apply": ["model", "practice", "practice", "transfer", "check"],
    "exam_prep": ["activate", "model", "practice", "check", "check"],
    "certification": ["model", "practice", "check", "check"],
    "revision": ["activate", "practice", "check"],
    "onboarding": ["model", "practice", "transfer"],
    "teach_others": ["model", "practice", "transfer", "check"],
}

PURPOSE_BIAS = {
    "exam_prep": {"check": ["mcq", "short_answer", "numeric_problem", "cloze"],
                  "practice": ["mcq", "short_answer", "numeric_problem"]},
    "teach_others": {"transfer": ["teach_back"]},
    "apply": {"transfer": ["scenario", "case_study", "find_the_bug"]},
    "onboarding": {"transfer": ["scenario", "roleplay"], "practice": ["scenario", "ordering"]},
    "revision": {"activate": ["flashcards", "mcq"], "practice": ["flashcards", "cloze", "mcq"]},
    "certification": {"check": ["mcq", "short_answer", "ordering"]},
}

PLAN_SYSTEM = """You are a learning designer choosing the activity for each stage of a lesson.
Choose from the allowed types per stage only. Prefer the type that best fits the kind of knowledge,
the learner's goal and the available evidence (e.g. real code → code activities; a real formula →
explorer/calculation; clear sequence → ordering/stepper). Vary types within the lesson. For each step
state the intent (what the learner should get out of it) and which misconception, if any, it targets.
difficulty: 0 easy .. 1 hard for this audience; ramp up across the lesson."""


def assets_for(objective: dict, unit_knowledge: dict[str, dict], evidence_els: list[dict], graph: dict) -> dict:
    uks = [unit_knowledge[u] for u in objective["units"] if u in unit_knowledge]
    figures = [e["id"] for e in evidence_els if e["kind"] == "figure" and e["media_path"]]
    for uk in uks:
        figures += [f["element_id"] for f in uk["figures"]]
    kt = objective["knowledge_type"]
    events = sum(len(uk["events"]) for uk in uks)
    return {
        "code": kt == "code" or any(e["kind"] == "code" for e in evidence_els),
        "formula": any(uk["formulas"] for uk in uks) or any(e["kind"] == "equation" for e in evidence_els),
        "sequence": kt in ("process", "procedure", "chronology") or any(uk["procedures"] for uk in uks) or events >= 3,
        "events": events >= 3,
        "chance": _mentions_chance(objective, evidence_els),
        "figure": bool(figures),
        "multi_concept": len(objective["concept_ids"]) >= 2 or len(graph["concepts"]) >= 4,
        "asset_3d": bool(models_3d := match_3d(objective, graph)),
        "assets_3d": models_3d,
        "figures": list(dict.fromkeys(figures))[:4],
        "misconceptions": [m for uk in uks for m in uk["misconceptions"]][:6],
        "procedures": [p for uk in uks for p in uk["procedures"]][:3],
        "formulas": [f for uk in uks for f in uk["formulas"]][:3],
        "events_list": [e for uk in uks for e in uk["events"]][:12],
    }


CHANCE = ("probabilit", "random", "sampling", "sample", "distribution", "temperature", "likelihood", "chance",
          "stochastic", "softmax", "odds", "expected value")


def _mentions_chance(objective: dict, els: list[dict]) -> bool:
    text = (objective["statement"] + " " + " ".join(e["text"][:400] for e in els[:20])).lower()
    return sum(text.count(w) for w in CHANCE) >= 3


def match_3d(objective: dict, graph: dict) -> list[dict]:
    """3D assets whose name/description/tags overlap the objective's statement and concepts."""
    import re as _re
    from . import db
    course_id = graph.get("course_id")
    assets = [a for a in (db.list_docs(course_id, "asset") or {}).values() if a.get("kind") == "3d"] if course_id else []
    if not assets:
        return []
    names = {c["id"]: c["name"] for c in graph["concepts"]}
    text = " ".join([objective["statement"]] + [names.get(c, "") for c in objective["concept_ids"]]).lower()
    words = {w for w in _re.findall(r"[a-z]{4,}", text)}
    out = []
    for a in assets:
        aw = {w for w in _re.findall(r"[a-z]{4,}", f"{a['name']} {a.get('description', '')} {' '.join(a.get('tags', []))}".lower())}
        if len(words & aw) >= 1 and a.get("hotspots"):
            out.append({"id": a["id"], "name": a["name"], "hotspots": [h["label"] for h in a["hotspots"]]})
    return out


def eligible(stage: str, kt: str, goal: Goal, assets: dict, provider: str) -> list[str]:
    def ok(key):
        t = REGISTRY.get(key)
        if not t or not t.enabled:
            return False
        if t.needs == "vision" and provider == "mock":
            return False
        return all(assets.get(r) for r in t.requires)

    prefs = PURPOSE_BIAS.get(goal.purpose, {}).get(stage, []) + PREFERRED.get(kt, {}).get(stage, [])
    if not goal.hands_on:
        prefs = [p for p in prefs if p not in ("roleplay",)]
    general = [k for k, t in REGISTRY.items() if stage in t.stages and kt in t.knowledge_types]
    out = [k for k in dict.fromkeys(prefs + general) if ok(k)]
    return out or ["mcq" if stage != "model" else "explainer"]


def stages_for(goal: Goal, minutes: int) -> list[str]:
    stages = list(STAGES_BY_PURPOSE[goal.purpose])
    if goal.depth == "overview" and len(stages) > 3:
        stages = [s for i, s in enumerate(stages) if not (s in ("practice", "transfer") and i == len(stages) - 2)]
    if goal.depth == "deep" and "transfer" not in stages:
        stages.append("transfer")
    if minutes and minutes <= 5:
        stages = [s for s in stages if s != "activate"][:3]
    return stages


def plan_objective(course_id: str, objective: dict, goal: Goal, assets: dict, concepts: list[dict],
                   tier: str = "fast") -> dict:
    kt = objective["knowledge_type"]
    stages = stages_for(goal, objective.get("estimated_minutes", 10))
    allowed = {s: eligible(s, kt, goal, assets, gateway.provider) for s in dict.fromkeys(stages)}
    all_types = sorted({t for v in allowed.values() for t in v})
    Step = create_model("PlanStep", stage=(Literal[tuple(dict.fromkeys(stages))], ...),
                        activity_type=(Literal[tuple(all_types)], ...),
                        intent=(str, ...), targets_misconception=(str, Field(description="or empty")),
                        difficulty=(float, ...))
    Plan = create_model("LessonPlanOut", rationale=(str, ...), steps=(list[Step], ...))
    miscon = "\n".join(f"- {m['misconception']} (correct: {m['correction']})" for m in assets["misconceptions"]) \
        or "(none recorded)"
    concept_txt = "\n".join(f"- {c['name']}: {c['definition'][:200]}" for c in concepts) or "-"
    avail = [k for k in ("code", "formula", "sequence", "events", "figure") if assets.get(k)]
    user = (f"Objective: {objective['statement']} (Bloom: {objective['bloom']}; knowledge type: {kt})\n"
            f"Success criteria: {'; '.join(objective['success_criteria'])}\n"
            f"Learner: {goal.audience_level} — {goal.audience_description or 'general'}; purpose {goal.purpose}; "
            f"about {objective.get('estimated_minutes', 10)} minutes for this objective.\n"
            f"Concepts:\n{concept_txt}\nKnown misconceptions:\n{miscon}\n"
            f"Evidence available: {', '.join(avail) or 'prose only'}\n\n"
            f"Stages in order: {', '.join(stages)}\nAllowed activity types per stage:\n"
            + "\n".join(f"- {s}: {', '.join(v)}" for s, v in allowed.items())
            + "\nReturn exactly one step per listed stage, in order.")
    out = gateway.structured(Plan, PLAN_SYSTEM, user, tier=tier, purpose="plan", course_id=course_id)
    steps = []
    for i, st in enumerate(out.steps[:len(stages)]):
        stage = stages[i] if i < len(stages) else st.stage
        atype = st.activity_type if st.activity_type in allowed.get(stage, []) else allowed[stage][0]
        steps.append({"stage": stage, "activity_type": atype, "intent": st.intent,
                      "targets_misconception": st.targets_misconception,
                      "difficulty": max(0.0, min(1.0, st.difficulty))})
    for stage in stages[len(steps):]:
        steps.append({"stage": stage, "activity_type": allowed[stage][0], "intent": "", "targets_misconception": "",
                      "difficulty": 0.5})
    return {"objective_id": objective["id"], "rationale": out.rationale, "steps": steps, "allowed": allowed}
