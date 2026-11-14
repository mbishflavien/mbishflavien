"""Builds the banner at the top of the profile, as two halves that sit edge to edge:

  assets/hero-tools.svg  the Octocat, then the logos of tools I use, crossfading every few seconds
  assets/hero-me.svg     my portrait, settling out of scrambled letters, with my name under it

Everything is drawn in dots in the profile's colours. The dots are real SVG shapes (not font
characters), so the pictures look the same on every device. Two separate images keep the page
smooth: a logo change only redraws its own half.

Only needs to run once:  python scripts/make_hero.py path/to/photo.png
The photo itself is not stored in the repo. The Octocat is scripts/octocat.png. The tool logos in
scripts/logos/ (and their brand colours in scripts/logos/colors.json) come from Simple Icons
(simpleicons.org, CC0), except bullmq.png.
"""
import base64
import json
import random
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from common import PALETTE, ROOT, write_asset

NAME = "MBISHIBISHI Flavien"
# The left half shows these in turn: (image in scripts/logos/, label under it).
LOGOS = [
    ("octocat", "GitHub"),
    # Languages
    ("typescript", "TypeScript"), ("javascript", "JavaScript"), ("python", "Python"), ("go", "Go"),
    ("openjdk", "Java"), ("dart", "Dart"), ("csharp", "C#"), ("php", "PHP"),
    # AI & Data
    ("scikitlearn", "Machine Learning"), ("modelcontextprotocol", "MCP"),
    # Frontend & UI/UX
    ("react", "React"), ("nextdotjs", "Next.js"), ("tailwindcss", "Tailwind CSS"), ("mui", "MUI"),
    ("shadcnui", "shadcn/ui"), ("figma", "Figma"), ("vite", "Vite"), ("cesium", "CesiumJS"),
    ("html5", "HTML"), ("css3", "CSS"),
    # Backend
    ("nodedotjs", "Node.js"), ("express", "Express"), ("django", "Django"), ("fastapi", "FastAPI"),
    ("gin", "Gin"), ("springboot", "Spring Boot"), ("graphql", "GraphQL"), ("socketdotio", "Socket.io"),
    ("bullmq", "BullMQ"), ("rabbitmq", "RabbitMQ"),
    # Mobile
    ("flutter", "Flutter"), ("firebase", "Firebase"),
    # Databases
    ("postgresql", "PostgreSQL"), ("mysql", "MySQL"), ("mongodb", "MongoDB"), ("redis", "Redis"),
    ("oracle", "Oracle PL/SQL"),
    # Cloud & DevOps
    ("amazonwebservices", "AWS"), ("googlecloud", "GCP"), ("docker", "Docker"),
    ("githubactions", "GitHub Actions"), ("git", "Git"), ("linux", "Linux"),
    # Hardware
    ("espressif", "ESP32"), ("arduino", "Arduino"),
]
SLOT = 3              # seconds each logo stays
FADE = 0.6            # seconds of crossfade between two logos
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
HALF_W = 575          # width of each half; side by side they span the page
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

# Logos keep their real brand colours, softened towards this calm grey-blue so they sit quietly on the navy.
MUTE, MUTE_BY = "#aeb3c2", 0.38
COLORS = json.loads((ROOT / "scripts" / "logos" / "colors.json").read_text())


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, k):
    return "#" + "".join(f"{round(x + (y - x) * k):02x}" for x, y in zip(rgb(a), rgb(b)))


def luminance(h):
    r, g, b = rgb(h)
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


def soften(h):
    """A brand colour made faint but still recognisable: blue stays blue, yellow stays yellow."""
    c = mix(h, MUTE, MUTE_BY)
    return c if luminance(c) > 0.4 else mix(c, "#d4d8e3", 0.45)   # dark colours lifted so they still show


def tone_colour(t):
    for hi, colour in TONES:
        if t < hi:
            return colour
    return TONES[-1][1]


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
    grid = to_grid(black, FACE_W, int(img.height * FACE_W / img.width) // BAND * BAND)
    return [[None if v is None else tone_colour(v) for v in row] for row in grid]


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
    w, h = CAT_W, int(img.height * CAT_W / img.width) // BAND * BAND
    grid = to_grid(cat, w, h)
    # Each dot takes the cat's own colour there (black body, peach face, brown eyes, blue puddle), softened.
    small = img.resize((w, h), Image.LANCZOS).quantize(colors=6).convert("RGB")
    return [[None if v is None else soften("#%02x%02x%02x" % small.getpixel((x, y))) for x, v in enumerate(row)]
            for y, row in enumerate(grid)]


def logo_dots(name):
    """A white-on-black tool logo, fitted into a square, with a soft glow so its dots get the palette's blend."""
    mark = Image.open(ROOT / "scripts" / "logos" / f"{name}.png").convert("L")
    mark = mark.crop(mark.point(lambda v: 255 if v > 128 else 0).getbbox())
    scale = LOGO_BOX / max(mark.size)
    w, h = max(1, round(mark.width * scale)), max(1, round(mark.height * scale))
    mask = mark.resize((w, h), Image.LANCZOS).point(lambda v: 255 if v > 110 else 0)
    cx, cy, far = w * 0.62, h * 0.35, ((w * 0.62) ** 2 + (h * 0.65) ** 2) ** 0.5
    glow = Image.new("L", (w, h))
    glow.putdata([int(255 * (1 - 0.45 * ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 / far)) for y in range(h) for x in range(w)])
    # Logos are flat shapes, so every dot inside them is lit, like an LED sign. Each dot is the logo's
    # softened brand colour (or the cream blend for logos without one), a little dimmer away from the glow.
    base = soften(COLORS[name]) if name in COLORS else None

    def colour(t):
        if base is None:
            return tone_colour(t)
        step = round((1 - t) / 0.45 * 3) / 3            # four shades are enough
        return mix(base, CARD, step * 0.35)
    return [[colour(glow.getpixel((x, y)) / 255) if mask.getpixel((x, y)) else None for x in range(w)]
            for y in range(h)]


# ---------- dots to SVG ----------

def band_path(grid, rows, left, top, pitch, colour):
    """The dots of some rows that have this colour, as one path.

    Each run of neighbouring dots in a row is one line; with round caps and a dash pattern of
    "0 pitch" it is drawn as a row of dots, so a solid shape costs a few bytes per row, not per dot."""
    d, px, py = [], None, None
    for y in rows:
        x = 0
        while x < len(grid[0]):
            if grid[y][x] == colour:
                start = x
                while x + 1 < len(grid[0]) and grid[y][x + 1] == colour:
                    x += 1
                ax, ay = round(left + start * pitch, 2), round(top + y * pitch, 2)
                move = f"M{ax:g} {ay:g}" if px is None else f"m{round(ax - px, 2):g} {round(ay - py, 2):g}"
                # A hair longer than the run, so the last dot (and a lone dot) is never dropped at the line's end.
                length = round((x - start) * pitch + 0.05, 2)
                d.append(f"{move}h{length:g}")
                px, py = ax + length, ay
            x += 1
    return "".join(d)


def dot_paths(grid, rows, left, top, pitch):
    out = []
    for colour in sorted({grid[y][x] for y in rows for x in range(len(grid[0])) if grid[y][x] is not None}):
        d = band_path(grid, rows, left + pitch / 2, top + pitch / 2, pitch, colour)
        out.append(f'<path stroke="{colour}" stroke-width="{pitch * 0.78:.2f}" '
                   f'stroke-dasharray="0 {pitch:g}" d="{d}"/>')
    return "".join(out)


def crossfade_keyframes(name, start, end, total):
    """Keyframes for something shown from `start` to `end` in a loop `total` seconds long,
    fading in and out over FADE seconds centred on those moments (wrapping round the loop)."""
    def opacity(t):
        best = 0
        for shift in (-total, 0, total):
            s, e = start + shift, end + shift
            if s - FADE / 2 <= t <= e + FADE / 2:
                best = max(best, min(1, (t - (s - FADE / 2)) / FADE, ((e + FADE / 2) - t) / FADE))
        return best
    marks = {0.0, float(total)}
    for shift in (-total, 0, total):
        for m in (start - FADE / 2, start + FADE / 2, end - FADE / 2, end + FADE / 2):
            if 0 <= m + shift <= total:
                marks.add(m + shift)
    frames = "".join(f"{t / total * 100:.3f}%{{opacity:{opacity(t):.2f}}}" for t in sorted(marks))
    return f"@keyframes {name}{{{frames}}}"


def card(width, height, rounded):
    """The navy background, rounded only on its outer side so the two halves join seamlessly."""
    r = 14
    if rounded == "left":
        d = f"M{r},0H{width}V{height}H{r}A{r},{r} 0 0 1 0,{height - r}V{r}A{r},{r} 0 0 1 {r},0Z"
    else:
        d = f"M0,0H{width - r}A{r},{r} 0 0 1 {width},{r}V{height - r}A{r},{r} 0 0 1 {width - r},{height}H0Z"
    return f'<path d="{d}" style="fill:{CARD}"/>'


def layout(face):
    pad = 24
    face_h = len(face) * FACE_PITCH
    name_y = round(pad + face_h + 30)
    return pad, face_h, name_y, name_y + pad


def tools_svg(logos, face):
    pad, face_h, name_y, height = layout(face)
    cx, cy = HALF_W / 2, pad + face_h * 0.45
    total = SLOT * len(logos)
    css, body = [f"text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:{INK}}}"
                 ".lb{font-size:26px;font-weight:700;letter-spacing:.08em}"
                 "path{fill:none;stroke-linecap:round}"], []
    for i, (grid, pitch, label) in enumerate(logos):
        css.append(crossfade_keyframes(f"l{i}", i * SLOT, (i + 1) * SLOT, total))
        css.append(f".l{i}{{animation:l{i} {total}s linear infinite both}}")
        w, h = len(grid[0]) * pitch, len(grid) * pitch
        left, top = round(cx - w / 2), round(cy - h / 2)
        body.append(f'<g class="l{i}">{dot_paths(grid, range(len(grid)), left, top, pitch)}'
                    f'<text class="lb" x="{cx}" y="{name_y}" text-anchor="middle">{label}</text></g>')
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {HALF_W} {height}" width="{HALF_W}" height="{height}" role="img">',
        "<title>Tools I build with, drawn in dots</title>",
        f"<style>{''.join(css)}</style>",
        card(HALF_W, height, "left"), *body, "</svg>"])


def me_svg(face):
    rnd = random.Random(3)
    pad, face_h, name_y, height = layout(face)
    face_w = len(face[0]) * FACE_PITCH
    face_x = round(HALF_W / 2 - face_w / 2)
    flag = base64.b64encode(b"flag{murakaza_neza}").decode()
    css = f"""
    text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre;fill:{INK}}}
    .d{{font-size:8px;fill-opacity:.45}}
    .nm{{font-size:{NAME_FONT}px;font-weight:700}}
    .n{{fill-opacity:.45}}
    path{{fill:none;stroke-linecap:round}}
    .gold{{fill:{PALETTE['gold']}}}
    .r{{animation:show {CYCLE}s linear infinite both}}
    .z{{animation:hide {CYCLE}s linear infinite both}}
    .nr{{animation:nshow {CYCLE}s linear infinite both}}
    .nz{{animation:nhide {CYCLE}s linear infinite both}}
    @keyframes show{{0%,14%{{opacity:0}}18%,86%{{opacity:1}}90%,100%{{opacity:0}}}}
    @keyframes hide{{0%,14%{{opacity:1}}18%,86%{{opacity:0}}90%,100%{{opacity:1}}}}
    @keyframes nshow{{0%,20%{{opacity:0}}20.5%,88%{{opacity:1}}88.5%,100%{{opacity:0}}}}
    @keyframes nhide{{0%,20%{{opacity:1}}20.5%,88%{{opacity:0}}88.5%,100%{{opacity:1}}}}
    """
    body = []
    # The portrait, band by band, starts as scrambled letters and settles into dots, top to bottom.
    cols = len(face[0])
    for b, top_row in enumerate(range(0, len(face), BAND)):
        rows = range(top_row, top_row + BAND)
        cells = [any(face[y][x] is not None for y in rows for x in (c * 2, c * 2 + 1)) for c in range(cols // 2)]
        if not any(cells):
            continue
        delay = f'style="animation-delay:{b * 0.03:.2f}s"'
        noise = "".join(rnd.choice(NOISE) if on else " " for on in cells)
        body.append(f'<text class="d z" {delay} x="{face_x}" y="{pad + (top_row + BAND) * FACE_PITCH}" '
                    f'textLength="{face_w}" lengthAdjust="spacing">{noise}</text>')
        body.append(f'<g class="r" {delay}>{dot_paths(face, rows, face_x, pad, FACE_PITCH)}</g>')
    # The name: once the portrait settles, each letter turns from a random character into the real one.
    x0 = HALF_W / 2 - (len(NAME) - 1) * NAME_STEP / 2
    for i, ch in enumerate(NAME):
        if ch == " ":
            continue
        x = x0 + i * NAME_STEP
        delay = f'style="animation-delay:{i * 0.09:.2f}s"'
        first_name = " gold" if i > NAME.index(" ") else ""
        body.append(f'<text class="nm n nz" {delay} x="{x:.1f}" y="{name_y}" text-anchor="middle">{rnd.choice(NAME_NOISE)}</text>')
        body.append(f'<text class="nm nr{first_name}" {delay} x="{x:.1f}" y="{name_y}" text-anchor="middle">{ch}</text>')
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {HALF_W} {height}" width="{HALF_W}" height="{height}" role="img">',
        f"<title>{NAME}, drawn in dots</title>",
        f"<!-- you found a quiet corner: {flag} -->",
        f"<style>{css}</style>",
        card(HALF_W, height, "right"), *body, "</svg>"])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/make_hero.py path/to/photo.png")
    face = portrait_dots(sys.argv[1])
    logos = [(octocat_dots(), CAT_PITCH, "GitHub")]
    logos += [(logo_dots(name), LOGO_PITCH, label) for name, label in LOGOS[1:]]
    write_asset("hero-tools.svg", tools_svg(logos, face))
    write_asset("hero-me.svg", me_svg(face))
    print("wrote assets/hero-tools.svg and assets/hero-me.svg")
