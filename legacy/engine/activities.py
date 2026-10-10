"""Activity type registry: schema + generation guidance + grading + planning metadata per type.

Adding a type = add a payload model, a REGISTRY entry, a grader branch, and a web renderer.
"""
import math
import re
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field, create_model


# ----------------------------------------------------------------------------- payload models

class Choice(BaseModel):
    text: str
    correct: bool
    rationale: str = Field(description="why this option is right/wrong — for wrong ones, name the misconception")


class RubricItem(BaseModel):
    criterion: str
    points: int


class ExplainerSection(BaseModel):
    heading: str
    markdown: str = Field(description="short, concrete, cites evidence inline like [e12]")


class Explainer(BaseModel):
    sections: list[ExplainerSection]
    key_points: list[str]
    analogy: str = Field(description="a helpful analogy for the audience, or empty")
    check_question: str
    check_answer: str


class WorkedStep(BaseModel):
    explanation: str
    work: str = Field(description="the step itself: markdown, may contain a fenced code block or calculation")
    why: str


class WorkedExample(BaseModel):
    problem: str
    steps: list[WorkedStep]
    answer: str
    common_errors: list[str]


class Annotation(BaseModel):
    lines: str = Field(description="line range like '3' or '4-6' (1-based)")
    note: str


class CodeWalkthrough(BaseModel):
    language: str
    code: str
    annotations: list[Annotation]
    takeaway: str
    try_it: str = Field(description="a small modification the learner could try")


class MCQ(BaseModel):
    question: str
    options: list[Choice]
    multiple: bool = Field(description="true if more than one option is correct")
    explanation: str


class ShortAnswer(BaseModel):
    question: str
    model_answer: str
    rubric: list[RubricItem]
    hints: list[str]


class Ordering(BaseModel):
    prompt: str
    items: list[str] = Field(description="in the CORRECT order; the client shuffles")
    explanation: str


class Pair(BaseModel):
    left: str
    right: str


class Matching(BaseModel):
    prompt: str
    pairs: list[Pair]
    explanation: str


class CatItem(BaseModel):
    text: str
    category: str
    why: str


class Categorize(BaseModel):
    prompt: str
    categories: list[str]
    items: list[CatItem]


class Blank(BaseModel):
    id: int
    answers: list[str] = Field(description="accepted answers, most canonical first")
    hint: str


class Cloze(BaseModel):
    passage: str = Field(description="text with blanks marked [[1]], [[2]], ...")
    blanks: list[Blank]


class Card(BaseModel):
    front: str
    back: str
    hint: str


class Flashcards(BaseModel):
    cards: list[Card]


class Predict(BaseModel):
    setup: str = Field(description="markdown situation, code or experiment; stop before the outcome")
    question: str
    options: list[Choice]
    reveal: str = Field(description="what actually happens and why, with evidence")


class FindTheBug(BaseModel):
    language: str
    code: str
    bug_lines: list[int] = Field(description="1-based line numbers containing the defect")
    question: str
    bug_explanation: str
    fixed_code: str


class ScChoice(BaseModel):
    text: str
    next_node: str = Field(description="id of the next node, or empty string to end")
    feedback: str
    quality: Literal["best", "acceptable", "poor"]


class ScNode(BaseModel):
    id: str
    text: str
    choices: list[ScChoice]


class Scenario(BaseModel):
    context: str
    start_node: str
    nodes: list[ScNode]
    debrief: str


class TEvent(BaseModel):
    when: str
    label: str
    detail: str
    sort_key: float = Field(description="numeric ordering key, e.g. a year")


class Timeline(BaseModel):
    intro: str
    events: list[TEvent]
    task: Literal["order", "explore"]


class CRow(BaseModel):
    dimension: str
    cells: list[str] = Field(description="one cell per subject, same order as subjects")


class CompareTable(BaseModel):
    prompt: str
    subjects: list[str]
    rows: list[CRow]
    takeaway: str
    question: str
    options: list[Choice]


class PStage(BaseModel):
    name: str
    description: str
    what_changes: str


class PPredict(BaseModel):
    after_stage: int = Field(description="0-based index of the stage after which the question is asked")
    question: str
    options: list[Choice]


class ProcessStepper(BaseModel):
    intro: str
    stages: list[PStage]
    predictions: list[PPredict]


class PVar(BaseModel):
    name: str
    symbol: str = Field(description="identifier used in expressions, letters/digits/_ only")
    min: float
    max: float
    step: float
    default: float
    unit: str


class POut(BaseModel):
    name: str
    symbol: str
    expression: str = Field(description="uses only variable symbols, numbers, + - * / ^ ( ) and "
                                        "sqrt log exp sin cos tan abs min max pow")
    unit: str


class PQuestion(BaseModel):
    prompt: str
    options: list[Choice]
    explanation: str


class ParameterExplorer(BaseModel):
    intro: str
    variables: list[PVar]
    outputs: list[POut]
    x_variable: str = Field(description="symbol of the variable plotted on the x axis")
    questions: list[PQuestion]
    caveat: str = Field(description="where this simplified model stops being accurate")


class NumericProblem(BaseModel):
    question: str
    answer: float
    tolerance: float = Field(description="absolute tolerance accepted")
    unit: str
    hints: list[str]
    solution: list[str]


class CNode(BaseModel):
    id: str
    label: str
    note: str


class CEdge(BaseModel):
    source: str
    target: str
    label: str


class ConceptMap(BaseModel):
    nodes: list[CNode]
    edges: list[CEdge]
    questions: list[PQuestion]


class CaseQ(BaseModel):
    question: str
    model_answer: str
    rubric: list[RubricItem]


class CaseStudy(BaseModel):
    case: str
    questions: list[CaseQ]


class TeachBack(BaseModel):
    prompt: str
    audience: str
    must_include: list[str]
    rubric: list[RubricItem]


class Roleplay(BaseModel):
    persona: str
    persona_brief: str = Field(description="who they are, what they know and want; stays within the evidence")
    setting: str
    learner_goal: str
    opening_line: str
    success_criteria: list[str]
    max_turns: int


class Scene(BaseModel):
    heading: str
    narration: str = Field(description="what the narrator says in this scene: 1–3 spoken sentences, no markdown")
    visual: Literal["title", "bullets", "flow", "code", "figure", "quote", "comparison"]
    bullets: list[str] = Field(description="bullets / flow steps / comparison lines 'A | B'; empty if unused")
    code: str = Field(description="short code for a code scene, else empty")
    figure_element_id: str = Field(description="id of a figure element with an image, only for figure scenes, else empty")
    seconds: int = Field(description="scene length if no narration audio, 4–15")


class VideoLesson(BaseModel):
    scenes: list[Scene]
    summary: str


class Outcome(BaseModel):
    label: str
    score: float = Field(description="relative weight (probability-like) or logit if uses_temperature")


class DistributionSampler(BaseModel):
    intro: str
    outcomes: list[Outcome]
    uses_temperature: bool = Field(description="true if scores are logits and a temperature slider reshapes them")
    temperature_min: float
    temperature_max: float
    temperature_default: float
    questions: list[PQuestion]
    takeaway: str


class TourStop(BaseModel):
    hotspot: str = Field(description="label of one of the model's hotspots, exactly as given")
    explanation: str


class Model3D(BaseModel):
    asset_id: str
    intro: str
    tour: list[TourStop]
    questions: list[PQuestion]


class DLabel(BaseModel):
    text: str
    x: float = Field(description="0..1 from the left of the image")
    y: float = Field(description="0..1 from the top of the image")
    explanation: str


class DiagramLabel(BaseModel):
    figure_element_id: str
    prompt: str
    labels: list[DLabel]


# ----------------------------------------------------------------------------- registry

@dataclass
class ActivityType:
    key: str
    label: str
    model: type[BaseModel]
    purpose: str
    guidance: str
    knowledge_types: tuple[str, ...]
    requires: tuple[str, ...] = ()
    grading: Literal["auto", "rubric", "self", "none", "dialogue"] = "auto"
    minutes: int = 3
    enabled: bool = True
    needs: str = ""  # provider/asset capability, e.g. "vision", "3d_asset"
    stages: tuple[str, ...] = ("practice", "check")
    tier: str = "standard"
    extra: dict = field(default_factory=dict)


GEN_RULES = (
    "Write for the stated audience and language. Every factual statement must be supported by the evidence; "
    "cite element ids inline like [e12] in learner-facing prose where helpful and list them in `evidence`. "
    "List the key factual claims your activity relies on in `key_claims` (each checkable against evidence). "
    "Do not reference 'the document' or 'the text' — speak about the subject itself. "
    "The concept list and misconceptions are orientation only: every fact you teach or test must be supported by "
    "the Evidence section. If the evidence is thin, make the activity narrower rather than filling gaps."
)

REGISTRY: dict[str, ActivityType] = {a.key: a for a in [
    ActivityType("explainer", "Explanation", Explainer, "teach a concept clearly with examples",
                 "2–4 short sections, concrete examples from the evidence, one analogy if genuinely helpful, "
                 "end with a quick self-check. No fluff, no summary of the source's structure.",
                 ("fact", "concept", "principle", "process", "procedure", "structure", "chronology", "argument",
                  "quantitative", "code", "language", "data"), grading="none", minutes=4, stages=("model",)),
    ActivityType("worked_example", "Worked example", WorkedExample, "model how an expert solves/does it",
                 "A realistic problem, 3–7 steps each with the action, the work and WHY. Show reasoning, not only "
                 "results. List the common errors a novice makes.",
                 ("procedure", "quantitative", "code", "principle"), grading="none", minutes=5, stages=("model",)),
    ActivityType("code_walkthrough", "Code walkthrough", CodeWalkthrough, "read and understand real code",
                 "Use code from the evidence (lightly trimmed). Annotate the lines that matter, in order. "
                 "`try_it` suggests one small change and what to expect.",
                 ("code",), requires=("code",), grading="none", minutes=4, stages=("model",)),
    ActivityType("mcq", "Multiple choice", MCQ, "check understanding or diagnose",
                 "One unambiguous question testing the objective (not trivia). 3–5 options; distractors are "
                 "plausible and each maps to a real misconception; no 'all of the above'. Rationale for every "
                 "option.", ("fact", "concept", "principle", "process", "procedure", "structure", "chronology",
                             "argument", "quantitative", "code", "language", "data"),
                 minutes=1, stages=("activate", "practice", "check", "transfer"), tier="standard"),
    ActivityType("short_answer", "Short answer", ShortAnswer, "explain in own words; deeper check",
                 "An open question requiring explanation/application, a concise model answer, a 2–4 criterion "
                 "rubric (points), and 2 graduated hints.",
                 ("concept", "principle", "process", "argument", "procedure", "code", "chronology", "data"),
                 grading="rubric", minutes=4, stages=("check", "transfer")),
    ActivityType("ordering", "Put in order", Ordering, "sequence steps, stages or events",
                 "4–7 items that have exactly one defensible order (a procedure, a process, a chronology). Never include "
                 "two items whose relative order does not matter; merge them into one item instead.",
                 ("procedure", "process", "chronology"), requires=("sequence",), minutes=2,
                 stages=("activate", "practice", "check")),
    ActivityType("matching", "Matching", Matching, "link terms to meanings, causes to effects, parts to roles",
                 "4–6 pairs, each right side matching exactly one left side.",
                 ("fact", "concept", "structure", "language", "chronology", "process"), minutes=2,
                 requires=("multi_concept",), stages=("practice", "check")),
    ActivityType("categorize", "Sort into groups", Categorize, "classify examples vs non-examples",
                 "2–4 categories and 6–10 items, including borderline cases that reveal understanding.",
                 ("concept", "argument", "structure", "data"), minutes=3, stages=("practice",)),
    ActivityType("cloze", "Fill the gaps", Cloze, "recall key terms/steps in context",
                 "A short passage (2–5 sentences, or a code snippet) with 2–5 blanks on the terms that matter; "
                 "accept reasonable synonyms.", ("fact", "procedure", "language", "code"), minutes=2,
                 stages=("practice", "check")),
    ActivityType("flashcards", "Flashcards", Flashcards, "retrieval practice of core facts/terms",
                 "4–8 cards, one idea per card, front is a question or cue (not just a word when avoidable).",
                 ("fact", "language", "concept"), grading="self", minutes=3, stages=("activate", "practice")),
    ActivityType("predict", "Predict, then see", Predict, "predict an outcome before it is revealed",
                 "Describe a situation/experiment/code run up to the moment before the result. Options are "
                 "plausible predictions; the reveal explains the actual outcome and why intuition fails.",
                 ("principle", "process", "code", "quantitative", "concept", "chronology"), minutes=2,
                 stages=("activate", "practice")),
    ActivityType("find_the_bug", "Find the bug", FindTheBug, "debug a realistic mistake",
                 "Code based on the evidence with one realistic defect reflecting a common misconception. "
                 "Keep it under 25 lines.", ("code",), requires=("code",), minutes=3, stages=("practice", "check")),
    ActivityType("scenario", "Decision scenario", Scenario, "apply knowledge to a realistic decision",
                 "A short realistic situation for the audience (their role/context) with 2–3 decision points, "
                 "3 choices each (best/acceptable/poor), consequences as feedback, and a debrief tying back to "
                 "the objective. Node ids like n1, n2.",
                 ("procedure", "principle", "argument", "concept", "code"), minutes=5, stages=("transfer", "practice")),
    ActivityType("timeline", "Timeline", Timeline, "place events in time and see causes",
                 "5–8 events from the evidence with dates and one-line significance.",
                 ("chronology",), requires=("events",), minutes=3, stages=("model", "practice")),
    ActivityType("compare_table", "Compare", CompareTable, "contrast related concepts on the dimensions that matter",
                 "2–4 subjects and 3–6 dimensions where they genuinely differ, a takeaway, then one question "
                 "that needs the comparison.", ("concept", "argument", "data", "structure", "code"),
                 requires=("multi_concept",), minutes=3, stages=("model", "practice")),
    ActivityType("process_stepper", "Step through the process", ProcessStepper, "see a process unfold stage by stage",
                 "3–7 stages with what changes at each; 1–3 'what happens next?' predictions between stages.",
                 ("process", "procedure"), requires=("sequence",), minutes=4, stages=("model", "practice")),
    ActivityType("parameter_explorer", "Explore the model", ParameterExplorer,
                 "manipulate a quantitative relationship and observe",
                 "Only when the evidence gives a real quantitative relationship. 1–3 variables with realistic "
                 "ranges, outputs as safe expressions using only the variable symbols, 2 questions answered by "
                 "experimenting, and the model's limits.",
                 ("quantitative", "principle"), requires=("formula",), minutes=5, stages=("model", "practice")),
    ActivityType("distribution_sampler", "Sample the distribution", DistributionSampler,
                 "draw random samples and see how probabilities (and temperature) shape outcomes",
                 "Only when the evidence involves chance, probability distributions, sampling or model output "
                 "probabilities. 3–8 outcomes with realistic weights; enable temperature only for logit/softmax "
                 "settings (range ~0.1–2). 2 questions answered by experimenting, and a takeaway.",
                 ("quantitative", "principle", "data", "concept"), requires=("chance",), minutes=4,
                 stages=("model", "practice")),
    ActivityType("numeric_problem", "Calculate", NumericProblem, "apply a formula/procedure to numbers",
                 "A realistic problem with a single numeric answer, tolerance, unit, 2 hints and a stepwise solution.",
                 ("quantitative", "data"), requires=("formula",), minutes=4, stages=("practice", "check", "transfer")),
    ActivityType("concept_map", "Concept map", ConceptMap, "see how ideas connect",
                 "5–10 nodes from the objective's concepts with labelled relations, then 2 questions about the "
                 "connections.", ("concept", "structure", "principle", "argument"), requires=("multi_concept",),
                 minutes=3, stages=("model",)),
    ActivityType("case_study", "Case study", CaseStudy, "analyse a realistic case",
                 "A concise case (150–300 words) grounded in the evidence, 2–3 analysis questions with model "
                 "answers and rubrics.", ("argument", "principle", "procedure", "chronology"), grading="rubric",
                 minutes=8, stages=("transfer",)),
    ActivityType("teach_back", "Teach it back", TeachBack, "explain it to someone else",
                 "Ask the learner to explain the idea to a specific audience; list what a good explanation must "
                 "include and a rubric.", ("concept", "principle", "process", "procedure", "argument"),
                 grading="rubric", minutes=4, stages=("transfer",)),
    ActivityType("roleplay", "Roleplay", Roleplay, "practise in conversation with a character",
                 "A persona the learner must interact with to achieve a goal that needs the objective "
                 "(e.g. advise a colleague, interview a historical figure, handle a customer). Persona stays "
                 "within the evidence.", ("argument", "language", "chronology", "procedure", "principle"),
                 grading="dialogue", minutes=6, stages=("transfer",)),
    ActivityType("diagram_label", "Label the diagram", DiagramLabel, "locate parts on a real figure",
                 "Use the provided figure. 3–7 labels with positions (0..1) and explanations.",
                 ("structure", "process"), requires=("figure",), minutes=3, needs="vision",
                 stages=("practice",), tier="standard"),
    ActivityType("video_lesson", "Narrated explainer", VideoLesson, "watch a short narrated, animated explanation",
                 "A 60–120 second storyboard of 4–8 scenes: hook → build the idea step by step → recap. Choose the "
                 "visual that carries each point (flow for processes, code for code, comparison for contrasts, a "
                 "source figure when one with an image is listed). Narration is conversational and exact; visuals "
                 "are keywords, not the narration repeated.", ("process", "concept", "principle", "procedure",
                                                                "chronology", "structure", "code"),
                 grading="none", minutes=2, stages=("model",)),
    ActivityType("model_3d", "Explore in 3D", Model3D, "explore a real 3D model with a guided tour",
                 "Use the attached 3D model and ONLY its listed hotspots. Write a short intro, a guided tour that visits "
                 "the hotspots in a sensible teaching order (structure → function), and 1–3 questions answered by "
                 "exploring the model.", ("structure", "process"), requires=("asset_3d",), grading="auto",
                 minutes=5, stages=("model", "practice")),
    ActivityType("video", "Video explainer", Explainer, "watch a short generated explainer",
                 "Requires a video generation provider.", ("process", "concept"), grading="none", enabled=False,
                 needs="video_provider", stages=("model",)),
]}


class Envelope(BaseModel):
    title: str
    instructions: str = Field(description="one sentence telling the learner what to do")
    evidence: list[str] = Field(description="element ids the activity is based on")
    key_claims: list[str]
    difficulty: float = Field(description="0 easy .. 1 hard for this audience")


_ENVELOPES: dict[str, type[BaseModel]] = {}


def envelope(key: str) -> type[BaseModel]:
    if key not in _ENVELOPES:
        t = REGISTRY[key]
        _ENVELOPES[key] = create_model(f"Activity_{key}", __base__=Envelope, payload=(t.model, ...))
    return _ENVELOPES[key]


def catalog() -> list[dict]:
    return [{"key": t.key, "label": t.label, "purpose": t.purpose, "knowledge_types": list(t.knowledge_types),
             "requires": list(t.requires), "grading": t.grading, "minutes": t.minutes, "enabled": t.enabled,
             "needs": t.needs, "stages": list(t.stages)} for t in REGISTRY.values()]


# ----------------------------------------------------------------------------- grading

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9.]+", " ", str(s).lower()).strip()


def _num(s):
    try:
        return float(str(s).replace(",", "").strip())
    except ValueError:
        return None


def grade_auto(atype: str, payload: dict, response: dict) -> dict:
    """Deterministic grading. Returns {score 0..1, correct bool, detail}. Response shapes are documented
    per type in the web renderers."""
    p, r = payload, response or {}

    def choices(opts, selected):
        correct = {i for i, o in enumerate(opts) if o["correct"]}
        sel = set(selected or [])
        if not correct:
            return 0.0, False
        hit = len(sel & correct) / len(correct) - len(sel - correct) / max(1, len(opts) - len(correct))
        return max(0.0, hit), sel == correct

    if atype in ("mcq", "predict"):
        s, ok = choices(p["options"], r.get("selected"))
        return {"score": s, "correct": ok}
    if atype == "compare_table":
        s, ok = choices(p["options"], r.get("selected"))
        return {"score": s, "correct": ok}
    if atype in ("process_stepper",):
        preds = p.get("predictions", [])
        answers = r.get("answers", {})
        res = [choices(q["options"], answers.get(str(i), []))[0] for i, q in enumerate(preds)]
        s = sum(res) / len(res) if res else 1.0
        return {"score": s, "correct": s >= 0.99}
    if atype in ("parameter_explorer", "concept_map", "model_3d", "distribution_sampler"):
        qs = p.get("questions", [])
        answers = r.get("answers", {})
        res = [choices(q["options"], answers.get(str(i), []))[0] for i, q in enumerate(qs)]
        s = sum(res) / len(res) if res else 1.0
        return {"score": s, "correct": s >= 0.99}
    if atype in ("ordering",):
        want = p["items"]
        got = r.get("order", [])
        s = sum(1 for a, b in zip(want, got) if a == b) / len(want) if want else 0
        return {"score": s, "correct": got == want}
    if atype == "timeline":
        want = [e["label"] for e in sorted(p["events"], key=lambda e: e["sort_key"])]
        got = r.get("order", [])
        s = sum(1 for a, b in zip(want, got) if a == b) / len(want) if want else 1.0
        return {"score": s, "correct": got == want or p.get("task") == "explore"}
    if atype == "matching":
        want = {x["left"]: x["right"] for x in p["pairs"]}
        got = r.get("pairs", {})
        s = sum(1 for k, v in want.items() if got.get(k) == v) / len(want) if want else 0
        return {"score": s, "correct": s == 1}
    if atype == "categorize":
        want = {str(i): x["category"] for i, x in enumerate(p["items"])}
        got = r.get("assign", {})
        s = sum(1 for k, v in want.items() if got.get(k) == v) / len(want) if want else 0
        return {"score": s, "correct": s == 1}
    if atype == "cloze":
        got = r.get("blanks", {})
        per = {}
        for bl in p["blanks"]:
            g = got.get(str(bl["id"]), "")
            ok = any(_norm(g) == _norm(a) for a in bl["answers"])
            if not ok and _num(g) is not None:
                ok = any(_num(a) is not None and abs(_num(a) - _num(g)) < 1e-6 for a in bl["answers"])
            per[str(bl["id"])] = ok
        s = sum(per.values()) / len(per) if per else 0
        return {"score": s, "correct": s == 1, "detail": per}
    if atype == "numeric_problem":
        g = _num(r.get("value"))
        ok = g is not None and math.isfinite(g) and abs(g - p["answer"]) <= max(p["tolerance"], 1e-9)
        return {"score": 1.0 if ok else 0.0, "correct": ok}
    if atype == "find_the_bug":
        want, got = set(p["bug_lines"]), set(r.get("lines", []))
        ok = bool(got) and got <= want | {x + d for x in want for d in (-1, 1)} and bool(got & want)
        return {"score": 1.0 if ok else 0.0, "correct": ok}
    if atype == "scenario":
        q = {"best": 1.0, "acceptable": 0.6, "poor": 0.0}
        path = r.get("qualities", [])
        s = sum(q.get(x, 0) for x in path) / len(path) if path else 0
        return {"score": s, "correct": s >= 0.8}
    if atype == "diagram_label":
        got = r.get("placed", {})
        labels = p["labels"]
        hits = sum(1 for i, l in enumerate(labels)
                   if (pt := got.get(str(i))) and math.dist((pt[0], pt[1]), (l["x"], l["y"])) < 0.08)
        s = hits / len(labels) if labels else 0
        return {"score": s, "correct": s == 1}
    if atype == "flashcards":
        ratings = r.get("ratings", {})
        val = {"again": 0.0, "hard": 0.5, "good": 0.85, "easy": 1.0}
        vals = [val.get(v, 0) for v in ratings.values()]
        s = sum(vals) / len(vals) if vals else 0
        return {"score": s, "correct": s >= 0.8}
    return {"score": None, "correct": None}


# ----------------------------------------------------------------------------- structural validation

_SAFE_FUNCS = {"sqrt", "log", "ln", "log10", "exp", "sin", "cos", "tan", "abs", "min", "max", "pow", "floor",
               "ceil", "round"}


def _expr_ok(expr: str, symbols: set[str]) -> str | None:
    """Check a parameter-explorer expression against the grammar the web evaluator accepts."""
    import ast
    try:
        tree = ast.parse(expr.replace("^", "**"), mode="eval")
    except SyntaxError:
        return f"expression does not parse: {expr}"
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id.lower() not in _SAFE_FUNCS:
                return f"expression uses a disallowed call: {expr}"
        elif isinstance(node, ast.Name):
            if node.id not in symbols and node.id.lower() not in _SAFE_FUNCS | {"pi", "e"}:
                return f"expression uses unknown symbol '{node.id}'"
        elif isinstance(node, (ast.Attribute, ast.Subscript, ast.Lambda, ast.Compare, ast.BoolOp, ast.IfExp)):
            return f"expression uses unsupported syntax: {expr}"
    return None


def structural_issues(atype: str, p: dict) -> list[str]:
    """Deterministic checks that an activity is well-formed and answerable. Runs before the model review."""
    out: list[str] = []

    def choices(opts, where="question"):
        if len(opts) < 2:
            out.append(f"{where}: fewer than 2 options")
        if not any(o["correct"] for o in opts):
            out.append(f"{where}: no option marked correct")
        if len({o["text"].strip().lower() for o in opts}) < len(opts):
            out.append(f"{where}: duplicate options")

    if atype in ("mcq", "predict", "compare_table"):
        choices(p["options"])
        if atype == "mcq" and not p.get("multiple") and sum(o["correct"] for o in p["options"]) > 1:
            out.append("single-answer question has several correct options")
    elif atype == "ordering":
        if len(p["items"]) < 3 or len(set(p["items"])) < len(p["items"]):
            out.append("ordering needs at least 3 distinct items")
    elif atype == "matching":
        if len(p["pairs"]) < 3:
            out.append("matching needs at least 3 pairs")
        if len({x["left"] for x in p["pairs"]}) < len(p["pairs"]) or \
                len({x["right"] for x in p["pairs"]}) < len(p["pairs"]):
            out.append("matching has duplicate left or right sides")
    elif atype == "categorize":
        cats = set(p["categories"])
        if len(cats) < 2:
            out.append("categorize needs at least 2 categories")
        bad = [x["text"] for x in p["items"] if x["category"] not in cats]
        if bad:
            out.append(f"items assigned to unknown categories: {bad[:3]}")
    elif atype == "cloze":
        marks = set(re.findall(r"\[\[(\d+)\]\]", p["passage"]))
        ids = {str(b["id"]) for b in p["blanks"]}
        if not ids or marks != ids:
            out.append(f"cloze blanks {sorted(ids)} do not match passage markers {sorted(marks)}")
        if any(not b["answers"] for b in p["blanks"]):
            out.append("a blank has no accepted answer")
    elif atype == "flashcards":
        if len(p["cards"]) < 3:
            out.append("fewer than 3 flashcards")
    elif atype == "find_the_bug":
        n = len(p["code"].split("\n"))
        if not p["bug_lines"] or any(x < 1 or x > n for x in p["bug_lines"]):
            out.append("bug_lines are empty or outside the code")
        if p["fixed_code"].strip() == p["code"].strip():
            out.append("fixed_code is identical to the buggy code")
    elif atype == "scenario":
        ids = {n["id"] for n in p["nodes"]}
        if p["start_node"] not in ids:
            out.append("start_node does not exist")
        dangling = [c["next_node"] for n in p["nodes"] for c in n["choices"] if c["next_node"] and c["next_node"] not in ids]
        if dangling:
            out.append(f"choices point to missing nodes: {dangling[:3]}")
        if not any(c["quality"] == "best" for n in p["nodes"] for c in n["choices"]):
            out.append("no 'best' choice anywhere")
    elif atype == "timeline":
        if len(p["events"]) < 3:
            out.append("timeline needs at least 3 events")
    elif atype == "process_stepper":
        if len(p["stages"]) < 3:
            out.append("process needs at least 3 stages")
        for i, q in enumerate(p["predictions"]):
            if not 0 <= q["after_stage"] < len(p["stages"]) - 1:
                out.append(f"prediction {i} is not placed between stages")
            choices(q["options"], f"prediction {i}")
    elif atype == "parameter_explorer":
        syms = {v["symbol"] for v in p["variables"]}
        if p["x_variable"] not in syms:
            out.append("x_variable is not one of the variables")
        for v in p["variables"]:
            if not v["min"] < v["max"] or not v["min"] <= v["default"] <= v["max"]:
                out.append(f"variable {v['symbol']} has an invalid range")
        for o in p["outputs"]:
            if err := _expr_ok(o["expression"], syms):
                out.append(err)
        for i, q in enumerate(p["questions"]):
            choices(q["options"], f"question {i}")
    elif atype == "numeric_problem":
        if p["tolerance"] < 0:
            out.append("negative tolerance")
    elif atype == "concept_map":
        ids = {n["id"] for n in p["nodes"]}
        if any(e["source"] not in ids or e["target"] not in ids for e in p["edges"]):
            out.append("edges reference missing nodes")
        for i, q in enumerate(p["questions"]):
            choices(q["options"], f"question {i}")
    elif atype == "diagram_label":
        if any(not (0 <= lb["x"] <= 1 and 0 <= lb["y"] <= 1) for lb in p["labels"]):
            out.append("label positions outside 0..1")
    elif atype == "short_answer":
        if not p["rubric"]:
            out.append("no rubric")
    elif atype == "distribution_sampler":
        if len(p["outcomes"]) < 2:
            out.append("needs at least 2 outcomes")
        if not p["uses_temperature"] and any(o["score"] < 0 for o in p["outcomes"]):
            out.append("negative weights without temperature/softmax")
        if p["uses_temperature"] and not 0 < p["temperature_min"] < p["temperature_max"]:
            out.append("invalid temperature range")
        for i, q in enumerate(p["questions"]):
            choices(q["options"], f"question {i}")
    elif atype == "model_3d":
        if not p["tour"]:
            out.append("the 3D tour has no stops")
        for i, q in enumerate(p["questions"]):
            choices(q["options"], f"question {i}")
    elif atype == "video_lesson":
        if len(p["scenes"]) < 3:
            out.append("a narrated explainer needs at least 3 scenes")
        if any(not sc["narration"].strip() for sc in p["scenes"]):
            out.append("a scene has no narration")
    elif atype == "case_study":
        if not p["questions"]:
            out.append("no questions")
    return out
