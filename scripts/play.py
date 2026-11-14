"""Runs when someone opens an issue. Reads the title, plays the move and writes a reply for the issue."""
import os

import ctf
import igisoro
import mural

GAMES = {"igisoro": igisoro.play, "mural": mural.play, "ctf": ctf.play}

title = os.environ["ISSUE_TITLE"].strip()
login = os.environ["ISSUE_USER"]
parts = title.split("|")
game = parts[0].strip().lower()

if game in GAMES and len(parts) >= 2:
    reply = GAMES[game](login, parts[-1])
else:
    reply = "I couldn't understand that title. Use the links on the profile and leave the title as it is."

with open(os.environ["REPLY_FILE"], "w", encoding="utf-8") as f:
    f.write(f"Hi @{login}! {reply}")
print(reply)
