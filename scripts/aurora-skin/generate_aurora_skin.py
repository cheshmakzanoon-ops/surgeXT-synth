#!/usr/bin/env python3
"""
Generates the Aurora skin (resources/data/skins/aurora.surge-skin).

Aurora keeps the control layout of the Surge Dark skin and redesigns everything
you see. The instrument is a set of frosted glass tiles floating over an aurora
lit night sky, each edge lit in the colour of its section, with recessed
holographic displays and light pipes that show the signal flow. Slider handles
are jewels in chrome bezels in their section's colour, and sliders draw their
value as a glowing fill.

The background and handles are drawn in HTML/CSS (aurora_art.py) and rendered
to 100/200/400% PNGs with Chromium. The other widget sprites come from the Dark
skin with their palette remapped and their buttons sculpted with gradients, so
re-running this script after the Dark skin changes keeps both in step.

Usage: python3 scripts/aurora-skin/generate_aurora_skin.py
Requires: Node.js with Playwright and Chromium (npm install playwright)
"""

import colorsys
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import aurora_art


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


def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


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


# Button faces: flat fills become top-lit gradients so every button reads as a
# sculpted, slightly convex piece of coloured glass
ON_FILLS = {remap("#FF9000"), remap("#FF9300"), C["pink"]}
FACE_FILLS = {remap("#242424"), remap("#1F1F1F"), remap("#28282A"), remap("#151515")}
SCULPT_DEFS = (
    '<linearGradient id="aurora_on" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#FFC2EA"/><stop offset="0.45" stop-color="#FF4FB8"/>'
    '<stop offset="1" stop-color="#C42887"/></linearGradient>'
    '<linearGradient id="aurora_face" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#2E2868"/><stop offset="1" stop-color="#110E31"/></linearGradient>'
    '<linearGradient id="aurora_cyan" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#B8F7FF"/><stop offset="0.45" stop-color="#3DC8F0"/>'
    '<stop offset="1" stop-color="#1A6FA8"/></linearGradient>'
)


def is_cyan_face(hexcol):
    r, g, b = hex_to_rgb(hexcol)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return 180 <= h * 360 <= 215 and s > 0.5 and 0.3 <= l <= 0.7


def sculpt(text):
    def swap(m):
        col = m.group(2).upper()
        if col in ON_FILLS:
            return f'{m.group(1)}url(#aurora_on)"'
        if col in FACE_FILLS:
            return f'{m.group(1)}url(#aurora_face)"'
        if is_cyan_face(col):
            return f'{m.group(1)}url(#aurora_cyan)"'
        return m.group(0)

    sculpted = re.sub(r'(<(?:rect|path)\b[^>]*?\sfill=")(#[0-9A-Fa-f]{6})"', swap, text)
    if sculpted == text:
        return text
    if "<defs>" in sculpted:
        return sculpted.replace("<defs>", "<defs>" + SCULPT_DEFS, 1)
    return sculpted.replace("</svg>", f"<defs>{SCULPT_DEFS}</defs></svg>")


def rails_horizontal():
    """Slider trays: recessed grooves. Columns are unmodulated / modulated by
    another source / modulated by the selected source; rows are plain, bipolar
    and semitone, then the same again for light panels."""
    out = []
    for col in range(3):
        for row in range(6):
            ox, cy, kind = 133 * col, 14 * row + 7, row % 3
            out.append(
                f'<rect x="{ox + 6}" y="{cy - 1.75}" width="121" height="3.5" rx="1.75" fill="url(#groove_h)"/>'
                f'<rect x="{ox + 7}" y="{cy + 1.85}" width="119" height="0.5" rx="0.25" fill="#FFFFFF" fill-opacity="0.12"/>'
            )
            if col == 1:
                out.append(f'<rect x="{ox + 5.75}" y="{cy - 2}" width="121.5" height="4" rx="2" fill="none" '
                           f'stroke="{C["mint"]}" stroke-opacity="0.45" stroke-width="0.6"/>')
            if col == 2:
                out.append(f'<rect x="{ox + 6}" y="{cy - 1.75}" width="121" height="3.5" rx="1.75" '
                           f'fill="{C["mint"]}" fill-opacity="0.35"/>'
                           f'<rect x="{ox + 5.75}" y="{cy - 2}" width="121.5" height="4" rx="2" fill="none" '
                           f'stroke="{C["mint"]}" stroke-width="0.8"/>')
            tick = "#8C84D0"
            for x in (10.5, 122.5):
                out.append(f'<circle cx="{ox + x}" cy="{cy - 4}" r="0.7" fill="{tick}"/>')
            if kind == 1:
                out.append(f'<rect x="{ox + 66}" y="{cy - 5}" width="1" height="2.4" rx="0.5" fill="{tick}"/>')
            if kind == 2:
                for i in range(15):
                    x = 10.5 + 8 * i
                    h = 2.2 if i == 7 else 1.1
                    out.append(f'<rect x="{ox + x - 0.4}" y="{cy + 3}" width="0.8" height="{h}" rx="0.4" '
                               f'fill="{tick}" fill-opacity="0.8"/>')
    return (
        '<svg width="399" height="84" viewBox="0 0 399 84" fill="none" xmlns="http://www.w3.org/2000/svg">'
        + "".join(out)
        + '<defs><linearGradient id="groove_h" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#000000"/><stop offset="1" stop-color="#14103A"/></linearGradient></defs></svg>'
    )


def rails_vertical():
    """Vertical trays: plain, bipolar, mini and mini bipolar rows."""
    rows = [(5, 70, 9.5, 65.5, None), (80, 145, 84.5, 140.5, 112.5),
            (155, 203, 159.5, 198.5, None), (230, 278, 234.5, 273.5, 254)]
    out = []
    for col in range(3):
        cx = 16 * col + 8
        for y0, y1, t0, t1, mid in rows:
            out.append(
                f'<rect x="{cx - 1.75}" y="{y0}" width="3.5" height="{y1 - y0}" rx="1.75" fill="url(#groove_v)"/>'
                f'<rect x="{cx + 1.85}" y="{y0 + 1}" width="0.5" height="{y1 - y0 - 2}" rx="0.25" fill="#FFFFFF" fill-opacity="0.10"/>'
            )
            if col == 1:
                out.append(f'<rect x="{cx - 2}" y="{y0 - 0.25}" width="4" height="{y1 - y0 + 0.5}" rx="2" fill="none" '
                           f'stroke="{C["mint"]}" stroke-opacity="0.45" stroke-width="0.6"/>')
            if col == 2:
                out.append(f'<rect x="{cx - 1.75}" y="{y0}" width="3.5" height="{y1 - y0}" rx="1.75" '
                           f'fill="{C["mint"]}" fill-opacity="0.35"/>'
                           f'<rect x="{cx - 2}" y="{y0 - 0.25}" width="4" height="{y1 - y0 + 0.5}" rx="2" fill="none" '
                           f'stroke="{C["mint"]}" stroke-width="0.8"/>')
            for y in (t0, t1):
                out.append(f'<circle cx="{cx - 4}" cy="{y}" r="0.7" fill="#8C84D0"/>')
            if mid:
                out.append(f'<rect x="{cx - 5}" y="{mid - 0.5}" width="2.4" height="1" rx="0.5" fill="#8C84D0"/>')
    return (
        '<svg width="48" height="282" viewBox="0 0 48 282" fill="none" xmlns="http://www.w3.org/2000/svg">'
        + "".join(out)
        + '<defs><linearGradient id="groove_v" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#000000"/><stop offset="1" stop-color="#14103A"/></linearGradient></defs></svg>'
    )


def build_widgets():
    out = DST / "SVG"
    out.mkdir(parents=True, exist_ok=True)
    for src in sorted((SRC / "SVG").glob("*.svg")):
        if src.name == "bmp00102.svg":
            continue
        text = remap_svg(src.read_text(), src.name)
        if HANDLE_FILES.match(src.name):
            text = glow_handles(text)
        else:
            text = sculpt(text)
        (out / src.name).write_text(text)
    (out / "bmp00154.svg").write_text(rails_horizontal())
    (out / "bmp00105.svg").write_text(rails_vertical())


# ---------------------------------------------------------------------------
# Rendered artwork: background and jewel handles
# ---------------------------------------------------------------------------

ZOOMS = (1, 2, 4)

# Each section's colour, used for its handles and value fills
ACCENTS = {
    "cyan": C["cyan"], "sky": C["sky"], "azure": C["azure"], "violet": C["violet"],
    "magenta": C["magenta"], "pink": C["pink"], "rose": C["rose"], "coral": C["coral"],
    "gold": C["gold"], "mint": C["mint"], "pearl": "#E6E0FF",
}


def multi_image(image_id, stem):
    rows = "".join(
        f'\n            <image zoom-level="{100 * z}" resource="PNG/{stem}_{100 * z}.png"/>' for z in ZOOMS
    )
    return f'        <multi-image id="{image_id}">{rows}\n        </multi-image>'


def build_pngs():
    """Renders the HTML artwork and returns the multi-image declarations for skin.xml."""
    png = DST / "PNG"
    if png.exists():
        shutil.rmtree(png)
    png.mkdir(parents=True)

    palette = dict(C)
    palette["_spectrum"] = SPECTRUM
    jobs, images = [], []

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        def job(stem, html, w, h, image_id):
            page = tmp / f"{stem}.html"
            page.write_text(html)
            jobs.append({"html": str(page), "out": str(png / stem), "width": w, "height": h,
                         "scales": list(ZOOMS)})
            images.append(multi_image(image_id, stem))

        job("background", aurora_art.background_html(palette, FONTS.resolve().as_uri()), W, H, "aurora-bg")

        for name, col in ACCENTS.items():
            for orient, vertical in (("h", False), ("v", True)):
                html, w, h = aurora_art.handle_sheet_html(col, C["mint"], vertical)
                job(f"handle_{orient}_{name}", html, w, h, f"aurora-handle-{orient}-{name}")

        for orient, vertical in (("h", False), ("v", True)):
            html, w, h = aurora_art.handle_sheet_html("#E6E0FF", "#E6E0FF", vertical, "hover")
            job(f"handle_{orient}_hover", html, w, h, f"aurora-handle-{orient}-hover")
            for hover in (False, True):
                html, w, h = aurora_art.sync_marker_html(vertical, hover)
                stem = f"handle_{orient}_sync" + ("_hover" if hover else "")
                job(stem, html, w, h, f"aurora-{stem.replace('_', '-')}")

        (tmp / "jobs.json").write_text(json.dumps(jobs))
        subprocess.run(["node", str(Path(__file__).parent / "render_png.js"), str(tmp / "jobs.json")],
                       check=True)

    return images


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
        "modbutton.sheen": "#FFFFFF2E",
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


def build_skin_xml(images):
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
        + "\n\n"
        + "\n".join(images)
        + '\n\n        <background image="aurora-bg"/>\n\n        '
    )
    body = src[:globals_start] + head + src[first_image:]
    body = re.sub(
        r"<surge-skin [^>]*>",
        '<surge-skin name="Aurora" author="Surge Synth Team" '
        'authorURL="https://surge-synth-team.org/" version="2">',
        body,
        count=1,
    )

    # One slider class per section and orientation: jewel handles and a glowing value fill
    classes = []
    for name, col in ACCENTS.items():
        for orient in ("h", "v"):
            classes.append(
                f'        <class name="aurora-{orient}-{name}" parent="Slider" '
                f'handle_image="aurora-handle-{orient}-{name}" '
                f'handle_hover_image="aurora-handle-{orient}-hover" '
                f'handle_temposync_image="aurora-handle-{orient}-sync" '
                f'handle_temposync_hover_image="aurora-handle-{orient}-sync-hover" '
                f'value_fill_color="{col}"/>'
            )
    body = body.replace("<component-classes>", "<component-classes>\n" + "\n".join(classes), 1)

    # Put every slider in its section's class, keeping the Dark skin's positions
    for cid, cls in slider_classes().items():
        pattern = re.compile(r'(<control ui_identifier="' + re.escape(cid) + r'"[^>]*?)(\s*/>)')
        m = pattern.search(body)
        if m:
            tag = re.sub(r'\sclass="[^"]*"', "", m.group(1))
            body = body[: m.start()] + f'{tag} class="{cls}"{m.group(2)}' + body[m.end():]
        else:
            body = body.replace(
                "</controls>", f'    <control ui_identifier="{cid}" class="{cls}"/>\n    </controls>', 1
            )
    (DST / "skin.xml").write_text(body)


def slider_classes():
    """Which section every slider belongs to."""
    h, v = {}, {}
    h.update({f"osc.{p}": "cyan" for p in ["pitch"] + [f"param_{i}" for i in range(1, 8)]})
    h.update({f"scene.{p}": "sky" for p in ("drift", "noise_color", "pitch", "portamento")})
    h["scene.fmdepth"] = "azure"
    h.update({"filter.feedback": "violet", "filter.cutoff_1": "violet", "filter.resonance_1": "violet",
              "filter.balance": "magenta", "filter.cutoff_2": "pink", "filter.resonance_2": "pink"})
    h.update({f"scene.{p}": "magenta" for p in ("volume", "pan", "width", "send_fx_1", "send_fx_2",
                                                 "send_fx_3", "send_fx_4")})
    h.update({f"lfo.{p}": "gold" for p in ("rate", "phase", "deform", "amplitude")})
    h.update({f"fx.param_{i}": "mint" for i in range(1, 13)})
    h.update({f"global.fx{i}_return": "mint" for i in range(1, 5)})
    h["global.volume"] = "pearl"

    v.update({f"mixer.level_{p}": "cyan" for p in ("o1", "o2", "o3", "ring12", "ring23", "noise",
                                                   "prefiltergain")})
    v.update({f"filter.{p}": "pink" for p in ("keytrack_1", "keytrack_2", "highpass", "waveshaper_drive")})
    v.update({"filter.envmod_1": "rose", "filter.envmod_2": "rose"})
    v.update({f"feg.{p}": "rose" for p in ("attack", "decay", "sustain", "release")})
    v.update({f"aeg.{p}": "coral" for p in ("attack", "decay", "sustain", "release")})
    v.update({"scene.velocity_sensitivity": "coral", "scene.gain": "coral"})
    v.update({f"lfo.{p}": "gold" for p in ("delay", "attack", "hold", "decay", "sustain", "release")})

    res = {k: f"aurora-h-{a}" for k, a in h.items()}
    res.update({k: f"aurora-v-{a}" for k, a in v.items()})
    return res


def main():
    if (DST / "SVG").exists():
        shutil.rmtree(DST / "SVG")
    build_widgets()
    images = build_pngs()
    build_skin_xml(images)
    print(f"Wrote {DST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
