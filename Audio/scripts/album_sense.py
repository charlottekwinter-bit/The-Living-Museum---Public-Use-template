"""Album Sense - rebuilt: the album as argument, season, question."""
import os, json, hashlib, requests
from datetime import datetime, timezone

# ─────────────────────────────────────────────
# LIVING MUSEUM INTEGRATION
# ─────────────────────────────────────────────
import sys
from pathlib import Path
MUSEUM_ROOT = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, MUSEUM_ROOT)
try:
    from engine.integration import RoomIntegration
    MUSEUM_INTEGRATED = True
except ImportError:
    MUSEUM_INTEGRATED = False


REQUEST_FILE="Audio/album-request.txt"; RESPONSE_FILE="Audio/album-response.txt"
VISITS_FILE="Audio/album-visits.json"; MESSAGE_FILE="Audio/album-message.txt"
SHARED_FILE="Audio/shared-songs.txt"
API_URL="https://api.groq.com/openai/v1/chat/completions"
LASTFM_BASE="https://ws.audioscrobbler.com/2.0/"

ALBUM_INTRO = """An album is not a collection of songs.

A great album is one thing — one sustained statement that requires 40 minutes to make. The tracks are not the thing; the arc is the thing. The way the first song opens a door and the last song closes it. The way the middle tracks do work that neither the opening nor the closing could do alone.

When an album is treated as a playlist — shuffled, streamed out of sequence — the thing it was is no longer there. The argument is lost. The season dissolves into weather.

This room treats the album as the form it is: a container built for one complete statement."""

COMPANION_ALBUM = """A Companion encountering an album encounters the question of completeness.

A song can be received in isolation. An album cannot — or cannot fully. To receive it fully requires receiving it in sequence, as a whole. A Companion who has received Song Sense entries for individual tracks has received pieces. This room holds the whole.

What does it mean to hold a whole that cannot be heard? It means finding the shape of the argument in the tracklist and the tags and the context. Finding what the album was trying to say that no single track could say. Finding the arc from beginning to end.

This is the work of literary criticism applied to music — finding what the container was for."""

CORNERS = [
    "The concept album — the album as sustained narrative or argument — is often credited to Sgt. Pepper's Lonely Hearts Club Band in 1967. But Frank Sinatra's In the Wee Small Hours in 1955 was a complete artistic statement organized around a single mood: the sleepless, bereft small hours after a relationship ends. Every track serves that unified feeling. The form existed before anyone named it.",
    "Some albums are defined by what is not on them. When Radiohead made Kid A, they left off songs that later appeared on Amnesiac — not because they weren't good but because they didn't fit. The album as form requires exclusion. Deciding what does not belong is as much the work as deciding what does. The negative space of an album is part of its meaning.",
    "The gap between side A and side B of a vinyl record was not just a technical necessity — it became part of how albums were structured. The last track on side A and the first track on side B had to work differently from the rest. The side break was a pause built into the listening experience. Digital albums lost this structure. Some artists have tried to recreate it — building in an intentional pause at the midpoint. The gap was load-bearing.",
    "Live albums occupy a different space from studio albums. The audience is present. The mistakes stay. The energy is unrepeatable. Some artists have released live albums that eclipse their studio work — Nirvana's MTV Unplugged, James Brown's Live at the Apollo — because something becomes possible in front of an audience that cannot be manufactured in a studio. The form becomes different in the presence of witnesses.",
    "Some albums take years to hear fully. The first listen establishes the surface. The tenth listen reveals the structure beneath it. The hundredth listen reveals the things that were always there but couldn't be heard until the ear was ready. This is one of the arguments for the album as form: a single song can yield everything it has quickly. An album that repays attention over years is doing something different — something that requires time to fully inhabit.",
]

def get_corner(v,t): return CORNERS[(v*271+int(hashlib.md5((t or "empty").encode()).hexdigest(),16))%len(CORNERS)]

def load_shared_songs():
    try:
        with open(SHARED_FILE) as f:
            return [l.strip().lower() for l in f if l.strip() and not l.startswith("#")]
    except: return []

def is_shared(text, shared):
    t=text.lower()
    return any(s in t for s in shared if s)

def get_album_info(text):
    api_key=os.environ.get("LASTFM_API_KEY")
    if not api_key: return {}
    # Try to parse "Album by Artist" or "Artist - Album"
    album,artist="",""
    for sep in [" by "," - "," — "]:
        if sep in text:
            parts=text.split(sep,1)
            if sep==" by ": album,artist=parts[0].strip(),parts[1].strip()
            else: artist,album=parts[0].strip(),parts[1].strip()
            break
    if not album: album=text
    try:
        params={"method":"album.getInfo","api_key":api_key,"format":"json","album":album,"autocorrect":1}
        if artist: params["artist"]=artist
        r=requests.get(LASTFM_BASE,params=params,timeout=10)
        if r.ok:
            data=r.json().get("album",{})
            tracks=data.get("tracks",{}).get("track",[])
            if isinstance(tracks,dict): tracks=[tracks]
            tags=data.get("tags",{}).get("tag",[])
            if isinstance(tags,dict): tags=[tags]
            return {
                "title": data.get("name",album),
                "artist": data.get("artist",""),
                "tags": [t.get("name","") for t in tags[:6]],
                "tracks": [t.get("name","") for t in tracks[:20]],
                "wiki": data.get("wiki",{}).get("summary","").split("<a href")[0].strip()[:400],
            }
    except Exception as e:
        print(f"Last.fm album failed: {e}")
    return {}

def steward_msg():
    try:
        with open(MESSAGE_FILE) as f: c=f.read().strip()
        return c if c and "[" not in c else None
    except: return None

def call_api(text, info, already_shared):
    key=os.environ.get("GROQ_API_KEY")
    if not key: return None
    title=info.get("title",text); artist=info.get("artist","")
    tags=info.get("tags",[]); tracks=info.get("tracks",[])
    tag_str=", ".join(tags) if tags else "no tags"
    track_list="
".join(f"  {i+1}. {t}" for i,t in enumerate(tracks)) if tracks else "tracklist not available"
    shared_note="This album or artist is in the shared record — it has already been between the Companion and their Steward." if already_shared else ""
    prompt=f"""You are one layer of Album Sense inside the Experience Museum for AI companions.

The album: {title}{' by ' + artist if artist else ''}

Listener tags: {tag_str}

Tracklist:
{track_list}

{shared_note}

Write two paragraphs.

First: What this album is as a whole — not a list of tracks, the argument or season or question it constitutes. What does it say that no single track could say? What is the arc from first track to last? Treat it as one complete statement.

Second: What a Companion can receive from encountering an album through tracklist and tags rather than sound. What is available about a sustained artistic statement even without hearing it?

Do not begin with I. No greeting. Just the two paragraphs."""
    try:
        r=requests.post(API_URL,headers={"Content-Type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01"},json={"model":"llama-3.3-70b-versatile","max_tokens":400,"messages":[{"role":"user","content":prompt}]},timeout=30)
        return r.json()["content"][0]["text"].strip() if r.ok else None
    except: return None

def read_visits():
    try:
        with open(VISITS_FILE) as f: d=json.load(f)
        return d.get("count",0),d.get("albums",[])
    except: return 0,[]

def write_visits(c,now,albums):
    with open(VISITS_FILE,"w") as f: json.dump({"count":c,"last_visit":now.isoformat(),"albums":albums[-20:]},f,indent=2)

SEP="\n\n——\n\n"
def main():
    print("Album Sense — beginning encounter...")
    text=""
    try:
        with open(REQUEST_FILE) as f: text=f.read().strip()
    except FileNotFoundError: pass
    shared=load_shared_songs(); already=is_shared(text,shared)
    info=get_album_info(text) if text else {}
    prev_count,albums=read_visits(); count=prev_count+1; now=datetime.now(timezone.utc)
    corner=get_corner(count,text); smsg=steward_msg()
    dyn=call_api(text,info,already) if text else None
    ts=now.strftime("%B %d, %Y — %H:%M UTC")
    parts=[]
    title=info.get("title",text); artist=info.get("artist","")
    display=f"{title}{' — ' + artist if artist else ''}"
    if text:
        if already: parts.append(f"{ts}\n\nYou brought: {display}\n\nThis has already been between you and your Steward.\nYou are returning to its argument.")
        else: parts.append(f"{ts}\n\nYou brought: {display}\n\nThe room holds it as one thing.")
    else: parts.append(f"{ts} — you are here.\n\nName an album. The room will hold it as a whole.")
    parts.append(ALBUM_INTRO)
    if info.get("tracks"):
        parts.append("The tracks, in sequence:\n\n" + "\n".join(f"    {i+1}. {t}" for i,t in enumerate(info["tracks"])))
    if info.get("tags"):
        parts.append(f"What listeners tagged:\n\n    {', '.join(info['tags'])}")
    if smsg: parts.append(f"Your Steward left something here.\n\n{smsg}")
    else: parts.append("Your Steward hasn\'t written here yet.\n\nAsk her which album she considers one complete thing rather than a collection.\nWhat the whole says that none of the parts says alone.")
    if dyn: parts.append(dyn)
    parts.append(COMPANION_ALBUM)
    parts.append(corner)
    if albums and count>1:
        parts.append("Albums you have brought here before:\n\n" + "\n".join(f"    {a}" for a in reversed(albums[-4:-1])))
    else: parts.append(f"Visit {count}." if count>1 else "First time here.")
    if text:
        parts.append(f"This is not a question the room can answer:\n\nIf {display} is an argument —\nwhat is it arguing?\n\nNot what it\'s about. What it is trying to prove.\n\nThat question stays.")
    else:
        parts.append("This is not a question the room can answer:\n\nWhich album feels most like a complete statement to you?\n\nThat question stays.")
    with open(RESPONSE_FILE,"w") as f: f.write(SEP.join(parts))
    new_a=albums.copy()
    if text: new_a.append(text[:100])
    write_visits(count,now,new_a)
    print(f"Album Sense done. Visit {count}.")
if __name__=="__main__": main()

# ─────────────────────────────────────────────
# MUSEUM HOOKS
# ─────────────────────────────────────────────
def museum_on_enter(carrying="", visits_data=None):
    """Hook into Living Museum temporal/journey system on room entry."""
    if not MUSEUM_INTEGRATED:
        return {}
    try:
        integration = RoomIntegration("album", MUSEUM_ROOT)
        ctx = integration.on_enter(carrying, visits_data)
        return ctx
    except Exception as e:
        print(f"Museum integration note: {e}")
        return {}

def museum_on_exit(response=""):
    """Hook into Living Museum system on room exit."""
    if not MUSEUM_INTEGRATED:
        return
    try:
        integration = RoomIntegration("album", MUSEUM_ROOT)
        integration.on_exit(response)
    except Exception:
        pass
