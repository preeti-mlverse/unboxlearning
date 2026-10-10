"""Structure-aware chunking, hybrid retrieval, and learning units.

* chunks  — retrieval-sized spans that never split code/tables and never cross sections
* units   — extraction-sized spans (a chapter/section) that the knowledge extractor reads whole
"""
import re
import threading
from functools import lru_cache

import numpy as np

from . import db
from .llm import gateway

CHUNK_TOKENS = 450
UNIT_MIN, UNIT_MAX = 700, 6000
MATH = set("∑∫√±≤≥≠≈∞πθλμσΔ∂∇∈=^×÷")


def tokens(s: str) -> int:
    return max(1, len(s) // 4)


def elements(source_id: str) -> list[dict]:
    return db.rows(db.conn().execute("SELECT * FROM elements WHERE source_id=? ORDER BY ord", (source_id,)))


def element_text(e: dict) -> str:
    if e["kind"] == "heading":
        return "#" * (e["level"] or 1) + " " + e["text"]
    if e["kind"] == "code":
        return "```\n" + e["text"] + "\n```"
    if e["kind"] == "list_item":
        return "- " + e["text"]
    if e["kind"] == "figure":
        return f"[figure] {e['text']}".strip()
    return e["text"]


# ----------------------------------------------------------------------------- chunks

def index_source(source_id: str) -> int:
    els = elements(source_id)
    chunks, cur, cur_tok, cur_path = [], [], 0, None

    def close():
        nonlocal cur, cur_tok
        if cur and any(e["kind"] != "heading" for e in cur):
            path = cur[-1]["section_path"] or []
            body = "\n".join(element_text(e) for e in cur)
            head = " > ".join(path)
            pages = [e["page"] for e in cur if e["page"] is not None]
            chunks.append({"text": (f"[{head}]\n" if head else "") + body, "section_path": path,
                           "element_ids": [e["id"] for e in cur],
                           "page_start": min(pages) if pages else None, "page_end": max(pages) if pages else None})
        cur, cur_tok = [], 0

    for e in els:
        t = tokens(e["text"])
        path = tuple(e["section_path"] or [])
        if e["kind"] == "heading" or path != cur_path or (cur_tok + t > CHUNK_TOKENS and cur_tok > 80):
            close()
        cur.append(e)
        cur_tok += t
        cur_path = path
    close()

    vecs = gateway.embed([c["text"] for c in chunks])
    first = db.reserve("chunk", max(len(chunks), 1))
    with db.tx() as c:
        c.execute("DELETE FROM chunks WHERE source_id=?", (source_id,))
        c.execute("DELETE FROM chunks_fts WHERE source_id=?", (source_id,))
        for i, (ch, v) in enumerate(zip(chunks, vecs)):
            cid = f"c{first + i}"
            c.execute("INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                      (cid, source_id, i, " > ".join(ch["section_path"]), ch["text"], db.dumps(ch["element_ids"]),
                       ch["page_start"], ch["page_end"], tokens(ch["text"]),
                       np.asarray(v, dtype=np.float32).tobytes(), gateway.last_embed_model))
            c.execute("INSERT INTO chunks_fts VALUES(?,?,?)", (cid, source_id, ch["text"]))
        c.execute("UPDATE sources SET status='indexed' WHERE id=?", (source_id,))
    _matrix.cache_clear()
    return len(chunks)


def ensure_embeddings(source_ids: list[str]) -> int:
    """Re-embed chunks made with a different embedding model (e.g. ingested before an API key was added)."""
    ph = ",".join("?" * len(source_ids))
    stale = db.conn().execute(f"SELECT id, text FROM chunks WHERE source_id IN ({ph}) AND "
                              f"(embed_model IS NULL OR embed_model != ?)", (*source_ids, gateway.embed_model)).fetchall()
    if not stale:
        return 0
    vecs = gateway.embed([r["text"] for r in stale])
    if gateway.last_embed_model != gateway.embed_model:
        return 0  # provider still unavailable; keep the existing vectors
    with db.tx() as c:
        for r, v in zip(stale, vecs):
            c.execute("UPDATE chunks SET embedding=?, embed_model=? WHERE id=?",
                      (np.asarray(v, dtype=np.float32).tobytes(), gateway.last_embed_model, r["id"]))
    _matrix.cache_clear()
    return len(stale)


_lock = threading.Lock()


@lru_cache(maxsize=16)
def _matrix(source_key: tuple) -> tuple[list[str], np.ndarray | None]:
    q = f"SELECT id, embedding FROM chunks WHERE source_id IN ({','.join('?' * len(source_key))})"
    rs = db.conn().execute(q, source_key).fetchall()
    if not rs:
        return [], None
    ids = [r["id"] for r in rs]
    dims = {len(r["embedding"]) for r in rs}
    if len(dims) != 1:
        return ids, None
    m = np.vstack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rs])
    m /= np.linalg.norm(m, axis=1, keepdims=True) + 1e-9
    return ids, m


def search(query: str, source_ids: list[str], k: int = 8) -> list[dict]:
    """Hybrid retrieval: BM25 (FTS5) + dense cosine, fused with reciprocal rank fusion.

    Filtering by source_ids happens before ranking, so nothing outside the course can be returned.
    """
    if not source_ids:
        return []
    key = tuple(sorted(source_ids))
    ranks: dict[str, float] = {}
    terms = [t for t in re.findall(r"\w+", query.lower()) if len(t) > 2][:24]
    if terms:
        fts_q = " OR ".join(f'"{t}"' for t in terms)
        ph = ",".join("?" * len(key))
        rs = db.conn().execute(f"SELECT chunk_id FROM chunks_fts WHERE chunks_fts MATCH ? AND source_id IN ({ph})"
                               f" ORDER BY bm25(chunks_fts) LIMIT 40", (fts_q, *key)).fetchall()
        for i, r in enumerate(rs):
            ranks[r["chunk_id"]] = ranks.get(r["chunk_id"], 0) + 1 / (60 + i)
    with _lock:
        ids, m = _matrix(key)
    if m is not None:
        qv = np.asarray(gateway.embed([query])[0], dtype=np.float32)
        if qv.shape[0] == m.shape[1]:
            sims = m @ (qv / (np.linalg.norm(qv) + 1e-9))
            for i, j in enumerate(np.argsort(-sims)[:40]):
                ranks[ids[j]] = ranks.get(ids[j], 0) + 1 / (60 + i)
    top = sorted(ranks, key=ranks.get, reverse=True)[:k]
    if not top:
        return []
    rs = db.conn().execute(f"SELECT * FROM chunks WHERE id IN ({','.join('?' * len(top))})", top).fetchall()
    by = {r["id"]: db.row(r) for r in rs}
    return [dict(by[i], score=round(ranks[i], 4)) for i in top if i in by]


# ----------------------------------------------------------------------------- units

def units(source_id: str) -> list[dict]:
    """Split a source into extraction units following its heading tree."""
    els = elements(source_id)
    if not els:
        return []

    def tok(span):
        return sum(tokens(e["text"]) for e in span)

    def split(span: list[dict]) -> list[list[dict]]:
        if tok(span) <= UNIT_MAX:
            return [span]
        levels = sorted({e["level"] for e in span[1:] if e["kind"] == "heading" and e["level"]})
        if levels:
            lvl = levels[0]
            parts, cur = [], []
            for e in span:
                if e["kind"] == "heading" and e["level"] == lvl and cur:
                    parts.append(cur)
                    cur = []
                cur.append(e)
            parts.append(cur)
            if len(parts) > 1:
                out = []
                for p in parts:
                    out.extend(split(p))
                return out
        # no usable headings: fixed-size windows on element boundaries
        parts, cur = [], []
        for e in span:
            cur.append(e)
            if tok(cur) >= UNIT_MAX * 0.8:
                parts.append(cur)
                cur = []
        if cur:
            parts.append(cur)
        return parts

    spans = split(els)
    merged: list[list[dict]] = []
    carry: list[dict] = []
    for s in spans:  # fold tiny spans (covers, part dividers, short intros) into their neighbours
        s = carry + s
        carry = []
        if tok(s) < UNIT_MIN:
            if merged and tok(merged[-1]) + tok(s) <= UNIT_MAX and                     (s[-1]["section_path"] or [])[:1] == (merged[-1][-1]["section_path"] or [])[:1]:
                merged[-1].extend(s)
            else:
                carry = s
            continue
        merged.append(s)
    if carry:
        if merged and tok(merged[-1]) + tok(carry) <= UNIT_MAX * 1.2:
            merged[-1].extend(carry)
        else:
            merged.append(carry)

    out = []
    for n, span in enumerate(merged, 1):
        first_h = next((e for e in span if e["kind"] == "heading"), None)
        path = (first_h or span[0])["section_path"] or []
        out.append({"id": f"{source_id}:u{n}", "source_id": source_id, "title": path[-1] if path else f"Part {n}",
                    "path": path, "element_ids": [e["id"] for e in span], "tokens": tok(span),
                    "pages": [p for p in (span[0]["page"], span[-1]["page"]) if p is not None],
                    "signals": signals(span)})
    return out


def signals(span: list[dict]) -> dict:
    text = " ".join(e["text"] for e in span)
    chars = len(text) or 1
    words = max(1, len(text.split()))
    kinds = {}
    for e in span:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    code_chars = sum(len(e["text"]) for e in span if e["kind"] == "code")
    return {
        "code_ratio": round(code_chars / chars, 3),
        "math_density": round((sum(ch in MATH for ch in text) + 20 * kinds.get("equation", 0)) / words, 3),
        "dates_per_1k": round(len(re.findall(r"\b(1[0-9]{3}|20[0-9]{2})\b", text)) * 1000 / words, 1),
        "list_items": kinds.get("list_item", 0),
        "numbered_steps": len(re.findall(r"(?:^|\s)(?:step\s*\d+|\d+\.\s+[A-Z])", text, re.I)),
        "tables": kinds.get("table", 0),
        "figures": kinds.get("figure", 0),
        "questions": text.count("?"),
        "imperatives": len(re.findall(r"(?:^|[.:]\s)(?:click|run|install|set|create|open|select|add|use|press|"
                                      r"configure|enter|choose|call|import|define|pass|type)\b", text, re.I)),
    }
