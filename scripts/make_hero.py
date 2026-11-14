"""Builds assets/hero.svg: a night-blue banner with, on the left, the Octocat morphing every few seconds
into the logos of tools I use, and on the right my portrait, with my name decoding under it.
Everything is drawn in dots in the profile's colours.

The dots are real SVG shapes (not font characters), so the picture looks the same on every device.

Only needs to run once:  python scripts/make_hero.py path/to/photo.png
The photo itself is not stored in the repo. The Octocat is scripts/octocat.png and the tool logos
in scripts/logos/ come from Simple Icons (simpleicons.org, CC0).
"""
import base64
import random
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from common import PALETTE, ROOT, write_asset

NAME = "MBISHIBISHI Flavien"
# The left side shows these in turn: (image in scripts/logos/, label under it).
LOGOS = [("octocat", "GitHub"), ("typescript", "TypeScript"), ("python", "Python"), ("react", "React"),
         ("nodedotjs", "Node.js"), ("fastapi", "FastAPI"), ("springboot", "Spring Boot"),
         ("flutter", "Flutter"), ("docker", "Docker"), ("linux", "Linux")]
SLOT = 3              # seconds each logo stays
FACE_W = 220          # dots across the portrait
FACE_PITCH = 2        # distance between portrait dots
CAT_W = 200           # dots across the Octocat (finer, it has small details)
CAT_PITCH = 2
LOGO_BOX = 120        # the tool logos fit in a square this many dots wide
LOGO_PITCH = 3        # tool logos are simple shapes, so their dots can be bigger and fewer
BAND = 4              # dot rows that appear together while the portrait settles
NAME_FONT, NAME_STEP = 28, 19
NOISE = "abcdefghijkmnopqrstuvwxyz0123456789"
NAME_NOISE = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789#%@$?"
CARD_W = 1150         # the banner spans the page; the pictures keep their own size
CYCLE = 14            # seconds for one loop of the portrait
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


# ---------- pictures to dots ----------

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
    return to_grid(black, FACE_W, int(img.height * FACE_W / img.width) // BAND * BAND)


def octocat_dots():
    """The Octocat drawn on white: the background is the white area touching the image edges (flood fill),
    so white inside the cat, like its eyes, stays. Lighter colours get more dots."""
    img = Image.open(ROOT / "scripts" / "octocat.png").convert("RGB")
    bg = img.copy()
    for corner in [(0, 0), (img.width - 1, 0), (0, img.height - 1), (img.width - 1, img.height - 1)]:
        ImageDraw.floodfill(bg, corner, (255, 0, 255), thresh=40)
    mask = Image.new("L", img.size)
    mask.putdata([0 if p == (255, 0, 255) else 255 for p in bg.get_flattened_data()])
    box = mask.getbbox()
    img, mask = img.crop(box), mask.crop(box)
    gray = ImageOps.grayscale(img).point(lambda v: int(255 * (0.3 + 0.7 * (v / 255) ** 1.6)))
    cat = Image.new("L", img.size, 0)
    cat.paste(gray, mask=mask)
    return to_grid(cat, CAT_W, int(img.height * CAT_W / img.width) // BAND * BAND)


def logo_dots(name):
    """A white-on-black tool logo, fitted into a square, with a soft glow so the dots get the palette's blend."""
    mark = Image.open(ROOT / "scripts" / "logos" / f"{name}.png").convert("L")
    mark = mark.crop(mark.point(lambda v: 255 if v > 128 else 0).getbbox())
    scale = LOGO_BOX / max(mark.size)
    w, h = max(1, round(mark.width * scale)), max(1, round(mark.height * scale))
    mask = mark.resize((w, h), Image.LANCZOS).point(lambda v: 255 if v > 110 else 0)
    cx, cy, far = w * 0.62, h * 0.35, ((w * 0.62) ** 2 + (h * 0.65) ** 2) ** 0.5
    glow = Image.new("L", (w, h))
    glow.putdata([int(255 * (1 - 0.45 * ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 / far)) for y in range(h) for x in range(w)])
    shape = Image.new("L", (w, h), 0)
    shape.paste(glow, mask=mask)
    dots = shape.convert("1")
    soft = shape.filter(ImageFilter.GaussianBlur(1))
    return [[soft.getpixel((x, y)) / 255 if dots.getpixel((x, y)) else None for x in range(w)] for y in range(h)]


# ---------- dots to SVG ----------

def band_path(grid, rows, left, top, pitch, lo, hi):
    """The dots of some rows whose tone is in [lo, hi), as one path: each dot is a zero-length line with a round cap."""
    d, px, py = [], None, None
    for y in rows:
        for x in range(len(grid[0])):
            if grid[y][x] is not None and lo <= grid[y][x] < hi:
                ax, ay = round(left + x * pitch, 1), round(top + y * pitch, 1)
                d.append(f"M{ax:g} {ay:g}h0" if px is None else f"m{round(ax - px, 1):g} {round(ay - py, 1):g}h0")
                px, py = ax, ay
    return "".join(d)


def dot_paths(grid, rows, left, top, pitch):
    out, lo = [], 0
    for hi, colour in TONES:
        d = band_path(grid, rows, left + pitch / 2, top + pitch / 2, pitch, lo, hi)
        if d:
            out.append(f'<path stroke="{colour}" stroke-width="{pitch * 0.78:.2f}" d="{d}"/>')
        lo = hi
    return "".join(out)


def noise_lines(grid, left, top, pitch, rnd, cls):
    """Scrambled letters in the shape of the picture: one letter per 2 x BAND dots."""
    cols, out = len(grid[0]), []
    for top_row in range(0, len(grid), BAND):
        rows = range(top_row, min(top_row + BAND, len(grid)))
        cells = [any(grid[y][x] is not None for y in rows for x in (c * 2, c * 2 + 1) if x < cols)
                 for c in range((cols + 1) // 2)]
        if any(cells):
            out.append((top_row, cells))
    size = 4 * pitch
    res = []
    for k in range(3):
        lines = "".join(
            f'<text x="{left}" y="{top + (r + BAND) * pitch}" textLength="{len(c) * 2 * pitch}" '
            f'lengthAdjust="spacing">{"".join(rnd.choice(NOISE) if on else " " for on in c)}</text>'
            for r, c in out)
        res.append(f'<g class="{cls} n f f{k}" style="font-size:{size}px">{lines}</g>')
    return res


def windows_keyframes(name, windows, total, ramp=0.15):
    """CSS keyframes that make something visible during each (start, end) window of a loop `total` seconds long."""
    pts = []
    for s, e in windows:
        pts += [(s - ramp, 0), (s, 1), (e, 1), (e + ramp, 0)]
    pts = sorted((min(max(t, 0), total) / total * 100, v) for t, v in pts)
    start = 1 if any(s <= 0 < e for s, e in windows) else 0
    end = 1 if any(s < total <= e for s, e in windows) else 0
    frames = [(0, start)] + pts + [(100, end)]
    return f"@keyframes {name}{{" + "".join(f"{p:.3f}%{{opacity:{v}}}" for p, v in frames) + "}"


def build_svg(face, logos):
    rnd = random.Random(3)
    pad = 24
    face_w, face_h = len(face[0]) * FACE_PITCH, len(face) * FACE_PITCH
    face_x = round(CARD_W * 0.75 - face_w / 2)       # portrait on the right
    top = pad
    name_y = round(top + face_h + 30)                # name right under the portrait
    height = name_y + pad
    logo_cx = CARD_W * 0.25                          # logos on the left, nothing in between
    logo_cy = top + face_h * 0.45
    total = SLOT * len(logos)
    flag = base64.b64encode(b"flag{murakaza_neza}").decode()

    css = [f"""
    text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre;fill:{INK}}}
    .d{{font-size:8px}}
    .nm{{font-size:{NAME_FONT}px;font-weight:700}}
    .lb{{font-size:26px;font-weight:700;letter-spacing:.08em}}
    .n{{fill-opacity:.45}}
    path{{fill:none;stroke-linecap:round}}
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
    """]
    body = []

    # Left: each logo holds for SLOT seconds. At every change the old logo dissolves into
    # scrambled letters, which settle into the next logo.
    for i, (grid, pitch, label) in enumerate(logos):
        t0 = i * SLOT
        css.append(windows_keyframes(f"l{i}", [(t0 + 0.4, t0 + SLOT - 0.25)], total))
        noise = [(t0 - 0.25, t0 + 0.4)] + ([(total - 0.25, total)] if t0 == 0 else [])
        css.append(windows_keyframes(f"s{i}", noise, total))
        css.append(f".l{i}{{animation:l{i} {total}s linear infinite both}}"
                   f".s{i}{{animation:s{i} {total}s linear infinite both}}")
        w, h = len(grid[0]) * pitch, len(grid) * pitch
        left, gtop = round(logo_cx - w / 2), round(logo_cy - h / 2)
        body.append(f'<g class="l{i}">{dot_paths(grid, range(len(grid)), left, gtop, pitch)}'
                    f'<text class="lb" x="{logo_cx}" y="{name_y}" text-anchor="middle">{label}</text></g>')
        body.append(f'<g class="s{i}">' + "".join(noise_lines(grid, left, gtop, pitch, rnd, "")) + "</g>")

    # Right: the portrait, band by band, starts as scrambled letters and settles into dots.
    cols = len(face[0])
    for b, top_row in enumerate(range(0, len(face), BAND)):
        rows = range(top_row, top_row + BAND)
        cells = [any(face[y][x] is not None for y in rows for x in (c * 2, c * 2 + 1)) for c in range(cols // 2)]
        if not any(cells):
            continue
        delay = f'style="animation-delay:{b * 0.03:.2f}s"'
        tl = f'x="{face_x}" y="{top + (top_row + BAND) * FACE_PITCH}" textLength="{face_w}" lengthAdjust="spacing"'
        body.append(f'<g class="z" {delay}>')
        for k in range(3):
            body.append(f'<text class="d n f f{k}" {tl}>{"".join(rnd.choice(NOISE) if on else " " for on in cells)}</text>')
        body.append("</g>")
        body.append(f'<g class="r" {delay}>{dot_paths(face, rows, face_x, top, FACE_PITCH)}</g>')

    # The name: once the portrait settles, each letter flickers through random characters, then locks in.
    x0 = face_x + face_w / 2 - (len(NAME) - 1) * NAME_STEP / 2
    for i, ch in enumerate(NAME):
        if ch == " ":
            continue
        x = x0 + i * NAME_STEP
        delay = f'style="animation-delay:{i * 0.09:.2f}s"'
        body.append(f'<g class="nz" {delay}>')
        for k in range(3):
            body.append(f'<text class="nm n f f{k}" x="{x:.1f}" y="{name_y}" text-anchor="middle">{rnd.choice(NAME_NOISE)}</text>')
        body.append("</g>")
        first_name = " gold" if i > NAME.index(" ") else ""
        body.append(f'<text class="nm nr{first_name}" {delay} x="{x:.1f}" y="{name_y}" text-anchor="middle">{ch}</text>')

    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CARD_W} {height}" width="{CARD_W}" height="{height}" role="img">',
        f"<title>{NAME}, and the tools I build with, drawn in dots</title>",
        f"<!-- you found a quiet corner: {flag} -->",
        f"<style>{''.join(css)}</style>",
        f'<rect width="{CARD_W}" height="{height}" rx="14" fill="{CARD}"/>',
        *body,
        "</svg>"])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/make_hero.py path/to/photo.png")
    logos = [(octocat_dots(), CAT_PITCH, "GitHub")]
    logos += [(logo_dots(name), LOGO_PITCH, label) for name, label in LOGOS[1:]]
    write_asset("hero.svg", build_svg(portrait_dots(sys.argv[1]), logos))
    print("wrote assets/hero.svg")
