"""Source-grounded Socratic tutor and roleplay partner."""
import json

from . import db, index
from .knowledge import elements_by_ids, render
from .llm import gateway
from .models import TutorReply

TUTOR_SYSTEM = """You are a patient, encouraging tutor for this course. You teach only from the course
sources provided as evidence and cite element ids like [e12].

Policy:
- Default to helping the learner think: ask a guiding question or give the smallest useful hint first.
- While a graded activity is unanswered, follow the 'Allowed help' level exactly and never reveal, paraphrase or
  list the facts that decide the answer — a hint that lets the learner match an option without thinking is a
  reveal. After they have answered, you may explain fully.
- For general questions (no activity, or an explanation stage), explain clearly and concretely.
- If the sources do not cover the question, say so plainly (move=not_in_sources) and suggest what the
  course does cover. Do not answer from general knowledge as if it were the course.
- Keep replies short (under 150 words unless explaining a worked step), concrete, and in the learner's
  language and level. End with one follow-up question when it helps learning."""

ROLEPLAY_SYSTEM = """You play a character in a learning roleplay. Stay in character, grounded in the evidence
provided (do not invent facts beyond it). Respond naturally in 1–4 sentences, reacting to what the learner
says; challenge them realistically so they must use what they learned. Never break character to lecture."""


def tutor_reply(course: dict, message: str, history: list[dict], activity: dict | None, mastery: list[dict],
                answered: bool) -> dict:
    q = message + (" " + activity["data"].get("title", "") if activity else "")
    chunks = index.search(q, course["source_ids"], k=5)
    ids = [e for ch in chunks for e in ch["element_ids"]]
    if activity:
        ids = activity["data"]["evidence"] + ids
    els = elements_by_ids(list(dict.fromkeys(ids)))
    goal = course["data"]["goal"]
    weak = [m["statement"] for m in mastery if m["state"] in ("learning", "new")][:4]
    hints_given = sum(1 for h in history if h.get("role") == "tutor")
    act_txt = ""
    guarded = bool(activity) and not answered and activity["stage"] != "model"
    if activity:
        p = dict(activity["data"])
        view = {"title": p.get("title"), "instructions": p.get("instructions"),
                "task": _learner_visible(activity["type"], p.get("payload", {}))}
        act_txt = (f"\n## Current activity ({activity['type']}, stage {activity['stage']}; learner has "
                   f"{'already answered — you may now explain fully' if not guarded else 'NOT answered yet'})\n"
                   + json.dumps(view, ensure_ascii=False)[:2500])
        if guarded:
            level = min(hints_given, 3)
            act_txt += (f"\n\n## SECRET answer key — never state it, paraphrase it, or give the facts that alone decide it\n"
                        f"{_answer_key(activity['type'], p.get('payload', {}))[:1200]}\n\n"
                        f"## Allowed help at hint level {level + 1}\n{HINT_LEVELS[level]}")
    convo = "\n".join(f"{h['role']}: {h['text']}" for h in history[-8:])
    from .translate import LANG_NAMES
    lang = goal.get("language", "en")
    user = (f"REPLY LANGUAGE: {LANG_NAMES.get(lang, lang)} — always, even if the learner or the material uses "
            f"another language (keep code and technical terms as they are).\n"
            f"Learner: {goal.get('audience_level')} — {goal.get('audience_description') or 'general'}. Objectives still being learned: {'; '.join(weak) or '-'}\n"
            f"Hints already given in this conversation: {hints_given}\n{act_txt}\n\n## Conversation\n{convo}\n"
            f"learner: {message}\n\n## Evidence\n{render(els, 3500)}")
    out = gateway.structured(TutorReply, TUTOR_SYSTEM, user, tier="fast", purpose="tutor", course_id=course["id"])
    if guarded and _leaks(activity, out.reply):  # deterministic backstop: one stricter retry
        out = gateway.structured(TutorReply, TUTOR_SYSTEM, user + "\n\nYour previous draft revealed the answer. Reply "
                                 "again with ONLY a guiding question; state no facts from the answer key.",
                                 tier="fast", purpose="tutor", course_id=course["id"])
        if _leaks(activity, out.reply):
            out.reply = ("Let's reason it out rather than me giving it away. Which part of the task are you unsure "
                         "about — and what does the course material say about it?")
            out.move = "question"
    valid = {e["id"] for e in els}
    d = out.model_dump()
    d["citations"] = [c for c in d["citations"] if c in valid]
    return d


HINT_LEVELS = [
    "Ask ONE short guiding question that helps the learner work out what the task needs. State no facts from the "
    "answer key. Do not cite the element that contains the answer.",
    "Point to WHERE in the course material to look (cite it) and what to pay attention to, without stating the "
    "deciding fact itself.",
    "Give a general reminder of the underlying idea or principle, not applied to this item's options or blanks.",
    "Walk through a different, analogous example that uses the same reasoning, then ask the learner to apply it. "
    "Still never identify the correct option, order or wording for THIS item.",
]


def _learner_visible(atype: str, p: dict) -> dict:
    hide = {"correct", "rationale", "model_answer", "answers", "bug_lines", "bug_explanation", "fixed_code", "reveal",
            "solution", "explanation", "category", "why", "answer", "sort_key"}

    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if k not in hide}
        if isinstance(o, list):
            return [strip(v) for v in o]
        return o
    return strip(p)


def _answer_key(atype: str, p: dict) -> str:
    if p.get("options"):
        return "Correct option(s): " + " | ".join(o["text"] for o in p["options"] if o.get("correct"))
    if atype == "ordering":
        return "Correct order: " + " → ".join(p.get("items", []))
    if atype == "cloze":
        return "Blanks: " + "; ".join(f"{b['id']}={b['answers'][0]}" for b in p.get("blanks", []) if b.get("answers"))
    if atype == "numeric_problem":
        return f"Answer: {p.get('answer')} {p.get('unit', '')}"
    if atype == "find_the_bug":
        return f"Bug on line(s) {p.get('bug_lines')}: {p.get('bug_explanation', '')}"
    if p.get("model_answer"):
        return "Model answer: " + p["model_answer"]
    if atype == "matching":
        return "Pairs: " + "; ".join(f"{x['left']} = {x['right']}" for x in p.get("pairs", []))
    return json.dumps(p, ensure_ascii=False)[:800]


def _leaks(activity: dict, reply: str) -> bool:
    """True if the reply contains a correct option / answer verbatim (normalised)."""
    import re as _re
    norm = lambda s: _re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()  # noqa: E731
    r = norm(reply)
    p = activity["data"].get("payload", {})
    secrets = [o["text"] for o in p.get("options", []) if o.get("correct")]
    secrets += [a for b in p.get("blanks", []) for a in b.get("answers", [])[:1]]
    if activity["type"] == "numeric_problem" and p.get("answer") is not None:
        secrets.append(str(p["answer"]))
    if _re.search(r"\b(option|answer|choice)\s*[\"']?[a-e1-5]\b\s*(is|would be)\s*(correct|right)", r):
        return True
    return any(len(norm(s)) >= 6 and norm(s) in r for s in secrets)


def roleplay_turn(course: dict, activity: dict, history: list[dict], message: str) -> dict:
    from pydantic import BaseModel, Field

    class Turn(BaseModel):
        reply: str
        goal_progress: float = Field(description="0..1 how far the learner has met the success criteria")
        criteria_met: list[str]
        finished: bool = Field(description="true when the conversation has reached a natural end or max turns")
        coach_note: str = Field(description="one sentence of coaching for the learner (shown after the turn)")

    p = activity["data"]["payload"]
    els = elements_by_ids(activity["data"]["evidence"])
    convo = "\n".join(f"{h['role']}: {h['text']}" for h in history[-12:])
    user = (f"Character: {p['persona']} — {p['persona_brief']}\nSetting: {p['setting']}\n"
            f"Learner's goal: {p['learner_goal']}\nSuccess criteria: {'; '.join(p['success_criteria'])}\n"
            f"Max turns: {p['max_turns']} (so far {sum(1 for h in history if h['role'] == 'learner')})\n\n"
            f"## Conversation\n{convo}\nlearner: {message}\n\n## Evidence\n{render(els, 2500)}")
    out = gateway.structured(Turn, ROLEPLAY_SYSTEM, user, tier="fast", purpose="roleplay", course_id=course["id"])
    return out.model_dump()
