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
# An original flat line-art view of Kigali built from the city's real landmarks: the Convention Centre
# dome, Kigali City Tower, BK Arena, Mount Kigali and hills covered in houses, with royal palms,
# jacarandas and acacias. Colours follow the hour (night, sunrise, day, sunset) and the weather.

G = 262                       # ground line (the boulevard)
BLOB = (f"M95,{G} C70,200 115,150 170,138 C185,92 250,66 300,88 C340,44 430,40 472,80 "
        f"C515,55 595,66 615,108 C672,102 738,150 718,{G}Z")

LINE_PHASES = {
    "night": dict(card="#0e1430", blob="#1b2650", line="#7383aa", hill="#22344c", tree="#2f4a3f", road="#2a3352",
                  tint="#141b36", tint_by=.62, cloud="#2a355a"),
    "dawn": dict(card="#fbf2ea", blob="#fbd8bd", line="#4a4560", hill="#d3e3b4", tree="#93c79c", road="#e9ddd2",
                 tint="#f6b89a", tint_by=.18, cloud="#fff6ef"),
    "day": dict(card="#f8f6f0", blob="#d6ecf7", line="#3b4a6b", hill="#cfe6b8", tree="#8cc79a", road="#e6e2da",
                tint="#ffffff", tint_by=0, cloud="#ffffff"),
    "dusk": dict(card="#f7e6dd", blob="#f6bd98", line="#4a3d5c", hill="#c9d6a6", tree="#86b48d", road="#ead6cb",
                 tint="#e58a6a", tint_by=.22, cloud="#fde9dc"),
    # Between night and day: deep purple-blue, so the change never passes through grey.
    "twilight": dict(card="#2e2a4f", blob="#5a4b7e", line="#a297c2", hill="#3c4a5c", tree="#3d5a4d", road="#433c5f",
                     tint="#3a2f5e", tint_by=.42, cloud="#6c5f8c"),
}
NIGHT_LIGHTS = ["#f3c969", "#7fa7d4", "#e07a5f", "#a8d5c4", "#c6b8e6"]   # the Convention Centre's dome lights


def line_palette(hour):
    """The line-art colours for this exact time, blending through the day like palette_at."""
    def blend(a, b, k):
        a, b = LINE_PHASES[a], LINE_PHASES[b]
        out = {key: mix(a[key], b[key], k) for key in a if key != "tint_by"}
        out["tint_by"] = a["tint_by"] + (b["tint_by"] - a["tint_by"]) * k
        return out
    # Sunset colours hold until 18:30, then fade quickly to night, so the scene never turns muddy.
    steps = [(5, "night"), (5.5, "twilight"), (6, "dawn"), (10, "day"), (17, "day"), (18, "dusk"), (18.4, "dusk"),
             (18.7, "twilight"), (19, "night")]
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


def windows(x, y, w, h, cols, rows, lit, off, rnd):
    """A neat grid of windows; after dark some of them glow."""
    out = []
    gw, gh = w / cols, h / rows
    for r in range(rows):
        for c in range(cols):
            on = lit and rnd.random() < .55
            out.append(f'<rect x="{x + c * gw + gw * .25:.1f}" y="{y + r * gh + gh * .28:.1f}" width="{gw * .5:.1f}" '
                       f'height="{gh * .44:.1f}" fill="{GOLD if on else off}" rx=".4"/>')
    return "".join(out)


def block(x, w, h, fill, pal, lit, rnd, cols=3, top="flat", base=G):
    """A plain building on the ground with windows; roofs can be flat, slanted or stepped."""
    line, y = pal["line"], base - h
    if top == "slant":
        shape = f"M{x},{base} V{y + 12} L{x + w},{y} V{base}Z"
    elif top == "step":
        shape = f"M{x},{base} V{y + 9} H{x + w * .2} V{y} H{x + w * .8} V{y + 9} H{x + w} V{base}Z"
    else:
        shape = f"M{x},{base} V{y} H{x + w} V{base}Z"
    wt = y + (14 if top != "flat" else 6)
    return (f'<path d="{shape}" fill="{fill}" {outline(line)}/>'
            + windows(x + 3, wt, w - 6, base - wt - 6, cols, max(2, int((base - wt) / 11)), lit, mix(line, fill, .55), rnd))


# ----- Kigali's landmarks -----

def convention_centre(cx, pal, lit, tint):
    """Kigali Convention Centre: a tall glass dome in stacked bands, glowing in colours at night."""
    line, w, h, base = pal["line"], 124, 86, G - 10
    glass = tint("#cfe0ea")
    out = []
    if lit:
        out.append(f'<ellipse cx="{cx}" cy="{base - h / 2}" rx="{w * .8:.0f}" ry="{h:.0f}" fill="url(#lamp)" opacity=".4"/>')
    out.append(f'<rect x="{cx - w / 2 - 8}" y="{base}" width="{w + 16}" height="10" fill="{tint("#e8eef2")}" {outline(line)}/>')
    # The dome: a tall curve made of stacked horizontal bands.
    bands = 7
    for k in range(bands):
        f0, f1 = k / bands, (k + 1) / bands
        w0, w1 = w / 2 * (1 - f0 ** 2.2) ** .5, w / 2 * (1 - f1 ** 2.2) ** .5
        y0, y1 = base - h * f0, base - h * f1
        fill = NIGHT_LIGHTS[k % len(NIGHT_LIGHTS)] if lit else (glass if k % 2 else mix(glass, "#ffffff", .45))
        out.append(f'<path d="M{cx - w0:.1f},{y0:.1f} L{cx - w1:.1f},{y1:.1f} L{cx + w1:.1f},{y1:.1f} L{cx + w0:.1f},{y0:.1f}Z" '
                   f'fill="{fill}" opacity="{.85 if lit else 1}" {outline(line, 1)}/>')
    for o in (-.6, -.3, 0, .3, .6):   # glass mullions
        out.append(f'<path d="M{cx + o * w * .08:.1f},{base - h:.1f} Q{cx + o * w * .45:.1f},{base - h * .55:.1f} '
                   f'{cx + o * w * .5:.1f},{base}" fill="none" {outline(line, .7)} opacity=".6"/>')
    return "".join(out)


def radisson(x, pal, lit, tint, rnd):
    """The curved hotel beside the Convention Centre."""
    line, w, h = pal["line"], 54, 40
    fill = tint("#efe2cf")
    shape = f"M{x},{G} V{G - h + 8} Q{x + w / 2},{G - h - 6} {x + w},{G - h + 8} V{G}Z"
    return (f'<path d="{shape}" fill="{fill}" {outline(line)}/>'
            + windows(x + 4, G - h + 10, w - 8, h - 16, 6, 3, lit, mix(line, fill, .55), rnd))


def city_tower(x, pal, lit, tint, rnd):
    """Kigali City Tower: the tallest building, a glass tower with a rounded front,
    horizontal bands, an open crown frame on top and the shopping podium at its base."""
    line, w, h = pal["line"], 44, 142
    glass = tint("#a9c9de")
    top = G - 26 - h
    body = f"M{x},{G - 26} V{top + 10} Q{x},{top} {x + 10},{top} H{x + w - 14} Q{x + w},{top} {x + w},{top + 16} V{G - 26}Z"
    out = [f'<path d="{body}" fill="{glass}" {outline(line)}/>']
    for yy in range(int(top + 14), G - 30, 7):   # floors
        out.append(f'<line x1="{x + 2}" y1="{yy}" x2="{x + w - 2}" y2="{yy}" {outline(line, .6)} opacity=".55"/>')
    out.append(f'<rect x="{x + w * .62:.1f}" y="{top + 8}" width="{w * .16:.1f}" height="{h - 12}" fill="{mix(glass, "#ffffff", .4)}" '
               f'{outline(line, .8)}/>')
    if lit:
        for yy in range(int(top + 15), G - 30, 7):
            for xx in range(int(x + 4), int(x + w - 6), 6):
                if rnd.random() < .45:
                    out.append(f'<rect x="{xx}" y="{yy + 1.5}" width="3" height="3" fill="{GOLD}"/>')
    # The crown: an open frame standing on the roof.
    out.append(f'<path d="M{x + 6},{top} V{top - 14} H{x + w - 6} V{top}" fill="none" {outline(line, 1.4)}/>'
               f'<line x1="{x + w / 2}" y1="{top - 14}" x2="{x + w / 2}" y2="{top - 26}" {outline(line, 1.2)}/>')
    # The podium (the mall at the bottom).
    pod = tint("#f1d3b3")
    out.append(f'<rect x="{x - 22}" y="{G - 26}" width="{w + 44}" height="26" fill="{pod}" {outline(line)}/>'
               + windows(x - 19, G - 23, w + 38, 18, 9, 2, lit, mix(line, pod, .55), rnd))
    return "".join(out)


def peace_plaza(x, pal, lit, tint, rnd):
    """A tall tower with a sharply slanted top and a green glass strip."""
    line, w, h = pal["line"], 32, 130
    fill = tint("#a8d5c4")
    y = G - h
    out = [f'<path d="M{x},{G} V{y + 22} L{x + w},{y} V{G}Z" fill="{fill}" {outline(line)}/>',
           f'<path d="M{x + w * .55},{G} V{y + 9} L{x + w * .75},{y + 5} V{G}Z" fill="{mix(fill, "#2f7d62", .3)}" {outline(line, .8)}/>']
    out.append(windows(x + 2, y + 28, w * .5, h - 34, 2, 10, lit, mix(line, fill, .55), rnd))
    return "".join(out)


def bank_tower(x, pal, lit, tint, rnd):
    """A blue glass office tower with vertical fins."""
    line, w, h = pal["line"], 30, 116
    fill = tint("#9cc7e8")
    y = G - h
    out = [f'<path d="M{x},{G} V{y} H{x + w} V{G}Z" fill="{fill}" {outline(line)}/>',
           f'<rect x="{x - 2}" y="{y - 6}" width="{w + 4}" height="6" fill="{tint("#e8eef2")}" {outline(line, 1.2)}/>']
    for k in range(1, 5):
        xx = x + k * w / 5
        out.append(f'<line x1="{xx:.1f}" y1="{y + 2}" x2="{xx:.1f}" y2="{G - 2}" {outline(line, .7)} opacity=".6"/>')
    if lit:
        for yy in range(y + 6, G - 6, 8):
            for k in range(5):
                if rnd.random() < .4:
                    out.append(f'<rect x="{x + k * w / 5 + 1.5:.1f}" y="{yy}" width="{w / 5 - 3:.1f}" height="3" fill="{GOLD}"/>')
    return "".join(out)


def twin_towers(x, pal, lit, tint, rnd):
    """Two joined towers of different heights."""
    a = block(x, 20, 96, tint("#f4b8a0"), pal, lit, rnd, 2, "step")
    b = block(x + 20, 20, 84, tint("#f7d38a"), pal, lit, rnd, 2, "step")
    return a + b


def arena(x, pal, lit, tint):
    """BK Arena: a long low hall under a gently curved roof."""
    line, w, h = pal["line"], 96, 28
    wall = tint("#c6b8e6")
    roof = tint("#e8eef2")
    out = [f'<rect x="{x}" y="{G - h}" width="{w}" height="{h}" fill="{wall}" {outline(line)}/>',
           f'<path d="M{x - 4},{G - h} Q{x + w / 2},{G - h - 22} {x + w + 4},{G - h}Z" fill="{roof}" {outline(line)}/>']
    for k in range(1, 8):
        xx = x + k * w / 8
        out.append(f'<line x1="{xx:.1f}" y1="{G - h + 4}" x2="{xx:.1f}" y2="{G - 4}" {outline(line, .8)} opacity=".6"/>')
    if lit:
        out.append(f'<rect x="{x + 4}" y="{G - h + 6}" width="{w - 8}" height="6" fill="{GOLD}" opacity=".7"/>')
    return "".join(out)


def hillside(d, fill, pal, lit, rnd, houses, area):
    """A hill covered in small houses, Kigali's signature look."""
    line = pal["line"]
    out = [f'<path d="{d}" fill="{fill}" {outline(line)}/>']
    x0, x1, ytop = area
    for _ in range(houses):
        x = rnd.uniform(x0, x1)
        y = rnd.uniform(ytop, G - 6)
        if lit:
            if rnd.random() < .7:
                out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="2" height="2" fill="{GOLD}" opacity=".85"/>')
        else:
            wall = mix(CREAM, fill, .2)
            roof = mix("#d9826a", fill, .25)
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="4" height="3" fill="{wall}" {outline(line, .5)}/>'
                       f'<path d="M{x - .5:.1f},{y:.1f} L{x + 2:.1f},{y - 2:.1f} L{x + 4.5:.1f},{y:.1f}Z" fill="{roof}"/>')
    return "".join(out)


def palm(x, h, pal):
    """A royal palm, like the ones lining Kigali's boulevards."""
    line, top = pal["line"], G - h
    fronds = "".join(f'<path d="M{x},{top} Q{x + dx * .5:.1f},{top - 8 + abs(dx) * .1:.1f} {x + dx:.1f},{top + 4 + abs(dx) * .25:.1f}" '
                     f'fill="none" stroke="{pal["tree"]}" stroke-width="3.2" stroke-linecap="round"/>' for dx in (-12, -7, 7, 12, -2, 3))
    return (f'<line x1="{x}" y1="{G}" x2="{x}" y2="{top}" {outline(line, 2)}/>' + fronds
            + f'<circle cx="{x}" cy="{top}" r="1.8" fill="{line}"/>')


def jacaranda(x, r, pal, tint):
    """A jacaranda in purple bloom."""
    line = pal["line"]
    bloom = tint("#b39ddb")
    return (f'<line x1="{x}" y1="{G}" x2="{x}" y2="{G - r - 4}" {outline(line, 1.5)}/>'
            f'<circle cx="{x - r * .5:.1f}" cy="{G - r - 7:.1f}" r="{r * .75:.1f}" fill="{bloom}" {outline(line, 1.1)}/>'
            f'<circle cx="{x + r * .5:.1f}" cy="{G - r - 8:.1f}" r="{r * .8:.1f}" fill="{bloom}" {outline(line, 1.1)}/>'
            f'<circle cx="{x:.1f}" cy="{G - r - 12:.1f}" r="{r * .8:.1f}" fill="{mix(bloom, "#ffffff", .15)}" {outline(line, 1.1)}/>')


def acacia(x, w, pal):
    """A flat-topped acacia."""
    line = pal["line"]
    return (f'<path d="M{x},{G} V{G - 14} M{x},{G - 10} L{x - 5},{G - 16} M{x},{G - 11} L{x + 6},{G - 17}" fill="none" {outline(line, 1.5)}/>'
            f'<path d="M{x - w / 2},{G - 16} Q{x},{G - 28} {x + w / 2},{G - 16}Z" fill="{pal["tree"]}" {outline(line, 1.2)}/>')


def build(now, temp, code, activity):
    hour = now.hour + now.minute / 60
    ph = phase_of(hour)
    pal = line_palette(hour)
    dark = ph == "night"
    lit = dark or hour >= 18.5 or hour < 6
    word = describe(code)
    rnd = random.Random(now.strftime("%Y%m%d%H"))      # sky details change with the hour
    land = random.Random(7)                             # the city stays the same
    partly, overcast = code == 2, code >= 3
    foggy, rainy, storm = 45 <= code < 51, code >= 51, code >= 95

    # Clouds and rain mute the colours.
    if rainy:
        grey, by = "#8f99a8", .5
    elif overcast:
        grey, by = "#b8c0ca", .38
    else:
        grey, by = "#ffffff", 0
    if dark:
        by *= .5
    pal["blob"] = mix(pal["blob"], grey, by)
    pal["card"] = mix(pal["card"], grey, by * .4)
    line = pal["line"]
    tint = lambda c: mix(mix(c, pal["tint"], pal["tint_by"]), grey, by * .35)

    css = """
    .drift{animation:drift linear infinite alternate}
    @keyframes drift{from{transform:translateX(-14px)}to{transform:translateX(14px)}}
    .tw{animation:tw 4s ease-in-out infinite alternate}
    @keyframes tw{from{opacity:.3}to{opacity:1}}
    .bird{animation:bob 3s ease-in-out infinite alternate}
    @keyframes bob{from{transform:translateY(0)}to{transform:translateY(-4px)}}
    .drop{animation:fall .8s linear infinite}
    @keyframes fall{from{transform:translate(0,0)}to{transform:translate(-8px,210px)}}
    .spin{animation:spin 60s linear infinite;transform-box:fill-box;transform-origin:center}
    @keyframes spin{to{transform:rotate(360deg)}}
    .flash{animation:flash 7s linear infinite;opacity:0}
    @keyframes flash{0%,90%{opacity:0}91%{opacity:1}92%{opacity:.2}93%{opacity:.9}95%,100%{opacity:0}}
    text{font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif}
    """
    defs = [f'<radialGradient id="lamp"><stop offset="0" stop-color="{GOLD}" stop-opacity=".8"/>'
            f'<stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>',
            f'<linearGradient id="fog" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{pal["card"]}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{pal["card"]}" stop-opacity=".85"/></linearGradient>',
            f'<clipPath id="frame"><rect width="{W}" height="{H}" rx="14"/></clipPath>',
            f'<clipPath id="sky"><path d="{BLOB}"/></clipPath>']
    o = [f'<rect width="{W}" height="{H}" fill="{pal["card"]}"/>', f'<path d="{BLOB}" fill="{pal["blob"]}"/>']

    # Hidden in plain sight.
    o.append(f'<text x="790" y="10" font-size="3" fill-opacity="0" text-anchor="end">{b"flag{amahoro}".hex()}</text>')

    # ---- sky, inside the blob ----
    sky = []
    sun = None
    if dark:
        if not overcast:
            for _ in range(26):
                x, y = rnd.uniform(110, 700), rnd.uniform(70, 170)
                s = rnd.uniform(1.5, 3)
                sky.append(f'<path class="tw" style="animation-delay:-{rnd.uniform(0, 4):.1f}s" d="M{x - s:.1f},{y:.1f} H{x + s:.1f} '
                           f'M{x:.1f},{y - s:.1f} V{y + s:.1f}" {outline(CREAM, 1)}/>')
        t = ((hour - 18) % 24) / 12
        sun = (150 + t * 500, 175 - math.sin(math.pi * t) * 118)
        if not rainy:
            sky.append(f'<g opacity="{.55 if overcast else 1}">{moon(*sun, 14, moon_phase(now), pal["blob"], line)}</g>')
    elif 6 <= hour <= 18 and not rainy:
        t = (hour - 6) / 12
        sun = (150 + t * 500, 190 - math.sin(math.pi * t) * 142)   # rides high enough to clear the City Tower
        sx, sy = sun
        rays = "".join(f'<line x1="{sx + 22 * math.cos(a):.1f}" y1="{sy + 22 * math.sin(a):.1f}" '
                       f'x2="{sx + 30 * math.cos(a):.1f}" y2="{sy + 30 * math.sin(a):.1f}" {outline(line, 1.4)}/>'
                       for a in (k * math.pi / 6 for k in range(12)))
        spinning = "" if overcast else f'<g class="spin">{rays}</g>'
        sky.append(f'<g opacity="{.5 if overcast else 1}">{spinning}'
                   f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="15" fill="{mix(GOLD, "#ffb36b", .35)}" {outline(line, 1.4)}/></g>')

    lights = len(sky)          # stars, moon and sun are drawn whole; clouds and rain stay inside the sky shape
    # ---- clouds ----
    if rainy:
        cfill, n = mix(pal["cloud"], "#6f7a8b", .55 if not dark else .2), 9
    elif overcast:
        cfill, n = mix(pal["cloud"], "#a3acb8", .45 if not dark else .15), 8
    else:
        cfill, n = pal["cloud"], {0: 1, 1: 2, 2: 4}.get(code, 2)
    spots = [(170, 118), (340, 74), (560, 90), (655, 140), (250, 148), (470, 118), (420, 70), (610, 70), (120, 160)]
    for x, y in spots[:n]:
        s = land.uniform(.9, 1.25) * (1.3 if overcast or rainy else 1)
        sky.append(f'<g class="drift" style="animation-duration:{land.randint(18, 30)}s;animation-delay:-{land.uniform(0, 30):.0f}s">'
                   f'{cloud_line(x, y, s, cfill, line)}</g>')
    # A cloud passing over part of the sun (partly cloudy), or a whole bank hiding it (cloudy, rain).
    if sun and (partly or overcast or rainy):
        sx, sy = sun
        big = 1.6 if (overcast or rainy) else 1.1
        sky.append(f'<g class="drift" style="animation-duration:26s">{cloud_line(sx + 20, sy + 14, big, cfill, line)}</g>')
        if overcast or rainy:
            sky.append(cloud_line(sx - 26, sy + 22, 1.3, mix(cfill, "#ffffff", .08), line))
    if storm:
        sky.append(f'<path class="flash" d="M455,95 L440,128 H452 L436,165 L470,118 H457 L470,95Z" fill="{GOLD}" {outline(line, 1.2)}/>')
    if rainy:
        for _ in range(80 if code >= 61 else 40):
            x = rnd.uniform(110, 730)
            sky.append(f'<line class="drop" x1="{x:.0f}" y1="{rnd.uniform(80, 120):.0f}" x2="{x - 3:.0f}" '
                       f'y2="{rnd.uniform(80, 120) + 9:.0f}" {outline(line, 1.1)} opacity=".5" '
                       f'style="animation-delay:-{rnd.uniform(0, .8):.2f}s"/>')
    o.append(f'<g>{"".join(sky[:lights])}</g><g clip-path="url(#sky)">{"".join(sky[lights:])}</g>')

    if not dark and not rainy and not overcast:
        for x, y in ((250, 112), (266, 119), (520, 66), (536, 60), (600, 118)):
            o.append(f'<path class="bird" style="animation-delay:-{land.uniform(0, 3):.1f}s" '
                     f'd="M{x - 5},{y} Q{x - 2.5},{y - 4} {x},{y} Q{x + 2.5},{y - 4} {x + 5},{y}" fill="none" {outline(line, 1.2)}/>')

    # ---- Mount Kigali and the hills full of houses ----
    o.append(f'<path d="M520,{G} L585,150 Q600,140 615,152 L700,{G}Z" fill="{mix(pal["hill"], pal["blob"], .45)}" {outline(line, 1.2)}/>'
             f'<path d="M600,143 V122 M596,128 H604 M597,134 H603" fill="none" {outline(line, 1.1)}/>')
    o.append(hillside(f"M95,{G} C110,190 190,170 270,186 C300,192 330,215 345,{G}Z", pal["hill"], pal, lit, land, 70, (110, 330, 195)))
    o.append(hillside(f"M440,{G} C470,205 540,180 610,196 C660,206 705,215 718,{G}Z", mix(pal["hill"], "#ffffff", .08),
                      pal, lit, land, 60, (455, 705, 205)))

    # ---- the city, left to right ----
    o.append(radisson(108, pal, lit, tint, land))
    o.append(convention_centre(222, pal, lit, tint))
    o.append(block(292, 24, 62, tint("#f2a7a0"), pal, lit, land, 2, "flat"))
    o.append(peace_plaza(318, pal, lit, tint, land))
    o.append(city_tower(374, pal, lit, tint, land))
    o.append(bank_tower(446, pal, lit, tint, land))
    o.append(twin_towers(480, pal, lit, tint, land))
    o.append(block(524, 26, 54, tint("#d9e3a5"), pal, lit, land, 3, "slant"))
    o.append(arena(560, pal, lit, tint))
    o.append(block(662, 28, 40, tint("#b9d6ef"), pal, lit, land, 3, "flat"))

    # ---- the boulevard, palms, jacarandas and acacias ----
    o.append(f'<rect x="70" y="{G}" width="670" height="9" fill="{mix(pal["road"], grey, by * .5)}" {outline(line, 1.4)}/>'
             f'<line x1="80" y1="{G + 4.5}" x2="730" y2="{G + 4.5}" stroke="{line}" stroke-width="1" stroke-dasharray="7 7" opacity=".45"/>')
    if rainy:   # a wet road catches a little light
        o.append(f'<rect x="70" y="{G + 1}" width="670" height="7" fill="{pal["blob"]}" opacity=".45"/>')
    for x, h in ((100, 52), (176, 44), (300, 48), (436, 56), (553, 46), (712, 50)):
        o.append(palm(x, h, pal))
    for x, r in ((150, 10), (285, 9), (668, 11)):
        o.append(jacaranda(x, r, pal, tint))
    for x, w in ((520, 26), (636, 24)):
        o.append(acacia(x, w, pal))

    # Fog drifts over the lower city.
    if foggy:
        o.append(f'<rect x="0" y="150" width="{W}" height="{G - 140}" fill="url(#fog)"/>'
                 f'<rect width="{W}" height="{H}" fill="{pal["card"]}" opacity=".25"/>')

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
