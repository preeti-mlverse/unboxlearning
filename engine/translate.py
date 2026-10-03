"""Multilingual courses: one canonical course, per-language renditions with the same ids.

* a course glossary per language (from the concept graph, teacher-editable) keeps terminology consistent
* every approved activity is translated into its own schema; a structural check guarantees answers,
  ids, numbers, code and citations are unchanged, otherwise the canonical version is kept
* learners switch language freely — mastery is keyed on activity/objective ids, so it carries over
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from pydantic import BaseModel, Field

from . import db
from .activities import envelope
from .config import settings
from .llm import gateway

LANG_NAMES = {"en": "English", "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "bn": "Bengali", "mr": "Marathi",
              "kn": "Kannada", "ml": "Malayalam", "gu": "Gujarati", "pa": "Punjabi", "ur": "Urdu", "ar": "Arabic",
              "es": "Spanish", "fr": "French", "de": "German", "pt": "Portuguese", "ja": "Japanese", "zh": "Chinese",
              "id": "Indonesian", "sw": "Swahili"}

FIXED_KEYS = {"id", "next_node", "start_node", "symbol", "expression", "x_variable", "figure_element_id",
              "media_path", "language", "code", "fixed_code", "lines", "evidence", "quality", "visual", "task"}

SYSTEM = """You are a professional educational translator. Translate every learner-facing string into the
target language for the stated audience, naturally and accurately — not word for word. Use the glossary for
terminology. Never change: structure, ids, numbers, true/false flags, code, formulas/expressions, element
citations like [e12], URLs, or proper names that are conventionally untranslated. Keep technical terms in
English (with the glossary rendering) when that is how practitioners in that language actually use them."""


class GlossaryEntry(BaseModel):
    term: str
    translation: str
    keep_english: bool = Field(description="true if practitioners normally keep the English term")


class Glossary(BaseModel):
    entries: list[GlossaryEntry]


class ObjText(BaseModel):
    statement: str
    success_criteria: list[str]


class ModText(BaseModel):
    title: str
    why: str


class CurriculumText(BaseModel):
    course_title: str
    learner_promise: str
    modules: list[ModText]
    objectives: list[ObjText]


def same_shape(a, b, key: str = "") -> bool:
    """True if b is a faithful structural rendition of a (only free text may differ)."""
    if isinstance(a, dict):
        return isinstance(b, dict) and a.keys() == b.keys() and all(same_shape(a[k], b[k], k) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(same_shape(x, y, key) for x, y in zip(a, b))
    if isinstance(a, bool) or isinstance(a, (int, float)):
        return a == b
    if isinstance(a, str):
        if key in FIXED_KEYS:
            return a == b
        return isinstance(b, str) and a.count("[e") == b.count("[e")
    return a == b


def glossary(course_id: str, lang: str) -> list[dict]:
    have = db.get_doc(course_id, "glossary", lang)
    if have:
        return have
    graph = db.get_doc(course_id, "graph") or {"concepts": []}
    terms = [c["name"] for c in sorted(graph["concepts"], key=lambda c: -c["importance"])[:120]]
    if not terms:
        return []
    out = gateway.structured(Glossary, SYSTEM, f"Target language: {LANG_NAMES.get(lang, lang)}\n"
                             "Create a glossary entry for each term:\n" + "\n".join(terms),
                             tier="fast", purpose="translate:glossary", course_id=course_id)
    entries = [e.model_dump() for e in out.entries]
    db.put_doc(course_id, "glossary", entries, lang)
    return entries


def _gloss_txt(entries):
    return "\n".join(f"- {e['term']} → {e['term'] if e['keep_english'] else e['translation']}" for e in entries[:120])


def translate_course(course_id: str, lang: str, job=None) -> dict:
    cur = db.get_doc(course_id, "curriculum")
    course = db.row(db.conn().execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone())
    audience = course["data"]["goal"].get("audience_description") or course["data"]["goal"].get("audience_level")
    name = LANG_NAMES.get(lang, lang)
    gl = glossary(course_id, lang)
    head = f"Target language: {name}\nAudience: {audience}\nGlossary:\n{_gloss_txt(gl)}\n\n"

    translate_curriculum(course_id, lang, head)

    acts = db.rows(db.conn().execute("SELECT * FROM activities WHERE course_id=? AND status='approved'", (course_id,)))
    done, kept = 0, 0

    def one(a):
        env = envelope(a["type"])
        canon = {k: a["data"][k] for k in env.model_fields}
        out = gateway.structured(env, SYSTEM, head + f"Translate this {a['type']} activity (JSON):\n"
                                 + db.dumps(canon), tier="fast", purpose=f"translate:{a['type']}", course_id=course_id)
        tr = out.model_dump()
        tr["evidence"] = canon["evidence"]
        if not same_shape(canon["payload"], tr["payload"]):
            out = gateway.structured(env, SYSTEM, head + "Your previous translation changed the structure, answers or "
                                     "fixed fields. Translate again, changing ONLY free text:\n" + db.dumps(canon),
                                     tier="fast", purpose=f"translate:{a['type']}", course_id=course_id)
            tr = out.model_dump()
            tr["evidence"] = canon["evidence"]
            if not same_shape(canon["payload"], tr["payload"]):
                return a["id"], None
        return a["id"], tr

    with ThreadPoolExecutor(settings.max_parallel) as ex:
        futs = [ex.submit(one, a) for a in acts]
        for i, f in enumerate(as_completed(futs), 1):
            try:
                aid, tr = f.result()
            except Exception:  # noqa: BLE001 - one failure must not stop the others
                kept += 1
                continue
            if tr is None:
                kept += 1
            else:
                with db.tx() as c:
                    c.execute("INSERT OR REPLACE INTO course_docs VALUES(?,?,?,?,?)",
                              (course_id, "activity_i18n", f"{aid}:{lang}", db.dumps(tr), time.time()))
                done += 1
            if job:
                job.update(progress=i / max(1, len(acts)), message=f"Translated {done}/{len(acts)} activities")
    langs = set(db.get_doc(course_id, "languages") or [])
    langs.add(lang)
    db.put_doc(course_id, "languages", sorted(langs))
    return {"lang": lang, "translated": done, "kept_canonical": kept, "total": len(acts)}


def translate_curriculum(course_id: str, lang: str, head: str | None = None) -> dict | None:
    cur = db.get_doc(course_id, "curriculum")
    if head is None:
        head = f"Target language: {LANG_NAMES.get(lang, lang)}\nGlossary:\n{_gloss_txt(glossary(course_id, lang))}\n\n"
    src = CurriculumText(course_title=cur["course_title"], learner_promise=cur["learner_promise"],
                         modules=[ModText(title=m["title"], why=m["why"]) for m in cur["modules"]],
                         objectives=[ObjText(statement=o["statement"], success_criteria=o["success_criteria"])
                                     for o in cur["objectives"]])
    ct = gateway.structured(CurriculumText, SYSTEM, head + "Translate EVERY field — including every objective statement and success "
                            "criterion (learners see them in their path):\n" + src.model_dump_json(), tier="fast",
                            purpose="translate:curriculum", course_id=course_id)
    if len(ct.modules) == len(cur["modules"]) and len(ct.objectives) == len(cur["objectives"]):
        db.put_doc(course_id, "curriculum_i18n", ct.model_dump(), lang)

    return db.get_doc(course_id, "curriculum_i18n", lang)


def localise_activity(a: dict, lang: str | None) -> dict:
    if not lang:
        return a
    tr = db.get_doc(a["course_id"], "activity_i18n", f"{a['id']}:{lang}")
    if tr:
        a = dict(a, data={**a["data"], **tr, "lang": lang})
    return a


def localise_curriculum(course_id: str, cur: dict, lang: str | None) -> dict:
    if not lang or not cur:
        return cur
    t = db.get_doc(course_id, "curriculum_i18n", lang)
    if not t:
        return cur
    cur = dict(cur, course_title=t["course_title"], learner_promise=t["learner_promise"])
    cur["modules"] = [dict(m, title=tm["title"], why=tm["why"]) for m, tm in zip(cur["modules"], t["modules"])]
    cur["objectives"] = [dict(o, statement=to["statement"], success_criteria=to["success_criteria"])
                         for o, to in zip(cur["objectives"], t["objectives"])]
    return cur
