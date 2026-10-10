"""Markdown and plain text → elements."""
import re

from .base import DocBuilder

FENCE = re.compile(r"^\s*(`{3,}|~{3,})\s*([\w+#.-]*)")
MD_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
LIST = re.compile(r"^\s*([-*+•]|\d{1,3}[.)])\s+(.*)")
IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)[^)]*\)")
NUMBERED_HEADING = re.compile(r"^(\d+(?:\.\d+){0,3})\.?\s+([A-Z].{2,80})$")


JSX_LINE = re.compile(r"^\s*</?[A-Z][\w.]*(\s[^>]*)?/?>\s*$")
INDEX_BANNER = re.compile(r"^> (## Documentation Index|Fetch the complete documentation index|Use this file to discover)")


def _strip_mdx(lines: list[str]) -> list[str]:
    """Drop MDX component tags (keeping their content) and top-level JS exports; never touch code fences."""
    out, in_fence, in_export = [], False, False
    for l in lines:
        if FENCE.match(l):
            in_fence = not in_fence
        if not in_fence:
            if l.startswith("export const ") or l.startswith("export default "):
                in_export = True
            if in_export:
                if l.rstrip() == "};":
                    in_export = False
                continue
            if JSX_LINE.match(l) or INDEX_BANNER.match(l) or re.match(r"^\s*\{/\*.*\*/\}\s*$", l):
                continue
        out.append(l)
    return out


def parse_markdown(text: str, title: str) -> DocBuilder:
    text = re.sub(r"</?(sup|sub|span|br|small)[^>]*>", "", text)
    lines = _strip_mdx(text.replace("\r\n", "\n").split("\n"))
    if not title or re.fullmatch(r"[\w.-]+\.(md|mdx|txt)", title):
        title = next((l[2:].strip() for l in lines if l.startswith("# ")), None) or title
    b = DocBuilder(title)
    i, para = 0, []

    def flush():
        if para:
            b.add("paragraph", " ".join(para))
            para.clear()

    while i < len(lines):
        ln = lines[i]
        m = FENCE.match(ln)
        if m:
            flush()
            fence, lang = m.group(1), m.group(2)
            body = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(fence):
                body.append(lines[i])
                i += 1
            b.add("code", "\n".join(body), meta={"language": lang} if lang else {})
            i += 1
            continue
        m = MD_HEADING.match(ln)
        if m:
            flush()
            b.heading(re.sub(r"[*_`]", "", m.group(2)), len(m.group(1)))
            i += 1
            continue
        if i + 1 < len(lines) and ln.strip() and re.fullmatch(r"\s*(=+|-{3,})\s*", lines[i + 1]) and not para:
            b.heading(ln.strip(), 1 if "=" in lines[i + 1] else 2)
            i += 2
            continue
        if ln.lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            flush()
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            b.add("table", "\n".join(rows))
            continue
        if ln.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i].lstrip("> "))
                i += 1
            b.add("quote", " ".join(quote))
            continue
        for alt, src in IMAGE.findall(ln):
            flush()
            b.add("figure", alt, meta={"url": src})
        ln = IMAGE.sub("", ln)
        m = LIST.match(ln)
        if m:
            flush()
            item = [m.group(2)]
            i += 1
            while i < len(lines) and lines[i].startswith((" ", "\t")) and lines[i].strip() \
                    and not LIST.match(lines[i]) and not FENCE.match(lines[i]):
                item.append(lines[i].strip())
                i += 1
            b.add("list_item", " ".join(item))
            continue
        if not ln.strip():
            flush()
        else:
            para.append(ln.strip())
        i += 1
    flush()
    return b


def looks_like_markdown(text: str) -> bool:
    return bool(re.search(r"^#{1,6}\s|^```|^\s*[-*]\s|\]\(http", text, re.M))


def parse_plain(text: str, title: str) -> DocBuilder:
    """Plain text: infer headings from short standalone lines, numbering and capitalisation."""
    b = DocBuilder(title)
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n"))
    for blk in blocks:
        lines = [l.rstrip() for l in blk.split("\n") if l.strip()]
        if not lines:
            continue
        if len(lines) == 1:
            t = lines[0].strip()
            m = NUMBERED_HEADING.match(t)
            if m:
                b.heading(m.group(2), m.group(1).count(".") + 1)
                continue
            if len(t) < 70 and not re.search(r"[.,;:!?]$", t) and (t.isupper() or t.istitle()):
                b.heading(t.title() if t.isupper() else t, 2 if b.stack else 1)
                continue
        if all(LIST.match(l) for l in lines):
            for l in lines:
                b.add("list_item", LIST.match(l).group(2))
            continue
        if sum(l.startswith(("    ", "\t")) for l in lines) == len(lines):
            b.add("code", "\n".join(l[4:] if l.startswith("    ") else l[1:] for l in lines))
            continue
        b.add("paragraph", " ".join(l.strip() for l in lines))
    return b
