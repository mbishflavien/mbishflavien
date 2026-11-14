"""Turns a portrait photo into assets/hero.svg: on a night-blue card, the GitHub mark on the left and
my portrait on the right, both drawn in dots in the profile's colours, with my name decoding under the portrait.

The dots are drawn as real SVG shapes (not font characters), so the picture looks
exactly the same on every device.

Only needs to run once:  python scripts/make_hero.py path/to/photo.png
The photo itself is not stored in the repo. The GitHub mark comes from scripts/github-mark.png.
"""
import base64
import random
import sys

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from common import PALETTE, ROOT, write_asset

NAME = "MBISHIBISHI Flavien"
DOTS_W = 220          # dots across the portrait
LOGO_W = 170          # dots across the GitHub mark
PITCH = 2             # distance between dots
DOT = 1.55            # dot size
BAND = 4              # dot rows that appear together while the picture settles
NAME_FONT, NAME_STEP = 28, 19
NOISE = "abcdefghijkmnopqrstuvwxyz0123456789"
NAME_NOISE = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789#%@$?"
CARD_W = 1150         # the card spans the page; the pictures keep their own size
CYCLE = 14            # seconds for one full loop
INK, CARD = PALETTE["cream"], PALETTE["navy"]
# Each dot takes a colour from how light the picture is there, blending smoothly
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


def to_grid(img, w, h):
    """Dithers a grayscale picture into dots (wherever it is light) and remembers the tone around each dot."""
    small = img.resize((w, h), Image.LANCZOS)
    dots = small.convert("1")   # Floyd-Steinberg dithering
    soft = small.filter(ImageFilter.GaussianBlur(1.5))
    # Each cell is None (no dot) or the tone around the dot (0 to 1), which picks its colour.
    return [[soft.getpixel((x, y)) / 255 if dots.getpixel((x, y)) else None for x in range(w)] for y in range(h)]


def portrait_dots(photo):
    img = Image.open(photo).convert("RGBA")
    alpha = img.getchannel("A").point(lambda a: 255 if a > 128 else 0)
    img = img.crop(alpha.getbbox())
    mask = img.getchannel("A").point(lambda a: 255 if a > 128 else 0)
    gray = ImageOps.grayscale(img.convert("RGB")).filter(ImageFilter.UnsharpMask(radius=3, percent=130, threshold=0))

    # Stretch the tones of the person across the full range, then lift the shadows a little
    # so dark skin and hair still get dots instead of disappearing into the dark card.
    tones = sorted(v for v, m in zip(gray.get_flattened_data(), mask.get_flattened_data()) if m)
    lo, hi = tones[int(len(tones) * 0.01)], tones[int(len(tones) * 0.99)]
    gray = gray.point(lambda v: int(255 * min(max((v - lo) / (hi - lo), 0), 1) ** 0.75))
    gray = ImageEnhance.Contrast(gray).enhance(1.15)
    black = Image.new("L", img.size, 0)
    black.paste(gray, mask=mask)
    return to_grid(black, DOTS_W, int(img.height * DOTS_W / img.width) // BAND * BAND)


def logo_dots():
    """The GitHub mark as dots: brightest near the top right, softer towards the rim."""
    mark = Image.open(ROOT / "scripts" / "github-mark.png").convert("L")
    mark = mark.crop(mark.point(lambda v: 255 if v > 128 else 0).getbbox())
    w = h = mark.width  # the mark's circle is as tall as it is wide
    canvas = Image.new("L", (w, h), 0)
    canvas.paste(mark, (0, 0))
    cx, cy, far = w * 0.62, h * 0.35, (w * w * 0.62 ** 2 + h * h * 0.65 ** 2) ** 0.5
    glow = Image.new("L", (w, h))
    glow.putdata([int(255 * (1 - 0.5 * ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 / far)) for y in range(h) for x in range(w)])
    shape = Image.new("L", (w, h), 0)
    shape.paste(glow, mask=canvas.point(lambda v: 255 if v > 128 else 0))
    return to_grid(shape, LOGO_W, LOGO_W // BAND * BAND)


def band_path(grid, rows, left, top, lo, hi):
    """The dots of a few rows whose tone is in [lo, hi), as one path: each dot is a zero-length line with a round cap."""
    d, px, py = [], None, None
    for y in rows:
        for x in range(len(grid[0])):
            if grid[y][x] is not None and lo <= grid[y][x] < hi:
                ax, ay = left + x * PITCH, top + y * PITCH
                d.append(f"M{ax} {ay}h0" if px is None else f"m{ax - px} {ay - py}h0")
                px, py = ax, ay
    return "".join(d)


def draw_dots(out, grid, left, top, rnd):
    """Each band of rows starts as scrambled letters, then settles into dots, top to bottom."""
    cols = len(grid[0])
    for b, top_row in enumerate(range(0, len(grid), BAND)):
        rows = range(top_row, min(top_row + BAND, len(grid)))
        cells = [any(grid[y][x] is not None for y in rows for x in (c * 2, c * 2 + 1) if x < cols)
                 for c in range((cols + 1) // 2)]
        if not any(cells):
            continue
        delay = f'style="animation-delay:{b * 0.03:.2f}s"'
        tl = (f'x="{left}" y="{top + (top_row + BAND) * PITCH}" textLength="{len(cells) * 2 * PITCH}" '
              'lengthAdjust="spacing"')
        out.append(f'<g class="z" {delay}>')
        for k in range(3):
            noise = "".join(rnd.choice(NOISE) if on else " " for on in cells)
            out.append(f'<text class="d n f f{k}" {tl}>{noise}</text>')
        out.append("</g>")
        out.append(f'<g class="r" {delay}>')
        lo = 0
        for hi, colour in TONES:
            d = band_path(grid, rows, left + PITCH / 2, top + PITCH / 2, lo, hi)
            if d:
                out.append(f'<path stroke="{colour}" d="{d}"/>')
            lo = hi
        out.append("</g>")


def build_svg(face, logo):
    rnd = random.Random(3)
    pad = 24
    face_w, face_h = len(face[0]) * PITCH, len(face) * PITCH
    logo_w, logo_h = len(logo[0]) * PITCH, len(logo) * PITCH
    face_x = round(CARD_W * 0.75 - face_w / 2)          # portrait on the right
    logo_x = round(CARD_W * 0.25 - logo_w / 2)          # GitHub mark on the left, nothing in between
    top = pad
    logo_y = round(top + face_h * 0.45 - logo_h / 2)
    name_y = round(top + face_h + 30)                   # name right under the portrait
    height = name_y + pad
    flag = base64.b64encode(b"flag{murakaza_neza}").decode()

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
    @keyframes nshow{{0%,20%{{opacity:0}}20.5%,88%{{opacity:1}}88.5%,100%{{opacity:0}}}}
    @keyframes nhide{{0%,20%{{opacity:1}}20.5%,88%{{opacity:0}}88.5%,100%{{opacity:1}}}}
    @keyframes flick{{0%{{opacity:1}}33%,100%{{opacity:0}}}}
    """
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CARD_W} {height}" width="{CARD_W}" height="{height}" role="img">',
        f"<title>The GitHub mark and {NAME}, drawn in dots</title>",
        f"<!-- you found a quiet corner: {flag} -->",
        f"<style>{css}</style>",
        f'<rect width="{CARD_W}" height="{height}" rx="14" fill="{CARD}"/>',
        # The photo is cut off at the shoulders, so the portrait fades softly into the card there.
        '<defs><radialGradient id="fade" cx=".5" cy=".38" r=".62" gradientUnits="objectBoundingBox">'
        '<stop offset=".72" stop-color="#fff"/><stop offset="1" stop-color="#000"/></radialGradient>'
        f'<mask id="soft"><rect x="{face_x}" y="{top}" width="{face_w}" height="{face_h + PITCH * BAND}" '
        'fill="url(#fade)"/></mask></defs>',
    ]

    draw_dots(out, logo, logo_x, logo_y, rnd)
    out.append('<g mask="url(#soft)">')
    draw_dots(out, face, face_x, top, rnd)
    out.append("</g>")

    # The name: once the pictures settle, each letter flickers through random characters, then locks in.
    x0 = face_x + face_w / 2 - (len(NAME) - 1) * NAME_STEP / 2
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
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/make_hero.py path/to/photo.png")
    write_asset("hero.svg", build_svg(portrait_dots(sys.argv[1]), logo_dots()))
    print("wrote assets/hero.svg")
