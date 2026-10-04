"""Round 3 of UnboxEd logo concepts (21-30): layers, steps, bridges, portals, dialogue.

Run: python make_concepts_3.py   ->  concepts/21-*.svg ... and logo-concepts-3.html
"""
from pathlib import Path

from make_concepts_2 import (AQUA, CORAL, LILAC, NAVY, PALE, PALE2, PLUM, SUN, VIOLET, WHITE, cube, faces, pts, star, svg)

HERE = Path(__file__).parent
OUT = HERE / "concepts"


def slab(cx, ty, w, h, top, left, right, op=1):
    """An isometric slab: a flat box whose top rhombus starts at y=ty."""
    hh = w * 0.577
    t = [(cx, ty), (cx + w, ty + hh), (cx, ty + 2 * hh), (cx - w, ty + hh)]
    lf = [(cx - w, ty + hh), (cx, ty + 2 * hh), (cx, ty + 2 * hh + h), (cx - w, ty + hh + h)]
    rf = [(cx, ty + 2 * hh), (cx + w, ty + hh), (cx + w, ty + hh + h), (cx, ty + 2 * hh + h)]
    o = f' fill-opacity="{op}"' if op < 1 else ""
    return (f'<polygon points="{pts(lf)}" fill="{left}"{o}/><polygon points="{pts(rf)}" fill="{right}"{o}/>'
            f'<polygon points="{pts(t)}" fill="{top}"{o}/>')


# 21. Layered Mastery: translucent layers that stack into one finished cube
def layered(dark=False):
    out = ""
    layers = [(VIOLET, "#3A25A6", "#2E1F86"), (AQUA, "#5EA9B3", "#43909A"), (CORAL, "#C94E37", "#A93D29"), (SUN, "#D9A300", "#B98A00")]
    for k, (t, l, r) in enumerate(layers):
        out += slab(32, 33 - k * 8.5, 21, 7.5, t, l, r, op=.82)
    return svg(out)


# 22. Level-Up Cube: a cube built from ascending, narrowing layers, topped by a spark
def level_up(base):
    out = (slab(32, 30, 22, 8, VIOLET, base, PLUM if base == NAVY else PALE2)
           + slab(32, 22, 15, 8, AQUA, "#5EA9B3", "#43909A")
           + slab(32, 15, 8.5, 8, SUN, "#D9A300", "#B98A00"))
    return svg(out + star(32, 7, 6, CORAL))


# 23. Staircase U: one arm solid, the other climbing in steps to a spark
def staircase_u(ink):
    # a solid U whose right arm climbs outward in three coloured steps, ending in a spark
    u = (f'<path d="M6 14h12v30h20v14H10a4 4 0 0 1-4-4z" fill="{ink}"/>')
    steps = (f'<path d="M38 44V36h12v22H38z" fill="{AQUA}"/>'
             f'<rect x="38" y="44" width="12" height="14" fill="{AQUA}"/>'
             f'<path d="M42 36V25h12v11z" fill="{CORAL}"/>'
             f'<path d="M46 25V14h12v11z" fill="{SUN}"/>')
    return svg(u + steps + star(52, 6.5, 5.5, SUN))


# 24. Concept Ladder: a ladder climbing out of a document
def ladder(paper):
    page = (f'<path d="M6 30a4 4 0 0 1 4-4h18l8 8v24a4 4 0 0 1-4 4H10a4 4 0 0 1-4-4z" fill="{paper}"/>'
            f'<path d="M28 26l8 8h-6a2 2 0 0 1-2-2z" fill="{CORAL}"/>'
            f'<rect x="11" y="42" width="15" height="3" rx="1.5" fill="{AQUA}"/><rect x="11" y="49" width="10" height="3" rx="1.5" fill="{AQUA}"/>')
    rails = (f'<line x1="22" y1="36" x2="44" y2="6" stroke="{SUN}" stroke-width="3.4" stroke-linecap="round"/>'
             f'<line x1="31" y1="40" x2="53" y2="10" stroke="{SUN}" stroke-width="3.4" stroke-linecap="round"/>')
    rungs = "".join(f'<line x1="{22 + 22 * t:.1f}" y1="{36 - 30 * t:.1f}" x2="{31 + 22 * t:.1f}" y2="{40 - 30 * t:.1f}" stroke="{SUN}" stroke-width="3" stroke-linecap="round"/>'
                    for t in (.2, .45, .7, .95))
    return svg(page + rails + rungs + star(56, 5, 4.5, CORAL))


# 25. Learning Bridge: knowledge on one side, a learner on the other, joined through the box
def learning_bridge(ink):
    book = f'<rect x="2" y="38" width="13" height="17" rx="2.5" fill="{AQUA}"/><rect x="5" y="42" width="7" height="2" rx="1" fill="{WHITE}"/><rect x="5" y="46.5" width="5" height="2" rx="1" fill="{WHITE}"/>'
    learner = f'<circle cx="55" cy="36" r="4.6" fill="{CORAL}"/><path d="M47.5 55a7.5 8 0 0 1 15 0z" fill="{CORAL}"/>'
    arc = f'<path d="M9 37 Q32 2 55 29" fill="none" stroke="{SUN}" stroke-width="4" stroke-linecap="round"/>'
    deck = f'<line x1="2" y1="58" x2="62" y2="58" stroke="{ink}" stroke-width="2.4" stroke-linecap="round" opacity=".35"/>'
    box = faces(cube(32, 22, 8.5), VIOLET, ink, PLUM if ink == NAVY else PALE2)
    return svg(deck + arc + book + learner + box)


# 26. Bridge U: an arch-shaped U spanning from knowledge to learner
def bridge_u(ink):
    arch = f'<path d="M8 56V30a24 24 0 0 1 48 0v26h-11V30a13 13 0 0 0-26 0v26z" fill="{ink}"/>'
    deck = f'<line x1="2" y1="56" x2="62" y2="56" stroke="{SUN}" stroke-width="4" stroke-linecap="round"/>'
    ends = f'<circle cx="4" cy="48" r="3.6" fill="{AQUA}"/><circle cx="60" cy="48" r="3.6" fill="{CORAL}"/>'
    traveller = star(32, 38, 5, SUN)
    return svg(arch + deck + ends + traveller)


# 27. Knowledge Gateway: a doorway built from three boxes, light inside
def gateway(ink, ink2):
    glow = f'<circle cx="32" cy="40" r="10" fill="{SUN}" opacity=".3"/><circle cx="32" cy="40" r="5.5" fill="{SUN}"/>'
    left = slab(14, 22, 8, 32, VIOLET, ink, ink2)
    right = slab(50, 22, 8, 32, VIOLET, ink, ink2)
    beam = slab(32, 8, 26, 8, CORAL, "#C94E37", "#A93D29")
    return svg(glow + left + right + beam)


# 28. The Portal Spark: a portal with a spark flying out, leaving a trail
def portal_spark(rim, inside):
    portal = (f'<path d="M8 58V30a18 18 0 0 1 36 0v28z" fill="{inside}"/>'
              f'<path d="M8 58V30a18 18 0 0 1 36 0v28" fill="none" stroke="{rim}" stroke-width="5" stroke-linejoin="round"/>')
    trail = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{SUN}" opacity="{o}"/>' for x, y, r, o in ((26, 40, 1.6, .45), (33, 33, 2, .65), (40, 26, 2.4, .85)))
    return svg(portal + trail + star(51, 15, 9, SUN))


# 29. Open Portal U: a U-shaped gateway with a concept floating inside
def open_portal_u(ink):
    u = f'<path d="M8 8h12v30a12 12 0 0 0 24 0V8h12v30a24 24 0 0 1-48 0z" fill="{ink}"/>'
    shadow = f'<ellipse cx="32" cy="45" rx="6" ry="1.8" fill="{SUN}" opacity=".35"/>'
    concept = faces(cube(32, 28, 8), SUN, "#D9A300", "#B98A00")
    sparks = f'<circle cx="23" cy="16" r="1.8" fill="{CORAL}"/><circle cx="42" cy="13" r="1.5" fill="{AQUA}"/>'
    return svg(u + shadow + concept + sparks)


# 30. Dialogue Box: the box itself becomes a speech bubble
def dialogue_box(lf, rf):
    c = cube(32, 31, 24)
    ll, b = c["left"][3], c["left"][2]
    tail = f'<polygon points="{pts([ll, (ll[0] + 9, ll[1] + 5), (ll[0] - 4, ll[1] + 14)])}" fill="{lf}"/>'
    body = faces(c, SUN, lf, rf)
    ul, cc = c["left"][0], c["left"][1]
    dots = ""
    for u in (.28, .5, .72):
        x = ul[0] + u * (cc[0] - ul[0]); y = ul[1] + u * (cc[1] - ul[1]) + 12
        dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{WHITE}"/>'
    return svg(tail + body + dots)


CONCEPTS = [
    ("21-layered-mastery", "Layered Mastery", "Translucent layers stacking into one finished cube: understanding built layer by layer.",
     ["Each layer a colour, together one solid shape", "Calm, modern and premium", "Translucency looks great on screen; flatten it for print"], layered(), layered(True)),
    ("22-level-up-cube", "Level-Up Cube", "A cube built from ascending, narrowing layers, topped with a spark.",
     ["Says 'levelling up' at a glance", "Pairs naturally with XP and streaks in the app", "Strong silhouette at small sizes"], level_up(NAVY), level_up(PALE)),
    ("23-staircase-u", "Staircase U", "A U whose right arm climbs in coloured steps to a spark: progressive learning.",
     ["Monogram and meaning in one: U for Unbox, steps for progress", "Very legible at 16 px", "Bold and confident"], staircase_u(NAVY), staircase_u(WHITE)),
    ("24-concept-ladder", "Concept Ladder", "A ladder climbing out of a document: from what's written to what's understood.",
     ["Clear story: the source becomes a way up", "The rungs feel like steps of a lesson", "More of an illustration than a monogram"], ladder(NAVY), ladder(WHITE)),
    ("25-learning-bridge", "Learning Bridge", "Knowledge on one side, the learner on the other, joined by a bridge that runs through the box.",
     ["Puts Unbox in the role of connector", "Human: the learner is in the picture", "Best wide; detailed for an app icon"], learning_bridge(NAVY), learning_bridge(WHITE)),
    ("26-bridge-u", "Bridge U", "The U turned into an arch bridge, a spark crossing beneath from knowledge to learner.",
     ["U for Unbox, arch for connection", "Architectural and trustworthy", "Simple enough for an app icon"], bridge_u(NAVY), bridge_u(WHITE)),
    ("27-knowledge-gateway", "Knowledge Gateway", "A minimal doorway built from three boxes, light glowing inside.",
     ["Box geometry, read as a gate", "Inviting: step through into knowledge", "Calm, suits institutions and NGOs"], gateway(NAVY, PLUM), gateway(PALE, PALE2)),
    ("28-portal-spark", "The Portal Spark", "A portal with a spark flying out of it, leaving a trail.",
     ["Movement and magic: the 'aha' leaving the portal", "Simple, iconic shapes", "The trail can animate on the site"], portal_spark(VIOLET, NAVY), portal_spark(LILAC, "#0E0B2E")),
    ("29-open-portal-u", "Open Portal U", "A U-shaped gateway with a small cube of knowledge floating inside.",
     ["U for Unbox, with the idea held inside it", "The floating cube links back to the box", "Clean at every size"], open_portal_u(NAVY), open_portal_u(WHITE)),
    ("30-dialogue-box", "Dialogue Box", "The box itself has become a speech bubble, with dots on its face.",
     ["Puts the tutor and conversation first", "Box and chat in one silhouette", "Distinctive among edtech logos"], dialogue_box(VIOLET, NAVY), dialogue_box(VIOLET, PALE2)),
]


def board():
    css = (HERE / "logo-concepts.html").read_text(encoding="utf-8")
    style = css[css.index("<style>"):css.index("</style>") + 8]
    head = css[:css.index("<style>")].replace("<title>UnboxEd logo concepts</title>", "<title>UnboxEd logo concepts, round 3</title>")
    extra = ("<style>.overview{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:0 0 28px}"
             ".overview figure{margin:0;background:#fff;border:2px solid var(--line);border-radius:18px;padding:16px 10px 10px;text-align:center}"
             ".overview img{width:84px;height:84px}.overview figcaption{font:600 13px Figtree,system-ui;margin-top:6px}"
             "@media(max-width:820px){.overview{grid-template-columns:repeat(2,minmax(0,1fr))}}</style>")
    overview = "".join(f'<figure><img src="concepts/{slug}.svg" alt=""><figcaption>{i}. {name}</figcaption></figure>'
                       for i, (slug, name, *_r) in enumerate(CONCEPTS, 21))
    sections = ""
    for i, (slug, name, idea, bullets, _, _) in enumerate(CONCEPTS, 21):
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
            "  <h1>UnboxEd: logo concepts, round 3</h1>\n"
            "  <p class=\"intro\">Ten more sample logos from your list: layers, steps, bridges, portals and dialogue. All ten side by side first; "
            "below, each on light and dark, with the wordmark, at favicon sizes and as an app icon.</p>\n"
            f"  <div class=\"overview\">{overview}</div>{sections}\n</div>\n</body>\n</html>\n")


if __name__ == "__main__":
    for slug, _, _, _, light, dark in CONCEPTS:
        (OUT / f"{slug}.svg").write_text(light, encoding="utf-8")
        (OUT / f"{slug}-dark.svg").write_text(dark, encoding="utf-8")
    (HERE / "logo-concepts-3.html").write_text(board(), encoding="utf-8")
    print(f"{len(CONCEPTS)} concepts written")
