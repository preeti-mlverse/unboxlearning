"""Content profiling: what kind of material is this, what kinds of knowledge does it hold, and what
goals can it genuinely support?  Deterministic signals + a model read of outline and samples."""
from . import db, index
from .llm import gateway
from .models import ContentProfile

SYSTEM = """You are an expert instructional designer and learning scientist. You analyse source material
before any teaching is designed. Be precise and evidence-based.

Knowledge types:
- fact: terms, names, definitions, values to remember
- concept: categories with defining features (what is / is not an X)
- principle: cause→effect relationships, rules, trade-offs
- process: how a system/phenomenon works over stages
- procedure: how to DO a task, step by step
- structure: parts and their arrangement/location
- chronology: events over time and their causes
- argument: cases, positions, judgement, evaluation
- quantitative: formulas and calculation
- code: programming APIs, snippets, configuration
- language: vocabulary, grammar, usage of a language
- data: reading tables, charts, statistics

Unit roles: core (what a learner should learn), supporting (examples, context), reference (API lists,
parameter tables, glossaries — look-up material), boilerplate (navigation, legal, changelogs, references,
link lists, contents pages). Suggest 3–6 goals the material genuinely supports, spanning different
purposes where sensible (understand, apply, exam_prep, certification, revision, onboarding, teach_others),
each phrased for a learner."""


def hint_types(sig: dict) -> list[str]:
    hints = []
    if sig["code_ratio"] > 0.15:
        hints.append("code")
    if sig["math_density"] > 0.04:
        hints.append("quantitative")
    if sig["dates_per_1k"] > 6:
        hints.append("chronology")
    if sig["numbered_steps"] >= 3 or sig["imperatives"] >= 4:
        hints.append("procedure")
    if sig["tables"] >= 2:
        hints.append("data/reference tables")
    if sig["figures"] >= 2:
        hints.append("visual")
    return hints


def outline(units: list[dict], sample_chars: int = 220) -> str:
    lines = []
    for u in units:
        els = db.conn().execute(
            f"SELECT text FROM elements WHERE id IN ({','.join('?' * min(len(u['element_ids']), 12))}) "
            f"AND kind NOT IN ('heading','figure')", u["element_ids"][:12]).fetchall()
        sample = " ".join(r["text"] for r in els)[:sample_chars]
        h = hint_types(u["signals"])
        lines.append(f"- {u['id']} | {' > '.join(u['path'])[:120] or u['title']} | ~{u['tokens']} tok"
                     f"{' | signals: ' + ', '.join(h) if h else ''}\n    {sample}")
    return "\n".join(lines)


def samples(units: list[dict], n: int = 4, chars: int = 1800) -> str:
    if not units:
        return ""
    picks = sorted(units, key=lambda u: -u["tokens"])[: n * 3]
    picks = [picks[i] for i in range(0, len(picks), max(1, len(picks) // n))][:n]
    out = []
    for u in picks:
        rs = db.conn().execute(f"SELECT * FROM elements WHERE id IN ({','.join('?' * len(u['element_ids']))}) "
                               f"ORDER BY ord", u["element_ids"]).fetchall()
        text = "\n".join(index.element_text(db.row(r)) for r in rs)[:chars]
        out.append(f"### Sample from {u['id']} ({' > '.join(u['path'])[:80]})\n{text}")
    return "\n\n".join(out)


def profile_sources(course_id: str, source_ids: list[str]) -> dict:
    all_units = []
    header = []
    for sid in source_ids:
        s = db.row(db.conn().execute("SELECT * FROM sources WHERE id=?", (sid,)).fetchone())
        us = index.units(sid)
        all_units.extend(us)
        st = s["meta"]["stats"]
        header.append(f"Source {sid}: '{s['title']}' ({s['kind']}, {st.get('pages') or '?'} pages, "
                      f"{st['chars']} chars, {st['code']} code blocks, {st['table']} tables, {st['figure']} figures, "
                      f"{st['equation']} equations). Parse notes: {'; '.join(s['meta']['parse_notes'][:3]) or 'none'}")
    user = ("\n".join(header) + f"\n\n## Units ({len(all_units)})\n" + outline(all_units) + "\n\n## Samples\n"
            + samples(all_units))
    prof = gateway.structured(ContentProfile, SYSTEM, user, tier="standard", purpose="profile", course_id=course_id)
    data = prof.model_dump()
    known = {u["id"]: u for u in all_units}
    roles = {a["unit_id"]: a for a in data["units"]}
    data["units"] = [{**{k: known[uid][k] for k in ("id", "source_id", "title", "path", "tokens", "pages", "signals",
                                                  "element_ids")},
                      "role": roles.get(uid, {}).get("role", "supporting"),
                      "knowledge_types": roles.get(uid, {}).get("knowledge_types", []),
                      "note": roles.get(uid, {}).get("note", ""),
                      "hints": hint_types(known[uid]["signals"])} for uid in known]
    tot = sum(w["weight"] for w in data["knowledge_mix"]) or 1
    for w in data["knowledge_mix"]:
        w["weight"] = round(w["weight"] / tot, 3)
    data["knowledge_mix"].sort(key=lambda w: -w["weight"])
    return data
