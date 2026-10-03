"""UnboxEd logo: the isometric open-box U, redrawn as clean vector on a true isometric grid.

Proportions are measured from the approved artwork (logo/ChatGPT Image Oct 4, 2026, 12_46_50 AM-2.png):
an open box whose two back walls rise as the arms of a U, a two-tone floor, and a small open box in the
middle whose opening is left empty.

Run: python make_unboxed_logo.py   ->  final/*.svg and unboxed-logo.html (review board)
"""
from pathlib import Path

HERE = Path(__file__).parent
FINAL = HERE / "final"
S = 0.57735  # isometric slope (tan 30°)

PALETTES = {
    # the colours in the approved artwork, sampled from the image
    "original": dict(arm_l="#14144F", arm_r="#FDBA0A", floor_l="#4444FC", floor_r="#14144F",
                     rim="#6E6EFC", wall="#4848FC", face="#3434F0", hole="#FFFFFF"),
    # recommended: the same design, tuned to the site palette (brand navy, warm gold, brand violet)
    "refined": dict(arm_l="#1B164B", arm_r="#F5B301", floor_l="#5B3FE0", floor_r="#2A2170",
                    rim="#A797FF", wall="#7B63F5", face="#4129B8", hole="#FFFFFF"),
    # alternative: brighter and warmer, for a more playful learner-facing feel
    "vivid": dict(arm_l="#1B164B", arm_r="#FFB627", floor_l="#6A4CFF", floor_r="#1B164B",
                  rim="#B7A9FF", wall="#8A73FF", face="#4A2FD6", hole="#FFFFFF"),
}
DARK = {  # on dark backgrounds the navy arm and floor need lifting so the U still reads
    "refined": dict(arm_l="#ECE9FC", floor_r="#C9C2F2", hole="#1B164B"),
    "vivid": dict(arm_l="#ECE9FC", floor_r="#C9C2F2", hole="#1B164B"),
    "original": dict(arm_l="#ECE9FC", floor_r="#C9C2F2", hole="#1B164B"),
}


def P(*pts):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)


def arm(x0, x1, y_top0, h, rising, r=30):
    """A wall panel of width x0..x1 whose top edge rises (left arm) or falls (right arm) at the iso slope.
    Top corners are rounded; bottom corners stay hidden behind the floor."""
    dy = (x1 - x0) * S * (-1 if rising else 1)
    tl, tr = (x0, y_top0), (x1, y_top0 + dy)
    bl, br = (x0, y_top0 + h), (x1, y_top0 + dy + h)
    ux, uy = 0.866, (-0.5 if rising else 0.5)  # unit vector along the top edge
    return (f"M{bl[0]:.1f} {bl[1]:.1f} L{tl[0]:.1f} {tl[1] + r:.1f} Q{tl[0]:.1f} {tl[1]:.1f} {tl[0] + r * ux:.1f} {tl[1] + r * uy:.1f} "
            f"L{tr[0] - r * ux:.1f} {tr[1] - r * uy:.1f} Q{tr[0]:.1f} {tr[1]:.1f} {tr[0]:.1f} {tr[1] + r:.1f} L{br[0]:.1f} {br[1]:.1f} Z")


def mark(c, view="276 258 702 702"):
    cx = 626.5
    L, R, B, Bk = (308, 766), (945, 766), (cx, 950), (cx, 766 - 318.5 * S)
    # floor: two-tone rhombus (left half / right half)
    floor = (f'<polygon points="{P(L, Bk, (cx, 766), B)}" fill="{c["floor_l"]}"/>'
             f'<polygon points="{P(Bk, R, B, (cx, 766))}" fill="{c["floor_r"]}"/>'
             f'<polygon points="{P(L, (cx, 766), B)}" fill="{c["floor_l"]}"/><polygon points="{P((cx, 766), R, B)}" fill="{c["floor_r"]}"/>')
    # the two back walls rising as the arms of the U
    arms = (f'<path d="{arm(308, 498, 405, 361, True)}" fill="{c["arm_l"]}"/>'
            f'<path d="{arm(755, 945, 405 - 190 * S, 361, False)}" fill="{c["arm_r"]}"/>')
    # the small open box in the middle
    w, top_y, fh = 127.5, 676, 74          # half-width, y of its top's side vertices, front-face height
    tl_, tf_, tr_, tb_ = (cx - w, top_y), (cx, top_y + w * S), (cx + w, top_y), (cx, top_y - w * S)
    rim_up = 32                            # the back walls of the small box rise above its top
    rim = f'<polygon points="{P((cx - w, top_y - rim_up), (cx, tb_[1] - rim_up), (cx + w, top_y - rim_up), tr_, tb_, tl_)}" fill="{c["rim"]}"/>'
    top = f'<polygon points="{P(tl_, tb_, tr_, tf_)}" fill="{c["wall"]}"/>'
    k = 0.86                               # the opening, inset inside the top
    hole = f'<polygon points="{P((cx - w * k, top_y), (cx, top_y - w * S * k), (cx + w * k, top_y), (cx, top_y + w * S * k))}" fill="{c["hole"]}"/>'
    faces = (f'<polygon points="{P(tl_, tf_, (cx, tf_[1] + fh), (cx - w, top_y + fh))}" fill="{c["face"]}"/>'
             f'<polygon points="{P(tf_, tr_, (cx + w, top_y + fh), (cx, tf_[1] + fh))}" fill="{c["face"]}"/>')
    body = floor + arms + rim + top + hole + faces
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}">{body}</svg>\n'


def palette(name, dark=False):
    c = dict(PALETTES[name])
    if dark:
        c.update(DARK[name])
    return c


if __name__ == "__main__":
    FINAL.mkdir(exist_ok=True)
    for name in PALETTES:
        (FINAL / f"unboxed-mark-{name}.svg").write_text(mark(palette(name)), encoding="utf-8")
        (FINAL / f"unboxed-mark-{name}-dark.svg").write_text(mark(palette(name, True)), encoding="utf-8")
    print("marks written:", ", ".join(PALETTES))
    # the chosen palette, as the final mark files used by the website
    (FINAL / "unboxed-mark.svg").write_text(mark(palette("refined")), encoding="utf-8")
    (FINAL / "unboxed-mark-dark.svg").write_text(mark(palette("refined", True)), encoding="utf-8")
    print("final: refined")
