"""Course lifecycle and background jobs.

Phase 1 — analyse: profile the sources and suggest goals (cheap; lets the teacher choose a goal/scope).
Phase 2 — build: extract (cached per unit, goal-independent) → graph → curriculum → plan → generate → verify.
"""
import logging
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import db
from .config import settings
from .activities import structural_issues
from .generate import finalize_verdict, generate_activity, save_activity, verify_activity
from .index import ensure_embeddings
from .knowledge import consolidate, design_curriculum, elements_by_ids, extract_unit
from .llm import gateway
from .models import Goal
from .planner import assets_for, plan_objective
from .profile import profile_sources

log = logging.getLogger("engine.pipeline")

QUALITY = {  # model tier per stage
    "economy": {"profile": "fast", "extract": "fast", "graph": "fast", "curriculum": "standard", "plan": "fast",
                "generate": "fast", "verify": "fast"},
    "balanced": {"profile": "standard", "extract": "fast", "graph": "standard", "curriculum": "standard",
                 "plan": "fast", "generate": "standard", "verify": "fast"},
    "best": {"profile": "standard", "extract": "standard", "graph": "standard", "curriculum": "premium",
             "plan": "standard", "generate": "standard", "verify": "standard"},
}


# ----------------------------------------------------------------------------- courses

def create_course(title: str, source_ids: list[str], goal: dict | None = None, settings_: dict | None = None) -> dict:
    cid = db.new_id("crs")
    data = {"source_ids": source_ids, "goal": Goal(**(goal or {})).model_dump(),
            "settings": {"quality": "balanced", "auto_approve": False, "scope_unit_ids": None, **(settings_ or {})}}
    now = time.time()
    with db.tx() as c:
        c.execute("INSERT INTO courses VALUES(?,?,?,?,?,?)", (cid, title, db.dumps(data), "created", now, now))
    return get_course(cid)


def get_course(cid: str) -> dict | None:
    r = db.row(db.conn().execute("SELECT * FROM courses WHERE id=?", (cid,)).fetchone())
    if r:
        r["source_ids"] = r["data"]["source_ids"]
    return r


def update_course(cid: str, **fields) -> dict:
    c = get_course(cid)
    data = c["data"]
    for k in ("goal", "settings", "source_ids"):
        if k in fields and fields[k] is not None:
            data[k] = Goal(**fields[k]).model_dump() if k == "goal" else (
                {**data["settings"], **fields[k]} if k == "settings" else fields[k])
    with db.tx() as con:
        con.execute("UPDATE courses SET data=?, title=COALESCE(?, title), status=COALESCE(?, status), updated_at=? "
                    "WHERE id=?", (db.dumps(data), fields.get("title"), fields.get("status"), time.time(), cid))
    return get_course(cid)


# ----------------------------------------------------------------------------- jobs

class Job:
    def __init__(self, course_id: str, kind: str):
        self.id = db.new_id("job")
        self.course_id = course_id
        self.kind = kind
        self.log: list[str] = []
        now = time.time()
        with db.tx() as c:
            c.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?)",
                      (self.id, course_id, kind, "running", "", 0.0, "", "[]", now, now))

    def update(self, stage=None, progress=None, message=None, status=None):
        if message:
            self.log.append(f"{time.strftime('%H:%M:%S')} {message}")
            log.info("[%s] %s", self.course_id, message)
        with db.tx() as c:
            c.execute("UPDATE jobs SET stage=COALESCE(?,stage), progress=COALESCE(?,progress), "
                      "message=COALESCE(?,message), status=COALESCE(?,status), log=?, updated_at=? WHERE id=?",
                      (stage, progress, message, status, db.dumps(self.log[-200:]), time.time(), self.id))


def latest_job(course_id: str) -> dict | None:
    return db.row(db.conn().execute("SELECT * FROM jobs WHERE course_id=? ORDER BY created_at DESC LIMIT 1",
                                    (course_id,)).fetchone())


def run_async(fn, *args):
    t = threading.Thread(target=fn, args=args, daemon=True)
    t.start()
    return t


def _guard(job: Job, fn):
    try:
        fn()
    except Exception as e:  # noqa: BLE001 - surface every failure to the UI
        job.update(status="failed", message=f"failed: {e}")
        log.error(traceback.format_exc())
        update_course(job.course_id, status="failed")


# ----------------------------------------------------------------------------- phase 1

def analyse(course_id: str) -> str:
    job = Job(course_id, "analyse")

    def go():
        course = get_course(course_id)
        tiers = QUALITY[course["data"]["settings"]["quality"]]
        update_course(course_id, status="analysing")
        if n := ensure_embeddings(course["source_ids"]):
            job.update(message=f"Re-embedded {n} chunks with {gateway.embed_model}")
        job.update(stage="profile", progress=0.1, message="Reading the sources and profiling the content")
        prof = profile_sources(course_id, course["source_ids"]) if tiers else None
        db.put_doc(course_id, "profile", prof)
        if not course["title"] or course["title"].startswith("Untitled"):
            update_course(course_id, title=prof["title"])
        update_course(course_id, status="analysed")
        job.update(stage="done", progress=1.0, status="done",
                   message=f"Profiled: {prof['genre']} · {len(prof['units'])} units · "
                           f"{len(prof['suggested_goals'])} suggested goals")

    run_async(_guard, job, go)
    return job.id


# ----------------------------------------------------------------------------- phase 2

def scope_units(course: dict, profile: dict) -> list[dict]:
    chosen = course["data"]["settings"].get("scope_unit_ids")
    units = profile["units"]
    if chosen:
        sel = [u for u in units if u["id"] in set(chosen)]
    else:
        sel = [u for u in units if u["role"] in ("core", "supporting")] or units
    return sel[: settings.max_sections]


def build(course_id: str) -> str:
    job = Job(course_id, "build")

    def go():
        course = get_course(course_id)
        goal = Goal(**course["data"]["goal"])
        tiers = QUALITY[course["data"]["settings"]["quality"]]
        profile = db.get_doc(course_id, "profile")
        if not profile:
            job.update(stage="profile", progress=0.02, message="Profiling sources")
            profile = profile_sources(course_id, course["source_ids"])
            db.put_doc(course_id, "profile", profile)
        update_course(course_id, status="building")
        ensure_embeddings(course["source_ids"])
        units = scope_units(course, profile)

        # 1. extraction (cached per unit — goal independent)
        cached = db.list_docs(course_id, "unit_knowledge")
        todo = [u for u in units if u["id"] not in cached]
        job.update(stage="extract", progress=0.05,
                   message=f"Extracting knowledge from {len(units)} units ({len(units) - len(todo)} cached)")
        uk = {u["id"]: cached[u["id"]] for u in units if u["id"] in cached}
        with ThreadPoolExecutor(settings.max_parallel) as ex:
            futs = {ex.submit(extract_unit, course_id, u, profile, tiers["extract"]): u for u in todo}
            for i, f in enumerate(as_completed(futs), 1):
                u = futs[f]
                try:
                    data = f.result()
                    uk[u["id"]] = data
                    db.put_doc(course_id, "unit_knowledge", data, u["id"])
                except Exception as e:  # noqa: BLE001
                    job.update(message=f"extract failed for {u['title']}: {e}")
                job.update(progress=0.05 + 0.3 * i / max(1, len(todo)))
        uk = {k: v for k, v in uk.items() if k in {u["id"] for u in units}}

        # 2. concept graph
        job.update(stage="graph", progress=0.36, message="Consolidating concepts into a graph")
        graph = consolidate(course_id, uk, tiers["graph"])
        graph["course_id"] = course_id
        db.put_doc(course_id, "graph", graph)

        # 3. curriculum for this goal
        job.update(stage="curriculum", progress=0.42,
                   message=f"Designing the path: {len(graph['concepts'])} concepts → objectives for '{goal.purpose}'")
        cur = design_curriculum(course_id, goal, profile, graph, uk, tiers["curriculum"])
        db.put_doc(course_id, "curriculum", cur)
        update_course(course_id, title=cur["course_title"])

        # 4. lesson plans
        job.update(stage="plan", progress=0.48, message=f"Planning {len(cur['objectives'])} lessons")
        db.del_docs(course_id, "plan")
        concepts = {c["id"]: c for c in graph["concepts"]}
        plans, assets = {}, {}

        def plan_one(o):
            els = elements_by_ids(o["evidence"])
            a = assets_for(o, uk, els, graph)
            p = plan_objective(course_id, o, goal, a, [concepts[c] for c in o["concept_ids"] if c in concepts],
                               tiers["plan"])
            return o["id"], a, p

        reserve = course["data"]["settings"].get("remediation_variants", True)
        with ThreadPoolExecutor(settings.max_parallel) as ex:
            for oid, a, p in ex.map(plan_one, cur["objectives"]):
                if reserve:  # a different item held back for learners who need another try
                    used = {st["activity_type"] for st in p["steps"]}
                    pool = p["allowed"].get("check") or p["allowed"].get("practice") or ["mcq"]
                    alt = next((t for t in pool if t not in used), pool[0])
                    p["steps"].append({"stage": "check", "activity_type": alt, "reserve": True, "difficulty": 0.5,
                                       "intent": "A fresh check of the same objective for a learner who struggled "
                                                 "the first time: different context and wording, same success criteria.",
                                       "targets_misconception": ""})
                plans[oid], assets[oid] = p, a
                db.put_doc(course_id, "plan", p, oid)
                db.put_doc(course_id, "assets", {k: v for k, v in a.items()}, oid)

        # 5. generate + verify
        with db.tx() as c:
            c.execute("DELETE FROM activities WHERE course_id=?", (course_id,))
        work = [(o, i, s) for o in cur["objectives"] for i, s in enumerate(plans[o["id"]]["steps"])]
        job.update(stage="generate", progress=0.55, message=f"Generating {len(work)} activities")
        auto = course["data"]["settings"].get("auto_approve")
        course = get_course(course_id)

        def gen_one(item):
            o, i, s = item
            cs = [concepts[c] for c in o["concept_ids"] if c in concepts]
            data = generate_activity(course, goal, o, s, cs, assets[o["id"]], tier=tiers["generate"])
            issues = structural_issues(s["activity_type"], data["payload"])
            if issues:  # one automatic repair attempt, telling the model exactly what was wrong
                data = generate_activity(course, goal, o, s, cs, assets[o["id"]], tier=tiers["generate"],
                                         instruction="The previous attempt was malformed: " + "; ".join(issues)
                                         + ". Produce a correct, complete version.")
                issues = structural_issues(s["activity_type"], data["payload"])
            aid = save_activity(course_id, o["id"], s, i, data, None, "draft")
            act = {"id": aid, "type": s["activity_type"], "stage": s["stage"], "objective_id": o["id"], "data": data}
            v = verify_activity(course, act, tiers["verify"])
            if issues:
                v = finalize_verdict(v, issues)
            status = "flagged" if v["verdict"] == "flagged" else ("approved" if auto else "draft")
            save_activity(course_id, o["id"], s, i, data, v, status, aid)
            return v["verdict"]

        flagged = 0
        with ThreadPoolExecutor(settings.max_parallel) as ex:
            futs = [ex.submit(gen_one, w) for w in work]
            for i, f in enumerate(as_completed(futs), 1):
                try:
                    flagged += f.result() == "flagged"
                except Exception as e:  # noqa: BLE001
                    job.update(message=f"an activity failed to generate: {e}")
                job.update(progress=0.55 + 0.44 * i / max(1, len(work)))
        update_course(course_id, status="ready")
        job.update(stage="done", progress=1.0, status="done",
                   message=f"Ready: {len(cur['objectives'])} objectives, {len(work)} activities, {flagged} flagged "
                           f"for review")

    run_async(_guard, job, go)
    return job.id


def regenerate_activity(course_id: str, activity_id: str, instruction: str = "", new_type: str | None = None) -> dict:
    course = get_course(course_id)
    act = db.row(db.conn().execute("SELECT * FROM activities WHERE id=?", (activity_id,)).fetchone())
    goal = Goal(**course["data"]["goal"])
    cur = db.get_doc(course_id, "curriculum")
    graph = db.get_doc(course_id, "graph")
    o = next(x for x in cur["objectives"] if x["id"] == act["objective_id"])
    concepts = {c["id"]: c for c in graph["concepts"]}
    assets = dict(db.get_doc(course_id, "assets", o["id"]) or {})
    from .planner import match_3d  # 3D models may have been attached after the build
    models = match_3d(o, {**graph, "course_id": course_id})
    if not models and (new_type or act["type"]) == "model_3d":
        models = [{"id": a["id"], "name": a["name"], "hotspots": [h["label"] for h in a["hotspots"]]}
                  for a in db.list_docs(course_id, "asset").values() if a.get("kind") == "3d" and a.get("hotspots")][:1]
    assets.update(asset_3d=bool(models), assets_3d=models)
    step = {"stage": act["stage"], "activity_type": new_type or act["type"], "intent": act["data"].get("intent", ""),
            "targets_misconception": act["data"].get("targets_misconception", ""),
            "difficulty": act["data"].get("difficulty", 0.5), "reserve": act["data"].get("reserve", False)}
    tiers = QUALITY[course["data"]["settings"]["quality"]]
    data = generate_activity(course, goal, o, step, [concepts[c] for c in o["concept_ids"] if c in concepts], assets,
                             instruction=instruction, tier=tiers["generate"])
    v = verify_activity(course, {"type": step["activity_type"], "stage": step["stage"], "objective_id": o["id"],
                                 "data": data}, tiers["verify"])
    if issues := structural_issues(step["activity_type"], data["payload"]):
        v = finalize_verdict(v, issues)
    save_activity(course_id, o["id"], step, act["ord"], data, v, "flagged" if v["verdict"] == "flagged" else "draft",
                  activity_id)
    return db.row(db.conn().execute("SELECT * FROM activities WHERE id=?", (activity_id,)).fetchone())
