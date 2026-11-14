"""Small helpers shared by every script in this folder."""
import html
import json
import pathlib
import time
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
USER = "mbishflavien"
REPO = f"{USER}/{USER}"


def load(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def save(name, obj):
    (ROOT / "data" / name).write_text(json.dumps(obj, indent=1), encoding="utf-8")


def write_asset(name, svg):
    (ROOT / "assets" / name).write_text(svg, encoding="utf-8")


def stamp():
    # Added to image URLs so GitHub shows the fresh picture instead of a cached one.
    return str(int(time.time()))


def issue_url(title, body="Just press **Create** below. You don't need to write anything else."):
    query = urllib.parse.urlencode({"title": title, "body": body})
    return f"https://github.com/{REPO}/issues/new?{query}"


def esc(text):
    return html.escape(str(text), quote=True)


def replace_block(name, content):
    """Swap the text between <!-- name:start --> and <!-- name:end --> in README.md."""
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    i = text.index(start) + len(start)
    j = text.index(end)
    path.write_text(text[:i] + "\n" + content.strip() + "\n" + text[j:], encoding="utf-8")


# One palette for every picture on the profile, taken from Kigali itself:
# the night sky, the day sky, the hills, Imigongo clay and the evening sun.
PALETTE = {
    "navy": "#0b1026",    # night sky, the cards' background
    "blue": "#1c2a52",    # deep evening blue
    "sky": "#7fa7d4",     # soft day sky
    "green": "#5f9a52",   # the hills
    "cream": "#efe6d6",   # Imigongo white, house walls
    "ochre": "#c0573a",   # Imigongo red, roofs
    "gold": "#e8b85c",    # sun, lights, fireflies
}
