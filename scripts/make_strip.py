"""Draws assets/strip-light.svg and assets/strip-dark.svg: a thin, endlessly scrolling Imigongo border.

Only needs to run once:  python scripts/make_strip.py
"""
from common import write_asset
THEMES = {"light": "#1f2328", "dark": "#e6edf3"}   # GitHub's own text colours

W, H, U = 800, 30, 30      # canvas width, height, width of one motif
TOP, BOT, MID = 4, 26, 15


def motifs(fg):
    """One repeat of the pattern: 8 motifs side by side, each U wide."""
    m = [
        f'<polygon points="0,{BOT} {U / 2},{TOP} {U},{BOT}" fill="{fg}"/>',                         # mountain
        f'<polygon points="{U / 2},{TOP} {U},{MID} {U / 2},{BOT} 0,{MID}" fill="none" stroke="{fg}" stroke-width="2"/>'
        f'<polygon points="{U / 2},{TOP + 6} {U - 6},{MID} {U / 2},{BOT - 6} 6,{MID}" fill="{fg}"/>',  # diamond in diamond
        f'<polygon points="0,{TOP} {U},{TOP} {U / 2},{MID}" fill="{fg}"/>'
        f'<polygon points="0,{BOT} {U},{BOT} {U / 2},{MID}" fill="{fg}"/>',                          # hourglass
        f'<polyline points="0,{BOT - 3} 7.5,{TOP + 3} 15,{BOT - 3} 22.5,{TOP + 3} 30,{BOT - 3}" fill="none" stroke="{fg}" stroke-width="3"/>',  # zigzag
    ]
    seq = m + m[::-1]
    return "".join(f'<g transform="translate({i * U},0)">{s}</g>' for i, s in enumerate(seq)), len(seq) * U


def build(fg):
    one, span = motifs(fg)
    copies = W // span + 2
    row = "".join(f'<g transform="translate({k * span},0)">{one}</g>' for k in range(copies))
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">',
        "<title>Imigongo pattern</title>",
        f"<style>.roll{{animation:roll 14s linear infinite}}@keyframes roll{{to{{transform:translateX(-{span}px)}}}}</style>",
        f'<line x1="0" y1="0.5" x2="{W}" y2="0.5" stroke="{fg}"/><line x1="0" y1="{H - .5}" x2="{W}" y2="{H - .5}" stroke="{fg}"/>',
        f'<g class="roll">{row}</g>',
        "</svg>"])


if __name__ == "__main__":
    for theme, fg in THEMES.items():
        write_asset(f"strip-{theme}.svg", build(fg))
    print("wrote assets/strip-light.svg and assets/strip-dark.svg")
