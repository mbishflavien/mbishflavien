"""Runs when someone opens a flag submission issue. Checks it and writes a reply for the issue."""
import os

import ctf

title = os.environ["ISSUE_TITLE"].strip()
login = os.environ["ISSUE_USER"]
parts = title.split("|")

if parts[0].strip().lower() == "ctf" and len(parts) >= 2:
    reply = ctf.play(login, parts[-1])
else:
    reply = "I couldn't understand that title. Use the link on the profile and keep the `ctf|` part."

with open(os.environ["REPLY_FILE"], "w", encoding="utf-8") as f:
    f.write(f"Hi @{login}! {reply}")
print(reply)
