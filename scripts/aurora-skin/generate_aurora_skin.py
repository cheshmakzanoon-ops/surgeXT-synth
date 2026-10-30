#!/usr/bin/env python3
"""
Generates the Aurora skin (resources/data/skins/aurora.surge-skin).

Aurora keeps the control layout of the Surge Dark skin but replaces its look:
a deep indigo night sky with soft aurora light behind translucent glass panels,
a colour spectrum that flows across the sections (cyan oscillators through
violet filters, rose and coral envelopes, golden modulators and mint effects),
glowing slider handles and an indigo/magenta/cyan widget palette.

Every widget sprite is derived from the Dark skin by remapping its palette, so
re-running this script after the Dark skin changes keeps both in step. The
background, slider handles and skin.xml colours are generated from scratch.

Usage: python3 scripts/aurora-skin/generate_aurora_skin.py
Requires: fontTools (pip install fonttools)
"""

import colorsys
import math
import random
import re
import shutil
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
SKINS = ROOT / "resources" / "data" / "skins"
SRC = SKINS / "dark-mode.surge-skin"
DST = SKINS / "aurora.surge-skin"
FONTS = DST / "fonts"

W, H = 904, 569

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

C = dict(
    void="#07061A",
    base="#0E0B26",
    panel="#151236",
    panel2="#1C1844",
    raised="#241F55",
    line="#2E2866",
    text="#ECEAFF",
    text2="#B3ADE6",
    text3="#7D76B8",
    ink="#0B0922",
    cyan="#3DE8FF",
    sky="#4FB8FF",
    azure="#7B8CFF",
    violet="#A97CFF",
    magenta="#E663FF",
    pink="#FF4FB8",
    rose="#FF6F91",
    coral="#FF9A5C",
    gold="#FFC94D",
    mint="#4DFFB4",
    lime="#A8FF6B",
)

# The aurora spectrum used for the signature lines and the wordmark
SPECTRUM = [
    (0.00, C["cyan"]),
    (0.20, C["azure"]),
    (0.40, C["violet"]),
    (0.58, C["pink"]),
    (0.76, C["coral"]),
    (0.90, C["gold"]),
    (1.00, C["mint"]),
]


def hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def rgb_to_hex(r, g, b):
    return "#" + "".join(f"{max(0, min(255, round(v * 255))):02X}" for v in (r, g, b))


def hls(hdeg, l, s):
    return rgb_to_hex(*colorsys.hls_to_rgb((hdeg % 360) / 360.0, l, s))


def remap(hexcol):
    """Map a colour from the Dark skin onto the Aurora palette.

    Neutrals become indigo-tinted, oranges become magenta-pink, blues become
    cyan, greens become mint and reds become rose. Lightness is preserved so
    contrast relationships in the original artwork survive."""
    r, g, b = hex_to_rgb(hexcol)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    hd = h * 360

    if l <= 0.02:
        return C["void"]
    if l >= 0.995:
        return "#FFFFFF"

    if s < 0.15:
        if l < 0.5:
            return hls(248, l * 0.95 + 0.015, 0.42)
        if l < 0.9:
            return hls(248, l, 0.55)
        return hls(248, l, 0.9)

    if 15 <= hd < 62:  # orange & amber -> magenta-pink
        nh = 322 + (hd - 34) * 0.6
        return hls(nh, min(0.82, l + 0.08), 1.0)
    if 62 <= hd < 170:  # greens -> mint
        return hls(158, min(0.8, l + 0.08), 1.0)
    if 170 <= hd < 250:  # blues -> cyan / azure
        nh = 190 + (hd - 200) * 0.5
        return hls(nh, min(0.85, l + 0.04), min(1.0, s + 0.1))
    if hd >= 330 or hd < 15:  # reds -> rose
        return hls(348, min(0.75, l + 0.05), 1.0)
    return hexcol


# ---------------------------------------------------------------------------
# Text as outlines (the SVG renderer has no font fallback, so we draw glyphs)
# ---------------------------------------------------------------------------


class Outliner:
    def __init__(self, path):
        self.font = TTFont(path)
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upm = self.font["head"].unitsPerEm
        self.hmtx = self.font["hmtx"]

    def _advance(self, ch, size):
        return self.hmtx[self.cmap[ord(ch)]][0] * size / self.upm

    def width(self, text, size, tracking=0.0):
        if not text:
            return 0
        return sum(self._advance(c, size) for c in text) + tracking * size * (len(text) - 1)

    def path(self, text, x, y, size, tracking=0.0, anchor="start"):
        w = self.width(text, size, tracking)
        if anchor == "middle":
            x -= w / 2
        elif anchor == "end":
            x -= w
        scale = size / self.upm
        ds = []
        for ch in text:
            gname = self.cmap[ord(ch)]
            pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
            self.glyphs[gname].draw(TransformPen(pen, (scale, 0, 0, -scale, x, y)))
            ds.append(pen.getCommands())
            x += self._advance(ch, size) + tracking * size
        return " ".join(d for d in ds if d)


# ---------------------------------------------------------------------------
# SVG building helpers
# ---------------------------------------------------------------------------


def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


class Svg:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.defs = []
        self.body = []
        self._n = 0

    def uid(self, p):
        self._n += 1
        return f"{p}{self._n}"

    def linear(self, x1, y1, x2, y2, stops):
        gid = self.uid("lg")
        st = "".join(
            f'<stop offset="{f(o)}" stop-color="{c}" stop-opacity="{f(a)}"/>' for o, c, a in stops
        )
        self.defs.append(
            f'<linearGradient id="{gid}" x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" '
            f'gradientUnits="userSpaceOnUse">{st}</linearGradient>'
        )
        return f"url(#{gid})"

    def radial(self, cx, cy, r, stops):
        gid = self.uid("rg")
        st = "".join(
            f'<stop offset="{f(o)}" stop-color="{c}" stop-opacity="{f(a)}"/>' for o, c, a in stops
        )
        self.defs.append(
            f'<radialGradient id="{gid}" cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" '
            f'gradientUnits="userSpaceOnUse">{st}</radialGradient>'
        )
        return f"url(#{gid})"

    def add(self, s):
        self.body.append(s)

    def rect(self, x, y, w, h, fill, rx=0, opacity=1.0, stroke=None, sw=1.0):
        s = f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}"'
        if rx:
            s += f' rx="{f(rx)}"'
        s += f' fill="{fill}"'
        if opacity != 1.0:
            s += f' fill-opacity="{f(opacity)}"'
        if stroke:
            s += f' stroke="{stroke}" stroke-width="{f(sw)}"'
        self.add(s + "/>")

    def circle(self, cx, cy, r, fill, opacity=1.0):
        s = f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="{fill}"'
        if opacity != 1.0:
            s += f' fill-opacity="{f(opacity)}"'
        self.add(s + "/>")

    def path(self, d, fill="none", stroke=None, sw=1.0, opacity=1.0):
        s = f'<path d="{d}" fill="{fill}"'
        if opacity != 1.0:
            s += f' opacity="{f(opacity)}"'
        if stroke:
            s += f' stroke="{stroke}" stroke-width="{f(sw)}" stroke-linecap="round"'
        self.add(s + "/>")

    def render(self):
        return (
            f'<svg width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
            f'fill="none" xmlns="http://www.w3.org/2000/svg">\n'
            + "\n".join(self.body)
            + "\n<defs>\n"
            + "\n".join(self.defs)
            + "\n</defs>\n</svg>\n"
        )


def rounded_top(x, y, w, h, r):
    return (
        f"M{f(x)} {f(y + h)}V{f(y + r)}Q{f(x)} {f(y)} {f(x + r)} {f(y)}"
        f"H{f(x + w - r)}Q{f(x + w)} {f(y)} {f(x + w)} {f(y + r)}V{f(y + h)}Z"
    )


def triangle(cx, cy, size, direction):
    s = size
    if direction == "left":
        return f"M{f(cx + s * 0.5)} {f(cy - s * 0.6)}L{f(cx - s * 0.5)} {f(cy)}L{f(cx + s * 0.5)} {f(cy + s * 0.6)}Z"
    return f"M{f(cx - s * 0.5)} {f(cy - s * 0.6)}L{f(cx + s * 0.5)} {f(cy)}L{f(cx - s * 0.5)} {f(cy + s * 0.6)}Z"


# ---------------------------------------------------------------------------
# The main background
# ---------------------------------------------------------------------------


def build_background(heading, label):
    s = Svg(W, H)

    # Night sky with aurora light
    s.rect(0, 0, W, H, s.linear(0, 0, W, H, [(0, "#1A1142", 1), (0.45, "#0C0A28", 1), (1, "#060518", 1)]))
    for cx, cy, r, col, a in [
        (820, -20, 430, "#FF3DCB", 0.42),
        (470, 250, 470, "#6A3DFF", 0.30),
        (-40, 560, 420, "#00D5FF", 0.30),
        (930, 600, 330, "#FF9F43", 0.22),
        (180, 40, 300, "#3D7BFF", 0.26),
    ]:
        s.circle(cx, cy, r, s.radial(cx, cy, r, [(0, col, a), (0.55, col, a * 0.35), (1, col, 0)]))

    rnd = random.Random(8675309)
    for _ in range(140):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        r = rnd.choice([0.35, 0.45, 0.55, 0.7, 0.9])
        s.circle(x, y, r, "#FFFFFF", rnd.uniform(0.15, 0.75))

    # Header glass and the spectrum horizon line
    s.rect(0, 0, W, 56, s.linear(0, 0, 0, 56, [(0, "#0A0820", 0.55), (1, "#140F36", 0.75)]))
    spectrum = s.linear(0, 0, W, 0, [(o, c, 1) for o, c in SPECTRUM])
    s.rect(0, 55.25, W, 1.5, spectrum)
    s.rect(0, 56.75, W, 3, s.linear(0, 56.75, 0, 59.75, [(0, "#FFFFFF", 0.10), (1, "#FFFFFF", 0)]))

    def panel(x0, y0, x1, y1, accent, header=None, r=7, fill_opacity=0.80):
        w, h = x1 - x0, y1 - y0
        s.rect(x0 + 0.5, y0 + 1.5, w, h, "#000000", rx=r, opacity=0.35)  # soft drop
        s.rect(x0, y0, w, h, s.linear(0, y0, 0, y1, [(0, "#1A1642", 1), (1, "#110E2E", 1)]),
               rx=r, opacity=fill_opacity)
        # Inner accent bloom in the upper corner
        s.rect(x0, y0, w, h, s.radial(x0 + w * 0.5, y0, max(w, h) * 0.9,
                                      [(0, accent, 0.15), (1, accent, 0)]), rx=r)
        if header:
            hy = header
            s.path(rounded_top(x0, y0, w, hy - y0, r),
                   fill=s.linear(0, y0, 0, hy, [(0, accent, 0.38), (1, accent, 0.08)]))
            s.rect(x0 + 1, hy - 0.5, w - 2, 1,
                   s.linear(x0, 0, x1, 0, [(0, accent, 0), (0.5, accent, 0.9), (1, accent, 0)]))
        s.rect(x0 + 0.5, y0 + 0.5, w - 1, h - 1, "none", rx=r - 0.5,
               stroke=s.linear(0, y0, 0, y1, [(0, "#FFFFFF", 0.22), (0.3, accent, 0.18), (1, "#FFFFFF", 0.05)]),
               sw=1.0)

    def screen(x0, y0, x1, y1, accent, r=5):
        s.rect(x0, y0, x1 - x0, y1 - y0, s.linear(0, y0, 0, y1, [(0, "#05040F", 0.92), (1, "#0B0922", 0.92)]), rx=r)
        s.rect(x0 + 0.5, y0 + 0.5, x1 - x0 - 1, y1 - y0 - 1, "none", rx=r - 0.5,
               stroke=s.linear(0, y0, 0, y1, [(0, accent, 0.45), (1, accent, 0.10)]), sw=1.0)

    def head(text, x, y, accent, anchor="middle", size=8.0, tracking=0.14):
        s.path(heading.path(text, x, y, size, tracking, anchor), fill=accent)

    def small(text, x, y, col=C["text2"], anchor="middle", size=7.0, tracking=0.06, font=None):
        s.path((font or label).path(text, x, y, size, tracking, anchor), fill=col)

    def flank(x, y, text_w, accent, gap=6, length=24):
        s.rect(x - text_w / 2 - gap - length, y, length, 1,
               s.linear(x - text_w / 2 - gap - length, 0, x - text_w / 2 - gap, 0, [(0, accent, 0), (1, accent, 0.8)]))
        s.rect(x + text_w / 2 + gap, y, length, 1,
               s.linear(x + text_w / 2 + gap, 0, x + text_w / 2 + gap + length, 0, [(0, accent, 0.8), (1, accent, 0)]))

    # ---- Header labels
    for t, x, y in [("SCENE", 27, 9), ("MODE", 74, 9), ("SPLIT", 121.5, 9), ("POLY", 121.5, 36.5),
                    ("PATCH BROWSER", 352, 9), ("STATUS", 577.5, 9), ("FX BYPASS  /  CHARACTER", 674.5, 9),
                    ("OUTPUT", 827, 9)]:
        head(t, x, y, C["text2"], size=7.0, tracking=0.16)
    for t, x in [("CATEGORY", 212), ("PATCH", 293), ("HISTORY", 483)]:
        small(t, x, 51.5, C["text3"], size=6.5, tracking=0.14)

    # Patch browser display: the hero of the header
    s.rect(157, 12, 390, 28, s.linear(0, 12, 0, 40, [(0, "#05040F", 0.85), (1, "#120E33", 0.85)]), rx=6)
    s.rect(157.5, 12.5, 389, 27, "none", rx=5.5,
           stroke=s.linear(157, 0, 547, 0, [(0, C["cyan"], 0.85), (0.5, C["violet"], 0.6), (1, C["pink"], 0.85)]))
    s.rect(170, 12.5, 364, 1, s.linear(170, 0, 534, 0, [(0, "#FFFFFF", 0), (0.5, "#FFFFFF", 0.35), (1, "#FFFFFF", 0)]))

    # ---- Oscillator column
    panel(2, 58, 147, 396, C["cyan"], header=77)
    head("OSCILLATOR", 8, 70.5, C["cyan"], anchor="start", size=7.5, tracking=0.10)
    screen(4, 80, 145, 181, C["cyan"])
    s.rect(6, 212.5, 137, 1, s.linear(6, 0, 143, 0, [(0, C["cyan"], 0), (0.5, C["cyan"], 0.45), (1, C["cyan"], 0)]))

    # ---- Row 1
    panel(150, 58, 297, 190, C["sky"], header=77)
    head("BEND DEPTH", 186, 70.5, C["sky"])
    head("PLAY MODE", 261, 70.5, C["sky"])
    small("DOWN", 173, 107)
    small("UP", 203, 107)
    s.rect(238.5, 91.5, 51, 48, s.linear(0, 91, 0, 140, [(0, "#05040F", 0.6), (1, "#05040F", 0.3)]), rx=4,
           stroke=s.linear(0, 91, 0, 140, [(0, C["sky"], 0.45), (1, C["sky"], 0.1)]))

    panel(300, 58, 447, 190, C["azure"], header=77)
    head("FM ROUTING", 373.5, 70.5, C["azure"])
    s.rect(306, 153.5, 135, 1, s.linear(306, 0, 441, 0, [(0, C["azure"], 0), (0.5, C["azure"], 0.4), (1, C["azure"], 0)]))

    panel(450, 58, 597, 190, C["violet"], header=77)
    head("FILTER CONFIG", 523.5, 70.5, C["violet"])
    s.rect(456, 153.5, 135, 1, s.linear(456, 0, 591, 0, [(0, C["violet"], 0), (0.5, C["violet"], 0.4), (1, C["violet"], 0)]))

    panel(600, 58, 747, 190, C["magenta"], header=77)
    head("SCENE OUTPUT", 673.5, 70.5, C["magenta"])

    # ---- Row 2
    panel(150, 193, 297, 258, C["sky"], header=212)
    head("SCENE", 157, 205.5, C["sky"], anchor="start")

    filt = s.linear(300, 0, 747, 0, [(0, C["violet"], 1), (0.5, C["magenta"], 1), (1, C["pink"], 1)])
    panel(300, 193, 747, 258, C["magenta"], header=212)
    head("FILTER 1", 463, 205.5, C["violet"], anchor="start", size=7.5)
    head("FILTER 2", 584, 205.5, C["pink"], anchor="end", size=7.5)
    s.path(triangle(457.5, 202.8, 4.5, "left"), fill=C["violet"])
    s.path(triangle(589.5, 202.8, 4.5, "right"), fill=C["pink"])
    for x in (448.5, 598.5):
        s.rect(x, 215, 1, 40, s.linear(0, 215, 0, 255, [(0, "#FFFFFF", 0), (0.5, "#FFFFFF", 0.14), (1, "#FFFFFF", 0)]))
    s.rect(300, 211.5, 447, 1, filt)

    # ---- Row 3
    panel(150, 262, 297, 396, C["cyan"])
    for t, x in [("1", 163.5), ("2", 183.5), ("3", 203.5), ("1×2", 223.5), ("2×3", 243.5), ("N", 263.5),
                 ("GAIN", 284)]:
        small(t, x, 383, size=6.8)
    for x0, x1, t in [(155, 212, "OSC"), (214, 252, "RING")]:
        s.rect(x0, 387.5, x1 - x0, 6.5, s.linear(x0, 0, x1, 0, [(0, C["cyan"], 0.9), (1, C["azure"], 0.9)]), rx=3.25)
        s.path(heading.path(t, (x0 + x1) / 2, 393, 5.5, 0.2, "middle"), fill=C["ink"])

    panel(300, 262, 447, 396, C["pink"])
    head("KEYTRACK", 331, 295, C["pink"], size=7.0)
    s.rect(377.5, 282.5, 64, 108, s.linear(0, 283, 0, 391, [(0, C["pink"], 0.16), (1, C["pink"], 0.03)]), rx=5,
           stroke=s.linear(0, 283, 0, 391, [(0, C["pink"], 0.55), (1, C["pink"], 0.12)]))
    head("SHAPER", 409.5, 295, C["pink"], size=7.0)
    for t, x in [("▸F1", 317), ("▸F2", 337), ("HP", 365)]:
        if t.startswith("▸"):
            s.path(triangle(x - 6.5, 380.6, 3.2, "right"), fill=C["text3"])
            small(t[1:], x + 1.5, 383, size=6.8)
        else:
            small(t, x, 383, size=6.8)

    panel(450, 262, 597, 396, C["rose"])
    w_ = heading.width("FILTER EG", 7.5, 0.14)
    head("FILTER EG", 522, 295, C["rose"], size=7.5)
    flank(522, 291.5, w_, C["rose"], length=28)
    for t, x in [("A", 466), ("D", 486), ("S", 506), ("R", 526)]:
        small(t, x, 383, size=6.8)
    for t, x in [("F1", 559), ("F2", 579)]:
        s.path(triangle(x - 6.5, 380.6, 3.2, "right"), fill=C["text3"])
        small(t, x + 1.5, 383, size=6.8)

    panel(600, 262, 747, 396, C["coral"])
    w_ = heading.width("AMP EG", 7.5, 0.14)
    head("AMP EG", 649, 295, C["coral"], size=7.5)
    flank(649, 291.5, w_, C["coral"], length=20)
    head("AMP", 719, 295, C["coral"], size=7.0)
    for t, x in [("A", 616), ("D", 636), ("S", 656), ("R", 676)]:
        small(t, x, 383, size=6.8)
    small("VEL", 712, 383, size=6.8)
    s.path(triangle(722, 380.6, 3.2, "right"), fill=C["text3"])
    small("GAIN", 734, 383, size=6.8)

    # ---- Modulation sources
    panel(2, 400, 747, 471, C["gold"], fill_opacity=0.7)
    s.rect(14, 400.5, 721, 1, s.linear(14, 0, 735, 0, [(0, C["gold"], 0), (0.2, C["gold"], 0.7),
                                                         (0.8, C["coral"], 0.7), (1, C["coral"], 0)]))

    # ---- LFO
    panel(2, 475, 747, 567, C["gold"])
    s.path(f"M9 475.5H24V566.5H9Q2.5 566.5 2.5 560V482Q2.5 475.5 9 475.5Z",
           fill=s.linear(0, 475, 0, 567, [(0, C["gold"], 0.32), (1, C["coral"], 0.12)]))
    s.rect(24, 478, 1, 86, s.linear(0, 478, 0, 564, [(0, C["gold"], 0.6), (1, C["gold"], 0.1)]))
    screen(233, 477.5, 596, 565.5, C["gold"])
    w_ = heading.width("LFO EG", 7.5, 0.14)
    head("LFO EG", 674, 486, C["gold"], size=7.5)
    flank(674, 482.5, w_, C["gold"], length=34)
    for t, x in [("D", 624), ("A", 644), ("H", 664), ("D", 684), ("S", 704), ("R", 724)]:
        small(t, x, 560, size=6.8)

    # ---- Effects
    panel(750, 58, 902, 190, C["mint"], header=77)
    head("EFFECTS", 826, 70.5, C["mint"])
    panel(750, 193, 902, 567, C["lime"], header=212)

    # Wordmark, in the quiet corner beside the main menu button
    mark = s.linear(758, 0, 842, 0, [(o, c, 1) for o, c in SPECTRUM])
    s.path(heading.path("SURGE XT", 758, 562.5, 12, 0.08), fill=mark)
    s.rect(758, 548.5, 84, 0.75, s.linear(758, 0, 842, 0, [(0, "#FFFFFF", 0.35), (1, "#FFFFFF", 0)]))

    return s.render()


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------

COLOR_RE = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
NAMED_RE = re.compile(r'((?:fill|stroke|stop-color)=")(black|white)(")')


# The Dark skin marks some selected states in blue rather than orange. Outside
# of hover sprites that blue means "selected", which Aurora always shows in pink.
DARK_SELECTED_BLUE = "#399DFF"


def remap_svg(text, name):
    def swap(m):
        col = m.group(0)
        if col.upper() == DARK_SELECTED_BLUE:
            if name.startswith("hoverOn"):
                return "#FF8FD3"
            if not name.startswith("hover"):
                return C["pink"]
        return remap(col)

    text = COLOR_RE.sub(swap, text)
    return NAMED_RE.sub(lambda m: m.group(1) + remap("#000000" if m.group(2) == "black" else "#FFFFFF")
                        + m.group(3), text)


ORB_RE = re.compile(r'<path d="M([\d.]+) ([\d.]+)C[^"]*" fill="url\(#(\w+)\)"/>')

# Orb body gradients (top to bottom) and halo colour, by the family of the
# Dark skin handle they replace
ORB_STYLES = {
    "accent": (["#B5FAFF", "#B88CFF", "#FF5FC8"], C["pink"]),  # regular handles
    "mod": (["#D2FFF0", "#4DFFB4", "#22C8E8"], C["mint"]),  # modulation mode
    "neutral": (["#FFFFFF", "#E2DCFF", "#A79CF0"], C["violet"]),  # light-panel variants
    "cool": (["#FFF6D6", "#FFC94D", "#FF8A5C"], C["gold"]),  # LFO handles
}


def orb_family(hexcol):
    r, g, b = hex_to_rgb(hexcol)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    hd = h * 360
    if s < 0.6:
        return "neutral"
    if 120 <= hd < 175:
        return "mod"
    if 175 <= hd < 260:
        return "cool"
    return "accent"


def glow_handles(text):
    """Slider handles: iridescent orbs with a soft halo and a glassy rim."""
    orbs = []
    for m in ORB_RE.finditer(text):
        nums = [float(v) for v in re.findall(r"-?[\d.]+", m.group(0).split('"')[1])]
        xs, ys = nums[0::2], nums[1::2]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        if 10 <= w <= 12 and 10 <= h <= 12:
            gid = m.group(3)
            g = re.search(r'<linearGradient id="' + gid + r'"[\s\S]*?</linearGradient>', text)
            stops = re.findall(r'stop-color="(#[0-9A-Fa-f]{6})"', g.group(0)) if g else []
            if stops:
                body, halo = ORB_STYLES[orb_family(stops[-1])]
                y0, y1 = min(ys), max(ys)
                newg = (
                    f'<linearGradient id="{gid}" x1="{f(min(xs))}" y1="{f(y0)}" x2="{f(max(xs))}" '
                    f'y2="{f(y1)}" gradientUnits="userSpaceOnUse">'
                    f'<stop stop-color="{body[0]}"/><stop offset="0.5" stop-color="{body[1]}"/>'
                    f'<stop offset="1" stop-color="{body[2]}"/></linearGradient>'
                )
                text = text.replace(g.group(0), newg)
                orbs.append(((max(xs) + min(xs)) / 2, (y0 + y1) / 2, halo))
    seen, halos, rims, defs = set(), [], [], []
    for i, (cx, cy, col) in enumerate(orbs):
        key = (round(cx, 1), round(cy, 1))
        if key in seen:
            continue
        seen.add(key)
        defs.append(
            f'<radialGradient id="aurora_halo{i}" cx="{f(cx)}" cy="{f(cy)}" r="9" gradientUnits="userSpaceOnUse">'
            f'<stop offset="0.45" stop-color="{col}" stop-opacity="0.55"/>'
            f'<stop offset="1" stop-color="{col}" stop-opacity="0"/></radialGradient>'
        )
        halos.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="9" fill="url(#aurora_halo{i})"/>')
        rims.append(
            f'<circle cx="{f(cx)}" cy="{f(cy)}" r="5.1" fill="none" stroke="#FFFFFF" stroke-opacity="0.55" '
            f'stroke-width="0.7"/>'
            f'<ellipse cx="{f(cx)}" cy="{f(cy - 2.4)}" rx="2.9" ry="1.4" fill="#FFFFFF" fill-opacity="0.45"/>'
        )
    if not halos:
        return text
    head_end = text.index(">") + 1
    text = text[:head_end] + "\n" + "\n".join(halos) + text[head_end:]
    text = text.replace("<defs>", "\n".join(rims) + "\n<defs>\n" + "\n".join(defs), 1)
    return text


HANDLE_FILES = re.compile(r"^(bmp|hover|bmpTS|hoverTS)0015[37]\.svg$|^[hv]slider_.*\.svg$")


def build_widgets():
    out = DST / "SVG"
    out.mkdir(parents=True, exist_ok=True)
    for src in sorted((SRC / "SVG").glob("*.svg")):
        if src.name == "bmp00102.svg":
            continue
        text = remap_svg(src.read_text(), src.name)
        if HANDLE_FILES.match(src.name):
            text = glow_handles(text)
        (out / src.name).write_text(text)


# ---------------------------------------------------------------------------
# skin.xml
# ---------------------------------------------------------------------------


def color_overrides():
    a = lambda c, alpha: c + f"{alpha:02X}"
    return {
        # Displays
        "osc.waveform": C["cyan"],
        "osc.waveform.animated": "#FFFFFF",
        "osc.waveform.dots": "#1E1A4A",
        "osc.line.bounds": a(C["cyan"], 0x30),
        "osc.line.center": a(C["cyan"], 0x50),
        "osc.wavename.background": "#123A52",
        "osc.wavename.background.hover": C["cyan"],
        "osc.wavename.frame": a(C["cyan"], 0x90),
        "osc.wavename.frame.hover": C["cyan"],
        "osc.wavename.text": C["cyan"],
        "osc.wavename.text.hover": C["ink"],
        "osc.waveform3d.current": C["cyan"],
        "osc.waveform3d.gradient.start": "#2A7FD8",
        "osc.waveform3d.gradient.end": "#7B4DFF",
        "osc.waveform3d.fill.gradient.start": a(C["cyan"], 0x30),
        "osc.waveform3d.fill.gradient.end": a(C["violet"], 0x30),
        "lfo.title.text": a(C["gold"], 0xE0),
        "lfo.waveform.background": "#00000000",
        "lfo.waveform.dots": "#2A2560",
        "lfo.waveform.ruler.text": C["text2"],
        "lfo.waveform.ruler.ticks": "#2E2866",
        "lfo.waveform.ruler.ticks.small": a(C["gold"], 0x40),
        "lfo.waveform.ruler.ticks.extended": "#2E2866",
        "lfo.waveform.bounds": "#2E2866",
        "lfo.waveform.center": "#3A3380",
        "lfo.waveform.envelope": a(C["coral"], 0x90),
        "lfo.waveform.wave": C["gold"],
        "lfo.waveform.wave.deactivated": a(C["gold"], 0x60),
        "lfo.waveform.wave.ghosted": a(C["gold"], 0x55),
        "lfo.type.selected.background": C["pink"],
        "lfo.type.selected.text": C["ink"],
        "lfo.type.unselected.text": C["text2"],
        "lfo.stepseq.background": "#0B0922",
        "lfo.stepseq.column.shadow": "#07061A",
        "lfo.stepseq.step.fill": C["gold"],
        "lfo.stepseq.step.fill.disabled": "#4A4390",
        "lfo.stepseq.step.fill.outside": "#4A4390",
        "lfo.stepseq.loop.outside.step.primary": "#110E2E",
        "lfo.stepseq.loop.outside.step.secondary": "#1A1642",
        "lfo.stepseq.loop.step.primary": "#1C1844",
        "lfo.stepseq.loop.step.secondary": "#151236",
        "lfo.stepseq.loop.markers": C["coral"],
        "lfo.stepseq.envelope": a(C["coral"], 0x90),
        "lfo.stepseq.wave": C["gold"],
        "lfo.stepseq.button.hover": C["cyan"],
        "msegeditor.background": "#0B0922",
        "msegeditor.curve": C["gold"],
        "msegeditor.curve.deformed": a(C["gold"], 0x80),
        "msegeditor.curve.highlight": "#FFE6A3",
        "msegeditor.panel": "#151236",
        "msegeditor.fill.gradient.start": a(C["gold"], 0x70),
        "msegeditor.fill.gradient.end": a(C["pink"], 0x08),
        "msegeditor.loop.marker": a(C["coral"], 0xA0),
        "msegeditor.loop.region.border": a(C["coral"], 0xA0),
        "waveshaper.preview.background": "#0B0922",
        "waveshaper.waveform.hover": "#FFFFFF",
        "waveshaper.text": C["text2"],
        "waveshaper.text.hover": "#FFFFFF",
        # Modulation buttons
        "modbutton.unused.fill": "#191543",
        "modbutton.unused.frame": "#3A3380",
        "modbutton.unused.frame.hover": C["text"],
        "modbutton.unused.text": "#9790D8",
        "modbutton.unused.text.hover": "#FFFFFF",
        "modbutton.used.fill": "#1D1A55",
        "modbutton.used.frame": C["cyan"],
        "modbutton.used.frame.hover": "#C9F8FF",
        "modbutton.used.text": C["cyan"],
        "modbutton.used.text.hover": "#C9F8FF",
        "modbutton.used.text.usedmod.hover": C["mint"],
        "modbutton.selected.fill": C["pink"],
        "modbutton.selected.frame": "#FFB8E4",
        "modbutton.selected.frame.hover": "#FFFFFF",
        "modbutton.selected.text": C["ink"],
        "modbutton.selected.text.hover": C["ink"],
        "modbutton.selected.text.usedmod.hover": "#0B5A44",
        "modbutton.selected.used.fill": C["pink"],
        "modbutton.selected.used.frame": "#FFFFFF",
        "modbutton.selected.used.frame.hover": "#FFFFFF",
        "modbutton.selected.used.text": C["ink"],
        "modbutton.selected.used.text.hover": C["ink"],
        "modbutton.selected.used.text.usedmod.hover": "#0B5A44",
        "modbutton.armed.fill": "#14523F",
        "modbutton.armed.frame": C["mint"],
        "modbutton.armed.frame.hover": "#D2FFEE",
        "modbutton.armed.text": C["mint"],
        "modbutton.armed.text.hover": "#D2FFEE",
        "modbutton.armed.text.usedmod.hover": C["cyan"],
        "modbutton.macro.slider.background": "#2A2470",
        "modbutton.macro.slider.border": "#151236",
        "modbutton.macro.slider.fill": C["pink"],
        "modbutton.macro.slider.currentvalue": C["gold"],
        # Sliders & labels
        "slider.light.label": C["text2"],
        "slider.dark.label": C["text2"],
        "slider.modulation.positive": C["mint"],
        "slider.modulation.negative": C["rose"],
        "menu.name": C["text2"],
        "menu.name.hover": "#FFFFFF",
        "menu.name.deactivated": "#5E57A0",
        "menu.value": C["text"],
        "menu.value.hover": "#FFFFFF",
        "menu.value.deactivated": "#5E57A0",
        "filtermenu.value": C["text"],
        "filtermenu.value.hover": "#FFFFFF",
        "scene.split_poly.text": C["text"],
        "scene.split_poly.text.hover": C["cyan"],
        "scene.pbrange.text": C["text"],
        "scene.pbrange.text.hover": C["cyan"],
        "scene.keytrackroot.text": C["text"],
        "scene.keytrackroot.text.hover": C["pink"],
        "multiswitch.background": "#15123A",
        "multiswitch.border": "#07061A",
        "multiswitch.separator": "#07061A",
        "multiswitch.text": C["text2"],
        "multiswitch.text.deactivated": "#4A4390",
        "multiswitch.on.text": C["ink"],
        "multiswitch.on.fill": C["pink"],
        "multiswitch.hover.text": C["ink"],
        "multiswitch.hover.fill": C["cyan"],
        "multiswitch.hoveron.text": C["ink"],
        "multiswitch.hoveron.fill": "#FF8FD3",
        "multiswitch.hoveron.border": "#FFFFFF",
        # Patch browser
        "patchbrowser.text": C["text"],
        "patchbrowser.text.hover": "#FFFFFF",
        "patchbrowser.tooltip.border": C["violet"],
        "patchbrowser.tooltip.background": "#151236",
        "patchbrowser.tooltip.text": C["text"],
        "patchbrowser.typeahead.border": C["violet"],
        "patchbrowser.typeahead.background": "#120F30",
        "patchbrowser.typeahead.background.highlight": "#2A2470",
        "patchbrowser.typeahead.text": C["text2"],
        "patchbrowser.typeahead.text.highlight": "#FFFFFF",
        "patchbrowser.typeahead.subtext": C["text3"],
        "patchbrowser.typeahead.subtext.highlight": C["cyan"],
        "patchbrowser.typeahead.separator": "#2E2866",
        # Effects
        "effect.label.separator": a(C["mint"], 0x70),
        "effect.label.text": C["mint"],
        "effect.label.presetname": C["text"],
        "effect.grid.scene.background": "#00000000",
        "effect.grid.scene.border": "#5E57A0",
        "effect.grid.scene.text": C["text2"],
        "effect.grid.scene.background.hover": "#FFFFFF18",
        "effect.grid.scene.border.hover": C["text2"],
        "effect.grid.scene.text.hover": "#FFFFFF",
        "effect.grid.unselected.background": "#151236",
        "effect.grid.unselected.border": "#5E57A0",
        "effect.grid.unselected.text": C["text2"],
        "effect.grid.unselected.background.hover": "#2A2470",
        "effect.grid.unselected.border.hover": C["text2"],
        "effect.grid.unselected.text.hover": "#FFFFFF",
        "effect.grid.selected.background": a(C["mint"], 0x30),
        "effect.grid.selected.border": C["mint"],
        "effect.grid.selected.text": C["mint"],
        "effect.grid.selected.background.hover": a(C["mint"], 0x50),
        "effect.grid.selected.border.hover": "#D2FFEE",
        "effect.grid.selected.text.hover": "#D2FFEE",
        "effect.grid.bypassed.background": "#151236",
        "effect.grid.bypassed.border": "#4A4390",
        "effect.grid.bypassed.text": "#5E57A0",
        "effect.grid.bypassed.background.hover": "#2A2470",
        "effect.grid.bypassed.border.hover": "#7D76B8",
        "effect.grid.bypassed.text.hover": "#7D76B8",
        "effect.grid.bypassed.selected.background": a(C["rose"], 0x22),
        "effect.grid.bypassed.selected.border": a(C["rose"], 0xA0),
        "effect.grid.bypassed.selected.text": a(C["rose"], 0xA0),
        "effect.grid.bypassed.selected.background.hover": a(C["rose"], 0x40),
        "effect.grid.bypassed.selected.border.hover": C["rose"],
        "effect.grid.bypassed.selected.text.hover": C["rose"],
        "effect.menu.text": C["text"],
        "effect.menu.text.hover": "#FFFFFF",
        # Meters & keyboard
        "vumeter.background": "#08071C",
        "vumeter.border": "#1C1844",
        "vumeter.level.low": C["cyan"],
        "vumeter.level.low.notch": "#08071C",
        "vumeter.level.mid": C["pink"],
        "vumeter.level.mid.notch": "#08071C",
        "vumeter.level.high": "#FF2E63",
        "vumeter.level.high.notch": "#08071C",
        "vumeter.level.gr": C["gold"],
        "vumeter.level.gr.notch": "#08071C",
        "vkb.key.mouse_over": a(C["cyan"], 0x80),
        "vkb.key.pressed": C["pink"],
        "vkb.octave.background": "#0E0B26",
        "vkb.wheel.background": "#151236",
        "vkb.wheel.border": "#07061A",
        "vkb.wheel.value": C["cyan"],
        # Dialogs, overlays and popups
        "overlay.background": "#07061AC8",
        "dialog.background": "#151236",
        "dialog.border": "#2E2866",
        "dialog.titlebar.background": "#0E0B26",
        "dialog.titlebar.text": "#FFFFFF",
        "dialog.button.background": "#1C1844",
        "dialog.button.border": "#3A3380",
        "dialog.button.text": C["text"],
        "dialog.button.hover.background": C["pink"],
        "dialog.button.hover.border": "#FFC2E6",
        "dialog.button.hover.text": C["ink"],
        "dialog.button.pressed.background": C["cyan"],
        "dialog.button.pressed.border": "#FFFFFF",
        "dialog.button.pressed.text": C["ink"],
        "dialog.textfield.focus": C["cyan"],
        "dialog.textfield.border": "#3A3380",
        "dialog.textfield.background": "#0B0922",
        "dialog.textfield.text": C["text"],
        "dialog.label.text": C["text2"],
        "dialog.checkbox.border": C["text2"],
        "dialog.checkbox.tick": C["cyan"],
        "infowindow.background": "#151236",
        "infowindow.border": C["violet"],
        "infowindow.foreground": C["text"],
        "infowindow.text": C["text"],
        "infowindow.text.modulation.positive": C["mint"],
        "infowindow.text.modulation.negative": C["rose"],
        "about.page.text": C["text"],
        "about.page.column.text": C["pink"],
        "about.page.link": C["cyan"],
        "about.page.hover.link": "#C9F8FF",
        "tabbar.active.background": "#3A1E5C",
        "tabbar.inactive.background": "#151236",
        "tabbar.border": C["pink"],
        "tabbar.text": C["text"],
        "tabbar.text.hover": C["cyan"],
        "modlist.border": "#3A3380",
        "modlist.text": C["text"],
        "modlist.text.dimmed": C["text3"],
        "modlist.arrows": C["text2"],
        "lfo.stepseq.button.background": "#1C1844",
        "lfo.stepseq.button.border": "#3A3380",
        "lfo.stepseq.button.arrow": C["text2"],
        "lfo.stepseq.button.arrow.hover": C["ink"],
        "formulaeditor.background": "#0B0922",
        "formulaeditor.text": C["text"],
        "formulaeditor.highlight": "#2A2470",
        "formulaeditor.linenumber.background": "#151236",
        "formulaeditor.linenumber.text": C["text3"],
        "formulaeditor.lua.bracket": C["gold"],
        "formulaeditor.lua.comment": C["text3"],
        "formulaeditor.lua.identifier": C["cyan"],
        "formulaeditor.lua.interpunction": C["text2"],
        "formulaeditor.lua.keyword": C["pink"],
        "formulaeditor.lua.number": C["violet"],
        "formulaeditor.lua.string": C["mint"],
    }


def resolve(value, named):
    seen = 0
    while not value.startswith("#") and value in named and seen < 8:
        value, seen = named[value], seen + 1
    return value


def build_skin_xml():
    src = (SRC / "skin.xml").read_text()

    # Every skinnable colour, starting from the Dark skin (or Surge's default)
    defaults = {}
    skincolors = (ROOT / "src" / "common" / "SkinColors.cpp").read_text()
    for cid, a1, a2, a3, a4 in re.findall(
        r'\(\s*"([a-z][a-z0-9_.]+)"\s*,\s*(0x[0-9A-Fa-f]+|\d+)(?:\s*,\s*(0x[0-9A-Fa-f]+|\d+))?'
        r"(?:\s*,\s*(\d+)\s*,\s*(\d+))?",
        skincolors,
    ):
        if a3:
            defaults[cid] = "#" + "".join(f"{int(v, 0):02X}" for v in (a1, a2, a3, a4))
        else:
            defaults[cid] = f"#{int(a1, 0):06X}" + (f"{int(a2, 0):02X}" if a2 else "")

    dark = dict(re.findall(r'<color id="([^"]+)" value="([^"]+)"/>', src))
    named = {k: v for k, v in dark.items()}
    overrides = color_overrides()

    lines = []
    for cid in sorted(defaults):
        if cid in overrides:
            v = overrides[cid]
        else:
            v = resolve(dark.get(cid, defaults[cid]), named)
            if not v.startswith("#"):
                v = defaults[cid]
            rgb, alpha = v[:7], v[7:]
            v = remap(rgb) + alpha
        lines.append(f'        <color id="{cid}" value="{v}"/>')

    globals_start = src.index("<globals>") + len("<globals>")
    first_image = src.index("<image id=")
    head = (
        "\n        <window-size x=\"904\" y=\"569\"/>\n\n"
        '        <defaultimage directory="SVG/"/>\n\n'
        '        <default-font family="Outfit-Medium"/>\n\n'
        "        <!-- Generated by scripts/aurora-skin/generate_aurora_skin.py -->\n"
        + "\n".join(lines)
        + "\n\n        "
    )
    body = src[:globals_start] + head + src[first_image:]
    body = re.sub(
        r"<surge-skin [^>]*>",
        '<surge-skin name="Aurora" author="Surge Synth Team" '
        'authorURL="https://surge-synth-team.org/" version="2">',
        body,
        count=1,
    )
    (DST / "skin.xml").write_text(body)


def main():
    heading = Outliner(FONTS / "Outfit-SemiBold.ttf")
    label = Outliner(FONTS / "Outfit-Medium.ttf")
    if (DST / "SVG").exists():
        shutil.rmtree(DST / "SVG")
    build_widgets()
    (DST / "SVG" / "bmp00102.svg").write_text(build_background(heading, label))
    build_skin_xml()
    print(f"Wrote {DST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
