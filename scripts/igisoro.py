"""Igisoro: the internet plays the bottom two rows, a small bot plays the top two.

Board: 4 rows x 8 pits. Rows 0-1 are the bot's (0 = back, 1 = front), rows 2-3 are yours (2 = front, 3 = back).
Each side sows anticlockwise around its own 16 pits. Pit numbers 1-16 follow that order for the internet.
"""
import math
import random

from common import esc, issue_url, load, replace_block, save, stamp, write_asset

RING = {
    "you": [(3, c) for c in range(8)] + [(2, c) for c in range(7, -1, -1)],
    "ai": [(0, c) for c in range(7, -1, -1)] + [(1, c) for c in range(8)],
}
FRONT = {"you": 2, "ai": 1}
BACK = {"you": 3, "ai": 0}
OTHER = {"you": "ai", "ai": "you"}


def new_board():
    return [[2] * 8 for _ in range(4)]


def legal(board, side):
    return [i for i, (r, c) in enumerate(RING[side]) if board[r][c] >= 2]


def sow(board, side, start):
    """Play one move. Returns (new board, seeds captured)."""
    b = [row[:] for row in board]
    ring, opp = RING[side], OTHER[side]
    r, c = ring[start]
    hand, b[r][c] = b[r][c], 0
    pos, captured, steps = start, 0, 0
    while hand and steps < 3000:
        pos = (pos + 1) % 16
        r, c = ring[pos]
        b[r][c] += 1
        hand -= 1
        steps += 1
        if hand == 0 and b[r][c] > 1:
            fr, bk = FRONT[opp], BACK[opp]
            if r == FRONT[side] and b[fr][c] and b[bk][c]:
                # Capture both facing pits and sow them again from where the move began.
                hand = b[fr][c] + b[bk][c]
                captured += hand
                b[fr][c] = b[bk][c] = 0
                pos = (start - 1) % 16
            else:
                # Relay: pick up the whole pit and keep going.
                hand, b[r][c] = b[r][c], 0
    b[r][c] += hand  # only matters if a move ever hits the safety limit
    return b, captured


def seeds(board, side):
    return sum(board[r][c] for r, c in RING[side])


def bot_move(board):
    """Looks two moves ahead: picks the move whose worst reply still leaves it best off."""
    best, choice = None, []
    for m in legal(board, "ai"):
        b1, _ = sow(board, "ai", m)
        replies = legal(b1, "you")
        if not replies:
            value = 999
        else:
            value = min(seeds(b2, "ai") - seeds(b2, "you") for b2 in (sow(b1, "you", r)[0] for r in replies))
        if best is None or value > best:
            best, choice = value, [m]
        elif value == best:
            choice.append(m)
    return random.choice(choice)


def fresh_state():
    return {"board": new_board(), "game": 1, "moves": 0, "score": {"internet": 0, "bot": 0},
            "last": {"you": None, "ai": None}, "log": [], "players": {}}


def end_game(st, winner):
    st["score"][winner] += 1
    st["game"] += 1
    st["board"] = new_board()
    st["moves"] = 0
    st["last"] = {"you": None, "ai": None}


def play(login, arg):
    st = load("igisoro.json")
    try:
        pit = int(arg)
    except ValueError:
        return "I couldn't read a pit number in that title. Use one of the links under the board."
    if pit - 1 not in legal(st["board"], "you"):
        return f"Pit {pit} can't be played right now (a pit needs at least 2 seeds). Pick one of the links under the board."

    board, cap = sow(st["board"], "you", pit - 1)
    st["players"][login] = st["players"].get(login, 0) + 1
    st["moves"] += 1
    st["last"] = {"you": pit - 1, "ai": None}
    reply = [f"You sowed from pit {pit}" + (f" and captured {cap} seeds! 🔥" if cap else ".")]
    entry = f"@{login} played pit {pit}" + (f", captured {cap}" if cap else "")

    if not legal(board, "ai"):
        reply.append("The bot has no moves left. **The internet wins this game!** 🎉 A new game has started.")
        st["log"].insert(0, entry + " and won the game for the internet 🎉")
        end_game(st, "internet")
    else:
        m = bot_move(board)
        board, cap2 = sow(board, "ai", m)
        st["last"]["ai"] = m
        reply.append("The bot answered" + (f" and captured {cap2} of your seeds." if cap2 else "."))
        entry += "; the bot answered" + (f", captured {cap2}" if cap2 else "")
        if not legal(board, "you"):
            reply.append("The internet has no moves left, so **the bot wins this game.** 🤖 A new game has started.")
            st["log"].insert(0, entry + " and won the game 🤖")
            end_game(st, "bot")
        else:
            st["board"] = board
            st["log"].insert(0, entry)
    st["log"] = st["log"][:5]
    save("igisoro.json", st)
    render(st)
    reply.append("\nThe board on the profile updates in a minute or so. Come back for another move!")
    return "\n\n".join(reply)


# ---------- drawing ----------

W, H = 760, 430
XS = [72 + c * 88 for c in range(8)]
YS = [84, 164, 266, 346]
STONES = ["#efe6d4", "#d8cbb2", "#b8a98c", "#e2d6c0"]


def pit_svg(r, c, n, label, mark):
    x, y = XS[c], YS[r]
    o = [f'<circle cx="{x}" cy="{y}" r="33" fill="url(#hole)"/>']
    for k in range(min(n, 14)):
        ang = k * 2.39996
        rad = 5.8 * (k + 0.5) ** 0.5
        o.append(f'<circle cx="{x + rad * math.cos(ang):.1f}" cy="{y + rad * math.sin(ang):.1f}" '
                 f'r="4.6" fill="{STONES[(k + r + c) % 4]}" stroke="#5a3a22" stroke-width=".6"/>')
    if mark:
        o.append(f'<circle class="pulse" cx="{x}" cy="{y}" r="36" fill="none" stroke="{mark}" stroke-width="3"/>')
    o.append(f'<circle cx="{x + 25}" cy="{y + 25}" r="10" fill="#2b1d16"/>'
             f'<text x="{x + 25}" y="{y + 29}" class="cnt">{n}</text>')
    if label:
        o.append(f'<circle cx="{x - 25}" cy="{y - 25}" r="10" fill="#f3c969"/>'
                 f'<text x="{x - 25}" y="{y - 21}" class="lbl">{label}</text>')
    return "".join(o)


def board_svg(st):
    b = st["board"]
    css = """
    text{font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif}
    .cnt{font-size:11px;fill:#f3ead9;text-anchor:middle;font-weight:600}
    .lbl{font-size:11px;fill:#2b1d16;text-anchor:middle;font-weight:700}
    .side{font-size:14px;fill:#8a6a4f;font-weight:600;letter-spacing:.06em}
    .pulse{animation:pulse 1.6s ease-in-out infinite}
    @keyframes pulse{0%,100%{opacity:.15}50%{opacity:1}}
    """
    you_mark = {RING["you"][st["last"]["you"]]: "#f3c969"} if st["last"]["you"] is not None else {}
    ai_mark = {RING["ai"][st["last"]["ai"]]: "#e0603a"} if st["last"]["ai"] is not None else {}
    marks = {**you_mark, **ai_mark}
    labels = {pos: str(i + 1) for i, pos in enumerate(RING["you"])}
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">',
         f"<title>Igisoro board, game {st['game']}</title><style>{css}</style>",
         '<defs><linearGradient id="wood" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#8a5a33"/>'
         '<stop offset="1" stop-color="#5e3a1e"/></linearGradient>'
         '<radialGradient id="hole" cx=".45" cy=".4" r=".7"><stop offset="0" stop-color="#3a2414"/>'
         '<stop offset="1" stop-color="#24150b"/></radialGradient></defs>',
         f'<text x="20" y="26" class="side">THE BOT · {seeds(b, "ai")} seeds</text>',
         f'<text x="{W - 20}" y="26" class="side" text-anchor="end">GAME #{st["game"]} · '
         f'INTERNET {st["score"]["internet"]} – {st["score"]["bot"]} BOT</text>',
         f'<rect x="12" y="38" width="{W - 24}" height="354" rx="22" fill="url(#wood)"/>',
         f'<line x1="30" y1="215" x2="{W - 30}" y2="215" stroke="#3d2412" stroke-width="3" stroke-dasharray="2 8" stroke-linecap="round"/>']
    for r in range(4):
        for c in range(8):
            o.append(pit_svg(r, c, b[r][c], labels.get((r, c)), marks.get((r, c))))
    o.append(f'<text x="20" y="{H - 14}" class="side">THE INTERNET (YOU) · {seeds(b, "you")} seeds</text>')
    if st["last"]["ai"] is not None:
        o.append(f'<text x="{W - 20}" y="{H - 14}" class="side" text-anchor="end">'
                 '<tspan fill="#f3c969">●</tspan> your last move  <tspan fill="#e0603a">●</tspan> bot\'s answer</text>')
    o.append("</svg>")
    return "\n".join(o)


def render(st=None):
    st = st or load("igisoro.json")
    write_asset("igisoro.svg", board_svg(st))
    ok = set(legal(st["board"], "you"))

    def cell(i):
        r, c = RING["you"][i]
        n = st["board"][r][c]
        if i in ok:
            return f'<td align="center"><a href="{esc(issue_url(f"igisoro|move|{i + 1}"))}"><b>{i + 1}</b></a><br><sub>{n} seeds</sub></td>'
        return f'<td align="center">{i + 1}<br><sub>{n}</sub></td>'

    front = "".join(cell(i) for i in range(15, 7, -1))
    back = "".join(cell(i) for i in range(8))
    log = "".join(f"<li>{esc(line)}</li>" for line in st["log"]) or "<li>No moves yet. Be the first!</li>"
    top = sorted(st["players"].items(), key=lambda kv: -kv[1])[:5]
    players = " · ".join(f'<a href="https://github.com/{esc(p)}">@{esc(p)}</a> ({n})' for p, n in top) or "nobody yet"
    replace_block("igisoro", f"""
<p align="center"><img src="assets/igisoro.svg?v={stamp()}" alt="Igisoro board" width="100%"></p>

<p align="center"><b>Your move.</b> Click a pit number to sow from it. Only pits with 2 or more seeds can be played.</p>

<table align="center">
<tr><td><sub>front row</sub></td>{front}</tr>
<tr><td><sub>back row</sub></td>{back}</tr>
</table>

<p align="center"><sub>Latest moves</sub></p>
<ul>{log}</ul>
<p align="center"><sub>Most moves: {players}</sub></p>
""")


if __name__ == "__main__":
    save("igisoro.json", fresh_state())
    render()
    print("new igisoro game ready")
