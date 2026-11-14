"""Draws assets/stats-light.svg and assets/stats-dark.svg: a black & white GitHub stats card.

Contributions, streaks, a year heatmap, and the languages across my public repos
(told apart by hatch patterns instead of colours). Runs with the hourly workflow.
"""
import json
import os
import urllib.request

from common import USER, esc, replace_block, stamp, write_asset
from make_hero import THEMES

# Files Flutter/Android/iOS generate on their own. They aren't code I wrote, so they don't count.
SKIP = {"C", "C++", "CMake", "Swift", "Objective-C", "Batchfile", "Makefile", "Dockerfile", "Shell", "Kotlin"}
W = 800


def api(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None)
    req.add_header("Accept", "application/vnd.github+json")
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def collect():
    repos = [r for r in api(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner") if not r["fork"]]
    langs = {}
    for r in repos:
        for name, size in api(r["languages_url"]).items():
            if name not in SKIP:
                langs[name] = langs.get(name, 0) + size
    days = []
    try:
        q = ('query($u:String!){user(login:$u){contributionsCollection{contributionCalendar'
             '{totalContributions weeks{contributionDays{contributionCount}}}}}}')
        cal = api("https://api.github.com/graphql", {"query": q, "variables": {"u": USER}})
        cal = cal["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        days = [d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"]]
        total = cal["totalContributions"]
    except Exception:
        total = None
    return {"repos": len(repos), "stars": sum(r["stargazers_count"] for r in repos),
            "langs": langs, "days": days, "total": total}


def streaks(days):
    longest = run = 0
    for n in days:
        run = run + 1 if n else 0
        longest = max(longest, run)
    current = 0
    for n in reversed(days[:-1] if days and not days[-1] else days):  # today may not have commits yet
        if not n:
            break
        current += 1
    return current, longest


def patterns(fg):
    p = [
        f'<rect width="8" height="8" fill="{fg}"/>',
        f'<path d="M-2,2 l4,-4 M0,8 l8,-8 M6,10 l4,-4" stroke="{fg}" stroke-width="1.6"/>',
        f'<circle cx="2" cy="2" r="1.3" fill="{fg}"/><circle cx="6" cy="6" r="1.3" fill="{fg}"/>',
        f'<path d="M0,2 h8 M0,6 h8" stroke="{fg}" stroke-width="1.4"/>',
        f'<path d="M0,0 l8,8 M8,0 l-8,8" stroke="{fg}" stroke-width="1"/>',
        f'<path d="M2,0 v8 M6,0 v8" stroke="{fg}" stroke-width="1.4"/>',
        f'<rect x=".5" y=".5" width="7" height="7" fill="none" stroke="{fg}"/>',
    ]
    return "".join(f'<pattern id="p{i}" width="8" height="8" patternUnits="userSpaceOnUse">{s}</pattern>'
                   for i, s in enumerate(p)), len(p)


def build(s, fg):
    defs, n_pat = patterns(fg)
    cur, best = streaks(s["days"])
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} 250" width="{W}" height="250" role="img">',
         "<title>GitHub stats</title>",
         f"<style>text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:{fg}}}"
         ".big{font-size:26px;font-weight:700}.lb{font-size:11px;fill-opacity:.65;letter-spacing:.08em}"
         ".lg{font-size:12px}.cell{animation:in .6s ease-out both}@keyframes in{from{opacity:0}}</style>",
         f"<defs>{defs}</defs>",
         f'<rect x=".5" y=".5" width="{W - 1}" height="249" rx="10" fill="none" stroke="{fg}" stroke-opacity=".35"/>']

    numbers = [(s["total"] if s["total"] is not None else "–", "CONTRIBUTIONS / YEAR"),
               (s["repos"], "PUBLIC REPOS"), (cur, "CURRENT STREAK"), (best, "LONGEST STREAK")]
    for i, (num, label) in enumerate(numbers):
        x, y = 24 + (i % 2) * 150, 48 + (i // 2) * 62
        o.append(f'<text x="{x}" y="{y}" class="big">{num}</text><text x="{x}" y="{y + 18}" class="lb">{label}</text>')

    langs = sorted(s["langs"].items(), key=lambda kv: -kv[1])
    top = langs[:n_pat - 1]
    rest = sum(v for _, v in langs[n_pat - 1:])
    if rest:
        top.append(("Other", rest))
    total = sum(v for _, v in top) or 1
    x0, bw = 340, 436
    o.append(f'<text x="{x0}" y="30" class="lb">LANGUAGES ACROSS MY PUBLIC REPOS</text>')
    x = x0
    for i, (name, v) in enumerate(top):
        w = bw * v / total
        o.append(f'<rect x="{x:.1f}" y="42" width="{w:.1f}" height="18" fill="url(#p{i})" stroke="{fg}" stroke-width=".8"/>')
        x += w
    for i, (name, v) in enumerate(top):
        lx, ly = x0 + (i % 3) * 148, 86 + (i // 3) * 22
        o.append(f'<rect x="{lx}" y="{ly - 10}" width="12" height="12" fill="url(#p{i})" stroke="{fg}" stroke-width=".8"/>'
                 f'<text x="{lx + 18}" y="{ly}" class="lg">{esc(name)} {100 * v / total:.1f}%</text>')

    days = s["days"][-53 * 7:]
    if days:
        peak = max(days) or 1
        o.append(f'<text x="24" y="168" class="lb">THE LAST YEAR, ONE SQUARE PER DAY</text>')
        for i, n in enumerate(days):
            cx, cy = 24 + (i // 7) * 14.3, 178 + (i % 7) * 9
            op = 0.08 if n == 0 else 0.3 + 0.7 * min(n / peak, 1) ** 0.6
            o.append(f'<rect class="cell" style="animation-delay:{i * 0.004:.2f}s" x="{cx:.1f}" y="{cy}" '
                     f'width="12" height="7" rx="1.5" fill="{fg}" fill-opacity="{op:.2f}"/>')
    o.append("</svg>")
    return "\n".join(o)


def main():
    s = collect()
    for theme, fg in THEMES.items():
        write_asset(f"stats-{theme}.svg", build(s, fg))
    v = stamp()
    replace_block("stats", f"""
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/stats-dark.svg?v={v}">
  <img src="assets/stats-light.svg?v={v}" alt="GitHub stats: {s['total']} contributions this year across {s['repos']} public repos" width="100%">
</picture>
""")
    print("stats:", s["total"], "contributions,", s["repos"], "repos,", len(s["langs"]), "languages")


if __name__ == "__main__":
    main()
