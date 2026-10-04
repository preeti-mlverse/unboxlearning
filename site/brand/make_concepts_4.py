"""Round 4 of UnboxEd logo concepts (31-41): networks, learning modes, compasses and paths.

Run: python make_concepts_4.py   ->  concepts/31-*.svg ... and logo-concepts-4.html
"""
import math
from pathlib import Path

from make_concepts_2 import AQUA, CORAL, LILAC, NAVY, PALE, PLUM, SUN, VIOLET, WHITE, pts, star, svg

HERE = Path(__file__).parent
OUT = HERE / "concepts"
PINK = "#FF8FAB"
MODES = [SUN, CORAL, AQUA, VIOLET, LILAC, PINK]


def node(x, y, r, col, ring=None):
    s = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{col}"/>'
    return s + (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r + 3}" fill="none" stroke="{ring}" stroke-width="1.6" opacity=".5"/>' if ring else "")


def line(a, b, col, w=2.4, dash=None, op=1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{col}" stroke-width="{w}" stroke-linecap="round"{d} opacity="{op}"/>'


def glyph(kind, x, y, ink=WHITE):
    """Tiny learning-mode glyphs, centred on (x, y)."""
    if kind == "read":
        return f'<rect x="{x - 3.5}" y="{y - 3}" width="7" height="1.6" rx=".8" fill="{ink}"/><rect x="{x - 3.5}" y="{y - .3}" width="7" height="1.6" rx=".8" fill="{ink}"/><rect x="{x - 3.5}" y="{y + 2.4}" width="4.5" height="1.6" rx=".8" fill="{ink}"/>'
    if kind == "hear":
        return f'<rect x="{x - 4}" y="{y - 1.5}" width="1.8" height="3" rx=".9" fill="{ink}"/><rect x="{x - .9}" y="{y - 4}" width="1.8" height="8" rx=".9" fill="{ink}"/><rect x="{x + 2.2}" y="{y - 2.5}" width="1.8" height="5" rx=".9" fill="{ink}"/>'
    if kind == "see":
        return f'<ellipse cx="{x}" cy="{y}" rx="4.4" ry="2.7" fill="none" stroke="{ink}" stroke-width="1.4"/><circle cx="{x}" cy="{y}" r="1.3" fill="{ink}"/>'
    if kind == "ask":
        return f'<rect x="{x - 4}" y="{y - 3.2}" width="8" height="5.4" rx="2" fill="{ink}"/><polygon points="{x - 2},{y + 2} {x + .5},{y + 2} {x - 2.2},{y + 4.2}" fill="{ink}"/>'
    if kind == "try":
        return f'<path d="M{x - 3} {y - 4}l6 3.4-2.6.8 1.4 2.6-1.3.7-1.4-2.6-2 1.9z" fill="{ink}"/>'
    if kind == "remember":
        return f'<path d="M{x + 3} {y}a3 3 0 1 1-.9-2.1" fill="none" stroke="{ink}" stroke-width="1.4" stroke-linecap="round"/><path d="M{x + 2.4} {y - 3.6}l-.3 1.9 1.9.2" fill="none" stroke="{ink}" stroke-width="1.2" stroke-linecap="round"/>'
    return ""


# 31. Neural Box: a minimal network inside an open geometric shell
def neural_box(ink):
    s = f'fill="none" stroke="{ink}" stroke-width="3.2" stroke-linejoin="round" stroke-linecap="round"'
    shell = (f'<path d="M12 31L32 41L52 31M12 31V47L32 57L52 47V31M32 41V57" {s}/>'
             f'<path d="M12 31L5 23M52 31L59 23" {s}/>')
    n = {"a": (21, 44), "b": (32, 33), "c": (43, 44), "d": (32, 50), "up": (32, 13)}
    net = (line(n["a"], n["b"], VIOLET) + line(n["b"], n["c"], VIOLET) + line(n["a"], n["d"], VIOLET) + line(n["c"], n["d"], VIOLET)
           + line(n["b"], n["up"], SUN, 2.4, "2 3"))
    nodes = node(*n["a"], 3.2, AQUA) + node(*n["c"], 3.2, CORAL) + node(*n["d"], 3, LILAC) + node(*n["b"], 3.6, VIOLET) + node(*n["up"], 4.6, SUN, ring=SUN)
    return svg(shell + net + nodes)


# 32. Learning Network U: connected nodes forming a U, the last one lit
def network_u(ink):
    p = [(14, 10), (13, 25), (16, 39), (24, 49), (36, 51), (46, 43), (50, 29), (51, 14)]
    links = "".join(line(p[k], p[k + 1], ink, 2.6) for k in range(len(p) - 1)) + line(p[1], p[3], ink, 1.4, op=.35) + line(p[4], p[6], ink, 1.4, op=.35)
    cols = [AQUA, VIOLET, AQUA, CORAL, VIOLET, CORAL, AQUA]
    dots = "".join(node(x, y, 3.6, cols[k]) for k, (x, y) in enumerate(p[:-1]))
    return svg(links + dots + node(*p[-1], 5, SUN, ring=SUN))


# 33. Knowledge Web: one central node branching into many modes, with smaller ideas beyond
def knowledge_web(ink):
    c = (32, 33)
    out, ends = "", []
    for k, col in enumerate(MODES[:5]):
        a = -math.pi / 2 + 2 * math.pi * k / 5
        e = (c[0] + 20 * math.cos(a), c[1] + 20 * math.sin(a))
        f = (c[0] + 28 * math.cos(a + .35), c[1] + 28 * math.sin(a + .35))
        out += line(c, e, col, 2.8) + line(e, f, col, 1.6, op=.6)
        ends.append((e, f, col))
    for e, f, col in ends:
        out += node(*e, 4.6, col) + node(*f, 2, col)
    return svg(out + node(*c, 7.5, ink) + node(*c, 2.8, SUN))


# 34. Hub & Modes: a central concept joined to read, hear, see, ask, try
def hub_modes(ink):
    c = (32, 33)
    kinds = ["read", "hear", "see", "ask", "try"]
    out, nodes = "", ""
    for k, kind in enumerate(kinds):
        a = -math.pi / 2 + 2 * math.pi * k / 5
        p = (c[0] + 21 * math.cos(a), c[1] + 21 * math.sin(a))
        out += line(c, p, ink, 2.2, op=.5)
        nodes += node(*p, 8, MODES[k]) + glyph(kind, *p)
    return svg(out + nodes + node(*c, 6.5, ink) + node(*c, 2.6, SUN))


# 35. Six-Sided Learning: six cells around a centre, honeycomb style
def hexagon(cx, cy, r, col):
    return f'<polygon points="{pts([(cx + r * math.cos(math.radians(60 * k - 90)), cy + r * math.sin(math.radians(60 * k - 90))) for k in range(6)])}" fill="{col}" stroke="{col}" stroke-width="1.2" stroke-linejoin="round"/>'


def six_sided(center):
    r, d = 8.6, 16.6
    out = hexagon(32, 32, r, center)
    for k, col in enumerate(MODES):
        a = math.radians(60 * k)
        out += hexagon(32 + d * math.cos(a), 32 + d * math.sin(a), r, col)
    return svg(out + node(32, 32, 2.6, SUN if center != SUN else NAVY))


# 36. Multi-Modal Star: six coloured points, one for each way to learn
def multimodal_star(center):
    petal = [(32, 31), (27.6, 20), (32, 3.5), (36.4, 20)]
    out = "".join(f'<polygon points="{pts(petal)}" fill="{col}" stroke="{col}" stroke-width="1.6" stroke-linejoin="round" transform="rotate({60 * k} 32 32)"/>'
                  for k, col in enumerate(MODES))
    return svg(out + node(32, 32, 5.4, center))


# 37. The Learning Compass: many directions, one goal
def compass(ink, ring_col):
    ring = f'<circle cx="32" cy="34" r="23" fill="none" stroke="{ring_col}" stroke-width="3.4"/>'
    ticks = "".join(line((32 + 19 * math.cos(math.radians(a)), 34 + 19 * math.sin(math.radians(a))),
                         (32 + 21.5 * math.cos(math.radians(a)), 34 + 21.5 * math.sin(math.radians(a))), ring_col, 1.6, op=.6)
                    for a in range(0, 360, 45))
    needle = (f'<polygon points="32,12 36,34 32,38 28,34" fill="{SUN}"/><polygon points="32,56 36,34 32,30 28,34" fill="{CORAL}"/>'
              f'<polygon points="12,34 32,31 34,34 32,37" fill="{AQUA}" opacity=".9"/><polygon points="52,34 32,31 30,34 32,37" fill="{LILAC}" opacity=".9"/>')
    goal = star(32, 5, 4.6, SUN)
    return svg(ring + ticks + needle + node(32, 34, 3.4, ink) + goal)


# 38. Adaptive Compass: a path that changes direction around a central learner
def adaptive_compass(ink):
    learner = f'<circle cx="29" cy="37" r="6.5" fill="{CORAL}"/><circle cx="29" cy="37" r="10.5" fill="none" stroke="{CORAL}" stroke-width="1.4" opacity=".35"/>'
    path = (f'<path d="M14 52 A17 17 0 1 1 45 41 L53 15" fill="none" stroke="{ink}" stroke-width="4" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')
    arrow = f'<path d="M46.5 18.5 L53.5 12.5 L57 21" fill="none" stroke="{ink}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
    marks = node(14, 52, 3.6, AQUA) + node(12.4, 30, 2.6, SUN) + node(35, 20.6, 2.6, VIOLET)
    return svg(learner + path + arrow + marks)


# 39. Choose Your Path: a branching path compressed into an icon
def choose_path(ink):
    trunk = f'<path d="M32 60V40" stroke="{ink}" stroke-width="5" stroke-linecap="round"/>'
    left = f'<path d="M32 42C32 32, 16 32, 14 20" fill="none" stroke="{AQUA}" stroke-width="5" stroke-linecap="round"/>'
    right = f'<path d="M32 42C32 32, 48 32, 50 22" fill="none" stroke="{CORAL}" stroke-width="5" stroke-linecap="round"/>'
    mid = f'<path d="M32 42V14" fill="none" stroke="{SUN}" stroke-width="5" stroke-linecap="round"/>'
    ends = node(14, 17, 4.6, AQUA) + node(50, 19, 4.6, CORAL)
    return svg(trunk + left + right + mid + ends + star(32, 8, 7, SUN))


# 40. Dynamic Route: one path splits, reconnects and climbs
def dynamic_route(ink):
    base = f'<path d="M32 60V46" stroke="{ink}" stroke-width="5" stroke-linecap="round"/>'
    left = f'<path d="M32 46C18 44, 16 30, 32 24" fill="none" stroke="{AQUA}" stroke-width="5" stroke-linecap="round"/>'
    right = f'<path d="M32 46C46 44, 48 30, 32 24" fill="none" stroke="{CORAL}" stroke-width="5" stroke-linecap="round"/>'
    up = f'<path d="M32 24V12" stroke="{SUN}" stroke-width="5" stroke-linecap="round"/><path d="M25 16l7-8 7 8" fill="none" stroke="{SUN}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
    joins = node(32, 46, 3.4, ink) + node(32, 24, 3.4, ink)
    return svg(base + left + right + up + joins)


# 41. Personal Path Pictogram: different curves reaching the same destination
def personal_paths(ink):
    goal = (50, 13)
    curves = (f'<path d="M6 56C14 44, 40 46, 50 13" fill="none" stroke="{AQUA}" stroke-width="3.6" stroke-linecap="round"/>'
              f'<path d="M20 60C36 52, 30 30, 50 13" fill="none" stroke="{CORAL}" stroke-width="3.6" stroke-linecap="round"/>'
              f'<path d="M4 34C22 18, 30 34, 50 13" fill="none" stroke="{VIOLET if ink == NAVY else LILAC}" stroke-width="3.6" stroke-linecap="round"/>')
    starts = node(6, 56, 3, AQUA) + node(20, 60, 3, CORAL) + node(4, 34, 3, VIOLET if ink == NAVY else LILAC)
    dest = f'<circle cx="{goal[0]}" cy="{goal[1]}" r="10" fill="{SUN}" opacity=".25"/>' + node(*goal, 6, ink) + node(*goal, 2.4, SUN)
    return svg(curves + starts + dest)


CONCEPTS = [
    ("31-neural-box", "Neural Box", "A minimal network inside an open box, one node rising out as a new idea.",
     ["Links 'unbox' with AI and connected knowledge", "Clean line style, calm and technical", "Lines get thin at 16 px"], neural_box(NAVY), neural_box(WHITE)),
    ("32-network-u", "Learning Network U", "Connected nodes tracing a U; the last node lights up.",
     ["Monogram made of connections", "Suggests an AI-powered journey", "Works as a progress animation: nodes lighting in turn"], network_u(NAVY), network_u(WHITE)),
    ("33-knowledge-web", "Knowledge Web", "One central node branching into five learning modes, each sprouting a smaller idea.",
     ["Organic and alive", "One source, many directions", "Reads as a burst at small sizes"], knowledge_web(NAVY), knowledge_web(WHITE)),
    ("34-hub-modes", "Hub & Modes", "A central concept joined to five nodes: read, hear, see, ask, try.",
     ["Spells out the five ways in, with tiny icons", "Great as a feature diagram on the website", "Icons vanish at 16 px; use plain dots there"], hub_modes(NAVY), hub_modes(WHITE)),
    ("35-six-sided", "Six-Sided Learning", "Six cells around a centre, honeycomb style, each a learning mode.",
     ["Hexagons echo the site's hex background", "Colourful but orderly", "Strong, compact silhouette"], six_sided(NAVY), six_sided(WHITE)),
    ("36-multimodal-star", "Multi-Modal Star", "A six-point star: read, hear, see, ask, try, remember.",
     ["Abstract, bright and memorable", "Clear at every size", "Close in spirit to Spark Box (1), with six modes instead of four"], multimodal_star(NAVY), multimodal_star(WHITE)),
    ("37-learning-compass", "The Learning Compass", "Many directions, one goal: a compass needle pointing to the spark.",
     ["Guidance and personal direction", "Classic, trustworthy shape", "Compasses are common in other brands"], compass(NAVY, NAVY), compass(WHITE, WHITE)),
    ("38-adaptive-compass", "Adaptive Compass", "A path that bends around the learner and then heads out and up.",
     ["Says 'the journey adapts to you'", "Dynamic and personal", "Needs a clean redraw to work small"], adaptive_compass(NAVY), adaptive_compass(WHITE)),
    ("39-choose-path", "Choose Your Path", "One trunk branching three ways; the middle path reaches the spark.",
     ["Choice and personalisation in one glance", "Very legible as an icon", "Also reads a little like a tree or plant"], choose_path(NAVY), choose_path(WHITE)),
    ("40-dynamic-route", "Dynamic Route", "One path splits into two, reconnects, and climbs upward.",
     ["Different routes, same progress", "Symmetrical and bold", "Arrow makes 'progress' unmistakable"], dynamic_route(NAVY), dynamic_route(WHITE)),
    ("41-personal-paths", "Personal Path Pictogram", "Three different curves from three starting points, all reaching the same destination.",
     ["Everyone learns differently, everyone gets there", "Inclusive message for schools and NGOs", "Works well wide; busy as an app icon"], personal_paths(NAVY), personal_paths(WHITE)),
]


def board(start=31):
    css = (HERE / "logo-concepts.html").read_text(encoding="utf-8")
    style = css[css.index("<style>"):css.index("</style>") + 8]
    head = css[:css.index("<style>")].replace("<title>UnboxEd logo concepts</title>", "<title>UnboxEd logo concepts, round 4</title>")
    extra = ("<style>.overview{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:0 0 28px}"
             ".overview figure{margin:0;background:#fff;border:2px solid var(--line);border-radius:18px;padding:16px 10px 10px;text-align:center}"
             ".overview img{width:84px;height:84px}.overview figcaption{font:600 13px Figtree,system-ui;margin-top:6px}"
             "@media(max-width:820px){.overview{grid-template-columns:repeat(2,minmax(0,1fr))}}</style>")
    overview = "".join(f'<figure><img src="concepts/{slug}.svg" alt=""><figcaption>{i}. {name}</figcaption></figure>'
                       for i, (slug, name, *_r) in enumerate(CONCEPTS, start))
    sections = ""
    for i, (slug, name, idea, bullets, _, _) in enumerate(CONCEPTS, start):
        lis = "".join(f"<li>{b}</li>" for b in bullets)
        sections += f'''
  <section class="concept">
    <div class="meta"><div class="num">Concept {i}</div><h2>{name}</h2><p>{idea}</p><ul>{lis}</ul></div>
    <div class="uses">
      <div class="tile light"><small>On light</small><img class="big" src="concepts/{slug}.svg" alt="{name} mark"></div>
      <div class="tile dark"><small>On dark</small><img class="big" src="concepts/{slug}-dark.svg" alt=""></div>
      <div class="tile light"><small>Wordmark</small><div class="lockup"><img src="concepts/{slug}.svg" alt=""><span><b>unbox</b> <i>learning</i></span></div></div>
      <div class="tile dark"><small>Wordmark, dark</small><div class="lockup"><img src="concepts/{slug}-dark.svg" alt=""><span><b>unbox</b> <i>learning</i></span></div></div>
      <div class="tile light"><small>Favicon sizes</small><div class="row2"><div class="sizes"><img src="concepts/{slug}.svg" alt=""><img src="concepts/{slug}.svg" alt=""><img src="concepts/{slug}.svg" alt=""></div><div class="tab"><img src="concepts/{slug}.svg" alt="">UnboxEd</div></div></div>
      <div class="tile light"><small>App icon</small><div class="app"><img src="concepts/{slug}-dark.svg" alt=""></div></div>
    </div>
  </section>'''
    return (head + style + extra + "</head>\n<body>\n<div class=\"wrap\">\n"
            "  <h1>UnboxEd: logo concepts, round 4</h1>\n"
            "  <p class=\"intro\">Eleven sample logos from your list: networks, learning modes, compasses and paths. All eleven side by side first; "
            "below, each on light and dark, with the wordmark, at favicon sizes and as an app icon.</p>\n"
            f"  <div class=\"overview\">{overview}</div>{sections}\n</div>\n</body>\n</html>\n")


if __name__ == "__main__":
    for slug, _, _, _, light, dark in CONCEPTS:
        (OUT / f"{slug}.svg").write_text(light, encoding="utf-8")
        (OUT / f"{slug}-dark.svg").write_text(dark, encoding="utf-8")
    (HERE / "logo-concepts-4.html").write_text(board(), encoding="utf-8")
    print(f"{len(CONCEPTS)} concepts written")
