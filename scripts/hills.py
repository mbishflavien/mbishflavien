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


# ---------- shapes ----------

def ridge(i):
    """Points along the top of ridge i (0 = farthest). Fixed seeds: the hills keep their shape all day."""
    rnd = random.Random(70 + i)
    near = i / (LAYERS - 1)
    waves = [(10 + 14 * near, 0.0045), (6 + 6 * near, 0.011), (3 + 2 * near, 0.026)]
    phases = [rnd.uniform(0, 6.28) for _ in waves]
    return [(x, BASES[i] + sum(a * math.sin(x * f + p) for (a, f), p in zip(waves, phases)))
            for x in range(-20, W + 40, 20)]


def smooth(pts):
    """A smooth curve through the points (Catmull-Rom turned into Bezier curves), for soft, rounded hills."""
    d = [f"M{pts[0][0]},{pts[0][1]:.1f}"]
    for i in range(len(pts) - 1):
        p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]},{p2[1]:.1f}")
    return "".join(d)


def area(pts):
    return smooth(pts) + f" L{pts[-1][0]},{H + 5} L{pts[0][0]},{H + 5} Z"


def shifted(pts, dy, wobble=0, k=0):
    return [(x, y + dy + wobble * math.sin(x * .02 + k)) for x, y in pts]


def height_at(pts, x):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[-1][1]


def moon_phase(now):
    """0 = new moon, 0.5 = full moon."""
    known_new = datetime.datetime(2000, 1, 6, 18, 14, tzinfo=datetime.timezone.utc)
    days = (now - known_new).total_seconds() / 86400
    return (days % 29.530588853) / 29.530588853


def moon(cx, cy, r, phase, sky):
    """The lit part of the moon for its phase: the bright limb plus the curved line between light and dark."""
    k = math.cos(2 * math.pi * phase)
    rx = abs(k) * r
    top, bottom = f"{cx:.1f},{cy - r:.1f}", f"{cx:.1f},{cy + r:.1f}"
    if phase < 0.5:   # waxing: lit on the right
        d = f"M{top} A{r},{r} 0 0 1 {bottom} A{rx:.1f},{r} 0 0 {0 if k > 0 else 1} {top}Z"
    else:             # waning: lit on the left
        d = f"M{top} A{r},{r} 0 0 0 {bottom} A{rx:.1f},{r} 0 0 {1 if k > 0 else 0} {top}Z"
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r * 3.2:.0f}" fill="url(#moonglow)"/>'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{mix(sky, CREAM, .12)}"/>'
            f'<path d="{d}" fill="{mix(CREAM, "#ffffff", .2)}"/>')


def cloud(rnd, uid, x, y, s, light, shade, op):
    """A cartoon cloud: round puffs on a flat bottom, with a soft darker band underneath."""
    puffs = [(0, 0, 13)] + [(rnd.uniform(-26, 26), rnd.uniform(-6, 2), rnd.uniform(8, 13)) for _ in range(4)]
    base = max(py + pr for _, py, pr in puffs) - 3
    circles = lambda fill, dy: "".join(
        f'<circle cx="{x + px * s:.1f}" cy="{y + (py + dy) * s:.1f}" r="{pr * s:.1f}" fill="{fill}"/>' for px, py, pr in puffs)
    return (f'<clipPath id="cl{uid}"><rect x="{x - 60 * s:.0f}" y="{y - 40 * s:.0f}" width="{120 * s:.0f}" '
            f'height="{(base + 40) * s:.0f}"/></clipPath>'
            f'<g clip-path="url(#cl{uid})" opacity="{op}">{circles(shade, 0)}{circles(light, -2.5)}</g>')


def banana(x, y, s, colour):
    """A banana plant: a short stem and big drooping leaves."""
    leaves = "".join(
        f'<path d="M0,-10 Q{dx * .5:.1f},{-18 + abs(dx) * .1:.1f} {dx:.1f},{-8 + abs(dx) * .35:.1f} '
        f'Q{dx * .55:.1f},{-12 + abs(dx) * .2:.1f} 0,-9Z"/>' for dx in (-17, -11, 11, 17, -4, 6))
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({s:.2f})" fill="{colour}">'
            f'<rect x="-1.4" y="-11" width="2.8" height="11" rx="1"/>{leaves}</g>')


def eucalyptus(x, y, s, colour):
    """A tall eucalyptus: thin trunk and a narrow, layered crown."""
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({s:.2f})" fill="{colour}">'
            f'<rect x="-.8" y="-26" width="1.6" height="26"/>'
            f'<ellipse cx="0" cy="-30" rx="5" ry="9"/><ellipse cx="-3" cy="-22" rx="4" ry="5"/>'
            f'<ellipse cx="3" cy="-24" rx="4" ry="5"/></g>')


# ---------- the scene ----------

def build(now, temp, code, activity):
    hour = now.hour + now.minute / 60
    ph = phase_of(hour)
    pal = palette_at(hour)
    dark = ph == "night"
    lit = dark or hour >= 18 or hour < 6              # windows and city lights are on
    word = describe(code)
    rnd = random.Random(now.strftime("%Y%m%d%H"))      # sky details change with the hour
    land = random.Random(7)                             # the town, road and trees stay where they are
    overcast = code >= 3
    foggy = 45 <= code < 51
    glow = pal["glow"] or pal["haze"]

    css = """
    .drift{animation:drift linear infinite}
    @keyframes drift{from{transform:translateX(-340px)}to{transform:translateX(1140px)}}
    .tw{animation:tw 5s ease-in-out infinite alternate}
    @keyframes tw{from{opacity:.3}to{opacity:1}}
    .ff{animation:float 9s ease-in-out infinite alternate}
    @keyframes float{0%{transform:translate(0,0);opacity:.15}50%{opacity:.8}100%{transform:translate(18px,-12px);opacity:.2}}
    .bird{animation:fly linear infinite}
    @keyframes fly{from{transform:translateX(-60px)}to{transform:translateX(880px)}}
    .drop{animation:fall .9s linear infinite}
    @keyframes fall{from{transform:translate(0,-40px)}to{transform:translate(-10px,330px)}}
    .sway{animation:sway 6s ease-in-out infinite alternate;transform-box:fill-box;transform-origin:50% 100%}
    @keyframes sway{from{transform:rotate(-2deg)}to{transform:rotate(2deg)}}
    text{font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif}
    """
    defs = [
        f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{pal["top"]}"/>'
        f'<stop offset=".72" stop-color="{pal["bottom"]}"/><stop offset="1" stop-color="{pal["bottom"]}"/></linearGradient>',
        f'<radialGradient id="sunglow"><stop offset="0" stop-color="{glow}" stop-opacity=".5"/>'
        f'<stop offset="1" stop-color="{glow}" stop-opacity="0"/></radialGradient>',
        f'<radialGradient id="moonglow"><stop offset="0" stop-color="{CREAM}" stop-opacity=".18"/>'
        f'<stop offset="1" stop-color="{CREAM}" stop-opacity="0"/></radialGradient>',
        f'<radialGradient id="lamp"><stop offset="0" stop-color="{GOLD}" stop-opacity=".85"/>'
        f'<stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>',
        f'<linearGradient id="mist" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{pal["haze"]}" stop-opacity="0"/>'
        f'<stop offset=".55" stop-color="{pal["haze"]}" stop-opacity="1"/><stop offset="1" stop-color="{pal["haze"]}" stop-opacity="0"/></linearGradient>',
        f'<clipPath id="frame"><rect width="{W}" height="{H}" rx="14"/></clipPath>',
    ]
    o = []

    # Hidden in plain sight.
    o.append(f'<text x="790" y="10" font-size="3" fill-opacity="0" text-anchor="end">{b"flag{amahoro}".hex()}</text>')

    # ---- sky ----
    if dark:
        for _ in range(80):
            y = rnd.random() ** 1.6 * 160
            twinkle = 'class="tw" ' if rnd.random() < .3 else ""
            o.append(f'<circle {twinkle}cx="{rnd.uniform(0, W):.0f}" cy="{y:.0f}" r="{rnd.uniform(.4, 1):.1f}" '
                     f'fill="{CREAM}" opacity="{rnd.uniform(.3, .8):.2f}" style="animation-delay:-{rnd.uniform(0, 5):.1f}s"/>')
        for _ in range(5):   # a few brighter stars drawn as little sparkles
            x, y, r = rnd.uniform(30, W - 30), rnd.uniform(15, 120), rnd.uniform(2.5, 3.5)
            o.append(f'<path class="tw" style="animation-delay:-{rnd.uniform(0, 5):.1f}s" fill="{CREAM}" opacity=".8" '
                     f'd="M{x:.0f},{y - r:.1f} Q{x:.0f},{y:.0f} {x + r:.1f},{y:.0f} Q{x:.0f},{y:.0f} {x:.0f},{y + r:.1f} '
                     f'Q{x:.0f},{y:.0f} {x - r:.1f},{y:.0f} Q{x:.0f},{y:.0f} {x:.0f},{y - r:.1f}Z"/>')
        t = ((hour - 18) % 24) / 12
        o.append(moon(60 + t * 680, 200 - math.sin(math.pi * t) * 150, 13, moon_phase(now), pal["top"]))
    else:
        t = min(max((hour - 6) / 12, 0), 1)
        sx, sy = 60 + t * 680, 225 - math.sin(math.pi * t) * 185
        if not overcast:
            o.append(f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="95" fill="url(#sunglow)"/>'
                     f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="36" fill="{glow}" opacity=".12"/>'
                     f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="26" fill="{glow}" opacity=".16"/>'
                     f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="16" fill="{mix(glow, "#ffffff", .35)}"/>')
        else:
            o.append(f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="70" fill="url(#sunglow)" opacity=".5"/>')
    if ph in ("dawn", "dusk"):
        o.append(f'<ellipse cx="{60 if ph == "dawn" else 740}" cy="150" rx="420" ry="70" fill="url(#sunglow)"/>')

    # Cartoon clouds drift slowly from left to right.
    if dark:
        light, shade, op = "#2c375a", "#1f2846", .8
    elif ph in ("dawn", "dusk") and not 10 <= hour < 17:
        light, shade, op = mix(glow, "#ffffff", .45), mix(pal["haze"], pal["top"], .3), .9
    else:
        light, shade, op = ("#e3e7ec", "#bcc4cf", .95) if overcast else ("#fbf9f4", "#d5dce5", .95)
    for c in range(CLOUDS.get(code, 8)):
        dur, delay = rnd.randint(150, 230), rnd.uniform(0, 230)
        o.append(f'<g class="drift" style="animation-duration:{dur}s;animation-delay:-{delay:.0f}s">'
                 f'{cloud(rnd, c, 0, rnd.uniform(40, 115), rnd.uniform(.9, 1.6), light, shade, op)}</g>')

    # ---- the land, far to near ----
    ridges = [ridge(i) for i in range(LAYERS)]
    colours = []
    for i, pts in enumerate(ridges):
        depth = 1 - i / (LAYERS - 1)                           # 1 = farthest, 0 = nearest
        colour = mix(pal["near"], pal["haze"], depth * 0.8)
        colours.append(colour)
        top_y = min(y for _, y in pts)
        defs.append(f'<linearGradient id="h{i}" gradientUnits="userSpaceOnUse" x1="0" y1="{top_y:.0f}" x2="0" y2="{H}">'
                    f'<stop offset="0" stop-color="{mix(colour, pal["haze"], .1)}"/>'
                    f'<stop offset="1" stop-color="{mix(colour, "#000000", .2)}"/></linearGradient>'
                    f'<clipPath id="c{i}"><path d="{area(pts)}"/></clipPath>')
        o.append(f'<path d="{area(pts)}" fill="url(#h{i})"/>')
        # Soft light catching the top of each ridge.
        o.append(f'<path d="{smooth(pts)}" fill="none" stroke="{mix(colour, glow, .45)}" stroke-width="{1 + i * .25:.2f}" '
                 f'opacity="{.18 if dark else .35}"/>')

        # Ridge 2: Kigali on the skyline, with the Convention Centre's dome.
        if i == 2:
            city = []
            for k in range(14):
                bx = 470 + k * 9 + land.uniform(-2, 2)
                bw, bh = land.uniform(5, 8), land.uniform(6, 20) * (1.3 if 4 <= k <= 8 else 1)
                by = height_at(pts, bx) + 4
                wall = mix("#1a2030", colour, .4) if lit else mix(CREAM, colour, .45)
                city.append(f'<rect x="{bx:.1f}" y="{by - bh:.1f}" width="{bw:.1f}" height="{bh + 6:.1f}" fill="{wall}"/>')
                if lit:
                    for wy in range(int(by - bh + 3), int(by), 4):
                        if land.random() < .5:
                            city.append(f'<rect x="{bx + 1.5:.1f}" y="{wy}" width="1.4" height="1.4" fill="{GOLD}" opacity=".8"/>')
            dx = 432
            dy = height_at(pts, dx) + 3
            # The Convention Centre's dome: one rounded dome with curved ribs, lit in warm colours at night.
            dw, dh = 22, 20
            shell = mix(GOLD, P["ochre"], .35) if lit else mix(CREAM, colour, .3)
            rib = mix(P["sky"], GOLD, .3) if lit else mix("#8e98a6", colour, .35)
            ribs = "".join(f'<path d="M{dx:.1f},{dy - dh:.1f} Q{dx + o * .9:.1f},{dy - dh * .55:.1f} {dx + o * 1.1:.1f},{dy}" '
                           f'fill="none" stroke="{rib}" stroke-width="1.1"/>' for o in (-16, -8, 0, 8, 16))
            dome = (f'<path d="M{dx - dw},{dy} A{dw},{dh} 0 0 1 {dx + dw},{dy}Z" fill="{shell}" opacity="{.85 if lit else .95}"/>'
                    + ribs)
            o.append(f'<g>{"".join(city)}{dome}</g>')
            if lit:
                o.append(f'<ellipse cx="{dx}" cy="{dy - 8}" rx="34" ry="18" fill="url(#lamp)" opacity=".35"/>')

        # Ridge 3: terraced fields, cartoon stripes in two greens.
        if i == 3:
            bands = []
            for k in range(12):
                a = shifted(pts, 6 + k * 6, 2, k)
                b = shifted(pts, 6 + (k + 1) * 6, 2, k + 1)
                band = smooth(a) + " L" + " L".join(f"{x},{y:.1f}" for x, y in reversed(b)) + "Z"
                tone = mix(colour, glow if k % 2 else "#000000", .08)
                bands.append(f'<path d="{band}" fill="{tone}"/>')
            o.append(f'<g clip-path="url(#c{i})" opacity=".8">{"".join(bands)}</g>')
            # A lake in the valley below, reflecting the sky.
            lx = 250
            ly = height_at(ridges[4], lx) - 4
            o.append(f'<ellipse cx="{lx}" cy="{ly:.0f}" rx="70" ry="9" fill="{mix(pal["bottom"], colour, .35)}"/>'
                     f'<ellipse cx="{lx - 10}" cy="{ly - 2:.0f}" rx="40" ry="2" fill="{mix(pal["bottom"], "#ffffff", .3)}" opacity=".5"/>')

        # Ridge 4: a red-dirt road winding up the hill, with houses along it.
        if i == 4:
            road = (f"M560,{H + 5} C540,{H - 20} 640,{H - 30} 610,{height_at(pts, 610) + 34:.0f} "
                    f"S520,{height_at(pts, 540) + 22:.0f} 500,{height_at(pts, 500) + 4:.0f}")
            o.append(f'<g clip-path="url(#c{i})" fill="none" stroke-linecap="round">'
                     f'<path d="{road}" stroke="{mix("#a5532f", colour, .35)}" stroke-width="7"/>'
                     f'<path d="{road}" stroke="{mix("#c8784a", colour, .3)}" stroke-width="2.5" opacity=".7"/></g>')
            for cx in (150, 330, 600, 700):
                for _ in range(land.randint(4, 7)):
                    x = cx + land.gauss(0, 22)
                    y = height_at(pts, x) + land.uniform(7, 24)
                    if lit and land.random() < .85:
                        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="url(#lamp)" opacity=".75"/>'
                                 f'<rect x="{x - .8:.1f}" y="{y - .8:.1f}" width="1.6" height="1.6" fill="{mix(GOLD, "#ffffff", .4)}"/>')
                    elif not lit:
                        wall = mix(CREAM, colour, .15)
                        roof = mix("#a8452b", colour, .15)
                        o.append(f'<g transform="translate({x:.1f},{y:.1f})">'
                                 f'<rect x="-3.5" y="-2.5" width="7" height="5" fill="{wall}"/>'
                                 f'<rect x="-.8" y="0" width="1.6" height="2.5" fill="{mix(roof, "#000000", .4)}"/>'
                                 f'<path d="M-4.5,-2.5 L0,-6 L4.5,-2.5Z" fill="{roof}"/></g>')

        # Mist pooling in the valley behind the next ridge.
        if i < LAYERS - 1:
            strength = .5 if foggy else (.26 if ph != "day" else .18)
            o.append(f'<rect x="-10" y="{BASES[i] - 6}" width="{W + 20}" height="34" fill="url(#mist)" '
                     f'opacity="{strength * depth + .05:.2f}"/>')

    # The nearest ridge: banana plants and eucalyptus trees, gently swaying.
    front = ridges[-1]
    plant = mix(pal["near"], "#000000", .3)
    plant2 = mix(pal["near"], glow, .12)
    x = -5
    while x < W + 10:
        x += land.uniform(22, 48)
        y = height_at(front, x) + 2
        if land.random() < .3:
            o.append(eucalyptus(x, y, land.uniform(1.1, 1.6), plant))
        else:
            o.append(f'<g class="sway" style="animation-delay:-{land.uniform(0, 6):.1f}s">'
                     f'{banana(x, y, land.uniform(1.2, 1.8), land.choice((plant, plant2)))}</g>')

    # A few birds by day, a few fireflies after dark (more when I have been busier on GitHub).
    critters = min(max(activity // 3, 3), 12)
    if ph in ("night", "dusk"):
        for _ in range(critters):
            o.append(f'<circle class="ff" cx="{rnd.uniform(20, 780):.0f}" cy="{rnd.uniform(262, 312):.0f}" r="1.2" '
                     f'fill="{GOLD}" style="animation-delay:-{rnd.uniform(0, 9):.1f}s;animation-duration:{rnd.uniform(7, 11):.1f}s"/>')
    else:
        for _ in range(min(critters, 6)):
            y, s = rnd.uniform(45, 130), rnd.uniform(.5, .8)
            o.append(f'<g class="bird" style="animation-duration:{rnd.randint(40, 70)}s;animation-delay:-{rnd.uniform(0, 70):.0f}s">'
                     f'<path transform="translate(0,{y:.0f}) scale({s:.2f})" d="M-8,0 Q-4,-4 0,0 Q4,-4 8,0" fill="none" '
                     f'stroke="{mix(pal["near"], pal["haze"], .3)}" stroke-width="1.4"/></g>')

    # Weather over everything.
    if foggy:
        o.append(f'<rect width="{W}" height="{H}" fill="{pal["haze"]}" opacity=".35"/>')
    if code >= 51:
        o.append(f'<rect width="{W}" height="{H}" fill="{pal["haze"]}" opacity=".18"/>')
        for _ in range(120 if code >= 61 else 60):
            x = rnd.randint(0, 840)
            o.append(f'<line class="drop" x1="{x}" y1="0" x2="{x - 3}" y2="14" stroke="{mix(pal["haze"], "#ffffff", .5)}" '
                     f'stroke-width=".8" stroke-opacity=".35" style="animation-delay:-{rnd.uniform(0, .9):.2f}s"/>')

    temp_txt = f" · {temp}°C" if temp is not None else ""
    caption = f"Kigali · {now:%H:%M}{temp_txt} · {word}"
    o.append(f'<rect x="14" y="{H - 40}" width="{len(caption) * 6.6 + 24:.0f}" height="26" rx="13" '
             f'fill="{NAVY}" fill-opacity=".45"/>'
             f'<text x="26" y="{H - 22}" font-size="13" fill="{CREAM}">{caption}</text>')

    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">',
        f"<title>Kigali right now: {pal['word']}, {word}</title>",
        f"<style>{css}</style>",
        f"<defs>{''.join(defs)}</defs>",
        '<g clip-path="url(#frame)">',
        f'<rect width="{W}" height="{H}" fill="url(#sky)"/>',
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
