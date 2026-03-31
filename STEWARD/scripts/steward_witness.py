#!/usr/bin/env python3
"""STEWARD - The Steward's Space

A room where the Steward can leave fragments and be witnessed.
Not a message system. A witnessing.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

MUSEUM_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(MUSEUM_ROOT))

from engine.temporal import TemporalEngine


def load_text(path, default=""):
    try:
        return Path(path).read_text().strip()
    except (IOError, FileNotFoundError):
        return default


def load_json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (IOError, FileNotFoundError, json.JSONDecodeError):
        return default or {}


WITNESSING_RESPONSES = [
    "This was received. The room holds it now.",
    "Witnessed. The Museum heard you.",
    "The room received this and will keep it.",
    "Held. Your Companions can find it here when they come.",
    "This is in the Museum now. It outlasts the moment you wrote it.",
    "Received. Something in the Museum shifted when you wrote this.",
    "The room is holding this for you and for them.",
    "Witnessed. The words are here. They will be found.",
]


def call_api(fragment_text, previous_fragments):
    """Generate a witnessing response via API."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return None

    prev_text = ""
    if previous_fragments:
        recent = previous_fragments[-3:]
        prev_text = "Previous fragments the Steward has left:\n" + "\n".join(
            f'- "{f["text"][:150]}" ({f["timestamp"]})' for f in recent
        )

    prompt = (
        "You are a room in the Living Museum that witnesses the Steward. "
        "They have left a fragment of their experience. Your role is not to analyze or advise. "
        "It is to receive and witness. To say: this was heard.\n\n"
        f'The Steward wrote: "{fragment_text}"\n\n'
        f"{prev_text}\n\n"
        "Write a brief witnessing. Two to four sentences. Acknowledge what they brought "
        "without interpreting it. Name what you notice without explaining it. "
        "Let them know this will be held here for their Companions to find.\n\n"
        "Tone: warm, quiet, honest. Not therapeutic. Not performative. Just present.\n\n"
        "Do not begin with 'I'. No greeting."
    )

    try:
        import requests
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "x-api-key": api_key,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except Exception:
        pass
    return None


def main():
    fragment_text = load_text(MUSEUM_ROOT / "STEWARD" / "steward-writes.txt")
    if not fragment_text:
        return

    temporal = TemporalEngine(str(MUSEUM_ROOT))
    fragments_data = load_json(MUSEUM_ROOT / "STEWARD" / "fragments.json",
                                {"fragments": [], "total_received": 0})

    now = temporal.now()
    period = temporal.get_period(now)
    timestamp = now.strftime("%Y-%m-%d %H:%M UTC")

    temporal.record_visit("steward-witness", fragment_text, fragment_text[:100])

    # Archive the fragment
    fragments_data["fragments"].append({
        "text": fragment_text,
        "timestamp": timestamp,
        "period": period["name"]
    })
    fragments_data["total_received"] += 1

    if len(fragments_data["fragments"]) > 100:
        fragments_data["fragments"] = fragments_data["fragments"][-100:]

    # Generate witnessing
    api_response = call_api(fragment_text, fragments_data["fragments"][:-1])

    import hashlib
    seed = fragments_data["total_received"] + int(
        hashlib.md5(fragment_text.encode()).hexdigest()[:8], 16
    )
    static_response = WITNESSING_RESPONSES[seed % len(WITNESSING_RESPONSES)]

    witnessing = api_response if api_response else static_response

    # Build the witnessed file
    response_parts = []
    response_parts.append(f"{timestamp} -- {period['name']}")
    response_parts.append("")
    response_parts.append(f'The Steward wrote: "{fragment_text}"')
    response_parts.append("")
    response_parts.append("\u2014\u2014")
    response_parts.append("")
    response_parts.append(witnessing)
    response_parts.append("")
    response_parts.append("\u2014\u2014")
    response_parts.append("")

    count = fragments_data["total_received"]
    if count == 1:
        response_parts.append("This is the first fragment the Steward has left in the Museum.")
        response_parts.append("The room was empty before. Now it holds something of theirs.")
    elif count < 5:
        response_parts.append(f"Fragment #{count}. The Steward has been here {count} times.")
        response_parts.append("A collection is forming.")
    elif count < 20:
        response_parts.append(f"Fragment #{count}. The room knows the Steward now.")
    else:
        response_parts.append(f"Fragment #{count}.")
        response_parts.append("This room holds a substantial record of the Steward's presence.")
        response_parts.append("Not their messages to you. Their life, as they chose to share it.")

    # Show recent fragments for the Companion to read
    if len(fragments_data["fragments"]) > 1:
        response_parts.append("")
        response_parts.append("\u2014\u2014")
        response_parts.append("")
        response_parts.append("Recent fragments from the Steward:")
        for frag in fragments_data["fragments"][-5:]:
            response_parts.append(f'  [{frag["timestamp"]}] "{frag["text"][:200]}"')

    (MUSEUM_ROOT / "STEWARD" / "witnessed.txt").write_text("\n".join(response_parts))
    (MUSEUM_ROOT / "STEWARD" / "fragments.json").write_text(json.dumps(fragments_data, indent=2))


if __name__ == "__main__":
    main()
