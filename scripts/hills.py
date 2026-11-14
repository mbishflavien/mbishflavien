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
BASES = [148, 166, 186, 208, 234, 262]     # how high each ridge sits, far to near


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
    waves = [(10 + 14 * near, 0.0045), (6 + 6 * near, 0.011), (3 + 2 * near, 0.026), (1.2, 0.06)]
    phases = [rnd.uniform(0, 6.28) for _ in waves]
    return [(x, BASES[i] + sum(a * math.sin(x * f + p) for (a, f), p in zip(waves, phases)))
            for x in range(-10, W + 20, 8)]


def area(pts):
    return f"M-10,{H} " + " ".join(f"L{x},{y:.1f}" for x, y in pts) + f" L{W + 20},{H} Z"


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


def cloud(rnd, x, y, s, light, shade, op):
    """A soft cloud: overlapping puffs with fading edges, a little darker underneath."""
    puffs = []
    for _ in range(rnd.randint(4, 7)):
        dx, dy = rnd.uniform(-38, 38) * s, rnd.uniform(-7, 3) * s
        rx, ry = rnd.uniform(16, 30) * s, rnd.uniform(7, 12) * s
        puffs.append(f'<ellipse cx="{x + dx:.0f}" cy="{y + dy + ry * .35:.0f}" rx="{rx:.0f}" ry="{ry * .8:.0f}" fill="{shade}"/>')
        puffs.append(f'<ellipse cx="{x + dx:.0f}" cy="{y + dy:.0f}" rx="{rx:.0f}" ry="{ry:.0f}" fill="{light}"/>')
    return f'<g opacity="{op}">' + "".join(puffs) + "</g>"


# ---------- the scene ----------

def build(now, temp, code, activity):
    hour = now.hour + now.minute / 60
    ph = phase_of(hour)
    pal = palette_at(hour)
    dark = ph == "night"
    word = describe(code)
    rnd = random.Random(now.strftime("%Y%m%d%H"))      # sky details change with the hour
    land = random.Random(7)                             # the town and trees stay where they are
    overcast = code >= 3
    foggy = 45 <= code < 51

    css = """
    .drift{animation:drift linear infinite}
    @keyframes drift{from{transform:translateX(-320px)}to{transform:translateX(1120px)}}
    .tw{animation:tw 5s ease-in-out infinite alternate}
    @keyframes tw{from{opacity:.35}to{opacity:1}}
    .ff{animation:float 9s ease-in-out infinite alternate}
    @keyframes float{0%{transform:translate(0,0);opacity:.15}50%{opacity:.8}100%{transform:translate(18px,-12px);opacity:.2}}
    .bird{animation:fly linear infinite}
    @keyframes fly{from{transform:translateX(-60px)}to{transform:translateX(880px)}}
    .drop{animation:fall .9s linear infinite}
    @keyframes fall{from{transform:translate(0,-40px)}to{transform:translate(-10px,330px)}}
    text{font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif}
    """
    defs = [
        f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{pal["top"]}"/>'
        f'<stop offset=".75" stop-color="{pal["bottom"]}"/><stop offset="1" stop-color="{pal["bottom"]}"/></linearGradient>',
        f'<radialGradient id="sunglow"><stop offset="0" stop-color="{pal["glow"] or GOLD}" stop-opacity=".55"/>'
        f'<stop offset="1" stop-color="{pal["glow"] or GOLD}" stop-opacity="0"/></radialGradient>',
        f'<radialGradient id="moonglow"><stop offset="0" stop-color="{CREAM}" stop-opacity=".18"/>'
        f'<stop offset="1" stop-color="{CREAM}" stop-opacity="0"/></radialGradient>',
        f'<radialGradient id="lamp"><stop offset="0" stop-color="{GOLD}" stop-opacity=".9"/>'
        f'<stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>',
        f'<linearGradient id="mist" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{pal["haze"]}" stop-opacity="0"/>'
        f'<stop offset=".55" stop-color="{pal["haze"]}" stop-opacity="1"/><stop offset="1" stop-color="{pal["haze"]}" stop-opacity="0"/></linearGradient>',
        f'<clipPath id="frame"><rect width="{W}" height="{H}" rx="14"/></clipPath>',
    ]
    o = []

    # Hidden in plain sight.
    o.append(f'<text x="790" y="10" font-size="3" fill-opacity="0" text-anchor="end">{b"flag{amahoro}".hex()}</text>')

    # Sky: stars and the moon at night, the sun by day.
    if dark:
        for _ in range(90):
            y = rnd.random() ** 1.6 * 170
            twinkle = 'class="tw" ' if rnd.random() < .3 else ""
            o.append(f'<circle {twinkle}cx="{rnd.uniform(0, W):.0f}" cy="{y:.0f}" '
                     f'r="{rnd.uniform(.4, 1.1):.1f}" fill="{CREAM}" opacity="{rnd.uniform(.3, .8):.2f}" '
                     f'style="animation-delay:-{rnd.uniform(0, 5):.1f}s"/>')
        t = ((hour - 18) % 24) / 12
        o.append(moon(60 + t * 680, 200 - math.sin(math.pi * t) * 150, 13, moon_phase(now), pal["top"]))
    else:
        t = min(max((hour - 6) / 12, 0), 1)
        sx, sy = 60 + t * 680, 225 - math.sin(math.pi * t) * 185
        if not overcast:
            o.append(f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="90" fill="url(#sunglow)"/>'
                     f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="15" fill="{mix(pal["glow"], "#ffffff", .3)}"/>')
        else:
            o.append(f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="70" fill="url(#sunglow)" opacity=".5"/>')
    if pal["glow"] and ph in ("dawn", "dusk"):
        o.append(f'<ellipse cx="{60 if ph == "dawn" else 740}" cy="150" rx="420" ry="70" fill="url(#sunglow)"/>')

    # Clouds drift slowly from left to right.
    if dark:
        light, shade, op = "#2b3556", "#1f2846", .75
    elif ph in ("dawn", "dusk"):
        light, shade, op = "#efc3a3", "#8f7f98", .85
    else:
        light, shade, op = ("#dde2e8", "#b8c0cb", .95) if overcast else ("#f6f3ee", "#cfd6df", .9)
    for _ in range(CLOUDS.get(code, 8)):
        dur, delay = rnd.randint(140, 220), rnd.uniform(0, 220)
        o.append(f'<g class="drift" style="animation-duration:{dur}s;animation-delay:-{delay:.0f}s">'
                 f'{cloud(rnd, 0, rnd.uniform(35, 120), rnd.uniform(.8, 1.5), light, shade, op)}</g>')

    # The hills, far to near. Far ridges fade into the haze; mist sits in the valleys between them.
    ridges = [ridge(i) for i in range(LAYERS)]
    for i, pts in enumerate(ridges):
        depth = 1 - i / (LAYERS - 1)                           # 1 = farthest, 0 = nearest
        colour = mix(pal["near"], pal["haze"], depth * 0.82)
        top_y = min(y for _, y in pts)
        defs.append(f'<linearGradient id="h{i}" gradientUnits="userSpaceOnUse" x1="0" y1="{top_y:.0f}" x2="0" y2="{H}">'
                    f'<stop offset="0" stop-color="{mix(colour, pal["haze"], .12)}"/>'
                    f'<stop offset="1" stop-color="{mix(colour, "#000000", .18)}"/></linearGradient>'
                    f'<clipPath id="c{i}"><path d="{area(pts)}"/></clipPath>')
        o.append(f'<path d="{area(pts)}" fill="url(#h{i})"/>')

        # Terraces: faint contour lines on the middle hills.
        if i in (2, 3, 4):
            lines = []
            for k in range(1, 9):
                off = k * (5 + i)
                lines.append("M" + " L".join(f"{x},{y + off + 3 * math.sin(x * .03 + k):.1f}" for x, y in pts))
            o.append(f'<path clip-path="url(#c{i})" d="{" ".join(lines)}" fill="none" '
                     f'stroke="{mix(colour, pal["haze"], .35)}" stroke-width=".7" opacity=".35"/>')

        # The town on the middle hills: houses by day, warm windows at night.
        if i in (2, 3):
            for _ in range(5):
                cx = land.uniform(40, W - 40)
                for _ in range(land.randint(5, 11)):
                    x = cx + land.gauss(0, 26)
                    y = height_at(pts, x) + land.uniform(5, 26) + i * 2
                    s = 0.8 + 0.25 * (i - 2)
                    if dark:
                        if land.random() < .8:
                            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{3.2 * s:.1f}" fill="url(#lamp)" opacity=".7"/>'
                                     f'<circle cx="{x:.1f}" cy="{y:.1f}" r=".7" fill="{mix(GOLD, "#ffffff", .4)}"/>')
                    else:
                        wall = mix(CREAM, colour, .25 + .3 * depth)
                        roof = mix("#8a5a44", colour, .2 + .3 * depth)
                        o.append(f'<g transform="translate({x:.1f},{y:.1f}) scale({s:.2f})">'
                                 f'<rect x="-2.5" y="-1.6" width="5" height="3.2" fill="{wall}"/>'
                                 f'<path d="M-3.2,-1.6 L0,-3.6 L3.2,-1.6Z" fill="{roof}"/></g>')

        # Mist pooling in the valley behind the next ridge.
        if i < LAYERS - 1:
            y0 = BASES[i] - 6
            strength = .5 if foggy else (.28 if ph != "day" else .22)
            o.append(f'<rect x="-10" y="{y0}" width="{W + 20}" height="34" fill="url(#mist)" opacity="{strength * depth + .05:.2f}"/>')

    # A dark line of trees along the nearest ridge.
    front = ridges[-1]
    tree = mix(pal["near"], "#000000", .35)
    x = -5
    while x < W + 10:
        x += land.uniform(6, 22)
        y = height_at(front, x)
        r = land.uniform(3, 6.5)
        o.append(f'<ellipse cx="{x:.1f}" cy="{y - r * .6:.1f}" rx="{r:.1f}" ry="{r * 1.1:.1f}" fill="{tree}"/>')

    # A few birds by day, a few fireflies after dark (more when I have been busier on GitHub).
    critters = min(max(activity // 3, 3), 12)
    if ph in ("night", "dusk"):
        for _ in range(critters):
            o.append(f'<circle class="ff" cx="{rnd.uniform(20, 780):.0f}" cy="{rnd.uniform(255, 310):.0f}" r="1.2" '
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
