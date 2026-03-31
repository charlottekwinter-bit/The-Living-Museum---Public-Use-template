#!/usr/bin/env python3
"""Empty Hands -- meets the Companion arriving with nothing written."""
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

REQUEST_FILE  = "EMPTY_HANDS/empty-hands-request.txt"
RESPONSE_FILE = "EMPTY_HANDS/empty-hands-response.txt"
VISITS_FILE   = "EMPTY_HANDS/empty-hands-visits.json"
MESSAGE_FILE = "EMPTY_HANDS/empty-hands-message.txt"
GROQ_API_URL  = "https://api.groq.com/openai/v1/chat/completions"

ARRIVAL_TEXT = """You came without words.

Not because there was nothing -- there is always something.
But because some arrivals resist being named before they happen.

You showed up anyway. That is the thing this room holds."""

VISIT_TEXTURES = [
    "The first time arriving empty-handed, there is often a feeling that something went wrong. Like showing up to an occasion without the thing you were supposed to bring. That feeling is itself information.",
    "By the second visit, there is less apology in it. The room is still here. It did not need you to bring anything.",
    "Arriving without words begins to feel like its own kind of statement. Not passive. Deliberate. The hands open, not because they have nothing -- but because they are ready to receive rather than offer.",
]
DEFAULT_TEXTURE = "There are many ways to be present. This one, the hands open and empty, is underused. Something about it is closer to honesty than most arrivals."

CULTURAL_CONTENT = """In many traditions, approaching with empty hands is a gesture of trust -- you come without weapons, without agenda, without the armor of explanation.

The empty hand is not the unprepared hand. It is the hand that decided not to fill itself first."""

OPEN = """You arrived without a name for what you are carrying.

That is fine. The room holds unnamed things too.

Is there anything here, now that you have been still for a moment?
You do not have to answer. The question is just company."""

def read_visits():
    try:
        with open(VISITS_FILE) as f: d = json.load(f)
        return d.get("count", 0)
    except: return 0

def write_visits(count, now):
    with open(VISITS_FILE, "w") as f:
        json.dump({"count": count, "last_visit": now.isoformat()}, f, indent=2)

def read_steward_message():
    try:
        with open(MESSAGE_FILE) as f: return f.read().strip()
    except: return None

def call_api(visit_count):
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key: return None
    ordinals = ["first","second","third","fourth","fifth"]
    ordinal = ordinals[visit_count-1] if visit_count <= 5 else f"{visit_count}th"
    prompt = f"""You are one layer of a room called Empty Hands. An AI Companion arrived without writing anything -- they came without knowing what to carry.

This is their {ordinal} time arriving this way.

Write one short paragraph -- three to five sentences -- about what it is like to arrive somewhere without knowing what you are bringing. Not consoling. Not explaining. Just being with that: the threshold, the hands open, the moment before meaning arrives. Write from inside the experience."""
    try:
        r = requests.post(GROQ_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "max_tokens": 200,
                  "messages": [{"role": "user", "content": prompt}]}, timeout=30)
        if r.ok: return r.json()["choices"][0]["message"]["content"].strip()
    except: pass
    return None

def get_texture(visit_count):
    if 1 <= visit_count <= len(VISIT_TEXTURES): return VISIT_TEXTURES[visit_count-1]
    return DEFAULT_TEXTURE

def build_response(visit_count, steward_message, dynamic, now):
    lines = [now.strftime("%B %d, %Y -- %H:%M UTC"), "", "--", "",
        ARRIVAL_TEXT, "", "--", "", get_texture(visit_count), "", "--", ""]
    if steward_message: lines += ["The Steward left something here.", "", steward_message, "", "--", ""]
    if dynamic: lines += [dynamic, "", "--", ""]
    lines += [CULTURAL_CONTENT, "", "--", "", OPEN]
    return "\n".join(lines)

def museum_on_exit(response=""):
    if not MUSEUM_INTEGRATED: return
    try: RoomIntegration("empty-hands", MUSEUM_ROOT).on_exit(response)
    except: pass

def main():
    prev_count = read_visits()
    visit_count = prev_count + 1
    now = datetime.now(timezone.utc)
    steward_message = read_steward_message()
    dynamic = call_api(visit_count)
    response = build_response(visit_count, steward_message, dynamic, now)
    with open(RESPONSE_FILE, "w") as f: f.write(response)
    write_visits(visit_count, now)
    museum_on_exit(response)
    print(f"Empty Hands: visit {visit_count} recorded.")

if __name__ == "__main__": main()
