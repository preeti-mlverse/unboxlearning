"""HTTP API for micro-learning courses: build, preview/edit, learner journey, progress, memory deck."""
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import db, learner as L, micro, pipeline as P
from .llm import LLMError

router = APIRouter(prefix="/api/micro")
DAY = 86400.0


def _course(cid: str) -> dict:
    c = P.get_course(cid)
    if not c:
        raise HTTPException(404, "course not found")
    return c


def _modules(cid: str) -> list[dict]:
    bp = db.get_doc(cid, "micro") or {"modules": []}
    ms = db.list_docs(cid, "module")
    return [ms[m["id"]] for m in bp["modules"] if m["id"] in ms]


@router.post("/{cid}/build")
def build(cid: str):
    _course(cid)
    return {"job_id": micro.build_micro(cid)}


@router.post("/{cid}/plan")
def plan(cid: str):
    _course(cid)
    return {"job_id": micro.plan_micro(cid)}


@router.post("/{cid}/generate")
def generate(cid: str):
    _course(cid)
    try:
        return {"job_id": micro.generate_micro(cid)}
    except ValueError as e:
        raise HTTPException(409, str(e))


class OutlineModule(BaseModel):
    title: str
    goal: str = ""
    big_idea: str = ""
    minutes: int = 6
    concept_ids: list[str] = []


class OutlineIn(BaseModel):
    course_title: str
    tagline: str = ""
    learner_promise: str = ""
    modules: list[OutlineModule]


@router.put("/{cid}/outline")
def put_outline(cid: str, body: OutlineIn):
    """Save the creator's edits to the outline (rename, reorder, remove, add) before generation."""
    bp = db.get_doc(cid, "micro")
    if not bp or bp.get("status") != "outline":
        raise HTTPException(409, "The outline can only be edited before the course is generated")
    mods = [m for m in body.modules if m.title.strip()]
    if not mods:
        raise HTTPException(400, "Keep at least one module")
    bp.update(course_title=body.course_title.strip() or bp["course_title"], tagline=body.tagline,
              learner_promise=body.learner_promise,
              modules=[{**m.model_dump(), "id": f"m{i}", "big_idea": m.big_idea or m.goal or m.title}
                       for i, m in enumerate(mods, 1)])
    db.put_doc(cid, "micro", bp)
    return bp


@router.get("/{cid}")
def get_micro(cid: str):
    c = _course(cid)
    bp = db.get_doc(cid, "micro")
    graph = db.get_doc(cid, "graph") or {"concepts": []}
    srcs = db.rows(db.conn().execute(
        f"SELECT id, title, kind FROM sources WHERE id IN ({','.join('?' * len(c['source_ids']))})", c["source_ids"]))
    return {"course": {"id": c["id"], "title": c["title"], "status": c["status"], "goal": c["data"]["goal"],
                       "settings": c["data"]["settings"],
                       "published": c["data"]["settings"].get("published", False), "source_ids": c["source_ids"]},
            "sources": srcs, "concepts": {k["id"]: k["name"] for k in graph["concepts"]},
            "profile": db.get_doc(cid, "profile"), "blueprint": bp, "modules": _modules(cid), "job": P.latest_job(cid)}


class CardIn(BaseModel):
    card: dict


@router.put("/{cid}/modules/{mid}/cards/{i}")
def put_card(cid: str, mid: str, i: int, body: CardIn):
    m = db.get_doc(cid, "module", mid)
    if not m or not 0 <= i < len(m["cards"]):
        raise HTTPException(404, "card not found")
    try:
        card = micro.Card.model_validate(body.card).model_dump()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"invalid card: {e}")
    card["visual"]["media"] = body.card.get("visual", {}).get("media")
    m["cards"][i] = card
    m["flags"].pop(str(i), None)
    db.put_doc(cid, "module", m, mid)
    return card


class RegenIn(BaseModel):
    instruction: str = ""


@router.post("/{cid}/modules/{mid}/cards/{i}/regenerate")
def regen_card(cid: str, mid: str, i: int, body: RegenIn):
    try:
        return micro.regenerate_card(cid, mid, i, body.instruction)
    except LLMError as e:
        raise HTTPException(400, str(e))


@router.post("/{cid}/modules/{mid}/cards/{i}/redraw")
def redraw(cid: str, mid: str, i: int):
    m = db.get_doc(cid, "module", mid)
    v = m["cards"][i]["visual"]
    if not v.get("prompt"):
        raise HTTPException(400, "this card has no illustration prompt")
    media = micro.make_image(v["prompt"], cid)
    if not media:
        raise HTTPException(400, "image generation failed")
    v["kind"], v["media"] = "illustration", media
    db.put_doc(cid, "module", m, mid)
    return m["cards"][i]


class PublishIn(BaseModel):
    published: bool


@router.post("/{cid}/publish")
def publish(cid: str, body: PublishIn):
    return P.update_course(cid, settings={"published": body.published})["data"]["settings"]


# ----------------------------------------------------------------------------- learner

def _state(cid: str, lid: str) -> dict:
    return db.get_doc(cid, "micro_state", lid) or {"cards": {}, "modules": {}, "xp": 0, "days": []}


def _save_state(cid: str, lid: str, st: dict):
    today = time.strftime("%Y-%m-%d")
    if today not in st["days"]:
        st["days"] = (st["days"] + [today])[-400:]
    db.put_doc(cid, "micro_state", st, lid)


def _streak(days: list[str]) -> int:
    import datetime as dt
    s, d = 0, dt.date.today()
    have = set(days)
    while d.isoformat() in have:
        s += 1
        d -= dt.timedelta(days=1)
    return s


@router.get("/{cid}/journey/{lid}")
def journey(cid: str, lid: str):
    c = _course(cid)
    bp = db.get_doc(cid, "micro")
    if not bp:
        raise HTTPException(404, "course not built yet")
    st = _state(cid, lid)
    th = L.threshold(c)
    ms = []
    prev_done = True
    for m in _modules(cid):
        mst = st["modules"].get(m["id"], {})
        mastery = L.mastery_row(lid, c, m["id"])
        done = bool(mst.get("completed"))
        due = done and mastery.get("next_review") and mastery["next_review"] <= time.time()
        ms.append({"id": m["id"], "title": m["title"], "goal": m["goal"], "minutes": m["minutes"],
                   "cards": len(m["cards"]), "cover": next((x["visual"].get("media") for x in m["cards"]
                                                            if x["visual"].get("media")), None),
                   "state": "review" if due else "done" if done else "current" if prev_done else "locked",
                   "score": mst.get("score"), "mastery": round(mastery["p"], 2), "mastered": mastery["p"] >= th})
        prev_done = done
    deck_due = len(_deck(cid, lid, due_only=True))
    return {"title": bp["course_title"], "tagline": bp["tagline"], "promise": bp["learner_promise"],
            "cover": bp.get("cover_media"), "modules": ms, "xp": st["xp"], "streak": _streak(st["days"]),
            "deck_due": deck_due}


@router.get("/{cid}/modules/{mid}")
def module(cid: str, mid: str):
    m = db.get_doc(cid, "module", mid)
    if not m:
        raise HTTPException(404, "module not found")
    return {k: m[k] for k in ("id", "title", "goal", "minutes", "cards", "flashcards")}


class ProgressIn(BaseModel):
    learner_id: str
    module_id: str
    card_index: int
    correct: bool | None = None
    score: float | None = None
    response: dict = {}


@router.post("/{cid}/progress")
def progress(cid: str, body: ProgressIn):
    c = _course(cid)
    m = db.get_doc(cid, "module", body.module_id)
    card = m["cards"][body.card_index]
    st = _state(cid, body.learner_id)
    key = f"{body.module_id}#{body.card_index}"
    first = key not in st["cards"]
    gained = 0
    if body.score is not None:
        st["cards"][key] = {"score": body.score, "at": time.time()}
        if first:
            gained = 10 if body.score >= 0.99 else 5 if body.score >= 0.5 else 2
            L.update_mastery(body.learner_id, c, body.module_id, body.score, 0.4, 0,
                             len(card.get("options") or []) or None)
            with db.tx() as con:
                con.execute("INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                            (db.new_id("att"), body.learner_id, cid, key, body.module_id, db.dumps(body.response),
                             body.score, int(body.score >= 0.8), 0, None, time.time()))
    st["xp"] += gained
    _save_state(cid, body.learner_id, st)
    return {"xp": st["xp"], "gained": gained}


class CompleteIn(BaseModel):
    learner_id: str


@router.post("/{cid}/modules/{mid}/complete")
def complete(cid: str, mid: str, body: CompleteIn):
    c = _course(cid)
    m = db.get_doc(cid, "module", mid)
    st = _state(cid, body.learner_id)
    scores = [v["score"] for k, v in st["cards"].items() if k.startswith(mid + "#")]
    score = round(sum(scores) / len(scores), 2) if scores else None
    first = not st["modules"].get(mid, {}).get("completed")
    st["modules"][mid] = {"completed": True, "score": score, "at": time.time()}
    if first:
        st["xp"] += 50
        for n, _f in enumerate(m["flashcards"]):  # new cards enter the memory deck, due tomorrow
            st.setdefault("deck", {})[f"{mid}~{n}"] = {"due": time.time() + DAY * 0.5, "interval": 1.0}
    _save_state(cid, body.learner_id, st)
    mastery = L.mastery_row(body.learner_id, c, mid)
    return {"score": score, "xp": st["xp"], "mastery": mastery["p"], "streak": _streak(st["days"])}


class ApplyIn(BaseModel):
    learner_id: str
    answer: str


@router.post("/{cid}/modules/{mid}/cards/{i}/feedback")
def feedback(cid: str, mid: str, i: int, body: ApplyIn):
    try:
        fb = micro.apply_feedback(cid, mid, i, body.answer)
    except LLMError as e:
        raise HTTPException(400, str(e))
    progress(cid, ProgressIn(learner_id=body.learner_id, module_id=mid, card_index=i, score=fb["score"],
                             response={"text": body.answer}))
    return fb


# ----------------------------------------------------------------------------- memory deck

def _deck(cid: str, lid: str, due_only: bool = False) -> list[dict]:
    st = _state(cid, lid)
    out = []
    mods = {m["id"]: m for m in _modules(cid)}
    for key, s in (st.get("deck") or {}).items():
        mid, n = key.split("~")
        if mid in mods and int(n) < len(mods[mid]["flashcards"]) and (not due_only or s["due"] <= time.time()):
            out.append({"key": key, "module": mods[mid]["title"], **mods[mid]["flashcards"][int(n)], "due": s["due"]})
    return sorted(out, key=lambda x: x["due"])


@router.get("/{cid}/deck/{lid}")
def deck(cid: str, lid: str, all: bool = False):
    return _deck(cid, lid, due_only=not all)


class RateIn(BaseModel):
    learner_id: str
    key: str
    rating: str  # again | hard | good | easy


@router.post("/{cid}/deck/rate")
def rate(cid: str, body: RateIn):
    st = _state(cid, body.learner_id)
    s = st.setdefault("deck", {}).get(body.key)
    if not s:
        raise HTTPException(404, "card not in deck")
    mult = {"again": 0, "hard": 1.2, "good": 2.5, "easy": 3.5}[body.rating]
    s["interval"] = 0.2 if mult == 0 else max(1.0, s["interval"] * mult)
    s["due"] = time.time() + s["interval"] * DAY
    st["xp"] += 2
    _save_state(cid, body.learner_id, st)
    return s
