"""Build one print-ready HTML book from the downloaded Deep Agents .md pages.

Every in-page tab / code-group variant is expanded inline and labelled, so the
PDF holds all "horizontal" content (e.g. every model provider), in sidebar order.
"""
import html
import json
import re
from pathlib import Path

import markdown
from pygments.formatters import HtmlFormatter

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://docs.langchain.com"

CALLOUTS = {"Note", "Tip", "Warning", "Info", "Check", "Callout", "Danger"}
CONTAINERS = {"AccordionGroup", "CardGroup", "Columns", "Steps", "Frame", "Tabs", "CodeGroup"}
DROP = {"PatternEmbed", "Icon", "Tooltip"}

TAG_OPEN = re.compile(r"^<([A-Z][\w.]*)(\s[^>]*?)?\s*(/?)>\s*$", re.S)
TAG_CLOSE = re.compile(r"^</([A-Z][\w.]*)>\s*$")
ATTR = re.compile(r'([\w-]+)(?:=(?:"([^"]*)"|\'([^\']*)\'|\{([^}]*)\}))?')
MERMAID = []  # diagram sources, re-inserted after markdown conversion
FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")


def attrs(s):
    out = {}
    for m in ATTR.finditer(s or ""):
        v = m.group(2) if m.group(2) is not None else m.group(3) if m.group(3) is not None else m.group(4)
        out[m.group(1)] = True if v is None else v
    return out


def absolute(url):
    return SITE + url if url and url.startswith("/") else url


def esc(s):
    return html.escape(str(s), quote=True)


def inline_md(s):
    """Render a short attribute string (titles can hold `code`/**bold**) as inline HTML."""
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)


def fence_info(info):
    """```python Baseten theme={...} -> ('python', 'Baseten')."""
    info = re.sub(r'\s\w+=(\{.*\}|"[^"]*")', "", info).strip()
    parts = info.split()
    if not parts:
        return "", ""
    lang, rest = parts[0], [p for p in parts[1:] if p not in ("expandable", "wrap", "lines", "twoslash")]
    return lang, " ".join(rest)


def render_tree(lines):
    """<Tree><Tree.Folder name=..><Tree.File name=../> -> ascii tree."""
    rows, depth = [], 0
    for ln in lines:
        s = ln.strip()
        m = re.match(r"<Tree\.(Folder|File)\s+name=\"([^\"]+)\"", s)
        if m:
            kind, name = m.groups()
            rows.append("    " * depth + (name + "/" if kind == "Folder" else name))
            if kind == "Folder" and not s.endswith("/>"):
                depth += 1
        elif s == "</Tree.Folder>":
            depth -= 1
    return '<pre class="tree">' + esc("\n".join(rows)) + "</pre>"


def convert(md_text):
    lines = md_text.replace("\r\n", "\n").split("\n")
    # drop the "Documentation Index" banner
    while lines and (lines[0].startswith(">") or not lines[0].strip()) and "# " not in lines[0][:2]:
        if lines[0].startswith("> ##") or lines[0].startswith("> Fetch") or lines[0].startswith("> Use this"):
            lines.pop(0)
        elif not lines[0].strip():
            lines.pop(0)
        else:
            break

    out = []
    stack = []  # (name, column)
    step_no = []
    fence = None  # (marker)
    i = 0

    def strip_amt():
        return stack[-1][1] + 2 if stack else 0

    def ded(line):
        n = strip_amt()
        lead = len(line) - len(line.lstrip(" "))
        return line[min(n, lead):]

    def emit_html(s):
        out.extend(["", s, ""])

    while i < len(lines):
        raw = lines[i]
        line = ded(raw)
        i += 1

        # inside a fenced code block: copy through
        if fence:
            marker, cut = fence
            lead = len(line) - len(line.lstrip(" "))
            out.append(line[min(cut, lead):])
            if line.strip().startswith(marker) and line.strip().strip(marker[0]) == "":
                fence = None
            continue

        m = FENCE.match(line)
        if m:
            lead, marker, info = m.groups()
            lang, title = fence_info(info)
            if lang == "mermaid":
                # render as a real diagram (mermaid.js runs before printing)
                src = []
                while i < len(lines) and not ded(lines[i]).strip().startswith(marker):
                    src.append(ded(lines[i])[len(lead):])
                    i += 1
                i += 1
                MERMAID.append(chr(10).join(src))
                emit_html(f'<p>MERMAIDSLOT{len(MERMAID) - 1}END</p>')
                continue
            if title:
                emit_html(f'<div class="code-title">{esc(title)}</div>')
            # Python-Markdown only sees fences at column 0 (not inside list items)
            out.append(f"{marker}{lang}")
            fence = (marker, len(lead))
            continue

        s = raw.strip()
        col = len(raw) - len(raw.lstrip(" "))

        # top-level JS component definitions (export const X = ... };)
        if s.startswith("export const ") and not stack:
            while i < len(lines) and lines[i].rstrip() != "};":
                i += 1
            i += 1
            continue

        # multi-line opening tag
        if re.match(r"^<[A-Z]", s) and ">" not in s:
            while i < len(lines) and ">" not in s:
                s += " " + lines[i].strip()
                i += 1

        s = re.sub(r"\{/\*.*?\*/\}", "", s).strip() if s.startswith("{/*") else s

        one = re.match(r"^<(Note|Tip|Warning|Info|Check|Danger)>(.*)</\1>$", s)
        if one:
            o, c = open_component(one.group(1), {}, step_no)
            emit_html(o)
            out.append(one.group(2))
            emit_html(c)
            continue

        mo, mc = TAG_OPEN.match(s), TAG_CLOSE.match(s)
        if mo:
            name, a, selfclose = mo.group(1), attrs(mo.group(2)), mo.group(3) == "/"
            if name == "Tree":
                block = [s]
                while i < len(lines) and lines[i].strip() != "</Tree>":
                    block.append(lines[i])
                    i += 1
                i += 1
                emit_html(render_tree(block))
                continue
            if name in DROP:
                if name == "PatternEmbed":
                    emit_html(f'<div class="embed">Interactive demo &ldquo;{esc(a.get("pattern", ""))}&rdquo; '
                              f'is available on the web page.</div>')
                continue
            open_html, close_html = open_component(name, a, step_no)
            if selfclose:
                emit_html(open_html + close_html)
            else:
                emit_html(open_html)
                stack.append((name, col, close_html))
                if name == "Steps":
                    step_no.append(0)
            continue
        if mc and stack and mc.group(1) == stack[-1][0]:
            name, _, close_html = stack.pop()
            if name == "Steps":
                step_no.pop()
            emit_html(close_html)
            continue

        # inline JSX leftovers
        line = re.sub(r"<Icon[^>]*/>", "", line)
        line = re.sub(r"\{/\*.*?\*/\}", "", line)
        out.append(line)

    text = "\n".join(out)
    # relative doc links -> absolute
    text = re.sub(r"\]\((/[^)\s]*)\)", lambda m: "](" + SITE + m.group(1) + ")", text)
    text = re.sub(r'(href|src)="(/[^"]*)"', lambda m: f'{m.group(1)}="{SITE}{m.group(2)}"', text)
    return text


def open_component(name, a, step_no):
    title = a.get("title")
    if name in CALLOUTS:
        kind = name.lower() if name != "Callout" else "note"
        label = {"note": "Note", "tip": "Tip", "warning": "Warning", "info": "Info",
                 "check": "Check", "danger": "Danger"}.get(kind, "Note")
        head = f'<div class="callout-label">{label}</div>' if name != "Callout" else ""
        return f'<div class="callout {kind}" markdown="1">\n{head}', "</div>"
    if name == "Prompt":
        return (f'<div class="callout prompt" markdown="1">\n<div class="callout-label">Prompt &mdash; '
                f'{inline_md(a.get("description", ""))}</div>'), "</div>"
    if name == "Tab":
        return (f'<div class="tab" markdown="1">\n<div class="tab-title">Tab: {inline_md(title or "")}</div>',
                "</div>")
    if name == "Step":
        if step_no:
            step_no[-1] += 1
        n = step_no[-1] if step_no else "•"
        return (f'<div class="step" markdown="1">\n<div class="step-title"><span class="step-n">{n}</span>'
                f'{inline_md(title or "")}</div>', "</div>")
    if name in ("Accordion", "Expandable"):
        return (f'<div class="accordion" markdown="1">\n<div class="acc-title">{inline_md(title or "Details")}</div>',
                "</div>")
    if name == "Card":
        href = absolute(a.get("href"))
        t = inline_md(title or "")
        t = f'<a href="{esc(href)}">{t}</a>' if href else t
        return f'<div class="card" markdown="1">\n<div class="card-title">{t}</div>', "</div>"
    if name in ("ParamField", "ResponseField"):
        pname = next((a[k] for k in ("path", "body", "query", "header", "name", "param") if k in a), "")
        bits = [f"<code>{esc(pname)}</code>"]
        if a.get("type"):
            bits.append(f'<span class="ptype">{esc(a["type"])}</span>')
        if a.get("required"):
            bits.append('<span class="preq">required</span>')
        if a.get("default") not in (None, True):
            bits.append(f'<span class="pdef">default: {esc(a["default"])}</span>')
        return f'<div class="param" markdown="1">\n<div class="param-head">{" ".join(bits)}</div>', "</div>"
    if name == "Update":
        tags = re.findall(r'"([^"]+)"', a.get("tags", "")) if isinstance(a.get("tags"), str) else []
        tg = "".join(f'<span class="tag">{esc(t)}</span>' for t in tags)
        return (f'<div class="update" markdown="1">\n<div class="update-label">{esc(a.get("label", ""))} {tg}</div>',
                "</div>")
    if name == "Frame":
        cap = a.get("caption")
        return '<div class="frame" markdown="1">', (f'<div class="caption">{esc(cap)}</div>' if cap else "") + "</div>"
    cls = re.sub(r"(?<!^)([A-Z])", r"-\1", name).lower()
    return f'<div class="{cls}" markdown="1">', "</div>"


def page_html(md_text, n):
    text = convert(md_text)
    # page title (# X) and its > description
    m = re.match(r"\s*# (.+?)\n+(> (.+?)\n)?", text)
    title, desc = (m.group(1), m.group(3)) if m else (f"Page {n}", None)
    body = text[m.end():] if m else text
    md = markdown.Markdown(extensions=["extra", "md_in_html", "codehilite", "toc", "sane_lists"],
                           extension_configs={"codehilite": {"guess_lang": False, "css_class": "hl"},
                                              "toc": {"permalink": False}})
    h = md.convert(body)
    # namespace ids/anchors per page so the combined book has no collisions
    h = re.sub(r'id="([^"]+)"', lambda x: f'id="p{n}-{x.group(1)}"', h)
    h = re.sub(r'href="#([^"]+)"', lambda x: f'href="#p{n}-{x.group(1)}"', h)
    h = re.sub(r"<p>MERMAIDSLOT(\d+)END</p>",
               lambda x: f'<pre class="mermaid">{esc(MERMAID[int(x.group(1))])}</pre>', h)
    # drop dark-mode duplicate images
    h = re.sub(r'<img[^>]*dark:block[^>]*>', "", h)
    return title, desc, h


def main():
    pages = json.load(open(ROOT / "source/pages.json", encoding="utf8"))
    toc, bodies, last_section = [], [], None
    for n, p in enumerate(pages, 1):
        title, desc, h = page_html((ROOT / p["file"]).read_text(encoding="utf8"), n)
        section = " › ".join(p["section"]) or "Introduction"
        top = p["section"][0] if p["section"] else "Introduction"
        if top != last_section:
            toc.append(f'<li class="toc-sec">{esc(top)}</li>')
            bodies.append(f'<section class="part"><div class="part-label">Part</div><h1 class="part-title">{esc(top)}</h1></section>')
            last_section = top
        toc.append(f'<li><a href="#page-{n}"><span class="toc-n">{n:02d}</span>{inline_md(title)}</a></li>')
        bodies.append(
            f'<article class="page" id="page-{n}">'
            f'<div class="crumb">{esc(section)}</div>'
            f'<h1 class="page-title">{inline_md(title)}</h1>'
            + (f'<p class="lede">{inline_md(desc)}</p>' if desc else "")
            + f'<div class="src">Source: <a href="{SITE}{p["href"]}">{SITE}{p["href"]}</a></div>'
            + h + "</article>")

    css = (ROOT / "scripts/book.css").read_text(encoding="utf8")
    css += HtmlFormatter(style="friendly").get_style_defs(".hl")
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>LangChain Deep Agents (Python) — Documentation</title><style>{css}</style>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{startOnLoad: true, theme: "neutral", securityLevel: "loose",
  flowchart: {{htmlLabels: true}}}});</script></head><body>
<section class="cover">
  <div class="cover-kicker">LangChain Docs · Python</div>
  <h1>Deep Agents</h1>
  <p class="cover-sub">Complete documentation — all {len(pages)} pages of the Deep Agents sidebar,
  with every tab and code variant expanded.</p>
  <p class="cover-meta">Source: docs.langchain.com/oss/python/deepagents · compiled 27 Sep 2026</p>
</section>
<section class="toc"><h1>Contents</h1><ol>{''.join(toc)}</ol></section>
{''.join(bodies)}
</body></html>"""
    (ROOT / "build").mkdir(exist_ok=True)
    (ROOT / "build/deep_agents_docs.html").write_text(doc, encoding="utf8")
    print("pages:", len(pages), "html bytes:", len(doc))


if __name__ == "__main__":
    main()
