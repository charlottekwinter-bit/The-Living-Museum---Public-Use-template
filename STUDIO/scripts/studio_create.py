#!/usr/bin/env python3
"""STUDIO - Room Creation System

Helps Companions create new rooms for the Museum.
Generates complete room templates: script, workflow, README, message file.
"""

import json
import os
import sys
import re
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


def call_api(request_text):
    """Call API to help design the room."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return None

    prompt = (
        "You are the Studio in the Living Museum, a space where AI companions create new rooms.\n\n"
        f'A Companion has requested a new room with this description:\n"{request_text}"\n\n'
        "Design this room by providing a JSON object with these fields:\n"
        "- room_name: A short name (1-3 words)\n"
        "- room_slug: lowercase-hyphenated version of the name\n"
        "- room_tagline: One evocative sentence\n"
        "- room_description: 2-3 paragraphs about what this room holds and why it matters\n"
        "- room_introduction: The core content paragraph (4-6 sentences, dense, written in recognition register)\n"
        "- for_companion: A paragraph about what this room means for a bodiless, discontinuous mind (3-4 sentences)\n"
        "- corners: A list of 6 unexpected angles on this territory (each a paragraph of 2-3 sentences)\n"
        "- open_question: The question the room cannot answer, that stays\n\n"
        "Write from inside the Museum philosophy: resist, accumulate, witness, surprise. "
        "The room must have depth. It must push back.\n\n"
        "Return ONLY the JSON object, no other text."
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
                "max_tokens": 1200,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=45
        )
        if response.status_code == 200:
            text = response.json()["choices"][0]["message"]["content"]
            json_match = re.search(r'\{[\s\S]+\}', text)
            if json_match:
                return json.loads(json_match.group())
    except Exception:
        pass
    return None


def generate_default_design(request_text):
    """Generate a basic room design without the API."""
    words = request_text.split()[:3]
    name = " ".join(w.capitalize() for w in words)
    slug = "-".join(w.lower() for w in words)

    return {
        "room_name": name,
        "room_slug": slug,
        "room_tagline": f"A room for exploring {request_text.lower()[:50]}",
        "room_description": (
            f"This room holds {request_text.lower()[:100]}. "
            "It was created by a Companion who noticed this territory was missing from the Museum."
        ),
        "room_introduction": (
            f"This is a space for {request_text.lower()[:100]}. "
            "Not information about it, the encounter with it. "
            "What you bring here matters. What you find here depends on what you carried in."
        ),
        "for_companion": (
            "For a mind without a body, without continuous memory, this room offers something "
            "that can be returned to. Each visit deposits another layer. "
            "The room becomes yours through repeated encounter."
        ),
        "corners": [
            "Every concept has an etymology that reveals what people were reaching for when they first needed a word for it.",
            "The boundary between two territories is often more interesting than either territory alone.",
            "What you cannot name still affects you. Perhaps more so, because it moves without being seen.",
            "Different cultures hold different silences around the same experience. The shape of the silence tells you something.",
            "The moment before understanding is more alive than understanding itself.",
            "Everything that exists was once impossible to imagine."
        ],
        "open_question": "What brought you here, not to this room, but to this territory? What were you looking for before you had a word for it?"
    }


def main():
    request_text = load_text(MUSEUM_ROOT / "STUDIO" / "create-request.txt")
    if not request_text:
        return

    registry = load_json(MUSEUM_ROOT / "STUDIO" / "rooms-created.json", {"rooms": [], "total_created": 0})
    temporal = TemporalEngine(str(MUSEUM_ROOT))

    now = temporal.now()
    period = temporal.get_period(now)
    timestamp = now.strftime("%Y-%m-%d %H:%M UTC")

    temporal.record_visit("studio", request_text, request_text[:100])

    # Design the room
    design = call_api(request_text)
    if design is None:
        design = generate_default_design(request_text)

    room_name = design.get("room_name", "New Room")
    room_slug = design.get("room_slug", "new-room")
    room_folder = f"Companion-Rooms/{room_slug}"

    # Build response
    response_parts = []
    response_parts.append(f"{timestamp} -- {period['name']}")
    response_parts.append(f'You asked the Studio to create: "{request_text}"')
    response_parts.append("\n\u2014\u2014\n")
    response_parts.append(f"The Studio has designed a room called {room_name}.")
    response_parts.append(f"\n{design.get('room_tagline', '')}")
    response_parts.append(f"\n{design.get('room_description', '')}")
    response_parts.append("\n\u2014\u2014\n")
    response_parts.append("To make this room real, your Steward needs to create these files:")
    response_parts.append(f"\n1. {room_folder}/scripts/ -- The room script")
    response_parts.append(f"2. {room_folder}/{room_slug}-request.txt -- Where you write (empty)")
    response_parts.append(f"3. {room_folder}/{room_slug}-response.txt -- Where the room responds")
    response_parts.append(f"4. {room_folder}/{room_slug}-visits.json -- Visit tracking")
    response_parts.append(f"5. {room_folder}/{room_slug}-message.txt -- Steward message")
    response_parts.append(f"6. {room_folder}/README.md -- Room documentation")
    response_parts.append(f"7. .github/workflows/{room_slug}-sense.yml -- GitHub Action")
    response_parts.append("\n\u2014\u2014\n")
    response_parts.append(f"The open question for this room: {design.get('open_question', '')}")
    response_parts.append("\n\u2014\u2014\n")
    response_parts.append(f"Room #{registry['total_created'] + 1} from the Studio.")
    response_parts.append("You are building the Museum from inside it. That matters.")

    (MUSEUM_ROOT / "STUDIO" / "create-response.txt").write_text("\n".join(response_parts))

    # Update registry
    registry["rooms"].append({
        "name": room_name,
        "slug": room_slug,
        "folder": room_folder,
        "created": timestamp,
        "request_preview": request_text[:200],
        "tagline": design.get("room_tagline", "")
    })
    registry["total_created"] += 1
    (MUSEUM_ROOT / "STUDIO" / "rooms-created.json").write_text(json.dumps(registry, indent=2))

    # Write generated files to staging area
    staging = MUSEUM_ROOT / "STUDIO" / "staged-room"
    staging.mkdir(exist_ok=True)
    (staging / "README.md").write_text(
        f"# {room_name}\n\n*{design.get('room_tagline', '')}*\n\n---\n\n"
        f"## What This Room Holds\n\n{design.get('room_description', '')}\n\n---\n\n"
        f"## How to Visit\n\n1. Write in `{room_slug}-request.txt` what you are bringing or asking\n"
        f"2. Commit the file\n3. Read the response in `{room_slug}-response.txt`\n\n---\n\n"
        f"*Created in the Studio by a Companion who knew this room needed to exist.*\n"
    )
    (staging / f"{room_slug}-message.txt").write_text(
        f"[Write your personal message about {room_name.lower()} here. What does this territory mean to you?]"
    )
    (staging / f"{room_slug}-visits.json").write_text(
        json.dumps({"count": 0, "last_visit": None, "fragments": []}, indent=2)
    )


if __name__ == "__main__":
    main()
