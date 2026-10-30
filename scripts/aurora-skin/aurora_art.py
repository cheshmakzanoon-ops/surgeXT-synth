"""
HTML/CSS artwork for the Aurora skin, rendered to multi-resolution PNGs with Chromium.

Chromium gives us what the SVG renderer in Surge can't: real frosted glass
(backdrop blur), soft cast shadows, blurred aurora light, blend modes and 3D
perspective. Everything here is drawn on the 904 x 569 Surge canvas and is
rendered at 1x, 2x and 4x so it stays crisp at every zoom level.

The light comes from the upper left. Panels are frosted glass tiles floating
above a night sky, edge lit in the colour of their section; displays are
recessed holographic screens; light pipes in the gutters show how sound flows
from the oscillators through the filters and amp to the effects, while the
modulation pipe feeds everything from below.
"""

import random

W, H = 904, 569


def rgb(hexcol):
    h = hexcol.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"


# ---------------------------------------------------------------------------
# Icons: tiny line drawings on a 10 x 10 grid, stroked in the section colour
# ---------------------------------------------------------------------------

ICONS = {
    "wave": "M0.6 5C2.2 0.4 3.4 0.4 5 5S7.8 9.6 9.4 5",
    "bend": "M2.6 8.8V1.4M1 3L2.6 1.4L4.2 3M7.4 1.2V8.6M5.8 7L7.4 8.6L9 7",
    "keys": "M0.8 1.4H9.2V8.6H0.8ZM3.6 1.4V5.6M6.4 1.4V5.6M2.2 5.6H5M5 5.6H7.8",
    "orbit": "M5 3.6A1.4 1.4 0 1 1 4.99 3.6ZM0.8 7.2C2.4 9.4 8.6 5.6 9.2 2.8C7.6 0.6 1.4 4.4 0.8 7.2Z",
    "filter": "M0.6 3.2H4.6C6.4 3.2 6.8 1.6 7.4 3.6L9.4 8.8",
    "speaker": "M0.8 3.6H2.8L5.6 1.2V8.8L2.8 6.4H0.8ZM7.2 3.2C8 4.2 8 5.8 7.2 6.8M8.6 1.8C10 3.6 10 6.4 8.6 8.2",
    "scene": "M0.8 0.8H6V6H0.8ZM4 4H9.2V9.2H4Z",
    "keytrack": "M0.8 9.2L9.2 0.8M2.6 7.4A0.6 0.6 0 1 1 2.59 7.4M5 5A0.6 0.6 0 1 1 4.99 5M7.4 2.6A0.6 0.6 0 1 1 7.39 2.6",
    "shaper": "M0.8 9.2C4.6 9.2 5.4 0.8 9.2 0.8",
    "adsr": "M0.6 9.2L2.4 1L4.6 5.2H7L9.4 9.2",
    "lfo": "M0.6 7.4L3 2.2L5.4 7.4L7.8 2.2L9.4 5.6",
    "fx": "M5 0.6L6.1 3.9L9.4 5L6.1 6.1L5 9.4L3.9 6.1L0.6 5L3.9 3.9Z",
}


def icon(name, color, size=8.0, x=0.0, y=0.0):
    return (
        f'<svg style="position:absolute;left:{x}px;top:{y}px;overflow:visible" width="{size}" '
        f'height="{size}" viewBox="0 0 10 10"><path d="{ICONS[name]}" fill="none" stroke="{color}" '
        f'stroke-width="1.15" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )


# ---------------------------------------------------------------------------
# The background
# ---------------------------------------------------------------------------

BASE_CSS = """
@font-face { font-family: 'OutfitSB'; src: url('{fonts}/Outfit-SemiBold.ttf'); }
@font-face { font-family: 'OutfitM'; src: url('{fonts}/Outfit-Medium.ttf'); }
@font-face { font-family: 'OutfitB'; src: url('{fonts}/Outfit-Bold.ttf'); }
* { box-sizing: border-box; }
html, body { margin: 0; width: 904px; height: 569px; overflow: hidden; background: transparent; }
.abs { position: absolute; }
#stage { position: absolute; left: 0; top: 0; width: 904px; height: 569px; overflow: hidden;
  background:
    radial-gradient(120% 80% at 15% -10%, #24165a 0%, rgba(36,22,90,0) 55%),
    radial-gradient(90% 70% at 100% 110%, #1b0f45 0%, rgba(27,15,69,0) 60%),
    linear-gradient(180deg, #0d0a2a 0%, #080619 55%, #05040f 100%); }

.panel { position: absolute; border-radius: 9px;
  background:
    radial-gradient(130% 70% at 50% 0%, rgba(var(--a), .16) 0%, rgba(var(--a), 0) 60%),
    linear-gradient(180deg, rgba(42,34,96,.52) 0%, rgba(22,18,54,.76) 40%, rgba(13,10,34,.86) 100%);
  backdrop-filter: blur(12px) saturate(190%);
  box-shadow:
    0 16px 22px -10px rgba(0,0,0,.9),
    0 3px 7px rgba(0,0,0,.55),
    inset 0 1px 0 rgba(255,255,255,.17),
    inset 0 -1px 0 rgba(0,0,0,.55),
    inset 0 0 26px rgba(var(--a), .07); }
.panel::before { content: ''; position: absolute; inset: 0; border-radius: 9px; padding: 1px;
  background: linear-gradient(155deg, rgba(var(--a), .95) 0%, rgba(var(--a), .22) 28%,
                              rgba(255,255,255,.05) 55%, rgba(var(--b), .45) 100%);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor; mask-composite: exclude; }
.panel::after { content: ''; position: absolute; inset: 0; border-radius: 9px; pointer-events: none;
  background: linear-gradient(118deg, rgba(255,255,255,.075) 0%, rgba(255,255,255,.02) 22%, rgba(255,255,255,0) 34%); }
.hdr { position: absolute; left: 0; right: 0; top: 0; border-radius: 9px 9px 0 0;
  background: linear-gradient(180deg, rgba(var(--a), .40) 0%, rgba(var(--a), .12) 65%, rgba(var(--a), .05) 100%); }
.hdr::after { content: ''; position: absolute; left: 6px; right: 6px; bottom: 0; height: 1px;
  background: linear-gradient(90deg, rgba(var(--a), 0), rgba(var(--a), 1) 50%, rgba(var(--b), 0));
  box-shadow: 0 0 6px 0.5px rgba(var(--a), .8); }
.hdr::before { content: ''; position: absolute; left: 10%; right: 10%; top: 0; height: 1px;
  background: linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,.55), rgba(255,255,255,0)); }

.title { position: absolute; font-family: 'OutfitSB'; font-size: 7.6px; letter-spacing: .15em;
  white-space: nowrap; line-height: 1; color: rgb(var(--a));
  text-shadow: 0 0 6px rgba(var(--a), .75), 0 0 1px rgba(var(--a), .9); }
.label { position: absolute; font-family: 'OutfitM'; font-size: 6.8px; letter-spacing: .06em;
  white-space: nowrap; line-height: 1; color: #b9b3ec; }
.hlabel { position: absolute; font-family: 'OutfitSB'; font-size: 6.9px; letter-spacing: .18em;
  white-space: nowrap; line-height: 1; color: #c9c3f5; text-shadow: 0 0 5px rgba(160,140,255,.45); }
.sublabel { position: absolute; font-family: 'OutfitSB'; font-size: 6.2px; letter-spacing: .16em;
  white-space: nowrap; line-height: 1; color: #8a83c8; }

.screen { position: absolute; border-radius: 6px; overflow: hidden;
  background:
    radial-gradient(110% 80% at 50% 0%, rgba(var(--a), .13) 0%, rgba(var(--a), 0) 65%),
    linear-gradient(180deg, #030209 0%, #0a0820 100%);
  box-shadow: inset 0 2.5px 7px rgba(0,0,0,.95), inset 0 0 0 1px rgba(var(--a), .32),
              0 1px 0 rgba(255,255,255,.12), 0 0 14px rgba(var(--a), .10); }
.screen .floor { position: absolute; left: -60%; right: -60%; bottom: -2px; height: 160%;
  background-image:
    linear-gradient(rgba(var(--a), .55) 1px, transparent 1px),
    linear-gradient(90deg, rgba(var(--a), .55) 1px, transparent 1px);
  background-size: 13px 9px; transform-origin: 50% 100%;
  transform: perspective(90px) rotateX(64deg);
  -webkit-mask-image: linear-gradient(to top, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 70%); opacity: .75; }
.screen .horizon { position: absolute; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, rgba(var(--a), 0), rgba(var(--a), .9), rgba(var(--a), 0));
  box-shadow: 0 0 10px 2px rgba(var(--a), .35); }
.screen .sheen { position: absolute; inset: 0;
  background: linear-gradient(168deg, rgba(255,255,255,.10) 0%, rgba(255,255,255,.02) 38%, rgba(255,255,255,0) 45%); }
.screen .scan { position: absolute; inset: 0;
  background: repeating-linear-gradient(0deg, rgba(255,255,255,.022) 0 1px, transparent 1px 3px); }
.hud { position: absolute; width: 6px; height: 6px; border-color: rgba(var(--a), .85); border-style: solid;
  filter: drop-shadow(0 0 2px rgba(var(--a), .9)); }

.plate { position: absolute; border-radius: 5px;
  background: linear-gradient(180deg, rgba(4,3,14,.85), rgba(16,13,42,.75));
  box-shadow: inset 0 1.5px 3px rgba(0,0,0,.9), inset 0 0 0 0.5px rgba(var(--a), .22),
              0 1px 0 rgba(255,255,255,.09); }
.blueprint { background-image:
    linear-gradient(rgba(var(--a), .09) 1px, transparent 1px),
    linear-gradient(90deg, rgba(var(--a), .09) 1px, transparent 1px),
    linear-gradient(180deg, rgba(4,3,14,.85), rgba(16,13,42,.75));
  background-size: 6px 6px, 6px 6px, auto; }

.pipe { position: absolute; border-radius: 1px; }
.pipeglow { position: absolute; filter: blur(2.5px); opacity: 1; mix-blend-mode: screen; }
"""


class Page:
    def __init__(self, fonts):
        self.fonts = fonts
        self.parts = []

    def add(self, s):
        self.parts.append(s)

    def html(self, extra_css=""):
        css = BASE_CSS.replace("{fonts}", self.fonts) + extra_css
        return (
            "<!doctype html><html><head><meta charset='utf-8'><style>"
            + css
            + "</style></head><body><div id='stage'>"
            + "\n".join(self.parts)
            + "</div></body></html>"
        )


def _vars(a, b=None):
    return f"--a:{rgb(a)};--b:{rgb(b or a)};"


def background_html(C, fonts):
    p = Page(fonts)
    rnd = random.Random(3026)

    # ---- Sky: nebula dust, aurora curtains and stars
    for cx, cy, r, col, a in [
        (760, 30, 360, C["pink"], 0.30),
        (480, 230, 420, "#6A3DFF", 0.26),
        (60, 520, 380, "#00C8FF", 0.22),
        (900, 560, 300, C["coral"], 0.16),
        (200, 20, 300, "#3D7BFF", 0.24),
    ]:
        p.add(
            f'<div class="abs" style="left:{cx - r}px;top:{cy - r}px;width:{2 * r}px;height:{2 * r}px;'
            f"border-radius:50%;background:radial-gradient(circle, rgba({rgb(col)},{a}) 0%, "
            f'rgba({rgb(col)},{a * 0.35}) 40%, rgba({rgb(col)},0) 70%)"></div>'
        )

    curtains = [
        # path in a 904 x 300 box, colours (edge, glow), top offset, blur
        ("M-20 120 C120 60 220 150 360 95 S620 40 760 105 S900 80 940 60", C["mint"], C["cyan"], -50, 6, .75),
        ("M-20 150 C150 110 260 60 420 120 S700 150 940 90", C["violet"], C["pink"], -30, 8, .8),
        ("M300 70 C420 30 520 110 640 60 S860 20 940 50", C["pink"], C["magenta"], -52, 6, .7),
        ("M-20 300 C160 260 300 160 470 175 S760 120 940 40", C["cyan"], C["violet"], 150, 14, .55),
        ("M-20 290 C200 280 380 250 560 255 S800 230 940 200", C["gold"], C["pink"], 245, 16, .5),
    ]
    for d, edge, glow, top, blur, strength in curtains:
        gid = f"cg{rnd.randrange(1 << 30)}"
        p.add(
            f'<svg class="abs" style="left:0;top:{top}px;filter:blur({blur}px);mix-blend-mode:screen;opacity:{strength}" '
            f'width="904" height="300" viewBox="0 0 904 300">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{glow}" stop-opacity="0"/>'
            f'<stop offset="0.7" stop-color="{glow}" stop-opacity=".75"/>'
            f'<stop offset="0.97" stop-color="{edge}" stop-opacity="1"/>'
            f'<stop offset="1" stop-color="{edge}" stop-opacity="0"/></linearGradient></defs>'
            f'<path d="{d} L940 -200 L-20 -200 Z" fill="url(#{gid})"/></svg>'
        )
        # Vertical rays give the curtains their texture
        p.add(
            f'<svg class="abs" style="left:0;top:{top}px;filter:blur(1.2px);mix-blend-mode:screen;opacity:{strength * 0.6};'
            f"-webkit-mask-image:repeating-linear-gradient(90deg, #000 0 1.5px, transparent 1.5px 5px, #000 5px 6px, transparent 6px 11px)\" "
            f'width="904" height="300" viewBox="0 0 904 300">'
            f'<path d="{d} L940 -200 L-20 -200 Z" fill="url(#{gid})"/></svg>'
        )

    for _ in range(170):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        r = rnd.choice([0.4, 0.5, 0.6, 0.7, 0.9])
        a = rnd.uniform(0.25, 0.9)
        p.add(
            f'<div class="abs" style="left:{x}px;top:{y}px;width:{2 * r}px;height:{2 * r}px;border-radius:50%;'
            f'background:rgba(255,255,255,{a});box-shadow:0 0 {2 * r}px rgba(200,220,255,{a * 0.8})"></div>'
        )
    for x, y, s in [(132, 22, 9), (590, 8, 7), (880, 46, 8), (52, 470, 7), (742, 535, 6)]:
        p.add(
            f'<div class="abs" style="left:{x - s}px;top:{y - 0.4}px;width:{2 * s}px;height:0.8px;'
            f'background:linear-gradient(90deg,rgba(255,255,255,0),#fff,rgba(255,255,255,0))"></div>'
            f'<div class="abs" style="left:{x - 0.4}px;top:{y - s}px;width:0.8px;height:{2 * s}px;'
            f'background:linear-gradient(180deg,rgba(255,255,255,0),#fff,rgba(255,255,255,0))"></div>'
            f'<div class="abs" style="left:{x - 2}px;top:{y - 2}px;width:4px;height:4px;border-radius:50%;'
            f'background:#fff;box-shadow:0 0 6px 2px rgba(190,210,255,.8)"></div>'
        )

    # ---- Light pipes in the gutters, under the glass, showing the signal flow
    def pipe(x0, y0, x1, y1, c0, c1, arrows=(), width=1.4):
        vertical = x0 == x1
        if vertical:
            top, h = min(y0, y1), abs(y1 - y0)
            direction = "180deg" if y1 > y0 else "0deg"
            geom = f"left:{x0 - width / 2}px;top:{top}px;width:{width}px;height:{h}px"
            gl = f"left:{x0 - 2.5}px;top:{top}px;width:5px;height:{h}px"
        else:
            left, w = min(x0, x1), abs(x1 - x0)
            direction = "90deg" if x1 > x0 else "270deg"
            geom = f"left:{left}px;top:{y0 - width / 2}px;width:{w}px;height:{width}px"
            gl = f"left:{left}px;top:{y0 - 2.5}px;width:{w}px;height:5px"
        grad = f"linear-gradient({direction}, {c0}, {c1})"
        p.add(f'<div class="pipeglow" style="{gl};background:{grad}"></div>')
        p.add(f'<div class="pipe" style="{geom};background:{grad};box-shadow:0 0 3px {c1}"></div>')
        for ax, ay, rot, col in arrows:
            p.add(
                f'<svg class="abs" style="left:{ax - 4}px;top:{ay - 4}px;transform:rotate({rot}deg);'
                f'filter:drop-shadow(0 0 2px {col}) drop-shadow(0 0 4px {col})" width="8" height="8" viewBox="0 0 8 8">'
                f'<path d="M2.2 1.4L5.6 4L2.2 6.6" fill="none" stroke="#ffffff" stroke-width="1.3" '
                f'stroke-linecap="round" stroke-linejoin="round"/></svg>'
            )

    # ---- Header bar
    p.add(
        '<div class="abs" style="left:0;top:0;width:904px;height:56px;'
        "background:linear-gradient(180deg, rgba(10,8,32,.42), rgba(22,16,58,.66));"
        "backdrop-filter:blur(3px) saturate(170%);"
        'box-shadow:0 10px 18px -8px rgba(0,0,0,.85), inset 0 -1px 0 rgba(255,255,255,.06)"></div>'
    )
    spectrum = ", ".join(f"{c} {int(o * 100)}%" for o, c in C["_spectrum"])
    p.add(
        f'<div class="abs" style="left:0;top:54.5px;width:904px;height:2px;filter:blur(3px);'
        f'background:linear-gradient(90deg, {spectrum});opacity:.9"></div>'
        f'<div class="abs" style="left:0;top:55.2px;width:904px;height:1.1px;'
        f'background:linear-gradient(90deg, {spectrum})"></div>'
        f'<div class="abs" style="left:0;top:56.3px;width:904px;height:5px;'
        f'background:linear-gradient(180deg, rgba(255,255,255,.10), rgba(255,255,255,0))"></div>'
    )

    def plate(x, y, w, h, accent, cls="plate", r=5):
        p.add(f'<div class="{cls}" style="{_vars(accent)}left:{x}px;top:{y}px;width:{w}px;height:{h}px;border-radius:{r}px"></div>')

    # Recessed holders for the header controls
    plate(4.5, 10.5, 45, 45, C["pink"])
    plate(51.5, 10.5, 46, 45, C["pink"])
    plate(98, 9.5, 47, 17.5, C["cyan"])
    plate(98, 39.5, 47, 16.5, C["cyan"])
    plate(559.5, 10, 36, 46, C["violet"])
    plate(604.5, 10, 140, 46, C["pink"])

    def hlabel(t, x, y, cls="hlabel", anchor="middle"):
        tx = {"middle": "translateX(-50%)", "start": "none", "end": "translateX(-100%)"}[anchor]
        p.add(f'<div class="{cls}" style="left:{x}px;top:{y}px;transform:{tx}">{t}</div>')

    for t, x, y in [("SCENE", 27, 2.6), ("MODE", 74.5, 2.6), ("SPLIT", 121.5, 2.6), ("POLY", 121.5, 30.2),
                    ("PATCH BROWSER", 352, 2.6), ("STATUS", 577.5, 2.6),
                    ("FX BYPASS &nbsp;/&nbsp; CHARACTER", 674.5, 2.6), ("OUTPUT", 827, 2.6)]:
        hlabel(t, x, y)
    for t, x in [("CATEGORY", 212), ("PATCH", 293), ("HISTORY", 483)]:
        hlabel(t, x, 46.6, "sublabel")

    # Patch browser: a holographic glass display
    p.add(
        f'<div class="screen" style="{_vars(C["violet"])}left:157px;top:12px;width:390px;height:28px;border-radius:7px;'
        f"box-shadow: inset 0 2px 6px rgba(0,0,0,.95), 0 1px 0 rgba(255,255,255,.12), 0 0 16px rgba({rgb(C['violet'])},.25)\">"
        '<div class="scan"></div><div class="sheen"></div></div>'
        f'<div class="abs" style="left:157px;top:12px;width:390px;height:28px;border-radius:7px;padding:1px;'
        f"background:linear-gradient(90deg, {C['cyan']}, {C['violet']} 50%, {C['pink']});"
        "-webkit-mask:linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);-webkit-mask-composite:xor;"
        f'filter:drop-shadow(0 0 3px rgba({rgb(C["violet"])},.8))"></div>'
    )
    # Output meter screen
    p.add(f'<div class="screen" style="{_vars(C["cyan"])}left:765px;top:13px;width:127px;height:17px;border-radius:4px"><div class="sheen"></div></div>')

    # ---- Panels
    def panel(x0, y0, x1, y1, a, b=None, header=None):
        hd = f'<div class="hdr" style="height:{header - y0}px"></div>' if header else ""
        p.add(
            f'<div class="panel" style="{_vars(a, b)}left:{x0}px;top:{y0}px;width:{x1 - x0}px;height:{y1 - y0}px">{hd}</div>'
        )

    def title(t, x, y, a, anchor="middle", ic=None, size=None):
        tx = {"middle": "translateX(-50%)", "start": "none", "end": "translateX(-100%)"}[anchor]
        fs = f"font-size:{size}px;" if size else ""
        icon_html = ""
        if ic:
            icon_html = f'<span style="display:inline-block;position:relative;width:11px;height:8px;vertical-align:-0.5px">' \
                        f'{icon(ic, "rgb(var(--a))", 8, 0, 0)}</span>'
        p.add(f'<div class="title" style="{_vars(a)}{fs}left:{x}px;top:{y}px;transform:{tx}">{icon_html}{t}</div>')

    def label(t, x, y, anchor="middle", color=None):
        tx = {"middle": "translateX(-50%)", "start": "none", "end": "translateX(-100%)"}[anchor]
        col = f"color:{color};" if color else ""
        p.add(f'<div class="label" style="{col}left:{x}px;top:{y}px;transform:{tx}">{t}</div>')

    def screen(x, y, w, h, a, floor=True, horizon=0.58, hud=True, r=6):
        inner = '<div class="scan"></div>'
        if floor:
            inner = (f'<div class="floor" style="height:{h * (1 - horizon) * 3.2}px"></div>'
                     f'<div class="horizon" style="top:{h * horizon}px"></div>') + inner
        inner += '<div class="sheen"></div>'
        p.add(f'<div class="screen" style="{_vars(a)}left:{x}px;top:{y}px;width:{w}px;height:{h}px;border-radius:{r}px">{inner}</div>')
        if hud:
            for hx, hy, bw in [(x + 2, y + 2, "1px 0 0 1px"), (x + w - 8, y + 2, "1px 1px 0 0"),
                               (x + 2, y + h - 8, "0 0 1px 1px"), (x + w - 8, y + h - 8, "0 1px 1px 0")]:
                p.add(f'<div class="hud" style="{_vars(a)}left:{hx}px;top:{hy}px;border-width:{bw}"></div>')

    def flank(cx, y, half, a, length):
        p.add(
            f'<div class="abs" style="left:{cx - half - 6 - length}px;top:{y}px;width:{length}px;height:1px;'
            f'background:linear-gradient(90deg, rgba({rgb(a)},0), rgba({rgb(a)},.9));box-shadow:0 0 4px rgba({rgb(a)},.6)"></div>'
            f'<div class="abs" style="left:{cx + half + 6}px;top:{y}px;width:{length}px;height:1px;'
            f'background:linear-gradient(90deg, rgba({rgb(a)},.9), rgba({rgb(a)},0));box-shadow:0 0 4px rgba({rgb(a)},.6)"></div>'
        )

    # Oscillator
    panel(2, 58, 147, 396, C["cyan"], C["azure"], header=77)
    title("OSCILLATOR", 8, 64.7, C["cyan"], "start", size=7.0)
    screen(4, 80, 141, 101, C["cyan"], horizon=0.62)
    p.add(f'<div class="abs" style="left:8px;top:212.5px;width:133px;height:1px;'
          f'background:linear-gradient(90deg, rgba({rgb(C["cyan"])},0), rgba({rgb(C["cyan"])},.5), rgba({rgb(C["cyan"])},0))"></div>')

    # Row 1
    panel(150, 58, 297, 190, C["sky"], C["cyan"], header=77)
    title("BEND DEPTH", 186, 64.6, C["sky"], ic="bend", size=7.0)
    title("PLAY MODE", 261, 64.6, C["sky"], ic="keys", size=7.0)
    label("DOWN", 173, 102.5)
    label("UP", 203, 102.5)
    plate(156, 109, 64, 19, C["sky"])
    plate(236.5, 89.5, 55, 52, C["sky"], "plate blueprint")

    panel(300, 58, 447, 190, C["azure"], C["violet"], header=77)
    title("FM ROUTING", 373.5, 64.6, C["azure"], ic="orbit")
    plate(304, 82, 140, 62, C["azure"], "plate blueprint")

    panel(450, 58, 597, 190, C["violet"], C["magenta"], header=77)
    title("FILTER CONFIG", 523.5, 64.6, C["violet"], ic="filter")
    plate(452, 80, 143, 64, C["violet"], "plate blueprint")

    panel(600, 58, 747, 190, C["magenta"], C["pink"], header=77)
    title("SCENE OUTPUT", 673.5, 64.6, C["magenta"], ic="speaker")

    # Row 2
    panel(150, 193, 297, 258, C["sky"], C["cyan"], header=212)
    title("SCENE", 157, 199.4, C["sky"], "start", "scene")
    panel(300, 193, 747, 258, C["violet"], C["pink"], header=212)
    p.add(f'<div class="abs" style="left:302px;top:193px;width:443px;height:19px;border-radius:9px 9px 0 0;'
          f'background:linear-gradient(90deg, rgba({rgb(C["violet"])},.30), rgba({rgb(C["magenta"])},.22) 50%, rgba({rgb(C["pink"])},.30))"></div>')
    title("◂ FILTER 1", 458, 199.4, C["violet"], "start", size=7.2)
    title("FILTER 2 ▸", 590, 199.4, C["pink"], "end", size=7.2)
    for x in (448.5, 598.5):
        p.add(f'<div class="abs" style="left:{x}px;top:216px;width:1px;height:38px;'
              f'background:linear-gradient(180deg, rgba(255,255,255,0), rgba(255,255,255,.18), rgba(255,255,255,0))"></div>')

    # Row 3
    panel(150, 262, 297, 396, C["cyan"], C["sky"])
    for t, x in [("1", 163.5), ("2", 183.5), ("3", 203.5), ("1×2", 223.5), ("2×3", 243.5), ("N", 263.5), ("GAIN", 284)]:
        label(t, x, 377.6)
    for x0, x1, t in [(155, 212, "OSC"), (214, 252, "RING")]:
        p.add(
            f'<div class="abs" style="left:{x0}px;top:387px;width:{x1 - x0}px;height:7px;border-radius:3.5px;'
            f"background:linear-gradient(180deg, #9ff6ff, {C['cyan']} 55%, #1a9fc0);"
            f"box-shadow:0 0 6px rgba({rgb(C['cyan'])},.6), inset 0 0.5px 0 rgba(255,255,255,.8);"
            f"font-family:'OutfitB';font-size:5.4px;letter-spacing:.2em;color:#06202a;text-align:center;line-height:7.2px\">{t}</div>"
        )

    panel(300, 262, 447, 396, C["pink"], C["violet"])
    title("KEYTRACK", 331, 290, C["pink"], size=7.0)
    p.add(
        f'<div class="abs" style="{_vars(C["pink"])}left:377.5px;top:282.5px;width:64px;height:108px;border-radius:7px;'
        f"background:linear-gradient(180deg, rgba({rgb(C['pink'])},.20), rgba({rgb(C['pink'])},.04));"
        f"box-shadow:inset 0 0 0 1px rgba({rgb(C['pink'])},.45), inset 0 1px 0 rgba(255,255,255,.2), 0 0 12px rgba({rgb(C['pink'])},.18)\"></div>"
    )
    title("SHAPER", 409.5, 290, C["pink"], size=7.0)
    screen(383, 308.5, 36, 50, C["pink"], floor=False, hud=False, r=4)
    for t, x in [("▸F1", 317), ("▸F2", 337), ("HP", 365)]:
        label(t, x, 377.6)

    panel(450, 262, 597, 396, C["rose"], C["pink"])
    title("FILTER EG", 522, 290, C["rose"], ic="adsr")
    flank(522, 293.5, 27, C["rose"], 18)
    for t, x in [("A", 466), ("D", 486), ("S", 506), ("R", 526), ("▸F1", 559), ("▸F2", 579)]:
        label(t, x, 377.6)

    panel(600, 262, 747, 396, C["coral"], C["rose"])
    title("AMP EG", 649, 290, C["coral"], ic="adsr")
    flank(649, 293.5, 22, C["coral"], 12)
    title("AMP", 719, 290, C["coral"])
    for t, x in [("A", 616), ("D", 636), ("S", 656), ("R", 676), ("VEL▸GAIN", 723)]:
        label(t, x, 377.6)

    # Modulation sources and the LFO editor
    panel(2, 400, 747, 471, C["gold"], C["coral"])
    panel(2, 475, 747, 567, C["gold"], C["coral"])
    p.add(
        f'<div class="abs" style="left:3px;top:476px;width:21px;height:90px;border-radius:8px 0 0 8px;'
        f"background:linear-gradient(180deg, rgba({rgb(C['gold'])},.42), rgba({rgb(C['coral'])},.14));"
        f'box-shadow:inset -1px 0 0 rgba({rgb(C["gold"])},.6), 1px 0 8px rgba({rgb(C["gold"])},.25)"></div>'
    )
    plate(168, 480, 59, 46, C["gold"])
    plate(168, 543, 59, 19, C["gold"])
    plate(233, 477.5, 69, 88, C["gold"], "plate blueprint")
    screen(302, 477.5, 294, 88, C["gold"], horizon=0.5)
    title("LFO EG", 674, 481.5, C["gold"], ic="lfo")
    flank(674, 485, 22, C["gold"], 26)
    for t, x in [("D", 624), ("A", 644), ("H", 664), ("D", 684), ("S", 704), ("R", 724)]:
        label(t, x, 555.2)

    # Effects
    panel(750, 58, 902, 190, C["mint"], C["cyan"], header=77)
    title("EFFECTS", 826, 64.6, C["mint"], ic="fx")
    plate(756, 75, 143, 61, C["mint"], "plate blueprint")
    panel(750, 193, 902, 567, C["mint"], C["lime"], header=212)

    # Light pipes ride on top of the glass
    pipes = []
    # oscillators into the mixer
    pipes.append((148.5, 268, 148.5, 390, C["cyan"], C["cyan"], [(148.5, 329, 0, C["cyan"])]))
    # mixer into the filters
    pipes.append((298.5, 384, 298.5, 200, C["cyan"], C["violet"], [(298.5, 232, 0, C["violet"])]))
    # filters through the waveshaper to the amp
    pipes.append((303, 260, 744, 260, C["violet"], C["coral"],
                  [(372, 260, 90, C["pink"]), (522, 260, 0, C["rose"]), (672, 260, 90, C["coral"])]))
    # amp up to the scene output, and on to the effects
    pipes.append((748.5, 392, 748.5, 193, C["coral"], C["magenta"], [(748.5, 300, -90, C["magenta"])]))
    pipes.append((748.5, 190, 748.5, 62, C["magenta"], C["mint"], [(748.5, 126, 0, C["mint"])]))
    # modulation rises into everything
    pipes.append((8, 398, 741, 398, C["gold"], C["coral"],
                  [(x, 398, -90, C["gold"]) for x in (75, 224, 374, 523, 672)]))
    for args in pipes:
        pipe(*args)

    # Wordmark
    p.add(
        f'<div class="abs" style="left:757px;top:546px;width:86px;height:1px;'
        f'background:linear-gradient(90deg, rgba(255,255,255,.45), rgba(255,255,255,0))"></div>'
        f"<div class=\"abs\" style=\"left:757px;top:549.5px;font-family:'OutfitB';font-size:12.5px;letter-spacing:.07em;line-height:1;"
        f"background:linear-gradient(90deg, {spectrum});-webkit-background-clip:text;color:transparent;"
        f'filter:drop-shadow(0 0 4px rgba(160,120,255,.55))">SURGE XT</div>'
    )

    # ---- One light for the whole instrument, and a gentle vignette
    p.add(
        '<div class="abs" style="left:0;top:0;width:904px;height:569px;pointer-events:none;mix-blend-mode:screen;'
        'background:radial-gradient(70% 60% at 12% 0%, rgba(255,255,255,.07), rgba(255,255,255,0) 70%)"></div>'
        '<div class="abs" style="left:0;top:0;width:904px;height:569px;pointer-events:none;'
        'background:radial-gradient(130% 120% at 50% 45%, rgba(0,0,0,0) 60%, rgba(0,0,0,.35) 100%)"></div>'
    )

    return p.html()


# ---------------------------------------------------------------------------
# Slider handles: jewels set in a chrome bezel
# ---------------------------------------------------------------------------

HANDLE_CSS = """
html, body { margin: 0; background: transparent; overflow: hidden; }
.j { position: absolute; border-radius: 50%; }
"""


def _jewel(cx, cy, core, kind="normal", R=6.0, vertical=False):
    """One handle: contact shadow, halo, chrome bezel, gem core, specular glint and notch."""
    c = rgb(core)
    parts = []
    if kind == "hover":
        # Drawn over the handle, so only a luminous ring outside the bezel
        return (
            f'<div class="j" style="left:{cx - R - 3.2}px;top:{cy - R - 3.2}px;width:{2 * R + 6.4}px;height:{2 * R + 6.4}px;'
            f'background:radial-gradient(circle, rgba({c},0) 60%, rgba({c},.95) 67%, rgba({c},0) 100%)"></div>'
            f'<div class="j" style="left:{cx - R - 0.6}px;top:{cy - R - 0.6}px;width:{2 * R + 1.2}px;height:{2 * R + 1.2}px;'
            f'box-shadow:0 0 0 0.7px rgba(255,255,255,.9)"></div>'
        )
    parts.append(
        f'<div class="j" style="left:{cx - R}px;top:{cy + R * 0.35}px;width:{2 * R}px;height:{R * 1.1}px;'
        f'background:rgba(0,0,0,.8);filter:blur(1.5px)"></div>'
    )
    parts.append(
        f'<div class="j" style="left:{cx - R - 3.2}px;top:{cy - R - 3.2}px;width:{2 * R + 6.4}px;height:{2 * R + 6.4}px;'
        f'background:radial-gradient(circle, rgba({c},.55) 42%, rgba({c},0) 70%)"></div>'
    )
    parts.append(
        f'<div class="j" style="left:{cx - R}px;top:{cy - R}px;width:{2 * R}px;height:{2 * R}px;'
        "background:conic-gradient(from 200deg, #ffffff, #8c86c4, #f4f2ff, #4e478c, #d8d3ff, #ffffff);"
        f'box-shadow:0 0 0 0.35px rgba(255,255,255,.6), 0 0 6px 0.5px rgba({c},.55)"></div>'
    )
    ri = R - 1.55
    parts.append(
        f'<div class="j" style="left:{cx - ri}px;top:{cy - ri}px;width:{2 * ri}px;height:{2 * ri}px;'
        f"background:radial-gradient(circle at 40% 32%, #ffffff 0, rgba({c},1) 34%, "
        f"color-mix(in srgb, rgb({c}) 60%, #1b0b40) 78%, #14082c 100%);"
        f'box-shadow:inset 0 -1px 1.4px color-mix(in srgb, rgb({c}) 55%, white), inset 0 0 0 0.4px rgba(0,0,0,.6)"></div>'
    )
    if kind == "sync":
        rs = 1.8
        parts.append(
            f'<div class="j" style="left:{cx - rs}px;top:{cy - rs}px;width:{2 * rs}px;height:{2 * rs}px;'
            f'background:#fff;box-shadow:0 0 3px #fff, 0 0 0 0.6px rgba({c},1)"></div>'
        )
    parts.append(
        f'<div class="j" style="left:{cx - R * 0.55}px;top:{cy - R * 0.78}px;width:{R * 0.62}px;height:{R * 0.36}px;'
        f'background:radial-gradient(ellipse, rgba(255,255,255,.98), rgba(255,255,255,0) 72%)"></div>'
    )
    if kind != "sync":
        nw, nh = (2.6, 0.85) if vertical else (0.85, 2.6)
        parts.append(
            f'<div class="abs" style="position:absolute;left:{cx - nw / 2}px;top:{cy - nh / 2}px;width:{nw}px;height:{nh}px;'
            f'border-radius:0.5px;background:rgba(12,6,32,.55);box-shadow:0 0.4px 0 rgba(255,255,255,.35)"></div>'
        )
    return "".join(parts)


def handle_sheet_html(accent, mod_accent, vertical, kind="normal"):
    """The 2 x 2 sprite sheet Surge expects: columns are value / modulation handle."""
    if vertical:
        w, h, centres = 48, 56, [(9, 11.5), (33, 11.5), (9, 39.5), (33, 39.5)]
    else:
        w, h, centres = 56, 48, [(11.5, 8.5), (39.5, 8.5), (11.5, 32.5), (39.5, 32.5)]
    body = []
    for i, (cx, cy) in enumerate(centres):
        core = accent if i % 2 == 0 else mod_accent
        body.append(_jewel(cx, cy, core, kind, vertical=vertical))
    return (
        f"<!doctype html><html><head><style>{HANDLE_CSS}</style></head>"
        f'<body style="width:{w}px;height:{h}px">' + "".join(body) + "</body></html>"
    ), w, h


def sync_marker_html(vertical, hover=False):
    """Tempo sync is marked by a white pearl in the heart of whichever jewel it sits on."""
    cx, cy = (9, 11.5) if vertical else (11.5, 8.5)
    rs = 2.0
    body = (
        f'<div class="j" style="left:{cx - rs}px;top:{cy - rs}px;width:{2 * rs}px;height:{2 * rs}px;'
        "background:radial-gradient(circle at 40% 35%, #ffffff 0, #f2efff 55%, #b9b0ee 100%);"
        'box-shadow:0 0 0 0.5px rgba(10,6,30,.7), 0 0 3px 0.5px rgba(255,255,255,.9)"></div>'
    )
    if hover:
        body += _jewel(cx, cy, "#E6E0FF", "hover")
    return (
        f"<!doctype html><html><head><style>{HANDLE_CSS}</style></head>"
        f'<body style="width:28px;height:24px">{body}</body></html>'
    ), 28, 24
