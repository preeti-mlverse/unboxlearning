"""Shared ingestion model: every parser emits Elements through a DocBuilder."""
import hashlib
import re
import time
from dataclasses import dataclass, field

from .. import db
from ..config import settings

ELEMENT_KINDS = ("heading", "paragraph", "list_item", "code", "table", "figure", "equation", "quote",
                 "note", "caption", "transcript")


@dataclass
class Element:
    kind: str
    text: str
    level: int | None = None
    page: int | None = None
    section_path: list[str] = field(default_factory=list)
    bbox: list[float] | None = None
    media_path: str | None = None
    confidence: float = 1.0
    meta: dict = field(default_factory=dict)


class DocBuilder:
    """Collects elements in reading order and tracks the heading stack for section paths."""

    def __init__(self, title: str):
        self.title = title
        self.elements: list[Element] = []
        self.stack: list[tuple[int, str]] = []
        self.notes: list[str] = []

    def heading(self, text: str, level: int, **kw):
        text = clean(text)
        if not text:
            return
        while self.stack and self.stack[-1][0] >= level:
            self.stack.pop()
        self.stack.append((level, text))
        self.elements.append(Element("heading", text, level=level, section_path=self.path(), **kw))

    def add(self, kind: str, text: str, **kw):
        text = text.strip("\n") if kind in ("code", "table") else clean(text)
        if not text and kind != "figure":
            return
        # merge soft-wrapped paragraph continuations (lowercase start after no terminal punctuation)
        prev = self.elements[-1] if self.elements else None
        if (kind == "paragraph" and prev and prev.kind == "paragraph" and prev.page == kw.get("page")
                and not re.search(r"[.!?:;”\"')\]]$", prev.text) and text[:1].islower()):
            prev.text = f"{prev.text} {text}"
            return
        self.elements.append(Element(kind, text, section_path=self.path(), **kw))

    def path(self) -> list[str]:
        return [t for _, t in self.stack]


def clean(s: str) -> str:
    s = re.sub(r"(?<=[A-Za-z])�(?=(s|ll|t|re|ve|d|m)\b)", "'", s)
    s = s.replace("�", "—")
    s = s.replace("­", "").replace("ﬁ", "fi").replace("ﬂ", "fl")
    s = re.sub(r"(\w)-\n(\w)", r"\1\2", s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\s*\n\s*", " ", s)
    return s.strip()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def table_markdown(rows: list[list]) -> str:
    rows = [[clean(str(c or "")).replace("|", "\\|") for c in r] for r in rows if r and any(c for c in r)]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(out)


def save_media(data: bytes, ext: str) -> str:
    name = f"{sha256_bytes(data)[:20]}.{ext.lstrip('.')}"
    p = settings.media_dir / name
    if not p.exists():
        p.write_bytes(data)
    return name


def store(builder: DocBuilder, *, kind: str, origin: str, sha: str, meta: dict | None = None,
          source_id: str | None = None) -> dict:
    """Persist a parsed document as a source + elements. Returns the source row."""
    els = builder.elements
    sid = source_id or db.new_id("src")
    first = db.reserve("element", max(len(els), 1))
    stats = {k: sum(1 for e in els if e.kind == k) for k in ELEMENT_KINDS}
    stats["chars"] = sum(len(e.text) for e in els)
    pages = [e.page for e in els if e.page is not None]
    stats["pages"] = max(pages) if pages else None
    low = [e.page for e in els if e.confidence < 0.6 and e.page is not None]
    m = {"stats": stats, "parse_notes": builder.notes, "low_confidence_pages": sorted(set(low))[:200],
         **(meta or {})}
    with db.tx() as c:
        c.execute("INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?)",
                  (sid, builder.title, kind, origin, sha, None, "parsed", db.dumps(m), time.time()))
        c.executemany(
            "INSERT INTO elements VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            [(f"e{first + i}", sid, i, e.kind, e.level, e.text, e.page, db.dumps(e.section_path),
              db.dumps(e.bbox) if e.bbox else None, e.media_path, e.confidence, db.dumps(e.meta))
             for i, e in enumerate(els)])
    return db.row(db.conn().execute("SELECT * FROM sources WHERE id=?", (sid,)).fetchone())
