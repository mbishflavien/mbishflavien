"""Turns a portrait photo into assets/hero.svg: a white dot portrait on a black card
(braille characters, 8 dots each), with my name decoding out of random letters above it.

Only needs to run once:  python scripts/make_hero.py path/to/photo.png
The photo itself is not stored in the repo.
"""
import base64
import random
import sys

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from common import write_asset

NAME = "MBISHIBISHI Flavien"
COLS = 110
CHAR_W = 4.0          # one braille character = 2 x 4 dots, so it is twice as tall as it is wide
LINE_H = 8.0
FONT = 8
NAME_FONT, NAME_STEP = 28, 19
NOISE = "abcdefghijkmnopqrstuvwxyz0123456789"
NAME_NOISE = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789#%@$?"
CYCLE = 14            # seconds for one full loop
INK, CARD = "#ffffff", "#000000"
BLANK = chr(0x2800)
DOTS = [(0, 0, 0x01), (0, 1, 0x02), (0, 2, 0x04), (1, 0, 0x08), (1, 1, 0x10), (1, 2, 0x20), (0, 3, 0x40), (1, 3, 0x80)]


def portrait_rows(photo):
    """Dithers the photo into dots (a dot wherever the photo is light) and packs every 2x4 block into one braille character."""
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

    w = COLS * 2
    h = int(img.height * w / img.width) // 4 * 4
    dots = black.resize((w, h), Image.LANCZOS).convert("1")   # Floyd-Steinberg dithering

    lines = []
    for y in range(0, h, 4):
        line = ""
        for x in range(0, w, 2):
            v = sum(bit for dx, dy, bit in DOTS if dots.getpixel((x + dx, y + dy)))
            line += chr(0x2800 + v)
        lines.append(line)
    return lines


def build_svg(lines):
    rnd = random.Random(3)
    art_w = COLS * CHAR_W
    pad = 18
    width = int(art_w + pad * 2)
    name_y = pad + NAME_FONT + 4
    art_top = name_y + 18
    height = int(art_top + len(lines) * LINE_H + pad)
    flag = base64.b64encode(b"flag{murakaza_neza}").decode()

    css = f"""
    text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre;fill:{INK}}}
    .d{{font-size:{FONT}px}}
    .nm{{font-size:{NAME_FONT}px;font-weight:700}}
    .n{{fill-opacity:.45}}
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
        '<filter id="bw"><feColorMatrix type="saturate" values="0"/></filter>',
        f'<rect width="{width}" height="{height}" rx="14" fill="{CARD}"/>',
        '<g filter="url(#bw)">',
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

    # The portrait: each line is scrambled letters first, then settles into dots, top to bottom.
    for i, line in enumerate(lines):
        if not line.strip(BLANK):
            continue
        y = art_top + (i + 1) * LINE_H
        delay = f'style="animation-delay:{i * 0.03:.2f}s"'
        tl = f'x="{pad}" y="{y:.1f}" textLength="{art_w:.1f}" lengthAdjust="spacing"'
        out.append(f'<g class="z" {delay}>')
        for k in range(3):
            noise = "".join(" " if c == BLANK else rnd.choice(NOISE) for c in line)
            out.append(f'<text class="d n f f{k}" {tl}>{noise}</text>')
        out.append("</g>")
        out.append(f'<text class="d r" {delay} {tl}>{line}</text>')
    out.append("</g></svg>")
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/make_hero.py path/to/photo.png")
    write_asset("hero.svg", build_svg(portrait_rows(sys.argv[1])))
    print("wrote assets/hero.svg")
