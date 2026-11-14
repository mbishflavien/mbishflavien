"""Turns a portrait photo into assets/hero.svg: a white dot portrait on a black card,
with my name decoding out of random letters above it.

The dots are drawn as real SVG shapes (not font characters), so the picture looks
exactly the same on every device.

Only needs to run once:  python scripts/make_hero.py path/to/photo.png
The photo itself is not stored in the repo.
"""
import base64
import random
import sys

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from common import write_asset

NAME = "MBISHIBISHI Flavien"
DOTS_W = 220          # dots across
PITCH = 2             # distance between dots
DOT = 1.55            # dot size
BAND = 4              # dot rows that appear together while the picture settles
NAME_FONT, NAME_STEP = 28, 19
NOISE = "abcdefghijkmnopqrstuvwxyz0123456789"
NAME_NOISE = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789#%@$?"
CYCLE = 14            # seconds for one full loop
INK, CARD = "#ffffff", "#000000"


def portrait_dots(photo):
    """Dithers the photo into a grid of dots: True wherever the photo is light."""
    img = Image.open(photo).convert("RGBA")
    alpha = img.getchannel("A").point(lambda a: 255 if a > 128 else 0)
    img = img.crop(alpha.getbbox())
    mask = img.getchannel("A").point(lambda a: 255 if a > 128 else 0)
    gray = ImageOps.grayscale(img.convert("RGB")).filter(ImageFilter.UnsharpMask(radius=3, percent=130, threshold=0))

    # Stretch the tones of the person across the full range, then lift the shadows a little
    # so dark skin and hair still get dots instead of disappearing into the black card.
    tones = sorted(v for v, m in zip(gray.get_flattened_data(), mask.get_flattened_data()) if m)
    lo, hi = tones[int(len(tones) * 0.01)], tones[int(len(tones) * 0.99)]
    gray = gray.point(lambda v: int(255 * min(max((v - lo) / (hi - lo), 0), 1) ** 0.75))
    gray = ImageEnhance.Contrast(gray).enhance(1.15)
    black = Image.new("L", img.size, 0)
    black.paste(gray, mask=mask)

    h = int(img.height * DOTS_W / img.width) // BAND * BAND
    dots = black.resize((DOTS_W, h), Image.LANCZOS).convert("1")   # Floyd-Steinberg dithering
    return [[bool(dots.getpixel((x, y))) for x in range(DOTS_W)] for y in range(h)]


def band_path(grid, rows, left, top):
    """All dots of a few rows as one path: each dot is a zero-length line with a round cap."""
    d, px, py = [], None, None
    for y in rows:
        for x in range(DOTS_W):
            if grid[y][x]:
                ax, ay = left + x * PITCH, top + y * PITCH
                d.append(f"M{ax} {ay}h0" if px is None else f"m{ax - px} {ay - py}h0")
                px, py = ax, ay
    return "".join(d)


def build_svg(grid):
    rnd = random.Random(3)
    pad = 18
    art_w = DOTS_W * PITCH
    width = int(art_w + pad * 2)
    name_y = pad + NAME_FONT + 4
    art_top = name_y + 20
    height = int(art_top + len(grid) * PITCH + pad)
    flag = base64.b64encode(b"flag{murakaza_neza}").decode()
    char_w = PITCH * 2                       # one scramble letter covers 2 x BAND dots

    css = f"""
    text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre;fill:{INK}}}
    .d{{font-size:8px}}
    .nm{{font-size:{NAME_FONT}px;font-weight:700}}
    .n{{fill-opacity:.45}}
    path{{fill:none;stroke:{INK};stroke-width:{DOT};stroke-linecap:round}}
    .r{{animation:show {CYCLE}s linear infinite both}}
    .z{{animation:hide {CYCLE}s linear infinite both}}
    .nr{{animation:nshow {CYCLE}s linear infinite both}}
    .nz{{animation:nhide {CYCLE}s linear infinite both}}
    .f{{opacity:0;animation:flick .45s steps(1) infinite}}
    .f1{{animation-delay:.15s}} .f2{{animation-delay:.3s}}
    @keyframes show{{0%,14%{{opacity:0}}18%,86%{{opacity:1}}90%,100%{{opacity:0}}}}
    @keyframes hide{{0%,14%{{opacity:1}}18%,86%{{opacity:0}}90%,100%{{opacity:1}}}}
    @keyframes nshow{{0%,4%{{opacity:0}}4.5%,88%{{opacity:1}}88.5%,100%{{opacity:0}}}}
    @keyframes nhide{{0%,4%{{opacity:1}}4.5%,88%{{opacity:0}}88.5%,100%{{opacity:1}}}}
    @keyframes flick{{0%{{opacity:1}}33%,100%{{opacity:0}}}}
    """
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img">',
        f"<title>{NAME}, drawn in dots</title>",
        f"<!-- you found a quiet corner: {flag} -->",
        f"<style>{css}</style>",
        f'<rect width="{width}" height="{height}" rx="14" fill="{CARD}"/>',
    ]

    # The name: each letter flickers through random characters, then locks in, one after another.
    x0 = width / 2 - (len(NAME) - 1) * NAME_STEP / 2
    for i, ch in enumerate(NAME):
        if ch == " ":
            continue
        x = x0 + i * NAME_STEP
        delay = f'style="animation-delay:{i * 0.09:.2f}s"'
        out.append(f'<g class="nz" {delay}>')
        for k in range(3):
            out.append(f'<text class="nm n f f{k}" x="{x:.1f}" y="{name_y}" text-anchor="middle">{rnd.choice(NAME_NOISE)}</text>')
        out.append("</g>")
        out.append(f'<text class="nm nr" {delay} x="{x:.1f}" y="{name_y}" text-anchor="middle">{ch}</text>')

    # The portrait: each band starts as scrambled letters, then settles into dots, top to bottom.
    for b, top_row in enumerate(range(0, len(grid), BAND)):
        rows = range(top_row, top_row + BAND)
        cells = [any(grid[y][x] for y in rows for x in (c * 2, c * 2 + 1)) for c in range(DOTS_W // 2)]
        if not any(cells):
            continue
        delay = f'style="animation-delay:{b * 0.03:.2f}s"'
        y_text = art_top + (top_row + BAND) * PITCH
        tl = f'x="{pad}" y="{y_text}" textLength="{art_w}" lengthAdjust="spacing"'
        out.append(f'<g class="z" {delay}>')
        for k in range(3):
            noise = "".join(rnd.choice(NOISE) if on else " " for on in cells)
            out.append(f'<text class="d n f f{k}" {tl}>{noise}</text>')
        out.append("</g>")
        out.append(f'<path class="r" {delay} d="{band_path(grid, rows, pad + PITCH / 2, art_top + PITCH / 2)}"/>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/make_hero.py path/to/photo.png")
    write_asset("hero.svg", build_svg(portrait_dots(sys.argv[1])))
    print("wrote assets/hero.svg")
