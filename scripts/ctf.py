"""Three hidden flags. Players send sha256("<their login>:<flag>") so nobody can copy someone else's answer.

The real flags live only in the repo secret CTF_FLAGS (one flag per line).
"""
import datetime
import hashlib
import os
import re

from common import esc, issue_url, load, replace_block, save

HINTS = [
    "The portrait is keeping a note it never draws.",
    "Walk slowly through Kigali. Someone left a scribble in a notebook, and the letters look shifted.",
    "Even the sky over the hills keeps a secret, written in a way only computers enjoy reading.",
]


def fresh_state():
    return {"solvers": {}}


def play(login, arg):
    flags = [f.strip() for f in os.environ.get("CTF_FLAGS", "").splitlines() if f.strip()]
    guess = arg.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", guess):
        return ("That doesn't look like a sha256 hash. Hash `yourlogin:flag{...}` "
                "(see the instructions under *Three flags*) and paste the 64 characters into the title.")
    if not flags:
        return "The flag checker isn't set up yet. Try again later!"
    st = load("ctf.json")
    me = st["solvers"].setdefault(login, {"found": [], "first": datetime.date.today().isoformat()})
    for n, flag in enumerate(flags, 1):
        if hashlib.sha256(f"{login}:{flag}".encode()).hexdigest() == guess:
            if n in me["found"]:
                return f"You already found flag {n}. Nice memory though!"
            me["found"].append(n)
            save("ctf.json", st)
            render(st)
            left = len(flags) - len(me["found"])
            more = f" {left} to go." if left else " That's all of them. Welcome to the Hall of Hackers! 🏆"
            return f"🚩 Correct, that's flag {n}!{more}"
    if not me["found"]:
        del st["solvers"][login]
    return "Not quite. Check the flag for typos (including `flag{` and `}`) and that you used your exact GitHub login."


def render(st=None):
    st = st or load("ctf.json")
    hints = "".join(f"<li>{esc(h)}</li>" for h in HINTS)
    ranked = sorted(st["solvers"].items(), key=lambda kv: (-len(kv[1]["found"]), kv[1]["first"]))
    rows = "".join(f'<tr><td><a href="https://github.com/{esc(u)}">@{esc(u)}</a></td>'
                   f'<td>{"🚩" * len(v["found"])}</td><td>{esc(v["first"])}</td></tr>' for u, v in ranked[:15])
    table = (f"<table align=\"center\"><tr><th>Hacker</th><th>Flags</th><th>Since</th></tr>{rows}</table>"
             if rows else '<p align="center"><sub>No one has found a flag yet.</sub></p>')
    link = esc(issue_url("ctf|PASTE_YOUR_HASH_HERE",
                         "Replace PASTE_YOUR_HASH_HERE in the title with your hash, then press Create."))
    replace_block("ctf", f"""
<p align="center">There are <b>3 flags</b> hidden in this profile. They look like <code>flag{{...}}</code>.</p>

<details>
<summary>Hints</summary>
<ol>{hints}</ol>
</details>

<details>
<summary>Found one? Here's how to submit it</summary>
<br>

So nobody can copy your answer from the issues, you send a hash of your login and the flag instead of the flag:

```bash
echo -n "yourlogin:flag{{...}}" | sha256sum
```

Then <a href="{link}">open a submission</a> and put the hash in the title, like `ctf|3f9a...`.
</details>

<h4 align="center">🏆 Hall of Hackers</h4>
{table}
""")


if __name__ == "__main__":
    save("ctf.json", fresh_state())
    render()
    print("ctf ready")
