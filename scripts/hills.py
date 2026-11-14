"""Draws assets/hills.svg: Kigali's hills at the real time of day, with the real weather.

Runs every hour from .github/workflows/hills.yml.
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
GOLD, CREAM, OCHRE, NAVY, SKY = P["gold"], P["cream"], P["ochre"], P["navy"], P["sky"]
PHASES = {
    "night": dict(sky=(P["navy"], P["blue"]), hills=("#26355f", "#1d3346", "#172b2a", "#10211c"), word="night"),
    "dawn": dict(sky=(P["blue"], "#e9a46a"), hills=("#7f7a98", "#5b7165", "#41663f", "#2f5232"), word="sunrise"),
    "day": dict(sky=("#6f9fd0", "#d7e6f1"), hills=("#a9c7a0", "#80b06a", P["green"], "#3f7a3c"), word="day"),
    "dusk": dict(sky=(P["blue"], "#d9875a"), hills=("#5f5a7e", "#495e5a", "#35503a", "#25402b"), word="sunset"),
}

WEATHER = [(0, "clear"), (1, "mostly clear"), (2, "partly cloudy"), (3, "cloudy"), (45, "foggy"),
           (51, "drizzle"), (61, "rain"), (80, "showers"), (95, "thunderstorm")]
CLOUDS = {0: 0, 1: 1, 2: 3, 3: 5}


def phase_of(hour):
    if 5 <= hour < 7:
        return "dawn"
    if 7 <= hour < 17:
        return "day"
    if 17 <= hour < 19:
        return "dusk"
    return "night"


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


def hill(i):
    rnd = random.Random(40 + i)          # fixed seed: the hills keep their shape, only light changes
    base = [150, 182, 218, 258][i]
    waves = [(30 - i * 3, 0.006), (14, 0.017), (5, 0.045)]
    phases = [rnd.uniform(0, 6.28) for _ in waves]
    pts = [(x, base + sum(a * math.sin(x * f + p) for (a, f), p in zip(waves, phases)))
           for x in range(0, W + 10, 10)]
    d = f"M0,{H} " + " ".join(f"L{x},{y:.1f}" for x, y in pts) + f" L{W},{H} Z"
    return d, pts


def cloud(x, y, s, fill, op, dur, delay):
    return (f'<g class="cloud" style="animation-duration:{dur}s;animation-delay:-{delay}s">'
            f'<g transform="translate({x},{y}) scale({s})" fill="{fill}" opacity="{op}">'
            '<ellipse cx="0" cy="0" rx="34" ry="13"/><ellipse cx="-18" cy="-8" rx="18" ry="12"/>'
            '<ellipse cx="12" cy="-12" rx="22" ry="15"/></g></g>')


def build(now, temp, code, activity):
    hour = now.hour + now.minute / 60
    ph = phase_of(now.hour)
    pal = PHASES[ph]
    dark = ph == "night"
    rnd = random.Random(now.strftime("%Y%m%d%H"))
    word = describe(code)

    css = """
    .cloud{animation:drift linear infinite}
    @keyframes drift{from{transform:translateX(-260px)}to{transform:translateX(1060px)}}
    .star{animation:tw 3s ease-in-out infinite alternate}
    @keyframes tw{from{opacity:.25}to{opacity:1}}
    .light{animation:tw 2.4s ease-in-out infinite alternate}
    .ff{animation:float 7s ease-in-out infinite alternate}
    @keyframes float{0%{transform:translate(0,0);opacity:.2}50%{opacity:1}100%{transform:translate(26px,-18px);opacity:.3}}
    .bird{animation:fly linear infinite}
    @keyframes fly{from{transform:translateX(-80px)}to{transform:translateX(900px)}}
    .drop{animation:fall .7s linear infinite}
    @keyframes fall{from{transform:translate(0,-40px)}to{transform:translate(-8px,330px)}}
    text{font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif}
    """

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">',
         f"<title>Kigali right now: {pal['word']}, {word}</title>",
         f"<style>{css}</style>",
         '<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
         f'<stop offset="0" stop-color="{pal["sky"][0]}"/><stop offset="1" stop-color="{pal["sky"][1]}"/>'
         '</linearGradient><clipPath id="frame"><rect width="800" height="320" rx="14"/></clipPath></defs>',
         '<g clip-path="url(#frame)">',
         f'<rect width="{W}" height="{H}" fill="url(#sky)"/>']

    # Hidden in plain sight.
    o.append(f'<text x="790" y="10" font-size="3" fill-opacity="0" text-anchor="end">'
             f'{b"flag{amahoro}".hex()}</text>')

    if dark:
        for _ in range(70):
            o.append(f'<circle class="star" cx="{rnd.uniform(0, W):.0f}" cy="{rnd.uniform(0, 170):.0f}" '
                     f'r="{rnd.uniform(.5, 1.6):.1f}" fill="{CREAM}" style="animation-delay:-{rnd.uniform(0, 3):.1f}s"/>')
        t = ((hour - 18) % 24) / 12
        mx, my = 60 + t * 680, 210 - math.sin(math.pi * t) * 170
        o.append(f'<circle cx="{mx:.0f}" cy="{my:.0f}" r="20" fill="{CREAM}"/>'
                 f'<circle cx="{mx + 8:.0f}" cy="{my - 5:.0f}" r="18" fill="{pal["sky"][0]}" opacity=".9"/>')
    else:
        t = min(max((hour - 6) / 12, 0), 1)
        sx, sy = 60 + t * 680, 230 - math.sin(math.pi * t) * 190
        o.append(f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="44" fill="{GOLD}" opacity=".25"/>'
                 f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="24" fill="{GOLD}"/>')

    n_clouds = CLOUDS.get(code, 6)
    cfill, cop = ("#2b3d70", .7) if dark else (P["cream"], .9 if code < 3 else .95)
    if code >= 3:
        cfill = "#3a4a78" if dark else "#c9d3e0"
    for i in range(n_clouds):
        o.append(cloud(0, rnd.uniform(30, 110), rnd.uniform(.8, 1.6), cfill, cop,
                       rnd.randint(90, 150), rnd.uniform(0, 150)))

    layers = [hill(i) for i in range(4)]
    for i, (d, _) in enumerate(layers):
        o.append(f'<path d="{d}" fill="{pal["hills"][i]}"/>')
        if i == 2:  # houses scattered on the middle hills
            for _ in range(30):
                x, y = rnd.choice(layers[2][1][2:-2])
                x += rnd.uniform(-5, 5)
                y += rnd.uniform(6, 30)
                if dark:
                    o.append(f'<circle class="light" cx="{x:.0f}" cy="{y:.0f}" r="1.6" fill="{GOLD}" '
                             f'style="animation-delay:-{rnd.uniform(0, 2.4):.1f}s"/>')
                else:
                    o.append(f'<g transform="translate({x:.0f},{y:.0f})"><rect x="-3" y="-2" width="6" height="4" '
                             f'fill="{CREAM}"/><path d="M-4,-2 L0,-5 L4,-2Z" fill="{OCHRE}"/></g>')

    critters = min(max(activity, 3), 30)
    if ph in ("night", "dusk"):
        for _ in range(critters):
            o.append(f'<circle class="ff" cx="{rnd.uniform(20, 780):.0f}" cy="{rnd.uniform(220, 300):.0f}" r="2" '
                     f'fill="{GOLD}" style="animation-delay:-{rnd.uniform(0, 7):.1f}s;'
                     f'animation-duration:{rnd.uniform(5, 9):.1f}s"/>')
    else:
        for _ in range(min(critters, 12)):
            y, s = rnd.uniform(40, 140), rnd.uniform(.6, 1.1)
            o.append(f'<g class="bird" style="animation-duration:{rnd.randint(25, 45)}s;'
                     f'animation-delay:-{rnd.uniform(0, 45):.0f}s"><path transform="translate(0,{y:.0f}) scale({s:.2f})" '
                     'd="M-8,0 Q-4,-5 0,0 Q4,-5 8,0" fill="none" stroke="{NAVY}" stroke-width="1.6"/></g>')

    if 45 <= code < 51:
        o.append(f'<rect y="150" width="{W}" height="170" fill="#ffffff" opacity=".35"/>')
    if code >= 51:
        for _ in range(90):
            x = rnd.randint(0, 820)
            o.append(f'<line class="drop" x1="{x}" y1="0" x2="{x - 3}" y2="12" stroke="{SKY}" '
                     f'stroke-opacity=".6" style="animation-delay:-{rnd.uniform(0, .7):.2f}s"/>')

    temp_txt = f" · {temp}°C" if temp is not None else ""
    caption = f"Kigali · {now:%H:%M}{temp_txt} · {word}"
    o.append(f'<rect x="14" y="{H - 40}" width="{len(caption) * 6.6 + 24:.0f}" height="26" rx="13" '
             'fill="{NAVY}" fill-opacity=".55"/>'
             f'<text x="26" y="{H - 22}" font-size="13" fill="{CREAM}">{caption}</text>')
    o.append("</g></svg>")
    return "\n".join(o), caption


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
