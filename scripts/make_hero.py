"""Turns a portrait photo into assets/hero-light.svg and assets/hero-dark.svg:
scrambled letters that settle into an ASCII portrait, in black or white on a transparent background.

Only needs to run once:  python scripts/make_hero.py path/to/photo.png
The photo itself is not stored in the repo.
"""
import base64
import random
import sys

from PIL import Image, ImageFilter, ImageOps

from common import write_asset

COLS = 56
CHAR_W = 6.6          # width of one character in the SVG
LINE_H = 12.0         # height of one line in the SVG
RAMP = " .:-=+*#%@"   # light to dark
NOISE = "abcdefghijkmnopqrstuvwxyz0123456789#%*+=?"
CYCLE = 14            # seconds for one full loop
THEMES = {"light": "#1f2328", "dark": "#e6edf3"}   # GitHub's own text colours


def portrait_rows(photo):
    img = Image.open(photo).convert("RGBA")
    alpha = img.getchannel("A").point(lambda a: 255 if a > 128 else 0)
    img = img.crop(alpha.getbbox())
    alpha = img.getchannel("A")

    gray = ImageOps.grayscale(img.convert("RGB")).filter(ImageFilter.UnsharpMask(radius=10, percent=260, threshold=0))
    edges = gray.filter(ImageFilter.FIND_EDGES)

    cell_w = img.width / COLS
    cell_h = cell_w * LINE_H / CHAR_W
    rows = int(img.height / cell_h)

    cells = []
    for r in range(rows):
        for c in range(COLS):
            box = (int(c * cell_w), int(r * cell_h), int((c + 1) * cell_w), int((r + 1) * cell_h))
            a = alpha.crop(box)
            area = a.width * a.height
            if sum(a.get_flattened_data()) / (255 * area) < 0.4:
                cells.append(None)
                continue
            cells.append((sum(gray.crop(box).get_flattened_data()) / area,
                          sum(edges.crop(box).get_flattened_data()) / area))

    # Spread brightness evenly over the ramp so the face keeps its detail.
    lums = sorted(v[0] for v in cells if v)
    top_edge = sorted(v[1] for v in cells if v)[int(len(lums) * 0.95)] or 1

    def rank(x):
        return sum(1 for v in lums if v < x) / len(lums)

    lines = []
    for r in range(rows):
        line = ""
        for c in range(COLS):
            v = cells[r * COLS + c]
            if v is None:
                line += " "
                continue
            ink = 0.7 * (1 - rank(v[0])) + 0.3 * min(v[1] / top_edge, 1)
            line += RAMP[1 + min(int(ink * (len(RAMP) - 1)), len(RAMP) - 2)]
        lines.append(line)
    return lines


def build_svg(lines, fg):
    rnd = random.Random(3)
    art_w = COLS * CHAR_W
    pad = 8
    width = int(art_w + pad * 2)
    art_h = len(lines) * LINE_H
    name_y = art_h + 42
    height = int(name_y + 14)
    flag = base64.b64encode(b"flag{murakaza_neza}").decode()

    css = f"""
    text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:11px;white-space:pre;fill:{fg}}}
    .n{{fill-opacity:.4}}
    .r{{animation:show {CYCLE}s linear infinite both}}
    .z{{animation:hide {CYCLE}s linear infinite both}}
    .f{{opacity:0;animation:flick .45s steps(1) infinite}}
    .f1{{animation-delay:.15s}} .f2{{animation-delay:.3s}}
    @keyframes show{{0%,12%{{opacity:0}}16%,86%{{opacity:1}}90%,100%{{opacity:0}}}}
    @keyframes hide{{0%,12%{{opacity:1}}16%,86%{{opacity:0}}90%,100%{{opacity:1}}}}
    @keyframes flick{{0%{{opacity:1}}33%,100%{{opacity:0}}}}
    .name{{font-size:20px;letter-spacing:.12em}}
    """
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img">',
        "<title>Flavien Mbishibishi, drawn in letters</title>",
        f"<!-- you found a quiet corner: {flag} -->",
        f"<style>{css}</style>",
        f'<defs><clipPath id="type"><rect x="0" y="{name_y - 22}" height="30" width="0">'
        f'<animate attributeName="width" values="0;0;{width};{width};0;0" keyTimes="0;.28;.4;.88;.9;1" '
        f'dur="{CYCLE}s" repeatCount="indefinite"/></rect></clipPath></defs>',
    ]
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        y = (i + 1) * LINE_H
        delay = f'style="animation-delay:{i * 0.05:.2f}s"'
        tl = f'x="{pad}" y="{y:.1f}" textLength="{art_w:.1f}" lengthAdjust="spacing"'
        out.append(f'<g class="z" {delay}>')
        for k in range(3):
            out.append(f'<text class="n f f{k}" {tl}>{"".join(" " if ch == " " else rnd.choice(NOISE) for ch in line)}</text>')
        out.append("</g>")
        out.append(f'<text class="r" {delay} {tl}>{line}</text>')
    out += [
        f'<text class="name" x="{width / 2}" y="{name_y}" text-anchor="middle" clip-path="url(#type)">FLAVIEN MBISHIBISHI</text>',
        "</svg>",
    ]
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/make_hero.py path/to/photo.png")
    rows = portrait_rows(sys.argv[1])
    for theme, fg in THEMES.items():
        write_asset(f"hero-{theme}.svg", build_svg(rows, fg))
    print("wrote assets/hero-light.svg and assets/hero-dark.svg")
