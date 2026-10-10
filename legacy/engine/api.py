"""HTTP API (FastAPI). Run: python -m uvicorn engine.api:app --port 8030"""
import copy
import random
import re
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import db, learner as L, pipeline as P
from .activities import REGISTRY, catalog
from .config import ROOT, settings
from .ingest import SUPPORTED, ingest_file, ingest_text, ingest_url
from .llm import LLMError, gateway
from .tutor import roleplay_turn, tutor_reply

app = FastAPI(title="UnboxEd engine", version="0.2")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")

from .api_micro import router as micro_router  # noqa: E402
from . import auth  # noqa: E402

auth.ensure_schema()
app.include_router(micro_router)
app.include_router(auth.router)


def _404(x, what="not found"):
    if not x:
        raise HTTPException(404, what)
    return x


# ----------------------------------------------------------------------------- meta

@app.on_event("startup")
def _probe_provider():
    import threading
    threading.Thread(target=gateway.check, daemon=True).start()


@app.post("/api/health/check")
def health_check():
    return gateway.check()


@app.get("/api/health")
def health():
    return {"ok": True, "provider": gateway.provider, "ai_status": gateway.status,
            "models": {t: gateway.model_for(t) for t in ("fast", "standard", "premium")},
            "embeddings": gateway.embed_model, "inputs": SUPPORTED, "quality_modes": list(P.QUALITY)}


@app.get("/api/catalog")
def get_catalog():
    return catalog()


@app.get("/api/usage")
def usage(course_id: str | None = None):
    q = "SELECT purpose, model, count(*) n, sum(input_tokens) tin, sum(output_tokens) tout, avg(ms) ms, " \
        "sum(1-ok) failed FROM llm_calls"
    args = ()
    if course_id:
        q += " WHERE course_id=?"
        args = (course_id,)
    return db.rows(db.conn().execute(q + " GROUP BY purpose, model ORDER BY n DESC", args))


# ----------------------------------------------------------------------------- sources

class UrlIn(BaseModel):
    url: str
    title: str | None = None
    crawl: bool = False
    max_pages: int = 30


class TextIn(BaseModel):
    text: str
    title: str = "Pasted text"


def _src_summary(s):
    return {k: s[k] for k in ("id", "title", "kind", "origin", "status", "created_at")} | {
        "stats": s["meta"]["stats"], "parse_notes": s["meta"]["parse_notes"],
        "low_confidence_pages": s["meta"].get("low_confidence_pages", [])}


@app.post("/api/sources/upload")
async def upload(files: list[UploadFile] = File(...), title: str | None = Form(None)):
    out = []
    for f in files:
        tmp = settings.upload_dir / f"incoming_{int(time.time() * 1000)}_{Path(f.filename).name}"
        tmp.write_bytes(await f.read())
        try:
            out.append(_src_summary(ingest_file(tmp, title if len(files) == 1 else None)))
        except (ValueError, LLMError) as e:
            raise HTTPException(400, str(e))
        finally:
            tmp.unlink(missing_ok=True)
    return out


@app.post("/api/sources/url")
def add_url(body: UrlIn):
    try:
        return _src_summary(ingest_url(body.url, body.title, body.crawl, body.max_pages))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"Could not ingest {body.url}: {e}")


@app.post("/api/sources/text")
def add_text(body: TextIn):
    return _src_summary(ingest_text(body.text, body.title))


@app.get("/api/sources")
def list_sources():
    return [_src_summary(s) for s in db.rows(db.conn().execute("SELECT * FROM sources ORDER BY created_at DESC"))]


@app.get("/api/sources/{sid}")
def get_source(sid: str, offset: int = 0, limit: int = 400):
    s = _404(db.row(db.conn().execute("SELECT * FROM sources WHERE id=?", (sid,)).fetchone()))
    els = db.rows(db.conn().execute("SELECT * FROM elements WHERE source_id=? ORDER BY ord LIMIT ? OFFSET ?",
                                    (sid, limit, offset)))
    total = db.conn().execute("SELECT count(*) FROM elements WHERE source_id=?", (sid,)).fetchone()[0]
    return {**_src_summary(s), "elements": els, "total": total, "offset": offset}


@app.get("/api/elements/{eid}")
def get_element(eid: str, context: int = 3):
    e = _404(db.row(db.conn().execute("SELECT * FROM elements WHERE id=?", (eid,)).fetchone()))
    near = db.rows(db.conn().execute("SELECT * FROM elements WHERE source_id=? AND ord BETWEEN ? AND ? ORDER BY ord",
                                     (e["source_id"], e["ord"] - context, e["ord"] + context)))
    s = db.row(db.conn().execute("SELECT id, title, kind, origin FROM sources WHERE id=?", (e["source_id"],)).fetchone())
    return {"element": e, "context": near, "source": s}


# ----------------------------------------------------------------------------- courses

class CourseIn(BaseModel):
    title: str = "Untitled course"
    source_ids: list[str]
    goal: dict | None = None
    settings: dict | None = None


class CoursePatch(BaseModel):
    title: str | None = None
    goal: dict | None = None
    settings: dict | None = None
    source_ids: list[str] | None = None


@app.post("/api/courses")
def create_course(body: CourseIn, request: Request):
    u = auth.current_user(request)
    if u and not auth.is_educator(u):
        raise HTTPException(403, "Creating courses needs an educator account")
    c = P.create_course(body.title, body.source_ids, body.goal, body.settings)
    if u:
        auth.set_owner(c["id"], u["id"])   # the course belongs to the educator who started it
    return c


@app.get("/api/courses")
def list_courses():
    out = []
    for c in db.rows(db.conn().execute("SELECT * FROM courses ORDER BY updated_at DESC")):
        n = db.conn().execute("SELECT status, count(*) n FROM activities WHERE course_id=? GROUP BY status",
                              (c["id"],)).fetchall()
        out.append({"id": c["id"], "title": c["title"], "status": c["status"], "updated_at": c["updated_at"],
                    "goal": c["data"]["goal"], "activities": {r["status"]: r["n"] for r in n}})
    return out


@app.get("/api/courses/{cid}")
def course_detail(cid: str):
    c = _404(P.get_course(cid))
    counts = db.conn().execute("SELECT status, count(*) n FROM activities WHERE course_id=? GROUP BY status",
                               (cid,)).fetchall()
    return {**c, "profile": db.get_doc(cid, "profile"), "graph": db.get_doc(cid, "graph"),
            "curriculum": db.get_doc(cid, "curriculum"), "plans": db.list_docs(cid, "plan"),
            "job": P.latest_job(cid), "activity_counts": {r["status"]: r["n"] for r in counts},
            "unit_knowledge_count": len(db.list_docs(cid, "unit_knowledge")),
            "sources": [_src_summary(s) for s in db.rows(db.conn().execute(
                f"SELECT * FROM sources WHERE id IN ({','.join('?' * len(c['source_ids']))})", c["source_ids"]))]}


@app.patch("/api/courses/{cid}")
def patch_course(cid: str, body: CoursePatch):
    _404(P.get_course(cid))
    return P.update_course(cid, **body.model_dump())


@app.post("/api/courses/{cid}/analyse")
def analyse(cid: str):
    _404(P.get_course(cid))
    return {"job_id": P.analyse(cid)}


@app.post("/api/courses/{cid}/build")
def build(cid: str):
    _404(P.get_course(cid))
    return {"job_id": P.build(cid)}


@app.get("/api/courses/{cid}/estimate")
def course_estimate(cid: str):
    from .estimate import estimate
    return estimate(_404(P.get_course(cid)))


@app.get("/api/courses/{cid}/job")
def job(cid: str):
    return P.latest_job(cid)


@app.get("/api/courses/{cid}/unit_knowledge/{uid}")
def unit_knowledge(cid: str, uid: str):
    return _404(db.get_doc(cid, "unit_knowledge", uid))


@app.get("/api/courses/{cid}/activities")
def activities(cid: str, objective_id: str | None = None):
    q, args = "SELECT * FROM activities WHERE course_id=?", [cid]
    if objective_id:
        q += " AND objective_id=?"
        args.append(objective_id)
    return db.rows(db.conn().execute(q + " ORDER BY objective_id, ord", args))


class ActivityPatch(BaseModel):
    status: str | None = None
    data: dict | None = None


@app.patch("/api/activities/{aid}")
def patch_activity(aid: str, body: ActivityPatch):
    a = _404(db.row(db.conn().execute("SELECT * FROM activities WHERE id=?", (aid,)).fetchone()))
    if body.data is not None:
        env = REGISTRY[a["type"]]
        from .activities import envelope
        envelope(env.key).model_validate({k: v for k, v in body.data.items()
                                          if k not in ("intent", "targets_misconception")})
    with db.tx() as c:
        c.execute("UPDATE activities SET status=COALESCE(?,status), data=COALESCE(?,data), updated_at=? WHERE id=?",
                  (body.status, db.dumps(body.data) if body.data is not None else None, time.time(), aid))
    return db.row(db.conn().execute("SELECT * FROM activities WHERE id=?", (aid,)).fetchone())


class RegenIn(BaseModel):
    instruction: str = ""
    type: str | None = None


@app.post("/api/courses/{cid}/activities/{aid}/regenerate")
def regenerate(cid: str, aid: str, body: RegenIn):
    if body.type and body.type not in REGISTRY:
        raise HTTPException(400, "unknown activity type")
    return P.regenerate_activity(cid, aid, body.instruction, body.type)


@app.post("/api/courses/{cid}/approve_all")
def approve_all(cid: str, include_flagged: bool = False):
    statuses = ("draft", "flagged") if include_flagged else ("draft",)
    with db.tx() as c:
        n = c.execute(f"UPDATE activities SET status='approved' WHERE course_id=? AND status IN "
                      f"({','.join('?' * len(statuses))})", (cid, *statuses)).rowcount
    return {"approved": n}


# ----------------------------------------------------------------------------- learning

HIDE = {"correct", "rationale", "model_answer", "answers", "bug_lines", "bug_explanation", "fixed_code", "reveal",
        "solution", "explanation", "category", "why", "x", "y", "sort_key"}


def learner_view(a: dict) -> dict:
    """Strip answer keys and shuffle what must be shuffled; the full payload is returned after an attempt."""
    a = copy.deepcopy(a)
    t = a["type"]
    p = a["data"]["payload"]
    rnd = random.Random(a["id"])
    graded = REGISTRY[t].grading in ("auto", "rubric") and t not in ("scenario",)
    if t == "ordering":
        p["items"] = rnd.sample(p["items"], len(p["items"]))
    if t == "timeline" and p.get("task") == "order":
        p["events"] = rnd.sample(p["events"], len(p["events"]))
    if t == "matching":
        p["rights"] = rnd.sample([x["right"] for x in p["pairs"]], len(p["pairs"]))
        p["pairs"] = [{"left": x["left"]} for x in p["pairs"]]

    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if k not in HIDE}
        if isinstance(o, list):
            return [strip(v) for v in o]
        return o

    if graded or t in ("predict", "process_stepper", "parameter_explorer", "concept_map", "compare_table"):
        keep = {k: p[k] for k in ("x_variable", "variables", "outputs") if k in p}
        p = strip(p)
        p.update(keep)
        if t == "numeric_problem":
            p.pop("answer", None)
            p.pop("tolerance", None)
    a["data"]["payload"] = p
    for k in ("key_claims", "context_ids", "intent", "targets_misconception"):
        a["data"].pop(k, None)
    return a


class LearnerIn(BaseModel):
    name: str


@app.post("/api/learners")
def make_learner(body: LearnerIn):
    return L.learner(body.name.strip() or "Learner")


@app.get("/api/courses/{cid}/learn/{lid}/next")
def learn_next(cid: str, lid: str, lang: str | None = None):
    from .translate import localise_activity
    c = _404(P.get_course(cid))
    n = L.next_step(c, lid)
    if n["activity"]:
        n["activity"] = learner_view(localise_activity(n["activity"], lang))
    if n.get("assessment"):
        from .evidence import public_view
        n["assessment"] = public_view(n["assessment"])
    return n


@app.get("/api/courses/{cid}/learn/curriculum")
def learn_curriculum(cid: str, lang: str | None = None):
    from .translate import localise_curriculum
    _404(P.get_course(cid))
    return {"curriculum": localise_curriculum(cid, db.get_doc(cid, "curriculum"), lang),
            "languages": db.get_doc(cid, "languages") or []}


class TranslateIn(BaseModel):
    lang: str


@app.post("/api/courses/{cid}/translate")
def translate(cid: str, body: TranslateIn):
    from .translate import translate_course
    _404(P.get_course(cid))
    job = P.Job(cid, "translate")

    def go():
        job.update(stage="translate", progress=0.02, message=f"Translating into {body.lang}")
        r = translate_course(cid, body.lang, job)
        job.update(stage="done", progress=1.0, status="done",
                   message=f"{body.lang}: {r['translated']}/{r['total']} activities translated"
                           + (f", {r['kept_canonical']} kept in the original language" if r["kept_canonical"] else ""))

    P.run_async(P._guard, job, go)
    return {"job_id": job.id}


@app.get("/api/courses/{cid}/glossary/{lang}")
def get_glossary(cid: str, lang: str):
    return db.get_doc(cid, "glossary", lang) or []


@app.put("/api/courses/{cid}/glossary/{lang}")
def put_glossary(cid: str, lang: str, entries: list[dict]):
    db.put_doc(cid, "glossary", entries, lang)
    return entries


@app.get("/api/courses/{cid}/learn/{lid}/progress")
def learn_progress(cid: str, lid: str):
    return L.progress(_404(P.get_course(cid)), lid)


@app.get("/api/courses/{cid}/learn/activity/{aid}")
def learn_activity(cid: str, aid: str, lang: str | None = None):
    from .translate import localise_activity
    a = _404(db.row(db.conn().execute("SELECT * FROM activities WHERE id=? AND course_id=?", (aid, cid)).fetchone()))
    return learner_view(localise_activity(a, lang))


class AttemptIn(BaseModel):
    learner_id: str
    response: dict
    hints: int = 0
    lang: str | None = None


@app.post("/api/activities/{aid}/attempt")
def attempt(aid: str, body: AttemptIn):
    from .translate import localise_activity
    a = _404(db.row(db.conn().execute("SELECT * FROM activities WHERE id=?", (aid,)).fetchone()))
    a = localise_activity(a, body.lang)  # text answers are graded in the language the learner saw
    c = P.get_course(a["course_id"])
    out = L.record_attempt(c, body.learner_id, a, body.response, body.hints)
    out["solution"] = a["data"]["payload"]
    return out


class TutorIn(BaseModel):
    learner_id: str
    message: str
    history: list[dict] = []
    activity_id: str | None = None
    answered: bool = False
    lang: str | None = None


@app.post("/api/courses/{cid}/tutor")
def tutor(cid: str, body: TutorIn):
    c = _404(P.get_course(cid))
    from .evidence import arm_for
    if arm_for(c, body.learner_id) == "static":
        raise HTTPException(403, "The tutor is not part of this study condition.")
    act = db.row(db.conn().execute("SELECT * FROM activities WHERE id=?", (body.activity_id,)).fetchone()) \
        if body.activity_id else None
    prog = L.progress(c, body.learner_id)["objectives"]
    if body.lang:
        from .translate import localise_activity
        c = dict(c, data={**c["data"], "goal": {**c["data"]["goal"], "language": body.lang}})
        act = localise_activity(act, body.lang) if act else act
    return tutor_reply(c, body.message, body.history, act, prog, body.answered)


class RoleplayIn(BaseModel):
    history: list[dict] = []
    message: str


@app.post("/api/activities/{aid}/roleplay")
def roleplay(aid: str, body: RoleplayIn):
    a = _404(db.row(db.conn().execute("SELECT * FROM activities WHERE id=?", (aid,)).fetchone()))
    return roleplay_turn(P.get_course(a["course_id"]), a, body.history, body.message)


class TtsIn(BaseModel):
    text: str
    voice: str = "alloy"


@app.post("/api/tts")
def tts(body: TtsIn):
    from .ingest.base import save_media, sha256_bytes
    key = sha256_bytes(f"{body.voice}:{body.text}".encode())[:20] + ".mp3"
    p = settings.media_dir / key
    if not p.exists():
        try:
            p.write_bytes(gateway.tts(body.text, body.voice))
        except LLMError as e:
            raise HTTPException(400, str(e))
    return {"url": f"/media/{key}"}


@app.get("/api/courses/{cid}/export/qti")
def export_qti(cid: str, include_unapproved: bool = False):
    from .export import qti_zip
    c = _404(P.get_course(cid))
    data, n = qti_zip(cid, include_unapproved)
    name = re.sub(r"[^\w-]+", "_", c["title"])[:60] or cid
    return Response(data, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{name}_qti21.zip"', "X-Item-Count": str(n)})


@app.get("/api/courses/{cid}/export/bundle")
def export_course(cid: str):
    from .export import export_bundle
    c = _404(P.get_course(cid))
    name = re.sub(r"[^\w-]+", "_", c["title"])[:60] or cid
    return Response(db.dumps(export_bundle(cid)), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{name}.course.json"'})


@app.post("/api/courses/import")
async def import_course(file: UploadFile = File(...)):
    import json as _json
    from .export import import_bundle
    try:
        return {"course_id": import_bundle(_json.loads(await file.read()))}
    except (ValueError, KeyError) as e:
        raise HTTPException(400, f"Not a valid course bundle: {e}")


@app.post("/api/courses/{cid}/assets")
async def add_asset(cid: str, file: UploadFile = File(...), name: str = Form(...), description: str = Form(""),
                    tags: str = Form("")):
    from .ingest.base import save_media
    _404(P.get_course(cid))
    ext = Path(file.filename).suffix.lower()
    if ext not in (".glb", ".gltf"):
        raise HTTPException(400, "3D models must be .glb (preferred) or self-contained .gltf")
    media = save_media(await file.read(), ext)
    aid = db.new_id("ast")
    asset = {"id": aid, "kind": "3d", "name": name, "description": description,
             "tags": [t.strip() for t in tags.split(",") if t.strip()], "media_path": media, "hotspots": []}
    db.put_doc(cid, "asset", asset, aid)
    return asset


@app.get("/api/courses/{cid}/assets")
def list_assets(cid: str):
    return list(db.list_docs(cid, "asset").values())


class AssetPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    hotspots: list[dict] | None = None


@app.put("/api/courses/{cid}/assets/{aid}")
def update_asset(cid: str, aid: str, body: AssetPatch):
    a = _404(db.get_doc(cid, "asset", aid))
    a.update({k: v for k, v in body.model_dump().items() if v is not None})
    db.put_doc(cid, "asset", a, aid)
    return a


@app.delete("/api/courses/{cid}/assets/{aid}")
def delete_asset(cid: str, aid: str):
    with db.tx() as c:
        c.execute("DELETE FROM course_docs WHERE course_id=? AND kind='asset' AND key=?", (cid, aid))
    return {"deleted": aid}


# ----------------------------------------------------------------------------- evidence

@app.get("/api/courses/{cid}/assessments")
def get_assessments(cid: str):
    from .evidence import list_assessments
    return list_assessments(cid)


@app.post("/api/courses/{cid}/assessments")
def put_assessment(cid: str, body: dict):
    from .evidence import save_assessment
    _404(P.get_course(cid))
    try:
        return save_assessment(cid, body)
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e))


@app.post("/api/courses/{cid}/assessments/import")
async def import_assessment(cid: str, file: UploadFile = File(...), kind: str = Form("pre"), name: str = Form("")):
    import json as _json
    from .evidence import parse_qti_zip, save_assessment
    raw = await file.read()
    try:
        if file.filename.lower().endswith(".zip"):
            items = parse_qti_zip(raw)
        else:
            data = _json.loads(raw)
            items = data["items"] if isinstance(data, dict) else data
        if not items:
            raise ValueError("no choice items found")
        return save_assessment(cid, {"kind": kind, "name": name or file.filename, "items": items, "source": "imported"})
    except (ValueError, KeyError) as e:
        raise HTTPException(400, f"Could not import: {e}")


@app.delete("/api/courses/{cid}/assessments/{aid}")
def delete_assessment(cid: str, aid: str):
    with db.tx() as c:
        c.execute("DELETE FROM course_docs WHERE course_id=? AND kind='assessment' AND key=?", (cid, aid))
    return {"deleted": aid}


class AssessmentAnswers(BaseModel):
    learner_id: str
    answers: dict[str, list[int]]


@app.post("/api/courses/{cid}/assessments/{aid}/submit")
def submit_assessment(cid: str, aid: str, body: AssessmentAnswers):
    from .evidence import submit
    try:
        return submit(_404(P.get_course(cid)), body.learner_id, aid, body.answers)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/courses/{cid}/evidence")
def evidence_report(cid: str):
    from .evidence import report
    _404(P.get_course(cid))
    return report(cid)


@app.get("/api/courses/{cid}/evidence.csv")
def evidence_csv(cid: str):
    from .evidence import results_csv
    return Response(results_csv(cid), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{cid}_assessment_results.csv"'})


@app.get("/api/courses/{cid}/items")
def items(cid: str):
    from .analytics import item_analysis
    _404(P.get_course(cid))
    return item_analysis(cid)


@app.get("/api/courses/{cid}/dashboard")
def dashboard(cid: str):
    return L.dashboard(_404(P.get_course(cid)))


# ----------------------------------------------------------------------------- web app

DIST = ROOT / "web" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = DIST / path
        if path and f.is_file():
            return FileResponse(f)
        return FileResponse(DIST / "index.html")
