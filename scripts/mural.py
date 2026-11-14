"""The Imigongo wall: 48 tiles, each visitor paints one (max 3 per person per wall).

The SVG replays the wall being painted in the order people painted it, then loops.
"""
import datetime

from common import esc, issue_url, load, replace_block, save, stamp, write_asset

COLS, ROWS, T = 8, 6, 80
LETTERS = "ABCDEFGH"
BLACK, WHITE, OCHRE, GREY = "#1b1b1b", "#f2ece1", "#9c3b22", "#8a8a8a"
COLORWAYS = [(BLACK, WHITE), (OCHRE, BLACK), (WHITE, BLACK), (BLACK, OCHRE), (WHITE, OCHRE), (GREY, WHITE)]
PER_PERSON = 3


def tile_id(r, c):
    return f"{LETTERS[c]}{r + 1}"


def fresh_state(walls_done=0):
    return {"walls_done": walls_done, "painted": [], "painters": {}}


def motif(kind, bg, fg):
    """One 80x80 imigongo-style tile, drawn at 0,0."""
    o = [f'<rect width="{T}" height="{T}" fill="{bg}"/>']
    if kind == 0:  # zigzag bands
        for k in range(4):
            y = 10 + k * 20
            pts = " ".join(f"{x},{y + (6 if (x // 10) % 2 else -6)}" for x in range(0, T + 10, 10))
            o.append(f'<polyline points="{pts}" fill="none" stroke="{fg}" stroke-width="5"/>')
    elif kind == 1:  # nested diamonds
        for k, s in enumerate([38, 28, 18, 8]):
            col = fg if k % 2 == 0 else bg
            o.append(f'<polygon points="40,{40 - s} {40 + s},40 40,{40 + s} {40 - s},40" fill="{col}"/>')
    elif kind == 2:  # hourglass triangles
        o.append(f'<polygon points="4,4 76,4 40,38" fill="{fg}"/><polygon points="4,76 76,76 40,42" fill="{fg}"/>')
        o.append(f'<polygon points="22,12 58,12 40,28" fill="{bg}"/><polygon points="22,68 58,68 40,52" fill="{bg}"/>')
    else:  # diagonal stripes
        for k in range(-80, 160, 20):
            o.append(f'<line x1="{k}" y1="0" x2="{k + 80}" y2="80" stroke="{fg}" stroke-width="7"/>')
    return "".join(o)


def kind_of(r, c):
    # Mirrored layout so the finished wall reads as one big pattern.
    mc, mr = min(c, COLS - 1 - c), min(r, ROWS - 1 - r)
    return (mc + mr) % 4


def wall_svg(st):
    pad, top = 20, 44
    w, h = COLS * T + pad * 2, ROWS * T + top + 40
    painted = {p["tile"]: k for k, p in enumerate(st["painted"])}
    n = len(painted)
    cycle = max(8, n * 0.35 + 5)
    css = ["text{font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif}",
           ".id{font-size:13px;fill:#7a6a5a;text-anchor:middle}",
           ".hd{font-size:15px;fill:#f2ece1;font-weight:600;letter-spacing:.05em}"]
    o = []
    for r in range(ROWS):
        for c in range(COLS):
            tid = tile_id(r, c)
            x, y = pad + c * T, top + r * T
            o.append(f'<g transform="translate({x},{y})"><rect width="{T}" height="{T}" fill="#2f2620"/>'
                     f'<rect x="3" y="3" width="{T - 6}" height="{T - 6}" fill="none" stroke="#5a4a3c" stroke-dasharray="4 4"/>'
                     f'<text x="40" y="45" class="id">{tid}</text></g>')
            if tid in painted:
                k = painted[tid]
                on = (k * 0.35 + 0.5) / cycle * 100
                bg, fg = COLORWAYS[(r * 3 + c + st["walls_done"]) % len(COLORWAYS)]
                css.append(f"@keyframes p{k}{{0%,{on:.1f}%{{opacity:0}}{on + 1.5:.1f}%,94%{{opacity:1}}100%{{opacity:0}}}}"
                           f".p{k}{{animation:p{k} {cycle:.1f}s linear infinite both}}")
                o.append(f'<g class="p{k}" transform="translate({x},{y})" clip-path="url(#tile)">'
                         f'{motif(kind_of(r, c), bg, fg)}</g>')
    head = (f'<text x="{pad}" y="28" class="hd">IMIGONGO WALL #{st["walls_done"] + 1}</text>'
            f'<text x="{w - pad}" y="28" class="hd" text-anchor="end">{n} / {COLS * ROWS} PAINTED</text>')
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">',
        f"<title>Imigongo wall, {n} of {COLS * ROWS} tiles painted</title>",
        f"<style>{''.join(css)}</style>",
        f'<defs><clipPath id="tile"><rect width="{T}" height="{T}"/></clipPath></defs>',
        f'<rect width="{w}" height="{h}" rx="18" fill="#1f1914"/>', head, *o,
        f'<text x="{w / 2}" y="{h - 14}" class="id" text-anchor="middle">the wall replays in the order people painted it</text>',
        "</svg>"])


def play(login, arg):
    st = load("mural.json")
    tid = arg.strip().upper()
    valid = {tile_id(r, c) for r in range(ROWS) for c in range(COLS)}
    if tid not in valid:
        return "I couldn't find that tile. Use one of the links under the wall."
    if any(p["tile"] == tid for p in st["painted"]):
        return f"Tile {tid} is already painted. Pick an empty one from the list under the wall."
    if st["painters"].get(login, 0) >= PER_PERSON:
        return f"You've already painted {PER_PERSON} tiles on this wall. Thank you! Leave the rest for others. 🙏"
    st["painted"].append({"tile": tid, "by": login, "at": datetime.date.today().isoformat()})
    st["painters"][login] = st["painters"].get(login, 0) + 1
    reply = f"You painted tile **{tid}**. 🎨 It shows up on the wall in a minute or so."
    if len(st["painted"]) == COLS * ROWS:
        save(f"mural_wall_{st['walls_done'] + 1}.json", st)
        st = fresh_state(st["walls_done"] + 1)
        reply += "\n\nThat was the last tile: **the wall is complete!** 🎉 It has been saved and a fresh wall has started."
    save("mural.json", st)
    render(st)
    return reply


def render(st=None):
    st = st or load("mural.json")
    write_asset("mural.svg", wall_svg(st))
    by_tile = {p["tile"]: p["by"] for p in st["painted"]}
    rows = []
    for r in range(ROWS):
        cells = []
        for c in range(COLS):
            tid = tile_id(r, c)
            if tid in by_tile:
                cells.append(f'<td align="center"><sub>{tid}</sub><br>🎨</td>')
            else:
                cells.append(f'<td align="center"><a href="{esc(issue_url(f"mural|paint|{tid}"))}">{tid}</a></td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    left = COLS * ROWS - len(by_tile)
    recent = ", ".join(f'<a href="https://github.com/{esc(p["by"])}">@{esc(p["by"])}</a> ({p["tile"]})'
                       for p in st["painted"][-6:][::-1]) or "nobody yet"
    replace_block("mural", f"""
<p align="center"><img src="assets/mural.svg?v={stamp()}" alt="Imigongo wall" width="100%"></p>

<details>
<summary><b>🖌️ Paint a tile</b> ({left} left, up to {PER_PERSON} per person)</summary>
<br>
<table align="center">
{"".join(rows)}
</table>
</details>

<p align="center"><sub>Recently painted by {recent}</sub></p>
""")


if __name__ == "__main__":
    save("mural.json", fresh_state())
    render()
    print("new wall ready")
