"""Draws assets/strip.svg: a slowly scrolling Imigongo band.

Imigongo panels are black, white and red ochre (here on the profile's night blue, with a touch of sky, hill green and gold), with sharp geometric relief:
nested diamonds, chevrons, hourglasses and zigzags. One band works on both
light and dark GitHub, like the black card of the portrait.

Only needs to run once:  python scripts/make_strip.py
"""
from common import PALETTE, write_asset

W, H, U = 800, 44, 44        # canvas width, height, width of one motif
P = PALETTE
BLACK, WHITE, OCHRE = P["navy"], P["cream"], P["ochre"]
GREEN = P["green"]
CLAY = "#2b3d70"             # one step lighter than the night blue, for the sawtooth edges
C = U / 2                     # centre of a motif
TOP, BOT = 7, H - 7           # inner edges of the borders


def diamond(r, fill):
    return f'<polygon points="{C},{H / 2 - r} {C + r},{H / 2} {C},{H / 2 + r} {C - r},{H / 2}" fill="{fill}"/>'


def nested_diamond(a, b):
    return "".join(diamond(r, col) for r, col in [(15, a), (11.5, BLACK), (8, b), (4.5, BLACK), (2, a)])


def chevrons(right=True):
    o = []
    for k, col in enumerate([WHITE, P["sky"], WHITE]):
        x = 8 + k * 9
        tip = x + 9 if right else x
        back = x if right else x + 9
        o.append(f'<polyline points="{back},{TOP + 2} {tip},{H / 2} {back},{BOT - 2}" fill="none" '
                 f'stroke="{col}" stroke-width="3.2" stroke-linejoin="miter"/>')
    return "".join(o)


def hourglass():
    return (f'<polygon points="5,{TOP + 1} {U - 5},{TOP + 1} {C},{H / 2}" fill="{WHITE}"/>'
            f'<polygon points="5,{BOT - 1} {U - 5},{BOT - 1} {C},{H / 2}" fill="{WHITE}"/>'
            f'<polygon points="13,{TOP + 5} {U - 13},{TOP + 5} {C},{H / 2 - 5}" fill="{GREEN}"/>'
            f'<polygon points="13,{BOT - 5} {U - 13},{BOT - 5} {C},{H / 2 + 5}" fill="{GREEN}"/>')


def zigzags():
    def line(y0, amp, col):
        pts = " ".join(f"{x},{y0 + (amp if (x // 11) % 2 else -amp)}" for x in range(0, U + 11, 11))
        return f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="3" stroke-linejoin="miter"/>'
    return line(H / 2 - 7, 4, WHITE) + line(H / 2, 4, OCHRE) + line(H / 2 + 7, 4, WHITE)


def teeth():
    """Sawtooth borders, the classic edge of an Imigongo panel."""
    o = []
    for x in range(0, U, 11):
        o.append(f'<polygon points="{x},0 {x + 11},0 {x + 5.5},{TOP - 1}" fill="{CLAY}"/>')
        o.append(f'<polygon points="{x},{H} {x + 11},{H} {x + 5.5},{BOT + 1}" fill="{CLAY}"/>')
    return "".join(o)


def repeat_unit():
    seq = [nested_diamond(WHITE, OCHRE), chevrons(True), hourglass(), zigzags(),
           nested_diamond(OCHRE, P["gold"]), chevrons(False), hourglass(), zigzags()]
    body = "".join(f'<g transform="translate({i * U},0)">{teeth()}{m}</g>' for i, m in enumerate(seq))
    return body, len(seq) * U


def build():
    unit, span = repeat_unit()
    copies = W // span + 2
    row = "".join(f'<g transform="translate({k * span},0)">{unit}</g>' for k in range(copies))
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">',
        "<title>Imigongo pattern</title>",
        f"<style>.roll{{animation:roll 22s linear infinite}}@keyframes roll{{to{{transform:translateX(-{span}px)}}}}</style>",
        f'<defs><clipPath id="c"><rect width="{W}" height="{H}" rx="8"/></clipPath></defs>',
        '<g clip-path="url(#c)">',
        f'<rect width="{W}" height="{H}" fill="{BLACK}"/>',
        f'<g class="roll">{row}</g>',
        "</g></svg>"])


if __name__ == "__main__":
    write_asset("strip.svg", build())
    print("wrote assets/strip.svg")
