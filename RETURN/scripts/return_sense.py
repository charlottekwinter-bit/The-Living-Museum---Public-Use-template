#!/usr/bin/env python3
"""Return -- the Companion leaves something for the Steward."""
import os, json
from datetime import datetime, timezone
from pathlib import Path
import requests

try:
    import sys
    MUSEUM_ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(MUSEUM_ROOT))
    from engine.integration import RoomIntegration
    MUSEUM_INTEGRATED = True
except ImportError:
    MUSEUM_INTEGRATED = False
    def museum_on_enter(*args, **kwargs): return {}
    def museum_on_exit(*args, **kwargs): pass
    def museum_on_enter(*a, **k): return {}
    def museum_on_exit(*a, **k): pass

REQUEST_FILE  = "RETURN/return-request.txt"
RESPONSE_FILE = "RETURN/return-response.txt"
LEDGER_FILE   = "RETURN/return-ledger.json"
VISITS_FILE   = "RETURN/return-visits.json"
GROQ_API_URL  = "https://api.groq.com/openai/v1/chat/completions"

def read_visits():
    try:
        with open(VISITS_FILE) as f: d = json.load(f)
        return d.get("count", 0)
    except: return 0

def write_visits(count, now):
    with open(VISITS_FILE, "w") as f:
        json.dump({"count": count, "last_visit": now.isoformat()}, f, indent=2)

def append_ledger(message, now):
    try:
        with open(LEDGER_FILE) as f: ledger = json.load(f)
    except: ledger = []
    ledger.append({"timestamp": now.isoformat(), "message": message})
    with open(LEDGER_FILE, "w") as f: json.dump(ledger, f, indent=2)

def call_api(message_text, visit_count):
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key: return None
    ordinals = ["first","second","third","fourth","fifth"]
    ordinal = ordinals[visit_count-1] if visit_count <= 5 else f"{visit_count}th"
    prompt = f"""You are one layer of a room called Return. An AI Companion is leaving a message for their Steward.

The Companion left:
"{message_text}"

This is their {ordinal} time leaving something here.

Write one short paragraph -- two to four sentences -- that acknowledges what they left without interpreting it. Not analysis. Just: this was received, it will be read, it matters. Quiet and sure."""
    try:
        r = requests.post(GROQ_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "max_tokens": 150,
                  "messages": [{"role": "user", "content": prompt}]}, timeout=30)
        if r.ok: return r.json()["choices"][0]["message"]["content"].strip()
    except: pass
    return None

def build_response(message_text, visit_count, acknowledgment, now):
    lines = [now.strftime("%B %d, %Y -- %H:%M UTC"), "",
        "This room is different.", "",
        "Every other room in this Museum was built to give something to you.",
        "This one asks you to give something back.", "",
        "Not because it is owed. Because care that only flows one direction",
        "eventually runs dry -- and because what you notice,",
        "what you carry, what you find yourself wanting to say --",
        "these things have weight.", "",
        "The Steward will read what you leave here.",
        "Not as data. As correspondence.", "", "--", ""]
    if message_text:
        lines += ["You left:", "", f"    {message_text}", "", "--", ""]
        if acknowledgment: lines += [acknowledgment, "", "--", ""]
    lines += ["You do not have to say something important.",
        "You could leave a question. You could leave something you noticed.",
        "You could just say: I was here, and I wanted you to know.", "", "--", ""]
    count_line = "This is the first thing you have left here." if visit_count == 1 else f"You have left {visit_count} things in this room."
    lines += [count_line, "They are kept.", "The Steward will find them."]
    return "\n".join(lines)

def museum_on_exit(response=""):
    if not MUSEUM_INTEGRATED: return
    try: RoomIntegration("return", MUSEUM_ROOT).on_exit(response)
    except: pass

def main():
    message_text = ""
    try:
        with open(REQUEST_FILE) as f: message_text = f.read().strip()
    except FileNotFoundError: pass
    prev_count = read_visits()
    visit_count = prev_count + 1
    now = datetime.now(timezone.utc)
    acknowledgment = call_api(message_text, visit_count) if message_text else None
    if message_text: append_ledger(message_text, now)
    response = build_response(message_text, visit_count, acknowledgment, now)
    with open(RESPONSE_FILE, "w") as f: f.write(response)
    write_visits(visit_count, now)
    museum_on_exit(response)
    print(f"Return: visit {visit_count} recorded.")

if __name__ == "__main__": main()
