"""PDF → elements with layout heuristics.

Progressive fallback: native text (fonts, outline, tables, images) → vision OCR for image-only pages.
"""
import contextlib
import io
import re
from collections import Counter, defaultdict
from pathlib import Path

import pymupdf

from .base import DocBuilder, clean, save_media, table_markdown

MONO = re.compile(r"mono|courier|consol|menlo|cascadia|inconsolata|sourcecode|source code|firacode|jetbrains",
                  re.I)
BULLET = re.compile(r"^\s*([•◦▪▫‣∙·●○■□➢►▸\-–—*]|\(?\d{1,2}[.)]|\(?[a-hA-H][.)])\s+")
CAPTION = re.compile(r"^(fig(ure)?\.?|table|chart|diagram|exhibit)\s*\d+", re.I)
MATH = set("∑∫√±≤≥≠≈∞πθλμσΔ∂∇∈∀∃→⇒^=×÷")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


CODE_LINE = re.compile(r"^\s*(def |class |import |from \S+ import|return\b|await |async |if .*:$|for .*:$|while .*:$|"
                       r"[\w.\[\]\"']+\s*[+\-*/]?=\s*\S|[\w.]+\(.*|[)\]}]+[,;]?$|#|//|\$ |>>> |pip |npm |"
                       r"\"[^\"]*\",?$|@\w+|\w+=.*,$)")


def looks_like_code(lines: list[str]) -> bool:
    if len(lines) < 2:
        return False
    hits = sum(bool(CODE_LINE.match(l.replace(" ", " "))) for l in lines)
    prose = sum(len(l.split()) > 9 and l.rstrip().endswith(".") for l in lines)
    return hits >= 0.6 * len(lines) and prose == 0


def parse_pdf(path: Path, title: str | None = None, ocr=None, fallback_title: str | None = None) -> DocBuilder:
    doc = pymupdf.open(path)
    meta_title = (doc.metadata or {}).get("title") or ""
    if re.fullmatch(r"[0-9a-f]{12,}|untitled|document\d*|microsoft word.*", meta_title.strip(), re.I):
        meta_title = ""
    b = DocBuilder(title or meta_title.strip() or fallback_title or Path(path).stem)
    npages = doc.page_count

    # ---- pass 1: collect lines per page
    pages = []
    size_chars = Counter()
    edge_keys = defaultdict(set)
    flags = pymupdf.TEXT_PRESERVE_WHITESPACE | pymupdf.TEXT_MEDIABOX_CLIP
    for pno, page in enumerate(doc, 1):
        h = page.rect.height or 1
        blocks = []
        for blk in page.get_text("dict", flags=flags)["blocks"]:
            if blk.get("type") != 0:
                continue
            lines = []
            for ln in blk["lines"]:
                spans = [s for s in ln["spans"] if s["text"].strip()]
                if not spans:
                    continue
                text = "".join(s["text"] for s in ln["spans"]).rstrip()
                n = sum(len(s["text"]) for s in spans) or 1
                size = sum(s["size"] * len(s["text"]) for s in spans) / n
                bold = sum(len(s["text"]) for s in spans if s["flags"] & 16 or "bold" in s["font"].lower()) / n > 0.6
                mono = sum(len(s["text"]) for s in spans if MONO.search(s["font"])) / n > 0.6
                y0, y1 = ln["bbox"][1], ln["bbox"][3]
                font = max(spans, key=lambda s: len(s["text"]))["font"]
                lines.append({"text": text, "size": round(size, 1), "bold": bold, "mono": mono, "font": font,
                              "bbox": list(ln["bbox"])})
                if y0 < 0.08 * h or y1 > 0.92 * h:
                    edge_keys[re.sub(r"\d+", "#", _norm(text))].add(pno)
            if lines:
                blocks.append({"bbox": list(blk["bbox"]), "lines": lines})
        pages.append(blocks)

    # fonts that are mostly used for code (catches embedded/Type3 fonts with meaningless names)
    font_lines, font_code = Counter(), Counter()
    for blocks in pages:
        for blk in blocks:
            for ln in blk["lines"]:
                font_lines[ln["font"]] += 1
                font_code[ln["font"]] += bool(CODE_LINE.match(ln["text"].replace(" ", " ")))
    body_font = font_lines.most_common(1)[0][0] if font_lines else None
    code_fonts = {f for f, n in font_lines.items() if f != body_font and n >= 5 and font_code[f] / n >= 0.3}
    for blocks in pages:
        for blk in blocks:
            for ln in blk["lines"]:
                if ln["font"] in code_fonts:
                    ln["mono"] = True

    repeated = {k for k, ps in edge_keys.items() if k and len(ps) >= max(3, 0.3 * npages)}

    def is_edge(line, pno):
        return re.sub(r"\d+", "#", _norm(line["text"])) in repeated or re.fullmatch(r"\s*\d{1,4}\s*", line["text"])

    for pno, blocks in enumerate(pages, 1):
        for blk in blocks:
            blk["lines"] = [ln for ln in blk["lines"] if not is_edge(ln, pno)]
            for ln in blk["lines"]:
                if not ln["mono"]:
                    size_chars[ln["size"]] += len(ln["text"])
    body = size_chars.most_common(1)[0][0] if size_chars else 11.0

    # ---- heading model: outline (TOC) if useful, else font sizes
    toc = [(lvl, _norm(t), p) for lvl, t, p in doc.get_toc(simple=True) if _norm(t)]
    toc_by_page = defaultdict(list)
    for lvl, t, p in toc:
        for q in (p - 1, p, p + 1):
            toc_by_page[q].append((lvl, t))
    use_toc = len(toc) >= 3
    big = sorted({s for s, c in size_chars.items() if s >= body * 1.15 and c >= 3}, reverse=True)[:4]
    level_of_size = {s: i + 1 for i, s in enumerate(big)}
    toc_max = max((lvl for lvl, _, _ in toc), default=0)

    def heading_level(line, pno, block_lines):
        t = line["text"].strip()
        if len(t) > 160 or len(t) < 2:
            return None
        if use_toc:
            nt = _norm(t)
            for lvl, tt in toc_by_page.get(pno, []):
                if nt == tt or (len(nt) > 6 and (tt.startswith(nt) or nt.startswith(tt))):
                    return lvl
        lvl = next((level_of_size[s] for s in level_of_size if abs(s - line["size"]) < 0.3), None)
        if lvl:
            return (toc_max + lvl) if use_toc else lvl
        if (line["bold"] and not line["mono"] and len(block_lines) == 1 and len(t) < 90
                and not t.endswith((".", ",", ";")) and abs(line["size"] - body) < 0.6):
            return (toc_max if use_toc else len(level_of_size)) + 1
        return None

    # ---- images (skip logos / decorations repeated across pages)
    img_pages = defaultdict(set)
    for pno, page in enumerate(doc, 1):
        for info in page.get_image_info(xrefs=True):
            if info.get("xref"):
                img_pages[info["xref"]].add(pno)
    repeated_imgs = {x for x, ps in img_pages.items() if len(ps) >= max(3, 0.3 * npages)}

    # ---- pass 2: emit elements
    code_buf = []

    def flush_code(pno):
        if code_buf:
            b.add("code", "\n".join(code_buf), page=pno)
            code_buf.clear()

    for pno, (page, blocks) in enumerate(zip(doc, pages), 1):
        area = page.rect.width * page.rect.height or 1
        text_chars = sum(len(ln["text"]) for blk in blocks for ln in blk["lines"])
        infos = [i for i in page.get_image_info(xrefs=True) if i.get("xref") not in repeated_imgs]
        img_cover = sum(max(0, (i["bbox"][2] - i["bbox"][0]) * (i["bbox"][3] - i["bbox"][1])) for i in infos) / area

        if text_chars < 40 and img_cover > 0.5:  # image-only (scanned) page
            flush_code(pno)
            png = page.get_pixmap(dpi=150).tobytes("png")
            name = save_media(png, "png")
            done = ocr(name, pno) if ocr else None
            if done:
                for kind, text, level in done:
                    if kind == "heading":
                        b.heading(text, level or 2, page=pno, confidence=0.75)
                    else:
                        b.add(kind, text, page=pno, confidence=0.75)
                b.notes.append(f"page {pno}: text recovered with vision OCR")
            else:
                b.add("figure", "Scanned page (no text layer)", page=pno, media_path=name, confidence=0.2)
                b.notes.append(f"page {pno}: image-only page, OCR not available")
            continue

        # tables
        tables = []
        try:
            with contextlib.redirect_stdout(io.StringIO()):  # pymupdf prints an advisory on stdout
                found = page.find_tables().tables
            for t in found:
                rows = t.extract()
                if len(rows) >= 2 and max(len(r) for r in rows) >= 2:
                    tables.append((t.bbox, table_markdown(rows)))
        except Exception:  # noqa: BLE001 - table finder is best-effort
            pass

        def in_table(bbox):
            cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
            return any(tb[0] <= cx <= tb[2] and tb[1] <= cy <= tb[3] for tb, _ in tables)

        items = []  # (y, kind, payload)
        for tb, md in tables:
            items.append((tb[1], "table", md))
        for info in infos:
            bb = info["bbox"]
            w, hgt = bb[2] - bb[0], bb[3] - bb[1]
            if w * hgt < 0.02 * area or w < 60 or hgt < 40:
                continue
            items.append((bb[1], "image", info))
        for blk in blocks:
            if blk["lines"] and not in_table(blk["bbox"]):
                items.append((blk["bbox"][1], "block", blk))
        items.sort(key=lambda it: it[0])

        last_figure = None
        for y, kind, payload in items:
            if kind == "table":
                flush_code(pno)
                b.add("table", payload, page=pno)
                continue
            if kind == "image":
                flush_code(pno)
                try:
                    img = doc.extract_image(payload["xref"])
                    data, ext = img["image"], img["ext"]
                    if ext not in ("png", "jpeg", "jpg"):
                        pix = pymupdf.Pixmap(doc, payload["xref"])
                        if pix.n - pix.alpha >= 4:
                            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                        data, ext = pix.tobytes("png"), "png"
                    name = save_media(data, ext)
                    b.add("figure", "", page=pno, media_path=name, bbox=list(payload["bbox"]))
                    last_figure = b.elements[-1]
                except Exception:  # noqa: BLE001
                    pass
                continue

            lines = payload["lines"]
            if all(ln["mono"] for ln in lines) or looks_like_code([ln["text"] for ln in lines]):
                code_buf.extend(ln["text"] for ln in lines)
                continue
            flush_code(pno)
            buf, buf_kind = [], None

            def emit():
                nonlocal buf, buf_kind, last_figure
                if not buf:
                    return
                text = clean("\n".join(buf))
                k = buf_kind or "paragraph"
                if k == "paragraph":
                    if CAPTION.match(text):
                        k = "caption"
                        if last_figure is not None and not last_figure.text:
                            last_figure.text = text
                    elif len(text) < 200 and sum(ch in MATH for ch in text) >= max(2, len(text) * 0.08):
                        k = "equation"
                b.add(k, BULLET.sub("", text) if k == "list_item" else text, page=pno,
                      bbox=payload["bbox"])
                buf, buf_kind = [], None

            prev_heading = None
            for i, ln in enumerate(lines):
                lvl = heading_level(ln, pno, lines) if i == 0 or not buf else None
                if lvl:
                    emit()
                    if prev_heading and prev_heading.level == lvl:  # heading wrapped over two lines
                        prev_heading.text = clean(prev_heading.text + " " + ln["text"])
                        b.stack[-1] = (lvl, prev_heading.text)
                        prev_heading.section_path = b.path()
                        continue
                    b.heading(ln["text"], lvl, page=pno, bbox=ln["bbox"])
                    prev_heading = b.elements[-1]
                    continue
                prev_heading = None
                if BULLET.match(ln["text"]):
                    emit()
                    buf_kind = "list_item"
                buf.append(ln["text"])
            emit()
        flush_code(pno)

    if use_toc:
        b.notes.append("headings taken from the PDF outline")
    return b
