"""Turns a portrait photo into assets/hero.svg: scrambled letters that settle into a dot portrait
(braille characters, 8 dots each), black on a white card, so it looks like the photo (not a negative) on both light and dark GitHub.

Only needs to run once:  python scripts/make_hero.py path/to/photo.png
The photo itself is not stored in the repo.
"""
import base64
import random
import sys

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from common import write_asset

COLS = 110
CHAR_W = 4.0          # one braille character = 2 x 4 dots, so it is twice as tall as it is wide
LINE_H = 8.0
FONT = 8
NOISE = "abcdefghijkmnopqrstuvwxyz0123456789"
CYCLE = 14            # seconds for one full loop
INK, PAPER = "#111111", "#ffffff"
BLANK = chr(0x2800)
DOTS = [(0, 0, 0x01), (0, 1, 0x02), (0, 2, 0x04), (1, 0, 0x08), (1, 1, 0x10), (1, 2, 0x20), (0, 3, 0x40), (1, 3, 0x80)]


def portrait_rows(photo):
    """Dithers the photo into black dots and packs every 2x4 block of dots into one braille character."""
    img = Image.open(photo).convert("RGBA")
    alpha = img.getchannel("A").point(lambda a: 255 if a > 128 else 0)
    img = img.crop(alpha.getbbox())
    paper = Image.new("RGB", img.size, "white")
    paper.paste(img.convert("RGB"), mask=img.getchannel("A"))

    gray = ImageOps.grayscale(paper).filter(ImageFilter.UnsharpMask(radius=3, percent=120, threshold=0))
    gray = ImageEnhance.Brightness(ImageEnhance.Contrast(gray).enhance(1.35)).enhance(1.2)
    w = COLS * 2
    h = int(img.height * w / img.width) // 4 * 4
    dots = gray.resize((w, h), Image.LANCZOS).convert("1")   # Floyd-Steinberg dithering

    lines = []
    for y in range(0, h, 4):
        line = ""
        for x in range(0, w, 2):
            v = sum(bit for dx, dy, bit in DOTS if dots.getpixel((x + dx, y + dy)) == 0)
            line += chr(0x2800 + v)
        lines.append(line)
    return lines


def build_svg(lines):
    rnd = random.Random(3)
    art_w = COLS * CHAR_W
    pad = 18
    width = int(art_w + pad * 2)
    art_h = len(lines) * LINE_H
    name_y = pad + art_h + 34
    height = int(name_y + 22)
    flag = base64.b64encode(b"flag{murakaza_neza}").decode()

    css = f"""
    text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:{FONT}px;white-space:pre;fill:{INK}}}
    .n{{fill-opacity:.35}}
    .r{{animation:show {CYCLE}s linear infinite both}}
    .z{{animation:hide {CYCLE}s linear infinite both}}
    .f{{opacity:0;animation:flick .45s steps(1) infinite}}
    .f1{{animation-delay:.15s}} .f2{{animation-delay:.3s}}
    @keyframes show{{0%,12%{{opacity:0}}16%,86%{{opacity:1}}90%,100%{{opacity:0}}}}
    @keyframes hide{{0%,12%{{opacity:1}}16%,86%{{opacity:0}}90%,100%{{opacity:1}}}}
    @keyframes flick{{0%{{opacity:1}}33%,100%{{opacity:0}}}}
    .name{{font-size:17px;letter-spacing:.14em}}
    """
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img">',
        "<title>Flavien Mbishibishi, drawn in letters</title>",
        f"<!-- you found a quiet corner: {flag} -->",
        f"<style>{css}</style>",
        f'<defs><clipPath id="type"><rect x="0" y="{name_y - 20}" height="28" width="0">'
        f'<animate attributeName="width" values="0;0;{width};{width};0;0" keyTimes="0;.28;.4;.88;.9;1" '
        f'dur="{CYCLE}s" repeatCount="indefinite"/></rect></clipPath></defs>',
        f'<filter id="bw"><feColorMatrix type="saturate" values="0"/></filter>',
        f'<rect width="{width}" height="{height}" rx="14" fill="{PAPER}"/>',
        '<g filter="url(#bw)">',
    ]
    for i, line in enumerate(lines):
        if not line.strip(BLANK):
            continue
        y = pad + (i + 1) * LINE_H
        delay = f'style="animation-delay:{i * 0.03:.2f}s"'
        tl = f'x="{pad}" y="{y:.1f}" textLength="{art_w:.1f}" lengthAdjust="spacing"'
        out.append(f'<g class="z" {delay}>')
        for k in range(3):
            noise = "".join(" " if ch == BLANK else rnd.choice(NOISE) for ch in line)
            out.append(f'<text class="n f f{k}" {tl}>{noise}</text>')
        out.append("</g>")
        out.append(f'<text class="r" {delay} {tl}>{line}</text>')
    out += [
        f'<text class="name" x="{width / 2}" y="{name_y}" text-anchor="middle" clip-path="url(#type)">FLAVIEN MBISHIBISHI</text>',
        "</g></svg>",
    ]
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/make_hero.py path/to/photo.png")
    write_asset("hero.svg", build_svg(portrait_rows(sys.argv[1])))
    print("wrote assets/hero.svg")
