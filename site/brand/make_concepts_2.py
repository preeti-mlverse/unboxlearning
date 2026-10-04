"""Generate the second round of UnboxEd logo concepts (box ideas 11-20) and their review board.

Run: python make_concepts_2.py   ->  concepts/11-*.svg ... and logo-concepts-2.html
"""
import math
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "concepts"
NAVY, PLUM, SUN, CORAL, AQUA, VIOLET, LILAC, WHITE, PALE, PALE2 = (
    "#1B164B", "#29245F", "#F2B900", "#E65F45", "#7CC1CA", "#4B32C8", "#B9A8FF", "#FFFFFF", "#ECE9FC", "#C9C2F2")


def svg(body, defs=""):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">{defs}{body}</svg>\n'


def pts(ps):
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in ps)


def cube(cx, cy, e):
    """Isometric cube centred on its front vertical edge's top point. Returns the three visible faces."""
    w = e * 0.866
    top, ur, c, ul = (cx, cy - e), (cx + w, cy - e / 2), (cx, cy), (cx - w, cy - e / 2)
    ll, b, lr = (cx - w, cy + e / 2), (cx, cy + e), (cx + w, cy + e / 2)
    return {"top": [top, ur, c, ul], "left": [ul, c, b, ll], "right": [c, ur, lr, b]}


def faces(f, top, left, right, extra=""):
    return (f'<polygon points="{pts(f["top"])}" fill="{top}" {extra}/>'
            f'<polygon points="{pts(f["left"])}" fill="{left}" {extra}/>'
            f'<polygon points="{pts(f["right"])}" fill="{right}" {extra}/>')


def star(cx, cy, r, col, inner=0.28):
    p = []
    for k in range(8):
        a = math.pi / 4 * k - math.pi / 2
        rr = r if k % 2 == 0 else r * inner
        p.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return f'<polygon points="{pts(p)}" fill="{col}" stroke="{col}" stroke-width=".8" stroke-linejoin="round"/>'


# ---------------------------------------------------------------- 11. The Unfolding Box
def unfolding(base, glyph_ink):
    out = ""
    flap = [(20, 19.5), (44, 19.5), (49, 3.5), (15, 3.5)]
    for ang, col in ((0, SUN), (90, CORAL), (180, AQUA), (270, VIOLET)):
        out += f'<polygon points="{pts(flap)}" fill="{col}" stroke="{col}" stroke-width="2" stroke-linejoin="round" transform="rotate({ang} 32 32)"/>'
    out += f'<rect x="20" y="20" width="24" height="24" rx="4" fill="{base}"/>'
    g = glyph_ink
    # visual (eye) on top, voice (sound bars) right, memory (loop) bottom, interaction (pointer) left
    out += (f'<ellipse cx="32" cy="11.5" rx="6" ry="3.6" fill="none" stroke="{g}" stroke-width="1.8"/><circle cx="32" cy="11.5" r="1.7" fill="{g}"/>'
            f'<rect x="49" y="30" width="2.2" height="4" rx="1.1" fill="{g}"/><rect x="52.4" y="27" width="2.2" height="10" rx="1.1" fill="{g}"/><rect x="55.8" y="29" width="2.2" height="6" rx="1.1" fill="{g}"/>'
            f'<path d="M36 52.5a4 4 0 1 1-1.2-2.9" fill="none" stroke="{g}" stroke-width="1.8" stroke-linecap="round"/><path d="M35.8 47.2l-.6 2.9 2.9.4" fill="none" stroke="{g}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="M9 27.5l7.5 4.2-3.2 1 1.7 3.2-1.6.8-1.7-3.2-2.3 2.3z" fill="{g}"/>')
    out += f'<circle cx="32" cy="32" r="4" fill="{SUN}"/>'
    return svg(out)


# ---------------------------------------------------------------- 12. Knowledge Burst
def burst(lf, rf, tf):
    rays = ""
    cols = [SUN, CORAL, AQUA, LILAC, SUN, CORAL, AQUA, LILAC]
    for k in range(8):
        a = math.pi / 4 * k - math.pi / 2
        r1, r2 = 20, (28.5 if k % 2 == 0 else 25.5)
        x1, y1, x2, y2 = 32 + r1 * math.cos(a), 33 + r1 * math.sin(a), 32 + r2 * math.cos(a), 33 + r2 * math.sin(a)
        rays += f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{cols[k]}" stroke-width="3.6" stroke-linecap="round"/>'
        rays += f'<circle cx="{32 + (r2 + 3.4) * math.cos(a):.1f}" cy="{33 + (r2 + 3.4) * math.sin(a):.1f}" r="2" fill="{cols[k]}"/>' if k % 2 == 0 else ""
    c = cube(32, 33, 13.5)
    return svg(rays + faces(c, tf, lf, rf))


# ---------------------------------------------------------------- 13. Box -> Path
def box_path(lf, rf, inside):
    c = cube(18, 41, 15.5)
    body = faces(c, inside, lf, rf)
    path = (f'<path d="M18 33 C 18 20, 31 29, 35 20 S 45 9, 54 11" fill="none" stroke="{SUN}" stroke-width="5" stroke-linecap="round"/>'
            f'<path d="M18 33 C 18 20, 31 29, 35 20 S 45 9, 54 11" fill="none" stroke="{WHITE}" stroke-width="1.2" stroke-linecap="round" stroke-dasharray="1.5 3.5" opacity=".9"/>')
    goal = f'<circle cx="55" cy="11" r="5.5" fill="{CORAL}"/><circle cx="55" cy="11" r="2.2" fill="{WHITE}"/>'
    return svg(body + path + goal)


# ---------------------------------------------------------------- 14. The Learning Portal
def portal(tf, lf, rf):
    c = cube(34, 34, 25)
    ul, cc, b, ll = c["left"]

    def at(u, v):
        return (ul[0] + u * (cc[0] - ul[0]) + v * (ll[0] - ul[0]), ul[1] + u * (cc[1] - ul[1]) + v * (ll[1] - ul[1]))
    door = [at(.26, .32), at(.74, .32), at(.74, 1), at(.26, 1)]
    arch_top = at(.5, .2)
    d = (f'M{door[3][0]:.2f} {door[3][1]:.2f} L{door[0][0]:.2f} {door[0][1]:.2f} '
         f'Q{arch_top[0]:.2f} {arch_top[1] - 4:.2f} {door[1][0]:.2f} {door[1][1]:.2f} L{door[2][0]:.2f} {door[2][1]:.2f} Z')
    glow = f'<polygon points="{pts([door[3], door[2], (door[2][0] - 9, door[2][1] + 7), (door[3][0] - 13, door[3][1] + 5)])}" fill="{SUN}" opacity=".35"/>'
    spark = star(at(.5, .62)[0], at(.5, .62)[1], 4.2, WHITE)
    return svg(glow + faces(c, tf, lf, rf) + f'<path d="{d}" fill="{SUN}"/>' + spark)


# ---------------------------------------------------------------- 15. Inside Out
def inside_out(tf, lf, rf):
    big = faces(cube(19, 35, 15), tf, lf, rf)
    bits = ""
    for (cx, cy, e, cols) in ((40, 30, 7, (SUN, "#D9A300", "#B98A00")), (50, 20, 6, (CORAL, "#C94E37", "#A93D29")),
                              (54, 38, 5.5, (AQUA, "#5EA9B3", "#43909A")), (44, 46, 5, (LILAC, "#9C88F0", "#8170DA"))):
        bits += faces(cube(cx, cy, e), *cols)
    return svg(big + bits)


# ---------------------------------------------------------------- 16. The Exploded Cube
def exploded(top_c, left_c, right_c, dot):
    c = cube(32, 35, 21)
    g = 3.2
    shift = {"top": (0, -g), "left": (-g * .87, g * .5), "right": (g * .87, g * .5)}
    out = ""
    for k, col in (("top", top_c), ("left", left_c), ("right", right_c)):
        dx, dy = shift[k]
        out += f'<polygon points="{pts([(x + dx, y + dy) for x, y in c[k]])}" fill="{col}" stroke="{col}" stroke-width="1.6" stroke-linejoin="round"/>'
    return svg(out + f'<circle cx="32" cy="35" r="3.2" fill="{dot}"/>')


# ---------------------------------------------------------------- 17. Infinite Box
def infinite(shadow):
    loop = "M32 32 L45 24 L58 32 L45 40 L32 32 L19 24 L6 32 L19 40 Z"
    defs = (f'<defs><linearGradient id="g17" x1="0" x2="1" y1="0" y2="0">'
            f'<stop offset="0" stop-color="{VIOLET}"/><stop offset=".5" stop-color="{CORAL}"/><stop offset="1" stop-color="{SUN}"/></linearGradient></defs>')
    depth = f'<path d="{loop}" transform="translate(0 7)" fill="none" stroke="{shadow}" stroke-width="6" stroke-linejoin="round"/>'
    edges = "".join(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + 7}" stroke="{shadow}" stroke-width="6" stroke-linecap="round"/>' for x, y in ((6, 32), (58, 32), (19, 40), (45, 40)))
    band = f'<path d="{loop}" fill="none" stroke="url(#g17)" stroke-width="6" stroke-linejoin="round"/>'
    return svg(depth + edges + band, defs)


# ---------------------------------------------------------------- 18. Nested Knowledge
def nested(tf, lf, rf):
    big = faces(cube(28, 40, 20), tf, lf, rf)
    mid = faces(cube(39, 22, 10), SUN, "#D9A300", "#B98A00")
    small = faces(cube(50, 9, 5.5), CORAL, "#C94E37", "#A93D29")
    return svg(big + mid + small)


# ---------------------------------------------------------------- 19. Box of Possibilities
def possibilities(tf, lf, rf):
    c = cube(32, 44, 17)
    body = faces(c, tf, lf, rf)
    t = c["top"]
    flaps = (f'<polygon points="{pts([t[3], t[0], (t[0][0] - 9, t[0][1] - 9), (t[3][0] - 9, t[3][1] - 9)])}" fill="{LILAC}"/>'
             f'<polygon points="{pts([t[0], t[1], (t[1][0] + 9, t[1][1] - 9), (t[0][0] + 9, t[0][1] - 9)])}" fill="{AQUA}"/>')
    shapes = (f'<circle cx="22" cy="9" r="5" fill="{SUN}"/>'
              f'<polygon points="33,1.5 39,12 27,12" fill="{CORAL}" stroke="{CORAL}" stroke-width="1.2" stroke-linejoin="round"/>'
              f'<rect x="43" y="9" width="9" height="9" rx="2" fill="{VIOLET}" transform="rotate(16 47.5 13.5)"/>'
              + star(32, 21, 4.5, SUN))
    return svg(flaps + body + shapes)


# ---------------------------------------------------------------- 20. One In, Many Out
def one_in_many_out(tf, lf, rf, inbound):
    c = cube(30, 34, 15)
    entry = (f'<line x1="2" y1="34" x2="9" y2="34" stroke="{inbound}" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="2 3"/>'
             f'<circle cx="13" cy="34" r="4" fill="{inbound}"/>')
    outs = (f'<rect x="47" y="8" width="13" height="9" rx="3.5" fill="{CORAL}"/><polygon points="50,16 54,16 50.5,20" fill="{CORAL}"/>'
            f'<circle cx="54" cy="31" r="5.6" fill="{SUN}"/><polygon points="52.3,28 52.3,34 57.2,31" fill="{NAVY}"/>'
            f'<rect x="48" y="43" width="12" height="9" rx="2" fill="{AQUA}"/><rect x="50.5" y="46" width="7" height="1.6" rx=".8" fill="{WHITE}"/><rect x="50.5" y="49" width="4.5" height="1.6" rx=".8" fill="{WHITE}"/>'
            + star(44, 56, 4.4, LILAC))
    fan = "".join(f'<line x1="44" y1="34" x2="{x}" y2="{y}" stroke="{col}" stroke-width="1.6" stroke-linecap="round" stroke-dasharray="1.5 2.5"/>'
                  for x, y, col in ((47, 16, CORAL), (48, 31, SUN), (48, 46, AQUA), (44, 51, LILAC)))
    return svg(entry + fan + faces(c, tf, lf, rf) + outs)


CONCEPTS = [
    ("11-unfolding-box", "The Unfolding Box", "A box whose panels open outward into four learning modes: see it, hear it, try it, remember it.",
     ["Each flap carries its mode: eye, voice, pointer, memory loop", "Tells the product story in one mark", "Icons get too small at 16 px; use the plain flaps there"],
     unfolding(NAVY, WHITE), unfolding(WHITE, WHITE)),
    ("12-knowledge-burst", "Knowledge Burst", "A compact cube with ideas radiating outward: hidden knowledge becoming accessible.",
     ["Energetic and celebratory", "Rays in the brand colours, ideas as dots at the tips", "Reads like a sun or badge at small sizes"],
     burst(NAVY, PLUM, VIOLET), burst(PALE, PALE2, VIOLET)),
    ("13-box-path", "Box → Path", "A box that opens into a continuous learning pathway, ending at a goal.",
     ["The path is the learning journey", "Works well animated: the path drawing itself", "Path could stretch across the page as a brand line"],
     box_path(VIOLET, NAVY, "#0E0B2E"), box_path(PALE, PALE2, VIOLET)),
    ("14-learning-portal", "The Learning Portal", "An open cube with a glowing doorway: step inside the knowledge.",
     ["Inviting: learning as a place you enter", "Glow spills out of the door", "Calm and premium; suits institutions"],
     portal(VIOLET, NAVY, PLUM), portal(VIOLET, PALE, PALE2)),
    ("15-inside-out", "Inside Out", "A solid box on one side, breaking into colourful modular pieces on the other.",
     ["Shows a heavy course becoming bite-sized modules", "Movement from left to right reads as progress", "Busy at 16 px"],
     inside_out(VIOLET, NAVY, PLUM), inside_out(VIOLET, PALE, PALE2)),
    ("16-exploded-cube", "The Exploded Cube", "The faces of a cube pulled slightly apart: knowledge unpacked into understandable parts.",
     ["The simplest of the round: three shapes and a dot", "Strong and crisp at every size", "Each face can take its own colour or mode"],
     exploded(SUN, VIOLET, CORAL, NAVY), exploded(SUN, LILAC, CORAL, WHITE)),
    ("17-infinite-box", "Infinite Box", "An impossible box folded into an infinity loop: endless learning from any source.",
     ["Distinctive geometric illusion", "Gradient from violet to coral to yellow", "Says 'lifelong learning' more than 'unbox'"],
     infinite(PLUM), infinite("#3A3478")),
    ("18-nested-knowledge", "Nested Knowledge", "Smaller cubes rising out of a larger one: concepts hidden inside concepts.",
     ["Shows depth: big topic, smaller ideas inside", "A clear upward direction", "Also hints at micro-learning"],
     nested(VIOLET, NAVY, PLUM), nested(VIOLET, PALE, PALE2)),
    ("19-box-of-possibilities", "Box of Possibilities", "An open box releasing different shapes, each a different way to learn.",
     ["Playful and colourful", "Shapes can map to formats: circle = audio, triangle = video, square = card", "Busiest mark of the round"],
     possibilities("#0E0B2E", NAVY, PLUM), possibilities(VIOLET, PALE, PALE2)),
    ("20-one-in-many-out", "One In, Many Out", "One plain shape enters the box; a chat bubble, a video, a card and a spark come out.",
     ["The clearest explanation of what the engine does", "Reads left to right, like the website hero", "Works best as an illustration or wide logo"],
     one_in_many_out(VIOLET, NAVY, PLUM, "#9C95C9"), one_in_many_out(VIOLET, PALE, PALE2, WHITE)),
]


def board():
    css = (HERE / "logo-concepts.html").read_text(encoding="utf-8")
    style = css[css.index("<style>"):css.index("</style>") + 8]
    head = css[:css.index("<style>")].replace("<title>UnboxEd logo concepts</title>", "<title>UnboxEd logo concepts, round 2</title>")
    sections = ""
    for i, (slug, name, idea, bullets, _, _) in enumerate(CONCEPTS, 11):
        lis = "".join(f"<li>{b}</li>" for b in bullets)
        sections += f'''
  <section class="concept">
    <div class="meta">
      <div class="num">Concept {i}</div>
      <h2>{name}</h2>
      <p>{idea}</p>
      <ul>{lis}</ul>
    </div>
    <div class="uses">
      <div class="tile light"><small>On light</small><img class="big" src="concepts/{slug}.svg" alt="{name} mark"></div>
      <div class="tile dark"><small>On dark</small><img class="big" src="concepts/{slug}-dark.svg" alt=""></div>
      <div class="tile light"><small>Wordmark</small><div class="lockup"><img src="concepts/{slug}.svg" alt=""><span><b>unbox</b> <i>learning</i></span></div></div>
      <div class="tile dark"><small>Wordmark, dark</small><div class="lockup"><img src="concepts/{slug}-dark.svg" alt=""><span><b>unbox</b> <i>learning</i></span></div></div>
      <div class="tile light"><small>Favicon sizes</small><div class="row2"><div class="sizes"><img src="concepts/{slug}.svg" alt=""><img src="concepts/{slug}.svg" alt=""><img src="concepts/{slug}.svg" alt=""></div><div class="tab"><img src="concepts/{slug}.svg" alt="">UnboxEd</div></div></div>
      <div class="tile light"><small>App icon</small><div class="app"><img src="concepts/{slug}-dark.svg" alt=""></div></div>
    </div>
  </section>'''
    overview = "".join(f'<figure><img src="concepts/{slug}.svg" alt=""><figcaption>{i}. {name}</figcaption></figure>'
                       for i, (slug, name, *_rest) in enumerate(CONCEPTS, 11))
    extra = ("<style>.overview{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:0 0 28px}"
             ".overview figure{margin:0;background:#fff;border:2px solid var(--line);border-radius:18px;padding:16px 10px 10px;text-align:center}"
             ".overview img{width:84px;height:84px}.overview figcaption{font:600 13px Figtree,system-ui;margin-top:6px}"
             "@media(max-width:820px){.overview{grid-template-columns:repeat(2,minmax(0,1fr))}}</style>")
    return (head + style + extra + "</head>\n<body>\n<div class=\"wrap\">\n"
            "  <h1>UnboxEd: logo concepts, round 2</h1>\n"
            "  <p class=\"intro\">Ten sample logos, all built from the box, one for each idea you shared. All ten are side by side first; "
            "below, each is shown on light and dark, with the wordmark, at favicon sizes and as an app icon.</p>\n"
            f"  <div class=\"overview\">{overview}</div>{sections}\n</div>\n</body>\n</html>\n")


if __name__ == "__main__":
    for slug, _, _, _, light, dark in CONCEPTS:
        (OUT / f"{slug}.svg").write_text(light, encoding="utf-8")
        (OUT / f"{slug}-dark.svg").write_text(dark, encoding="utf-8")
    (HERE / "logo-concepts-2.html").write_text(board(), encoding="utf-8")
    print(f"{len(CONCEPTS)} concepts written")
