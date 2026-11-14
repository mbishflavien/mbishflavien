"""Turns a portrait photo into assets/hero.svg: scrambled letters that settle into an ASCII portrait.

Only needs to run once:  python scripts/make_hero.py path/to/photo.png
The photo itself is not stored in the repo.
"""
import base64
import random
import sys

from PIL import Image, ImageFilter, ImageOps

from common import write_asset

COLS = 72
CHAR_W = 6.6          # width of one character in the SVG
LINE_H = 12.0         # height of one line in the SVG
RAMP = " .:-=+*#%@"   # light to dark
NOISE = "abcdefghijkmnopqrstuvwxyz0123456789#%*+=?"
CYCLE = 14            # seconds for one full loop

PAPER, INK, OCHRE = "#f3ead9", "#2b1d16", "#9c3b22"


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
            cover = sum(a.get_flattened_data()) / (255 * a.width * a.height)
            if cover < 0.4:
                cells.append(None)
                continue
            lum = sum(gray.crop(box).get_flattened_data()) / (a.width * a.height)
            edge = sum(edges.crop(box).get_flattened_data()) / (a.width * a.height)
            cells.append((lum, edge))

    # Spread brightness evenly over the ramp so the face keeps its detail.
    lums = sorted(v[0] for v in cells if v)
    top_edge = sorted(v[1] for v in cells if v)[int(len(lums) * 0.95)] or 1

    def rank(x):
        lo, hi = 0, len(lums)
        while lo < hi:
            mid = (lo + hi) // 2
            if lums[mid] < x:
                lo = mid + 1
            else:
                hi = mid
        return lo / len(lums)

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


def scramble(line, rnd):
    return "".join(" " if ch == " " else rnd.choice(NOISE) for ch in line)


def build_svg(lines):
    rnd = random.Random(3)
    pad_x, top = 34, 40
    art_w = COLS * CHAR_W
    width = int(art_w + pad_x * 2)
    art_h = len(lines) * LINE_H
    height = int(top + art_h + 96)
    name_y = top + art_h + 40
    flag = base64.b64encode(b"flag{murakaza_neza}").decode()

    css = f"""
    text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:11px;white-space:pre}}
    .a{{fill:{INK}}} .n{{fill:{OCHRE}}}
    .r{{animation:show {CYCLE}s linear infinite both}}
    .z{{animation:hide {CYCLE}s linear infinite both}}
    .f{{opacity:0;animation:flick .45s steps(1) infinite}}
    .f1{{animation-delay:.15s}} .f2{{animation-delay:.3s}}
    @keyframes show{{0%,12%{{opacity:0}}16%,86%{{opacity:1}}90%,100%{{opacity:0}}}}
    @keyframes hide{{0%,12%{{opacity:1}}16%,86%{{opacity:0}}90%,100%{{opacity:1}}}}
    @keyframes flick{{0%{{opacity:1}}33%,100%{{opacity:0}}}}
    .title{{font-family:Georgia,'Times New Roman',serif;font-size:24px;fill:{INK}}}
    .sub{{font-family:Georgia,'Times New Roman',serif;font-size:14px;fill:{OCHRE};font-style:italic}}
    .cover{{fill:{PAPER};animation:type {CYCLE}s steps(22) infinite both}}
    .cover2{{fill:{PAPER};animation:type2 {CYCLE}s steps(28) infinite both}}
    @keyframes type{{0%,30%{{transform:translateX(0)}}40%,88%{{transform:translateX({width}px)}}90%,100%{{transform:translateX(0)}}}}
    @keyframes type2{{0%,40%{{transform:translateX(0)}}50%,88%{{transform:translateX({width}px)}}90%,100%{{transform:translateX(0)}}}}
    """

    zig = " ".join(f"{x},{12 if (x // 12) % 2 else 4}" for x in range(0, width + 12, 12))
    zig_b = " ".join(f"{x},{height - (12 if (x // 12) % 2 else 4)}" for x in range(0, width + 12, 12))

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img">',
        "<title>Flavien Mbishibishi, drawn in letters</title>",
        f"<!-- you found a quiet corner: {flag} -->",
        f"<style>{css}</style>",
        f'<rect width="{width}" height="{height}" rx="18" fill="{PAPER}"/>',
        f'<polyline points="{zig}" fill="none" stroke="{OCHRE}" stroke-width="2.5"/>',
        f'<polyline points="{zig_b}" fill="none" stroke="{OCHRE}" stroke-width="2.5"/>',
    ]
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        y = top + (i + 1) * LINE_H
        delay = f'style="animation-delay:{i * 0.05:.2f}s"'
        tl = f'x="{pad_x}" y="{y:.1f}" textLength="{art_w:.1f}" lengthAdjust="spacing"'
        out.append(f'<g class="z" {delay}>')
        for k in range(3):
            out.append(f'<text class="n f f{k}" {tl}>{scramble(line, rnd)}</text>')
        out.append("</g>")
        out.append(f'<text class="a r" {delay} {tl}>{line}</text>')

    out += [
        f'<text class="title" x="{width / 2}" y="{name_y}" text-anchor="middle">Flavien Mbishibishi</text>',
        f'<rect class="cover" x="0" y="{name_y - 26}" width="{width}" height="34"/>',
        f'<text class="sub" x="{width / 2}" y="{name_y + 26}" text-anchor="middle">IT student · Kigali, Rwanda</text>',
        f'<rect class="cover2" x="0" y="{name_y + 10}" width="{width}" height="24"/>',
        "</svg>",
    ]
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/make_hero.py path/to/photo.png")
    write_asset("hero.svg", build_svg(portrait_rows(sys.argv[1])))
    print("wrote assets/hero.svg")
