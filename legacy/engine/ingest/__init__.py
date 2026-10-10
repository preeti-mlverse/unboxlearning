"""Ingestion entry points: detect the input type, parse to elements, store, then index."""
import mimetypes
import shutil
from pathlib import Path

from .. import db
from ..config import settings
from .base import sha256_bytes, store
from .media import parse_audio, parse_image, parse_youtube, vision_ocr, youtube_id
from .office import parse_docx, parse_pptx
from .pdf import parse_pdf
from .sheets import parse_csv, parse_epub, parse_xlsx
from .text import looks_like_markdown, parse_markdown, parse_plain
from .web import discover_site, fetch, merge_pages, parse_html

AUDIO_VIDEO = {".mp3", ".wav", ".m4a", ".mp4", ".mpeg", ".mpga", ".webm", ".ogg", ".flac", ".mov"}
IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
# linked documents that are downloaded and parsed as files rather than read as web pages
FILE_EXTS = {".pdf", ".docx", ".pptx", ".xlsx", ".xlsm", ".csv", ".tsv", ".epub"}

SUPPORTED = {
    "pdf": "PDF (text layer; scanned pages via vision OCR)",
    "docx": "Word documents",
    "pptx": "PowerPoint decks (slides + speaker notes)",
    "md/txt": "Markdown and plain text",
    "html/url": "Web pages (main content, tables, code, figures)",
    "site": "Documentation sites / sections (llms.txt index or same-prefix crawl)",
    "youtube": "YouTube videos with captions",
    "audio/video": "Audio or video files up to 25 MB (speech-to-text)",
    "image": "Images of pages, slides or diagrams (vision)",
    "xlsx/csv": "Spreadsheets and CSV tables (one section per sheet)",
    "epub": "E-books (chapters in reading order)",
}


def _existing(sha: str):
    return db.row(db.conn().execute("SELECT * FROM sources WHERE sha256=?", (sha,)).fetchone())


def _finish(builder, kind, origin, sha, meta=None):
    from ..index import index_source
    src = store(builder, kind=kind, origin=origin, sha=sha, meta=meta)
    index_source(src["id"])
    return db.row(db.conn().execute("SELECT * FROM sources WHERE id=?", (src["id"],)).fetchone())


def ingest_file(path: str | Path, title: str | None = None, dedupe: bool = True) -> dict:
    path = Path(path)
    data = path.read_bytes()
    sha = sha256_bytes(data)
    if dedupe and (hit := _existing(sha)):
        return hit
    keep = settings.upload_dir / f"{sha[:16]}{path.suffix.lower()}"
    if not keep.exists():
        shutil.copyfile(path, keep)
    ext = path.suffix.lower()
    if ext == ".pdf":
        b, kind = parse_pdf(keep, title, ocr=vision_ocr, fallback_title=path.stem), "pdf"
    elif ext == ".docx":
        b, kind = parse_docx(keep, title or path.stem), "docx"
    elif ext == ".pptx":
        b, kind = parse_pptx(keep, title or path.stem), "pptx"
    elif ext in (".md", ".markdown", ".mdx"):
        b, kind = parse_markdown(data.decode("utf-8", "replace"), title or path.stem), "markdown"
    elif ext in (".txt", ".text", ".rst"):
        txt = data.decode("utf-8", "replace")
        b = parse_markdown(txt, title or path.stem) if looks_like_markdown(txt) else parse_plain(txt, title or path.stem)
        kind = "text"
    elif ext in (".html", ".htm"):
        b, kind = parse_html(data.decode("utf-8", "replace"), path.as_uri(), title), "html"
    elif ext in (".xlsx", ".xlsm"):
        b, kind = parse_xlsx(keep, title or path.stem), "spreadsheet"
    elif ext in (".csv", ".tsv"):
        b = parse_csv(data.decode("utf-8-sig", "replace"), title or path.stem, "\t" if ext == ".tsv" else None)
        kind = "spreadsheet"
    elif ext == ".epub":
        b, kind = parse_epub(keep, title), "epub"
    elif ext in AUDIO_VIDEO:
        b, kind = parse_audio(keep, title), "audio"
    elif ext in IMAGES:
        b, kind = parse_image(keep, title), "image"
    else:
        raise ValueError(f"Unsupported file type {ext}. Supported: {', '.join(SUPPORTED)}")
    return _finish(b, kind, path.name, sha, {"file": keep.name})


def ingest_text(text: str, title: str = "Pasted text") -> dict:
    sha = sha256_bytes(text.encode())
    if hit := _existing(sha):
        return hit
    b = parse_markdown(text, title) if looks_like_markdown(text) else parse_plain(text, title)
    return _finish(b, "text", "pasted", sha)


def ingest_url(url: str, title: str | None = None, crawl: bool = False, max_pages: int = 40) -> dict:
    url = url.strip()
    if youtube_id(url):
        b = parse_youtube(url)
        return _finish(b, "youtube", url, sha256_bytes(url.encode()))
    if crawl:
        pages = discover_site(url, max_pages)
        built = []
        for p in pages:
            try:
                r = fetch(p)
            except Exception:  # noqa: BLE001
                continue
            ct = r.headers.get("content-type", "")
            if "markdown" in ct or p.endswith(".md") or "text/plain" in ct:
                built.append((p, parse_markdown(r.text, p.rsplit("/", 1)[-1])))
            else:
                built.append((p, parse_html(r.text, p, download_images=5)))
        b = merge_pages(title or built[0][1].title if built else url, built)
        b.notes.append(f"{len(built)} pages collected from the site")
        return _finish(b, "site", url, sha256_bytes(("site:" + url + str(len(built))).encode()), {"pages": pages})
    r = fetch(url)
    ct = r.headers.get("content-type", "").split(";")[0]
    ext = mimetypes.guess_extension(ct) or ""
    tail = Path(url.split("?")[0].lower()).suffix
    if tail in FILE_EXTS:
        ext = tail
    elif ct == "application/pdf":
        ext = ".pdf"
    if ext in FILE_EXTS or ct.startswith(("audio/", "video/", "image/")):
        tmp = settings.upload_dir / f"download{ext or Path(url).suffix}"
        tmp.write_bytes(r.content)
        src = ingest_file(tmp, title)
        tmp.unlink(missing_ok=True)
        return src
    sha = sha256_bytes(r.content)
    if hit := _existing(sha):
        return hit
    if "markdown" in ct or url.endswith(".md"):
        b = parse_markdown(r.text, title or url.rsplit("/", 1)[-1])
    elif ct.startswith("text/plain"):
        b = parse_markdown(r.text, title or url) if looks_like_markdown(r.text) else parse_plain(r.text, title or url)
    else:
        b = parse_html(r.text, str(r.url), title)
    return _finish(b, "url", url, sha)
