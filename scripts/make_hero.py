"""Turns a portrait photo into assets/hero.svg: a dot portrait in the profile's colours on a night-blue card,
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

from common import PALETTE, write_asset

NAME = "MBISHIBISHI Flavien"
DOTS_W = 220          # dots across
PITCH = 2             # distance between dots
DOT = 1.55            # dot size
BAND = 4              # dot rows that appear together while the picture settles
NAME_FONT, NAME_STEP = 28, 19
NOISE = "abcdefghijkmnopqrstuvwxyz0123456789"
NAME_NOISE = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789#%@$?"
CARD_W = 1150         # the card spans the page; the portrait stays centred at its own size
CYCLE = 14            # seconds for one full loop
INK, CARD = PALETTE["cream"], PALETTE["navy"]
# Each dot takes a colour from how light the photo is there, blending smoothly
# from sky blue in the shadows, through cream, to a pale gold on the brightest highlights.
STOPS = [(0.0, PALETTE["sky"]), (0.55, PALETTE["cream"]), (0.9, PALETTE["cream"]), (1.0, "#f3d79c")]
STEPS = 8


def blend(t):
    for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0)
            a, b = (int(c0[i:i + 2], 16) for i in (1, 3, 5)), (int(c1[i:i + 2], 16) for i in (1, 3, 5))
            return "#" + "".join(f"{round(x + (y - x) * k):02x}" for x, y in zip(a, b))
    return STOPS[-1][1]


TONES = [((i + 1) / STEPS if i < STEPS - 1 else 1.01, blend((i + 0.5) / STEPS)) for i in range(STEPS)]


def portrait_dots(photo):
    """Dithers the photo into dots (wherever the photo is light) and remembers the tone around each dot."""
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
    small = black.resize((DOTS_W, h), Image.LANCZOS)
    dots = small.convert("1")   # Floyd-Steinberg dithering
    soft = small.filter(ImageFilter.GaussianBlur(1.5))
    # Each cell is None (no dot) or the tone around the dot (0 to 1), which picks its colour.
    return [[soft.getpixel((x, y)) / 255 if dots.getpixel((x, y)) else None for x in range(DOTS_W)]
            for y in range(h)]


def band_path(grid, rows, left, top, lo, hi):
    """The dots of a few rows whose tone is in [lo, hi), as one path: each dot is a zero-length line with a round cap."""
    d, px, py = [], None, None
    for y in rows:
        for x in range(DOTS_W):
            if grid[y][x] is not None and lo <= grid[y][x] < hi:
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
    path{{fill:none;stroke-width:{DOT};stroke-linecap:round}}
    .gold{{fill:{PALETTE['gold']}}}
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
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CARD_W} {height}" width="{CARD_W}" height="{height}" role="img">',
        f"<title>{NAME}, drawn in dots</title>",
        f"<!-- you found a quiet corner: {flag} -->",
        f"<style>{css}</style>",
        f'<rect width="{CARD_W}" height="{height}" rx="14" fill="{CARD}"/>',
        f'<g transform="translate({(CARD_W - width) / 2:.0f},0)">',
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
        first_name = " gold" if i > NAME.index(" ") else ""
        out.append(f'<text class="nm nr{first_name}" {delay} x="{x:.1f}" y="{name_y}" text-anchor="middle">{ch}</text>')

    # The photo is cut off at the shoulders, so the portrait fades softly into the card there.
    art_h = len(grid) * PITCH
    out.append(
        f'<defs><radialGradient id="fade" cx=".5" cy=".38" r=".62" gradientUnits="objectBoundingBox">'
        '<stop offset=".72" stop-color="#fff"/><stop offset="1" stop-color="#000"/></radialGradient>'
        f'<mask id="soft"><rect x="{pad}" y="{art_top}" width="{art_w}" height="{art_h + PITCH * BAND}" fill="url(#fade)"/></mask></defs>'
        '<g mask="url(#soft)">')
    # The portrait: each band starts as scrambled letters, then settles into dots, top to bottom.
    for b, top_row in enumerate(range(0, len(grid), BAND)):
        rows = range(top_row, top_row + BAND)
        cells = [any(grid[y][x] is not None for y in rows for x in (c * 2, c * 2 + 1)) for c in range(DOTS_W // 2)]
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
        out.append(f'<g class="r" {delay}>')
        lo = 0
        for hi, colour in TONES:
            d = band_path(grid, rows, pad + PITCH / 2, art_top + PITCH / 2, lo, hi)
            if d:
                out.append(f'<path stroke="{colour}" d="{d}"/>')
            lo = hi
        out.append("</g>")
    out.append("</g></g></svg>")
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/make_hero.py path/to/photo.png")
    write_asset("hero.svg", build_svg(portrait_dots(sys.argv[1])))
    print("wrote assets/hero.svg")
