"""Web pages, documentation sites and URL-addressed files → elements."""
import re
from collections import deque
from urllib.parse import urldefrag, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag

from .base import DocBuilder, Element, clean, save_media, table_markdown
from .text import parse_markdown

UA = {"User-Agent": "Mozilla/5.0 (LearningEngine/0.1; +https://localhost) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
DROP_TAGS = ["script", "style", "noscript", "svg", "form", "iframe", "button", "nav", "footer", "header", "aside",
             "template", "input", "select"]
DROP_CLASS = re.compile(r"^(nav|navbar|navigation|sidebar|side-bar|toc|table-of-contents|breadcrumbs?|footer|"
                        r"site-header|page-header|cookie.*|banner|advert.*|ads?|share|social|mw-editsection|navbox|"
                        r"catlinks|printfooter|reflist|references|noprint|hatnote|mw-jump-link|skip-link|edit-link|"
                        r"related|newsletter|subscribe|infobox|sidebar-.*|vertical-navbox|mw-references-wrap)$", re.I)


def fetch(url: str, timeout: float = 40.0) -> httpx.Response:
    r = httpx.get(url, headers=UA, follow_redirects=True, timeout=timeout)
    r.raise_for_status()
    return r


def parse_html(html: str, url: str, title: str | None = None, download_images: int = 25) -> DocBuilder:
    soup = BeautifulSoup(html, "lxml")
    og = soup.find("meta", property="og:title")
    page_title = title or (og.get("content") if og else None) or (soup.title.get_text(strip=True) if soup.title else url)
    for t in soup(DROP_TAGS):
        t.decompose()
    for t in soup.find_all(attrs={"role": re.compile("navigation|banner|contentinfo|complementary")}):
        t.decompose()
    for t in soup.find_all(class_=True):
        if t.attrs is None or t.name in ("html", "body", "main", "article"):
            continue
        if any(DROP_CLASS.match(c) for c in t.get("class", [])):
            t.decompose()
    main = (soup.find("main") or soup.find("article") or soup.find(attrs={"role": "main"})
            or soup.find(id=re.compile(r"^(content|main|mw-content-text|bodyContent)$")) or soup.body or soup)

    b = DocBuilder(clean(page_title))
    budget = {"images": download_images}

    def text_of(node) -> str:
        return clean(node.get_text(" "))

    def walk(node: Tag):
        inline: list[str] = []

        def flush_inline():
            t = clean(" ".join(inline))
            if t:
                b.add("paragraph", t, meta={"url": url})
            inline.clear()

        for ch in node.children:
            if isinstance(ch, NavigableString):
                if ch.strip():
                    inline.append(str(ch))
                continue
            if not isinstance(ch, Tag):
                continue
            name = ch.name
            if name in ("a", "span", "strong", "em", "b", "i", "code", "sup", "sub", "abbr", "small", "mark", "u"):
                inline.append(ch.get_text(" "))
                continue
            flush_inline()
            if re.fullmatch(r"h[1-6]", name):
                b.heading(text_of(ch), int(name[1]), meta={"url": url})
            elif name == "p":
                t = text_of(ch)
                if t:
                    b.add("paragraph", t, meta={"url": url})
                for img in ch.find_all("img"):
                    _image(b, img, url, budget)
            elif name == "pre":
                cls = " ".join(ch.get("class", []) + (ch.code.get("class", []) if ch.code else []))
                lang = re.search(r"language-([\w+#-]+)", cls)
                b.add("code", ch.get_text(), meta={"language": lang.group(1)} if lang else {})
            elif name in ("ul", "ol"):
                for li in ch.find_all("li", recursive=False):
                    nested = [n.extract() for n in li.find_all(["ul", "ol"], recursive=False)]
                    t = text_of(li)
                    if t:
                        b.add("list_item", t, meta={"url": url})
                    for n in nested:
                        walk_list(n)
            elif name == "table":
                rows = [[c.get_text(" ") for c in tr.find_all(["th", "td"])] for tr in ch.find_all("tr")]
                if len(rows) >= 2 and max(len(r) for r in rows) >= 2:
                    b.add("table", table_markdown(rows), meta={"url": url})
                elif rows:
                    b.add("paragraph", " ".join(" ".join(r) for r in rows))
            elif name in ("img",):
                _image(b, ch, url, budget)
            elif name == "figure":
                cap = ch.find("figcaption")
                img = ch.find("img")
                if img:
                    _image(b, img, url, budget, caption=text_of(cap) if cap else None)
                elif ch.find("pre"):
                    walk(ch)
            elif name == "blockquote":
                b.add("quote", text_of(ch))
            elif name == "math" or "mwe-math" in " ".join(ch.get("class", [])):
                ann = ch.find("annotation")
                b.add("equation", ann.get_text() if ann else (ch.get("alttext") or text_of(ch)))
            elif name == "dl":
                for item in ch.find_all(["dt", "dd"], recursive=False):
                    b.add("paragraph", text_of(item))
            elif name in ("br", "hr"):
                continue
            else:
                walk(ch)
        flush_inline()

    def walk_list(lst: Tag):
        for li in lst.find_all("li", recursive=False):
            nested = [n.extract() for n in li.find_all(["ul", "ol"], recursive=False)]
            t = text_of(li)
            if t:
                b.add("list_item", t, meta={"url": url, "indent": 1})
            for n in nested:
                walk_list(n)

    walk(main)
    if sum(len(e.text) for e in b.elements) < 300:
        try:
            import trafilatura
            md = trafilatura.extract(html, output_format="markdown", include_tables=True, include_formatting=True,
                                     favor_recall=True)
            if md and len(md) > 300:
                fb = parse_markdown(md, b.title)
                fb.notes.append("main content recovered with trafilatura fallback")
                return fb
        except Exception:  # noqa: BLE001
            pass
    return b


def _image(b: DocBuilder, img: Tag, base: str, budget: dict, caption: str | None = None):
    src = img.get("src") or img.get("data-src")
    if not src or src.startswith("data:"):
        return
    src = urljoin(base, src)
    alt = clean(img.get("alt") or "")
    w = int(re.sub(r"\D", "", str(img.get("width") or "0")) or 0)
    if w and w < 80:  # icons
        return
    media = None
    if budget["images"] > 0:
        try:
            r = httpx.get(src, headers=UA, timeout=20, follow_redirects=True)
            ct = r.headers.get("content-type", "")
            if r.status_code == 200 and ct.startswith("image/") and len(r.content) > 4000 and "svg" not in ct:
                media = save_media(r.content, ct.split("/")[1].split(";")[0].replace("jpeg", "jpg"))
                budget["images"] -= 1
        except httpx.HTTPError:
            pass
    b.add("figure", caption or alt, media_path=media, meta={"url": src})


def discover_site(url: str, max_pages: int = 40) -> list[str]:
    """Pages of a docs site/section: llms.txt index when present, else a same-prefix crawl."""
    u = urlparse(url)
    prefix = u.path.rsplit("/", 1)[0] if not u.path.endswith("/") else u.path.rstrip("/")
    root = f"{u.scheme}://{u.netloc}"
    found: list[str] = []
    for idx in (f"{root}{prefix}/llms.txt", f"{root}/llms.txt"):
        try:
            txt = fetch(idx, timeout=20).text
        except httpx.HTTPError:
            continue
        for link in re.findall(r"\((https?://[^)\s]+)\)", txt):
            lp = urlparse(link)
            if lp.netloc == u.netloc and lp.path.startswith(prefix):
                found.append(link)
        if found:
            start = [f for f in found if f.rstrip("/").removesuffix(".md") == url.rstrip("/")]
            return list(dict.fromkeys(start + found))[:max_pages]
    seen, queue = {url}, deque([url])
    while queue and len(found) < max_pages:
        cur = queue.popleft()
        try:
            r = fetch(cur, timeout=20)
        except httpx.HTTPError:
            continue
        if "html" not in r.headers.get("content-type", ""):
            continue
        found.append(cur)
        for a in BeautifulSoup(r.text, "lxml").find_all("a", href=True):
            link = urldefrag(urljoin(cur, a["href"]))[0]
            lp = urlparse(link)
            if lp.netloc == u.netloc and lp.path.startswith(prefix) and link not in seen \
                    and not re.search(r"\.(png|jpe?g|gif|svg|zip|pdf|css|js)$", lp.path, re.I):
                seen.add(link)
                queue.append(link)
    return found


def merge_pages(title: str, builders: list[tuple[str, DocBuilder]]) -> DocBuilder:
    """Combine several page builders into one document; each page becomes a top-level section."""
    out = DocBuilder(title)
    for n, (url, pb) in enumerate(builders, 1):
        out.heading(pb.title, 1, page=n, meta={"url": url})
        top = min((e.level for e in pb.elements if e.kind == "heading" and e.level), default=1)
        skip_title = True
        for e in pb.elements:
            if e.kind == "heading":
                if skip_title and clean(e.text).lower() == clean(pb.title).lower():
                    skip_title = False
                    continue
                out.heading(e.text, e.level - top + 2, page=n, meta=e.meta)
            else:
                out.elements.append(Element(e.kind, e.text, page=n, section_path=out.path(), media_path=e.media_path,
                                            confidence=e.confidence, meta=e.meta))
        out.notes.extend(pb.notes)
    return out
