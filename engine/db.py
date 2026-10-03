"""SQLite storage. One file, WAL mode, JSON columns for documents.

The schema mirrors the research report's data model (source → element → chunk →
concept/objective → activity → attempt/mastery) so it can move to Postgres + pgvector
without changing callers.
"""
import json
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources(
  id TEXT PRIMARY KEY, title TEXT, kind TEXT, origin TEXT, sha256 TEXT, language TEXT,
  status TEXT, meta TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS elements(
  id TEXT PRIMARY KEY, source_id TEXT, ord INTEGER, kind TEXT, level INTEGER, text TEXT,
  page INTEGER, section_path TEXT, bbox TEXT, media_path TEXT, confidence REAL, meta TEXT);
CREATE INDEX IF NOT EXISTS ix_el_src ON elements(source_id, ord);
CREATE TABLE IF NOT EXISTS chunks(
  id TEXT PRIMARY KEY, source_id TEXT, ord INTEGER, section_path TEXT, text TEXT,
  element_ids TEXT, page_start INTEGER, page_end INTEGER, tokens INTEGER, embedding BLOB, embed_model TEXT);
CREATE INDEX IF NOT EXISTS ix_ch_src ON chunks(source_id, ord);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(chunk_id UNINDEXED, source_id UNINDEXED, text,
  tokenize='porter unicode61');
CREATE TABLE IF NOT EXISTS courses(
  id TEXT PRIMARY KEY, title TEXT, data TEXT, status TEXT, created_at REAL, updated_at REAL);
CREATE TABLE IF NOT EXISTS course_docs(
  course_id TEXT, kind TEXT, key TEXT, data TEXT, updated_at REAL, PRIMARY KEY(course_id, kind, key));
CREATE TABLE IF NOT EXISTS activities(
  id TEXT PRIMARY KEY, course_id TEXT, objective_id TEXT, type TEXT, stage TEXT, ord INTEGER,
  data TEXT, status TEXT, verify TEXT, created_at REAL, updated_at REAL);
CREATE INDEX IF NOT EXISTS ix_act_course ON activities(course_id, objective_id, ord);
CREATE TABLE IF NOT EXISTS learners(id TEXT PRIMARY KEY, name TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS attempts(
  id TEXT PRIMARY KEY, learner_id TEXT, course_id TEXT, activity_id TEXT, objective_id TEXT,
  response TEXT, score REAL, correct INTEGER, hints INTEGER, feedback TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS mastery(
  learner_id TEXT, course_id TEXT, objective_id TEXT, p REAL, attempts INTEGER, correct INTEGER,
  last_at REAL, next_review REAL, interval_days REAL, PRIMARY KEY(learner_id, objective_id));
CREATE TABLE IF NOT EXISTS jobs(
  id TEXT PRIMARY KEY, course_id TEXT, kind TEXT, status TEXT, stage TEXT, progress REAL,
  message TEXT, log TEXT, created_at REAL, updated_at REAL);
CREATE TABLE IF NOT EXISTS counters(name TEXT PRIMARY KEY, value INTEGER);
CREATE TABLE IF NOT EXISTS llm_calls(
  id INTEGER PRIMARY KEY AUTOINCREMENT, course_id TEXT, purpose TEXT, model TEXT,
  input_tokens INTEGER, output_tokens INTEGER, ms INTEGER, ok INTEGER, created_at REAL);
"""

_local = threading.local()
_init_lock = threading.Lock()
_counter_lock = threading.Lock()
_initialised = False


def conn() -> sqlite3.Connection:
    global _initialised
    c = getattr(_local, "conn", None)
    if c is None:
        c = sqlite3.connect(settings.db_path, timeout=30, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        with _init_lock:
            if not _initialised:
                c.executescript(SCHEMA)
                _initialised = True
        _local.conn = c
    return c


@contextmanager
def tx():
    c = conn()
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def reserve(name: str, n: int) -> int:
    """Reserve n consecutive integers from a named counter; returns the first."""
    with _counter_lock, tx() as c:
        r = c.execute("SELECT value FROM counters WHERE name=?", (name,)).fetchone()
        start = (r["value"] if r else 0) + 1
        c.execute("INSERT OR REPLACE INTO counters VALUES(?,?)", (name, start + n - 1))
    return start


def dumps(v) -> str:
    return json.dumps(v, ensure_ascii=False, default=lambda o: o.model_dump() if hasattr(o, "model_dump") else str(o))


def loads(s):
    return json.loads(s) if s else None


def row(r: sqlite3.Row | None, json_cols=("data", "meta", "section_path", "bbox", "element_ids", "verify",
                                          "response", "log", "feedback")):
    if r is None:
        return None
    d = dict(r)
    for k in json_cols:
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except json.JSONDecodeError:
                pass
    d.pop("embedding", None)
    return d


def rows(rs):
    return [row(r) for r in rs]


# ---- course documents (profile, knowledge, curriculum, plan, ...) ----

def put_doc(course_id: str, kind: str, data, key: str = "") -> None:
    with tx() as c:
        c.execute("INSERT OR REPLACE INTO course_docs VALUES(?,?,?,?,?)",
                  (course_id, kind, key, dumps(data), time.time()))


def get_doc(course_id: str, kind: str, key: str = ""):
    r = conn().execute("SELECT data FROM course_docs WHERE course_id=? AND kind=? AND key=?",
                       (course_id, kind, key)).fetchone()
    return loads(r["data"]) if r else None


def list_docs(course_id: str, kind: str) -> dict:
    rs = conn().execute("SELECT key, data FROM course_docs WHERE course_id=? AND kind=?", (course_id, kind))
    return {r["key"]: loads(r["data"]) for r in rs}


def del_docs(course_id: str, kind: str) -> None:
    with tx() as c:
        c.execute("DELETE FROM course_docs WHERE course_id=? AND kind=?", (course_id, kind))


def log_llm(course_id, purpose, model, tin, tout, ms, ok):
    with tx() as c:
        c.execute("INSERT INTO llm_calls(course_id,purpose,model,input_tokens,output_tokens,ms,ok,created_at)"
                  " VALUES(?,?,?,?,?,?,?,?)", (course_id, purpose, model, tin, tout, ms, int(ok), time.time()))
