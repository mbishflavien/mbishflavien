"""Draws assets/hills.svg: Kigali's hills at the real time of day, with the real weather.

Runs from .github/workflows/hills.yml (or by hand from the Actions tab). A picture on GitHub can't read the
viewer's clock, so the scene follows Kigali's time at the moment it is drawn.

The scene aims to look calm and real rather than cartoonish: ridges fade into the haze as they get
farther away, mist sits in the valleys, the middle hills carry faint terraces, the town's houses turn
into warm windows at night, and the moon shows its real phase for the date.
"""
import datetime
import json
import math
import os
import random
import urllib.request

from common import PALETTE, USER, replace_block, stamp, write_asset

KIGALI = datetime.timezone(datetime.timedelta(hours=2))
W, H = 800, 320

P = PALETTE
GOLD, CREAM, NAVY = P["gold"], P["cream"], P["navy"]

# For each time of day: sky top and bottom, the haze far hills fade into, the nearest ridge's colour,
# and the warm glow low on the horizon around the sun.
PHASES = {
    "night": dict(top="#060a1c", bottom="#17213f", haze="#26315a", near="#0b1512", glow=None, word="night"),
    "dawn": dict(top="#27305e", bottom="#e3a77a", haze="#9b8ba6", near="#1d3124", glow="#f2c08a", word="sunrise"),
    "day": dict(top="#5b8fc4", bottom="#d3e2ec", haze="#b9cddb", near="#2d5a2b", glow="#fff3d6", word="day"),
    "dusk": dict(top="#232450", bottom="#d98a5c", haze="#8f7690", near="#1b2a21", glow="#f0a46a", word="sunset"),
}

WEATHER = [(0, "clear"), (1, "mostly clear"), (2, "partly cloudy"), (3, "cloudy"), (45, "foggy"),
           (51, "drizzle"), (61, "rain"), (80, "showers"), (95, "thunderstorm")]
CLOUDS = {0: 0, 1: 2, 2: 4, 3: 7}
LAYERS = 6
BASES = [140, 158, 178, 198, 226, 286]     # how high each ridge sits, far to near


def phase_of(hour):
    """Kigali's day: night 19:00-05:00, sunrise 05:00-10:00, day 10:00-17:00, sunset 17:00-19:00."""
    if 5 <= hour < 10:
        return "dawn"
    if 10 <= hour < 17:
        return "day"
    if 17 <= hour < 19:
        return "dusk"
    return "night"


def palette_at(hour):
    """The sky and hill colours for this exact time, blending smoothly inside each window:
    first light at 5, sunrise at 6, full day by 10; golden at 17, sunset at 18, night by 19."""
    def blend(a, b, k):
        a, b = PHASES[a], PHASES[b]
        out = {key: mix(a[key] or a["haze"], b[key] or b["haze"], k) for key in ("top", "bottom", "haze", "near", "glow")}
        out["word"] = (a if k < .5 else b)["word"]
        return out
    steps = [(5, "night"), (6, "dawn"), (10, "day"), (17, "day"), (18, "dusk"), (19, "night")]
    if hour < 5 or hour >= 19:
        return dict(PHASES["night"])
    for (h0, a), (h1, b) in zip(steps, steps[1:]):
        if h0 <= hour < h1:
            return blend(a, b, (hour - h0) / (h1 - h0))
    return dict(PHASES["day"])


def describe(code):
    word = "clear"
    for c, w in WEATHER:
        if code >= c:
            word = w
    return word


def fetch_weather():
    url = ("https://api.open-meteo.com/v1/forecast?latitude=-1.9441&longitude=30.0619"
           "&current=temperature_2m,weather_code")
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            cur = json.load(r)["current"]
        return round(cur["temperature_2m"]), int(cur["weather_code"])
    except Exception:
        return None, 0


def fetch_activity():
    """How many public things I did on GitHub in the last 30 days."""
    req = urllib.request.Request(f"https://api.github.com/users/{USER}/events/public?per_page=100")
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            events = json.load(r)
    except Exception:
        return 8
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
    return sum(1 for e in events
               if datetime.datetime.fromisoformat(e["created_at"].replace("Z", "+00:00")) > since)


# ---------- colour helpers ----------

def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, k):
    return "#" + "".join(f"{round(x + (y - x) * k):02x}" for x, y in zip(rgb(a), rgb(b)))


# ---------- line-art Kigali ----------
# An original flat line-art skyline: pastel shapes with clean outlines on a soft sky blob.
# Colours follow the hour (night, sunrise, day, sunset, blended like palette_at) and the weather.

G = 262                       # ground line
BLD = ["#f4b8a0", "#f7d38a", "#a8d5c4", "#c6b8e6", "#9cc7e8", "#f2a7a0", "#d9e3a5", "#b9d6ef"]

LINE_PHASES = {
    "night": dict(card="#0e1430", blob="#1b2650", line="#7383aa", hill="#22344c", tree="#2f4a3f", water="#24325e",
                  tint="#141b36", tint_by=.62, cloud="#2a355a"),
    "dawn": dict(card="#fbf2ea", blob="#fbd8bd", line="#4a4560", hill="#d3e3b4", tree="#93c79c", water="#f3cdb8",
                 tint="#f6b89a", tint_by=.18, cloud="#fff6ef"),
    "day": dict(card="#f8f6f0", blob="#d6ecf7", line="#3b4a6b", hill="#cfe6b8", tree="#8cc79a", water="#bfe1f2",
                tint="#ffffff", tint_by=0, cloud="#ffffff"),
    "dusk": dict(card="#f7e6dd", blob="#f6bd98", line="#4a3d5c", hill="#c9d6a6", tree="#86b48d", water="#eeb79c",
                 tint="#e58a6a", tint_by=.22, cloud="#fde9dc"),
}


def line_palette(hour):
    """The line-art colours for this exact time, blending through the day like palette_at."""
    def blend(a, b, k):
        a, b = LINE_PHASES[a], LINE_PHASES[b]
        out = {key: mix(a[key], b[key], k) for key in a if key != "tint_by"}
        out["tint_by"] = a["tint_by"] + (b["tint_by"] - a["tint_by"]) * k
        return out
    steps = [(5, "night"), (6, "dawn"), (10, "day"), (17, "day"), (18, "dusk"), (19, "night")]
    if hour < 5 or hour >= 19:
        return dict(LINE_PHASES["night"])
    for (h0, a), (h1, b) in zip(steps, steps[1:]):
        if h0 <= hour < h1:
            return blend(a, b, (hour - h0) / (h1 - h0))
    return dict(LINE_PHASES["day"])


def moon_phase(now):
    """0 = new moon, 0.5 = full moon."""
    known_new = datetime.datetime(2000, 1, 6, 18, 14, tzinfo=datetime.timezone.utc)
    days = (now - known_new).total_seconds() / 86400
    return (days % 29.530588853) / 29.530588853


def moon(cx, cy, r, phase, sky, line):
    """The moon in its real phase, drawn in the same outlined style."""
    k = math.cos(2 * math.pi * phase)
    rx = abs(k) * r
    top, bottom = f"{cx:.1f},{cy - r:.1f}", f"{cx:.1f},{cy + r:.1f}"
    if phase < 0.5:   # waxing: lit on the right
        d = f"M{top} A{r},{r} 0 0 1 {bottom} A{rx:.1f},{r} 0 0 {0 if k > 0 else 1} {top}Z"
    else:             # waning: lit on the left
        d = f"M{top} A{r},{r} 0 0 0 {bottom} A{rx:.1f},{r} 0 0 {1 if k > 0 else 0} {top}Z"
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{mix(sky, CREAM, .1)}" stroke="{line}" stroke-width="1.4"/>'
            f'<path d="{d}" fill="{CREAM}"/>')


def outline(line, w=1.5):
    return f'stroke="{line}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"'


def cloud_line(x, y, s, fill, line):
    """An outlined cartoon cloud with a flat bottom."""
    d = (f"M{x - 30 * s:.1f},{y:.1f} a{9 * s:.1f},{9 * s:.1f} 0 0 1 {8 * s:.1f},-{11 * s:.1f} "
         f"a{12 * s:.1f},{12 * s:.1f} 0 0 1 {21 * s:.1f},-{6 * s:.1f} a{11 * s:.1f},{11 * s:.1f} 0 0 1 {19 * s:.1f},{5 * s:.1f} "
         f"a{8 * s:.1f},{8 * s:.1f} 0 0 1 {12 * s:.1f},{12 * s:.1f}Z")
    return f'<path d="{d}" fill="{fill}" {outline(line, 1.3)}/>'


def windows(x, y, w, h, cols, rows, lit, win, off, line, rnd):
    """A neat grid of windows; after dark some of them glow."""
    out = []
    gw, gh = w / cols, h / rows
    for r in range(rows):
        for c in range(cols):
            on = lit and rnd.random() < .55
            out.append(f'<rect x="{x + c * gw + gw * .25:.1f}" y="{y + r * gh + gh * .25:.1f}" width="{gw * .5:.1f}" '
                       f'height="{gh * .5:.1f}" fill="{win if on else off}" rx=".4"/>')
    return "".join(out)


def tower(x, w, h, fill, top, pal, lit, rnd, cols=3, rows=None):
    """A building standing on the ground line, with a few kinds of roof."""
    line = pal["line"]
    y = G - h
    if top == "spire":
        shape = f"M{x},{G} V{y} H{x + w} V{G}Z M{x + w / 2},{y} V{y - 16}"
    elif top == "slant":
        shape = f"M{x},{G} V{y + 8} L{x + w},{y} V{G}Z"
    elif top == "step":
        shape = f"M{x},{G} V{y + 10} H{x + w * .2} V{y} H{x + w * .8} V{y + 10} H{x + w} V{G}Z"
    elif top == "round":
        shape = f"M{x},{G} V{y + w / 2} A{w / 2},{w / 2} 0 0 1 {x + w},{y + w / 2} V{G}Z"
    else:
        shape = f"M{x},{G} V{y} H{x + w} V{G}Z"
    rows = rows or max(2, int(h / 12))
    win_top = y + (12 if top in ("step", "round", "slant") else 6)
    return (f'<path d="{shape}" fill="{fill}" {outline(line)}/>'
            + windows(x + 3, win_top, w - 6, G - win_top - 8, cols, rows, lit, GOLD, mix(line, fill, .55), line, rnd))


def dome(cx, w, h, fill, pal, lit):
    """The Convention Centre's dome: a striped half-dome on a base."""
    line = pal["line"]
    base_y = G - 8
    out = [f'<rect x="{cx - w / 2 - 6}" y="{base_y}" width="{w + 12}" height="8" fill="{mix(fill, "#ffffff", .3)}" {outline(line)}/>',
           f'<path d="M{cx - w / 2},{base_y} A{w / 2},{h} 0 0 1 {cx + w / 2},{base_y}Z" fill="{fill}" {outline(line)}/>']
    for k in range(1, 6):     # curved horizontal bands
        f = k / 6
        out.append(f'<path d="M{cx - w / 2 * (1 - f * f) ** .5:.1f},{base_y - h * f:.1f} '
                   f'Q{cx:.1f},{base_y - h * f - 4:.1f} {cx + w / 2 * (1 - f * f) ** .5:.1f},{base_y - h * f:.1f}" '
                   f'fill="none" {outline(line, .9)}/>')
    for o in (-.55, -.2, .2, .55):   # ribs
        out.append(f'<path d="M{cx:.1f},{base_y - h:.1f} Q{cx + o * w * .6:.1f},{base_y - h * .5:.1f} {cx + o * w * .62:.1f},{base_y}" '
                   f'fill="none" {outline(line, .9)}/>')
    if lit:
        out.insert(0, f'<ellipse cx="{cx}" cy="{base_y - h / 2}" rx="{w * .75:.0f}" ry="{h:.0f}" fill="url(#lamp)" opacity=".45"/>')
    return "".join(out)


def tree(x, r, pal):
    line = pal["line"]
    return (f'<line x1="{x}" y1="{G}" x2="{x}" y2="{G - r - 4}" {outline(line, 1.4)}/>'
            f'<circle cx="{x}" cy="{G - r - 8:.1f}" r="{r}" fill="{pal["tree"]}" {outline(line, 1.3)}/>')


def house(x, y, w, fill, roof, pal):
    line = pal["line"]
    return (f'<path d="M{x},{y} V{y - w * .7:.1f} H{x + w} V{y}Z" fill="{fill}" {outline(line, 1.2)}/>'
            f'<path d="M{x - 2},{y - w * .7:.1f} L{x + w / 2:.1f},{y - w * 1.25:.1f} L{x + w + 2},{y - w * .7:.1f}Z" fill="{roof}" {outline(line, 1.2)}/>'
            f'<rect x="{x + w * .38:.1f}" y="{y - w * .38:.1f}" width="{w * .24:.1f}" height="{w * .38:.1f}" fill="{line}" opacity=".5"/>')


def build(now, temp, code, activity):
    hour = now.hour + now.minute / 60
    ph = phase_of(hour)
    pal = line_palette(hour)
    dark = ph == "night"
    lit = dark or hour >= 18.5 or hour < 6
    word = describe(code)
    rnd = random.Random(now.strftime("%Y%m%d%H"))      # sky details change with the hour
    land = random.Random(7)                             # the city stays the same
    overcast = code >= 3
    foggy = 45 <= code < 51
    line = pal["line"]
    tint = lambda c: mix(c, pal["tint"], pal["tint_by"])

    css = """
    .drift{animation:drift linear infinite}
    @keyframes drift{from{transform:translateX(-120px)}to{transform:translateX(120px)}}
    .tw{animation:tw 4s ease-in-out infinite alternate}
    @keyframes tw{from{opacity:.3}to{opacity:1}}
    .bird{animation:bob 3s ease-in-out infinite alternate}
    @keyframes bob{from{transform:translateY(0)}to{transform:translateY(-4px)}}
    .drop{animation:fall .9s linear infinite}
    @keyframes fall{from{transform:translate(0,-30px)}to{transform:translate(-8px,240px)}}
    .spin{animation:spin 60s linear infinite;transform-box:fill-box;transform-origin:center}
    @keyframes spin{to{transform:rotate(360deg)}}
    text{font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif}
    """
    defs = [f'<radialGradient id="lamp"><stop offset="0" stop-color="{GOLD}" stop-opacity=".8"/>'
            f'<stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>',
            f'<clipPath id="frame"><rect width="{W}" height="{H}" rx="14"/></clipPath>',
            f'<clipPath id="sky"><path id="blobpath" d="M95,{G} C70,200 120,150 175,140 C190,95 250,70 300,92 '
            f'C340,50 430,48 470,85 C510,60 590,70 610,110 C670,105 735,150 715,{G}Z"/></clipPath>']
    o = [f'<rect width="{W}" height="{H}" fill="{pal["card"]}"/>',
         f'<path d="M95,{G} C70,200 120,150 175,140 C190,95 250,70 300,92 C340,50 430,48 470,85 '
         f'C510,60 590,70 610,110 C670,105 735,150 715,{G}Z" fill="{pal["blob"]}"/>']

    # Hidden in plain sight.
    o.append(f'<text x="790" y="10" font-size="3" fill-opacity="0" text-anchor="end">{b"flag{amahoro}".hex()}</text>')

    # ---- sky, inside the blob ----
    sky = []
    if dark:
        for _ in range(26):
            x, y = rnd.uniform(110, 700), rnd.uniform(70, 190)
            s = rnd.uniform(1.5, 3)
            sky.append(f'<path class="tw" style="animation-delay:-{rnd.uniform(0, 4):.1f}s" d="M{x - s:.1f},{y:.1f} H{x + s:.1f} '
                       f'M{x:.1f},{y - s:.1f} V{y + s:.1f}" {outline(CREAM, 1)}/>')
        t = ((hour - 18) % 24) / 12
        sky.append(moon(150 + t * 500, 175 - math.sin(math.pi * t) * 95, 14, moon_phase(now), pal["blob"], line))
    elif not overcast and 6 <= hour <= 18:
        t = (hour - 6) / 12
        sx, sy = 150 + t * 500, 190 - math.sin(math.pi * t) * 115
        rays = "".join(f'<line x1="{sx + 22 * math.cos(a):.1f}" y1="{sy + 22 * math.sin(a):.1f}" '
                       f'x2="{sx + 30 * math.cos(a):.1f}" y2="{sy + 30 * math.sin(a):.1f}" {outline(line, 1.4)}/>'
                       for a in (k * math.pi / 6 for k in range(12)))
        sky.append(f'<g class="spin">{rays}</g>'
                   f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="15" fill="{mix(GOLD, "#ffb36b", .35)}" {outline(line, 1.4)}/>')
    o.append(f'<g clip-path="url(#sky)">{"".join(sky)}</g>')

    # Clouds (more and greyer with the weather) and birds by day.
    n = {0: 2, 1: 3, 2: 4}.get(code, 6)
    cfill = mix(pal["cloud"], "#9aa3b0", .35) if overcast and not dark else pal["cloud"]
    spots = [(150, 120), (330, 78), (560, 92), (650, 140), (250, 150), (470, 125)]
    for (x, y) in spots[:n]:
        s = land.uniform(.8, 1.15)
        o.append(f'<g class="drift" style="animation-duration:{land.randint(30, 50)}s;animation-direction:alternate;'
                 f'animation-delay:-{land.uniform(0, 30):.0f}s">{cloud_line(x, y, s, cfill, line)}</g>')
    if not dark and code < 51:
        for x, y in ((250, 115), (268, 122), (520, 70), (536, 64), (600, 120)):
            o.append(f'<path class="bird" style="animation-delay:-{land.uniform(0, 3):.1f}s" '
                     f'd="M{x - 5},{y} Q{x - 2.5},{y - 4} {x},{y} Q{x + 2.5},{y - 4} {x + 5},{y}" fill="none" {outline(line, 1.2)}/>')

    # ---- hills behind the city ----
    o.append(f'<path d="M80,{G} C120,205 210,200 300,{G}Z" fill="{pal["hill"]}" {outline(line)}/>')
    o.append(f'<path d="M470,{G} C520,198 640,190 735,{G}Z" fill="{mix(pal["hill"], "#ffffff", .1)}" {outline(line)}/>')

    # ---- the city, left to right ----
    c = [tint(b) for b in BLD]
    o.append(tower(110, 26, 34, c[0], "flat", pal, lit, land, 2))
    o.append(tower(132, 20, 22, c[6], "flat", pal, lit, land, 2))
    o.append(dome(210, 104, 58, tint("#d9e6ee"), pal, lit))
    o.append(tower(272, 22, 70, c[5], "slant", pal, lit, land, 2))
    o.append(tower(300, 34, 118, c[0], "spire", pal, lit, land, 3))
    o.append(tower(339, 30, 96, c[1], "step", pal, lit, land, 3))
    o.append(tower(374, 26, 132, c[2], "flat", pal, lit, land, 2))
    o.append(tower(405, 38, 80, c[4], "flat", pal, lit, land, 4))
    o.append(tower(448, 22, 104, c[3], "round", pal, lit, land, 2))
    o.append(tower(475, 28, 88, c[6], "slant", pal, lit, land, 3))
    for hx, hy in ((515, 238), (540, 230), (566, 236), (592, 242)):
        o.append(house(hx, hy, 15, tint(BLD[land.randint(0, 7)]), tint("#e98b6d"), pal))
    o.append(tower(612, 30, 64, c[7], "round", pal, lit, land, 3))
    o.append(tower(648, 24, 40, c[5], "flat", pal, lit, land, 2))
    o.append(tower(676, 20, 28, c[1], "flat", pal, lit, land, 2))

    # A low shopping row along the ground, trees and the lake.
    o.append(f'<rect x="240" y="{G - 14}" width="70" height="14" fill="{tint(BLD[7])}" {outline(line, 1.3)}/>'
             + windows(243, G - 12, 64, 10, 8, 1, lit, GOLD, mix(line, BLD[7], .55), line, land))
    for x, r in ((96, 8), (148, 7), (265, 9), (360, 7), (500, 9), (602, 8), (700, 10), (722, 7)):
        o.append(tree(x, r, pal))
    o.append(f'<path d="M620,{G} C640,{G + 12} 720,{G + 12} 740,{G}Z" fill="{pal["water"]}" {outline(line, 1.3)}/>'
             f'<line x1="650" y1="{G + 5}" x2="672" y2="{G + 5}" {outline(line, 1)}/>'
             f'<line x1="684" y1="{G + 7}" x2="706" y2="{G + 7}" {outline(line, 1)}/>')
    o.append(f'<line x1="70" y1="{G}" x2="740" y2="{G}" {outline(line, 1.6)}/>')

    # ---- weather over the scene ----
    if foggy:
        o.append(f'<rect width="{W}" height="{H}" fill="{pal["card"]}" opacity=".45"/>')
    if code >= 51:
        drops = []
        for _ in range(70 if code >= 61 else 35):
            x = rnd.uniform(110, 720)
            drops.append(f'<line class="drop" x1="{x:.0f}" y1="40" x2="{x - 3:.0f}" y2="50" {outline(line, 1.1)} '
                         f'opacity=".55" style="animation-delay:-{rnd.uniform(0, .9):.2f}s"/>')
        o.append(f'<g clip-path="url(#sky)">{"".join(drops)}</g>')

    temp_txt = f" · {temp}°C" if temp is not None else ""
    caption = f"Kigali · {now:%H:%M}{temp_txt} · {word}"
    o.append(f'<rect x="14" y="{H - 40}" width="{len(caption) * 6.6 + 24:.0f}" height="26" rx="13" '
             f'fill="{NAVY}" fill-opacity=".55"/>'
             f'<text x="26" y="{H - 22}" font-size="13" fill="{CREAM}">{caption}</text>')

    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">',
        f"<title>Kigali right now: {word}</title>",
        f"<style>{css}</style>",
        f"<defs>{''.join(defs)}</defs>",
        '<g clip-path="url(#frame)">',
        *o,
        "</g></svg>"]), caption


def main():
    now = datetime.datetime.now(KIGALI)
    temp, code = fetch_weather()
    activity = fetch_activity()
    svg, caption = build(now, temp, code, activity)
    write_asset("hills.svg", svg)
    replace_block("hills", f'<img src="assets/hills.svg?v={stamp()}" alt="{caption}" width="100%">')
    print(caption, "| activity:", activity)


if __name__ == "__main__":
    main()
