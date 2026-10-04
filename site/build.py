"""Build the UnboxEd marketing site into public/.

Each file in src/pages is an HTML fragment with a small header comment:

    <!--
    title: How it works
    description: One sentence for search results.
    nav: how
    -->

The fragment is wrapped in the shared layout (head, header, footer) and written as
<path>/index.html, so every page has a clean URL such as /how-it-works/ on any static host.
Run:  python build.py          (build)
      python build.py --check  (build, then verify every internal link and asset exists)
"""
import hashlib
import re
import shutil
import sys
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
SRC, OUT = ROOT / "src", ROOT / "public"
SITE = "https://unboxlearning.in"
BRAND = "UnboxEd"
TAGLINE = "Any knowledge in. Real learning out."
EMAIL = "preeti.agrawal@lightbulblabs.tech"
PHONE = "+91 70048 47355"
PHONE_TEL = "+917004847355"

NAV = [("how", "How it works", "/how-it-works/"), ("experience", "Experience", "/experience/"),
       ("educators", "For Educators", "/educators/"), ("learners", "For Learners", "/learners/"),
       ("organizations", "For Organizations", "/organizations/"), ("impact", "Impact", "/impact/"),
       ("about", "About", "/about/")]
DEMO = ("Try the demo", "/demo/")
CTA = ("Sign up", "/signup/")
LOGIN = ("Log in", "/login/")

FOOTER = [
    ("Product", [("How it works", "/how-it-works/"), ("AI Tutor", "/experience/#tutor"),
                 ("Interactive Learning", "/experience/#interactive"), ("Voice", "/experience/#voice"),
                 ("Multilingual", "/experience/#multilingual"), ("Personalization", "/experience/#personalization")]),
    ("Solutions", [("Learners", "/learners/"), ("Educators", "/educators/"), ("Schools", "/organizations/#schools"),
                   ("Organizations", "/organizations/#companies"), ("NGOs", "/organizations/#ngos")]),
    ("Company", [("About", "/about/"), ("Impact", "/impact/"), ("Research", "/about/#research"),
                 ("Partners", "/about/#partners"), ("Contact", "/contact/")]),
    ("Resources", [("Blog", "/blog/"), ("Documentation", "/docs/"), ("Privacy", "/privacy/"), ("Terms", "/terms/")]),
]

SPRITES = """<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<symbol id="logo" viewBox="276 258 702 702"><polygon points="308.0,766.0 626.5,582.1 626.5,766.0 626.5,950.0" fill="#5B3FE0"/><polygon points="626.5,582.1 945.0,766.0 626.5,950.0 626.5,766.0" fill="#C9C2F2"/><polygon points="308.0,766.0 626.5,766.0 626.5,950.0" fill="#5B3FE0"/><polygon points="626.5,766.0 945.0,766.0 626.5,950.0" fill="#C9C2F2"/><path d="M308.0 766.0 L308.0 435.0 Q308.0 405.0 334.0 390.0 L472.0 310.3 Q498.0 295.3 498.0 325.3 L498.0 656.3 Z" fill="#ECE9FC"/><path d="M755.0 656.3 L755.0 325.3 Q755.0 295.3 781.0 310.3 L919.0 390.0 Q945.0 405.0 945.0 435.0 L945.0 766.0 Z" fill="#F5B301"/><polygon points="499.0,644.0 626.5,570.4 754.0,644.0 754.0,676.0 626.5,602.4 499.0,676.0" fill="#A797FF"/><polygon points="499.0,676.0 626.5,602.4 754.0,676.0 626.5,749.6" fill="#7B63F5"/><polygon points="516.9,676.0 626.5,612.7 736.1,676.0 626.5,739.3" fill="#1B164B"/><polygon points="499.0,676.0 626.5,749.6 626.5,823.6 499.0,750.0" fill="#4129B8"/><polygon points="626.5,749.6 754.0,676.0 754.0,750.0 626.5,823.6" fill="#4129B8"/></symbol>
<symbol id="mira" viewBox="0 0 64 64"><circle cx="32" cy="32" r="30" fill="#4B32C8"/><circle cx="32" cy="34" r="21" fill="#FFF7F1"/><path d="M13 23c5-11 15-15 23-13s12 6 14 12c-8-4-21-6-37 1z" fill="#1B164B"/><ellipse cx="24.5" cy="31" rx="2.6" ry="3.3" fill="#1B164B"/><ellipse cx="39.5" cy="31" rx="2.6" ry="3.3" fill="#1B164B"/><circle cx="19" cy="38" r="3" fill="#E65F45" opacity=".45"/><circle cx="45" cy="38" r="3" fill="#E65F45" opacity=".45"/><ellipse class="mouth" cx="32" cy="42" rx="5" ry="2" fill="#1B164B"/><circle cx="50" cy="12" r="5" fill="#F2B900"/></symbol>
<symbol id="check" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#1E9E78"/><path d="M7 12.5l3.2 3.2L17 9" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></symbol>
<symbol id="arrow" viewBox="0 0 40 24"><path d="M2 12h32M24 3l10 9-10 9" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/></symbol>
<symbol id="i-mic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3M8 21h8"/></symbol>
<symbol id="i-eye" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></symbol>
<symbol id="i-phone" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="2" width="12" height="20" rx="3"/><path d="M11 18h2"/></symbol>
<symbol id="i-feather" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20 14 10M20 4c-6 0-12 4-12 12h6c4 0 6-6 6-12z"/></symbol>
<symbol id="i-sliders" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/></symbol>
<symbol id="i-layers" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 2 8l10 5 10-5-10-5zM2 13l10 5 10-5M2 18l10 5 10-5"/></symbol>
<symbol id="i-book" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h6a2 2 0 0 1 2 2v14a2 2 0 0 0-2-2H4zM20 4h-6a2 2 0 0 0-2 2v14a2 2 0 0 1 2-2h6z"/></symbol>
<symbol id="i-spark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/></symbol>
<symbol id="i-hand" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 13V5a2 2 0 0 1 4 0v6M12 10V4a2 2 0 0 1 4 0v7M16 9a2 2 0 0 1 4 0v5a7 7 0 0 1-7 7h-1a7 7 0 0 1-6-3.4L3 13a2 2 0 0 1 3.4-2L8 13"/></symbol>
<symbol id="i-flask" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3h6M10 3v6L4 19a2 2 0 0 0 1.7 3h12.6A2 2 0 0 0 20 19l-6-10V3M7 15h10"/></symbol>
<symbol id="i-cards" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="6" width="13" height="15" rx="2"/><path d="M8 3h11a2 2 0 0 1 2 2v12"/></symbol>
<symbol id="i-target" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/></symbol>
<symbol id="i-mask" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6c5-2 11-2 16 0v5a8 8 0 0 1-16 0z"/><path d="M8 11h2M14 11h2M9 15c2 1.5 4 1.5 6 0"/></symbol>
<symbol id="i-headphones" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18v-6a9 9 0 0 1 18 0v6"/><rect x="3" y="15" width="4" height="6" rx="1.5"/><rect x="17" y="15" width="4" height="6" rx="1.5"/></symbol>
<symbol id="i-list" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6h12M9 12h12M9 18h12M4 6h.01M4 12h.01M4 18h.01"/></symbol>
<symbol id="i-repeat" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 2l4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3"/></symbol>
<symbol id="i-globe" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></symbol>
<symbol id="i-chat" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1.1-4.4A8 8 0 1 1 21 12z"/></symbol>
<symbol id="i-shield" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 4 6v6c0 5 3.4 8.3 8 9 4.6-.7 8-4 8-9V6z"/><path d="m9 12 2 2 4-4"/></symbol>
<symbol id="i-chart" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></symbol>
<symbol id="i-clock" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></symbol>
<symbol id="i-users" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="3.5"/><path d="M2 20c.8-3.5 3.6-5.5 7-5.5s6.2 2 7 5.5M16 4.5a3.5 3.5 0 0 1 0 7M18 14.8c2 .7 3.4 2.6 4 5.2"/></symbol>
</defs></svg>"""

FONTS = ("https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800"
         "&family=Figtree:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap")


def asset_v(name: str) -> str:
    """Short content fingerprint, so browsers fetch a fresh copy whenever the file changes."""
    return hashlib.sha1((SRC / "assets" / name).read_bytes()).hexdigest()[:10]


def parse(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"\s*<!--(.*?)-->", text, re.S)
    meta = {}
    if m:
        for line in m.group(1).strip().splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
        text = text[m.end():]
    return meta, expand(text.strip())


def expand(text: str, seen: tuple = ()) -> str:
    """Replace <!-- @include name --> with src/partials/name.html, so pages share sections."""
    def sub(m):
        name = m.group(1)
        if name in seen:
            raise ValueError(f"include loop: {name}")
        return expand((SRC / "partials" / f"{name}.html").read_text(encoding="utf-8").strip(), seen + (name,))
    return re.sub(r"<!--\s*@include\s+([\w-]+)\s*-->", sub, text)


def url_for(rel: Path) -> str:
    parts = list(rel.with_suffix("").parts)
    if parts == ["index"]:
        return "/"
    if parts == ["404"]:
        return "/404.html"
    return "/" + "/".join(parts) + "/"


def wordmark() -> str:
    """UnboxEd with the tagline set underneath; 'Ed' picks up the accent colour."""
    return (f'<span class="wm"><b>Unbox<em>Ed</em></b><small>{TAGLINE}</small></span>')


def header(active: str) -> str:
    links = "".join(f'<a href="{href}"{" aria-current=\"page\"" if key == active else ""}>{label}</a>' for key, label, href in NAV)
    links += (f'<a class="m-cta" href="{DEMO[1]}">{DEMO[0]}</a><a class="m-cta" href="{LOGIN[1]}">{LOGIN[0]}</a>'
              f'<a class="m-cta" href="{CTA[1]}">{CTA[0]} →</a>')
    return f"""<header class="nav">
  <div class="wrap">
    <a class="brand" href="/" aria-label="{BRAND} home"><svg width="40" height="40" aria-hidden="true"><use href="#logo"/></svg>{wordmark()}</a>
    <nav class="nav-links" aria-label="Main">{links}</nav>
    <div class="nav-cta"><a class="nav-login" href="{LOGIN[1]}"{" aria-current=\"page\"" if active == "login" else ""}>{LOGIN[0]}</a><a class="btn btn-ghost btn-sm" href="{DEMO[1]}">{DEMO[0]}</a><a class="btn btn-primary btn-sm" href="{CTA[1]}">{CTA[0]}</a></div>
    <button class="menu-btn" type="button" aria-expanded="false" aria-label="Open menu">Menu</button>
  </div>
</header>"""


def footer() -> str:
    cols = "".join(f'<div><h4>{t}</h4><ul>{"".join(f"<li><a href=\"{h}\">{l}</a></li>" for l, h in items)}</ul></div>'
                   for t, items in FOOTER)
    return f"""<footer class="site">
  <div class="wrap">
    <div class="cols">
      <div><a class="brand" href="/" aria-label="{BRAND} home"><svg width="44" height="44" aria-hidden="true"><use href="#logo"/></svg>{wordmark()}</a>
        <p>Turn what people know into experiences other people can understand.</p>
        <p class="f-contact"><a href="mailto:{EMAIL}">{EMAIL}</a><a href="tel:{PHONE_TEL}">{PHONE}</a></p></div>
      {cols}
    </div>
    <div class="base"><span>© {date.today().year} {BRAND}</span><span>unboxlearning.in</span></div>
  </div>
</footer>"""


def page(meta: dict, body: str, url: str) -> str:
    title = meta.get("title", BRAND)
    full_title = title if title.startswith(BRAND) else f"{title} · {BRAND}"
    desc = meta.get("description", "")
    canonical = SITE + (url if url != "/404.html" else "/")
    robots = '<meta name="robots" content="noindex">' if url == "/404.html" else ""
    ld = ""
    if url == "/":
        ld = ('<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization",'
              f'"name":"{BRAND}","url":"{SITE}","logo":"{SITE}/assets/logo.svg","email":"{EMAIL}","telephone":"{PHONE_TEL}"}}</script>')
    return f"""<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{escape(full_title)}</title>
<meta name="description" content="{escape(desc)}">
<link rel="canonical" href="{canonical}">
{robots}
<meta property="og:type" content="website">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:title" content="{escape(full_title)}">
<meta property="og:description" content="{escape(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{SITE}/assets/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#1B164B">
<link rel="icon" href="/assets/logo.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="/assets/site.css?v={asset_v("site.css")}">
{ld}
</head>
<body>
{SPRITES}
{header(meta.get("nav", ""))}
<main id="top">
{body}
</main>
{footer()}
<script src="/assets/site.js?v={asset_v("site.js")}" defer></script>
</body>
</html>
"""


def build() -> list[str]:
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC / "assets", OUT / "assets")
    urls = []
    for f in sorted((SRC / "pages").rglob("*.html")):
        rel = f.relative_to(SRC / "pages")
        meta, body = parse(f)
        url = url_for(rel)
        dest = OUT / "404.html" if url == "/404.html" else OUT / url.strip("/") / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(page(meta, body, url), encoding="utf-8")
        if url != "/404.html":
            urls.append(url)
    today = date.today().isoformat()
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n",
        encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    for extra in ("vercel.json", "CNAME", "_redirects", "_headers"):
        if (SRC / extra).exists():
            shutil.copy(SRC / extra, OUT / extra)
    return urls


def check() -> int:
    """Every internal href/src must resolve to a built file, and every #anchor to an id on that page."""
    bad = 0
    for f in OUT.rglob("*.html"):
        html = f.read_text(encoding="utf-8")
        ids = set(re.findall(r'\sid="([^"]+)"', html))
        for ref in re.findall(r'(?:href|src)="([^"]+)"', html):
            if ref.startswith(("http", "mailto:", "tel:", "data:")):
                continue
            path, _, frag = ref.partition("#")
            path = path.split("?")[0]
            if not path:
                if frag and frag not in ids:
                    print(f"  {f.relative_to(OUT)}: missing anchor #{frag}")
                    bad += 1
                continue
            target = OUT / path.lstrip("/")
            if path.endswith("/"):
                target = target / "index.html"
            if not target.exists():
                print(f"  {f.relative_to(OUT)}: broken link {ref}")
                bad += 1
            elif frag:
                tids = set(re.findall(r'\sid="([^"]+)"', target.read_text(encoding="utf-8")))
                if frag not in tids:
                    print(f"  {f.relative_to(OUT)}: missing anchor {ref}")
                    bad += 1
    return bad


if __name__ == "__main__":
    pages = build()
    print(f"Built {len(pages)} pages + 404 into {OUT}")
    if "--check" in sys.argv:
        n = check()
        print("All links OK" if not n else f"{n} broken links")
        sys.exit(1 if n else 0)
