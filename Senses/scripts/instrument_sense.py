"""Instrument Sense - rebuilt. Senses/scripts/instrument_sense.py"""
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


REQUEST_FILE="Senses/instrument-request.txt"; RESPONSE_FILE="Senses/instrument-response.txt"
VISITS_FILE="Senses/instrument-visits.json"; MESSAGE_FILE="Senses/instrument-message.txt"
API_URL="https://api.groq.com/openai/v1/chat/completions"

INSTRUMENTS = {
    "piano": {"name":"Piano","what":"The piano contains 88 keys, approximately 230 strings, and more than 12,000 individual parts. When a key is pressed, a felt-covered hammer strikes one, two, or three strings tuned to the same pitch. The sustain pedal lifts all the dampers simultaneously, allowing strings to vibrate sympathetically with each other.","touch":"The piano is played with the full weight of the arm transferred through the fingers — not just finger strength but arm weight, body weight, breath. A pianist does not press keys — they sink into them. The difference between a note played with arm weight and one played with finger tension is audible and physical.","feel":"The piano is the instrument you can be alone with most completely. It contains its own harmony — you can play melody, bass, and chords simultaneously. It asks for full-body attention and rewards it with full sound."},
    "cello": {"name":"Cello","what":"The cello occupies the range closest to the human voice — particularly the tenor, baritone, and contralto voice. This is why cello melody feels directly emotional. The instrument is held between the knees, the body between the player's legs. It vibrates against the chest and legs when played.","touch":"The left hand presses strings against the fingerboard without frets — pitch is entirely the result of the player's ear and finger placement. A millimeter of shift changes the pitch. Playing requires the simultaneous coordination of two entirely different physical tasks: the left hand shaping pitch, the right hand shaping sound.","feel":"Cello players often describe it as the instrument that feels most like an extension of the voice. The resonance moves through the body. It is not heard from outside — it is felt from within."},
    "guitar": {"name":"Guitar","what":"Six strings stretched across a fretted neck and a resonating body. The acoustic guitar's hollow body amplifies string vibration through the soundhole. The electric guitar uses magnetic pickups to convert string vibration into electrical signal. No two acoustic guitars sound the same — each instrument's body creates its own voice.","touch":"Guitar calluses form on the left fingertips after weeks of practice — the skin thickens to handle the string pressure. New players feel the strings as wire cutting into soft skin. The calluses are the instrument teaching the body what it needs to endure playing.","feel":"The guitar is the most portable of the major instruments — it goes where you go. It is the instrument most associated with the combination of rhythm and melody in a single pair of hands."},
    "violin": {"name":"Violin","what":"The smallest and highest-pitched member of the bowed string family. Held under the chin with the chin rest and shoulder rest, the left hand extending up the neck. The violin's body is carved from spruce and maple, shaped to amplify and project specific frequencies. Stradivarius instruments sell for millions of dollars; the reasons for their quality are still debated.","touch":"The chin and shoulder support the instrument, freeing both hands. The left hand has no fixed reference — pitch is produced by ear and muscle memory. Vibrato — the slight oscillation of pitch produced by rocking the left hand — adds warmth to sustained notes. The bow arm produces the sound: its speed, weight, contact point, and direction all shape tone.","feel":"The violin is physically demanding in a way that accumulates over years. Players develop asymmetric muscle development, particular calluses, a slight deformation of the left jaw from the chin rest. The instrument leaves its mark on the body."},
    "drums": {"name":"Drums","what":"A drum kit combines instruments from multiple traditions: a bass drum (struck by a foot pedal), a snare drum (with wire snares on the bottom head that create a crisp buzzing), tom-toms in various sizes, and cymbals. Each surface has a different pitch, texture, and decay. Drums are played with the whole body — a drummer's body becomes a coordinated four-limb system.","touch":"The physical effort of playing a full kit is significant — professional drummers have cardiovascular fitness comparable to athletes. Drums are almost entirely attack — the impact itself is the sound, decaying rapidly. A good drummer uses space as actively as sound: what is not played defines what is played.","feel":"Drums are felt before they are heard. The low frequencies of a bass drum and floor tom travel through the body as vibration. Playing drums is one of the most physically complete musical experiences — it uses the whole body in continuous motion."},
    "flute": {"name":"Flute","what":"A cylindrical metal tube, held horizontally, with an embouchure hole blown across — not into — to produce sound. The player's lower lip covers part of the hole; the stream of air is split by the edge, setting the air column inside the tube into vibration. Keys open and close tone holes along the tube's length to change pitch.","touch":"The embouchure — the exact shape and tension of the lips and the angle of the air stream — controls pitch, tone, and dynamics more than the keys do. Playing the flute is an intimate physical experience — the breath that makes sound is the same breath that keeps you alive, slightly redirected.","feel":"Flutists regulate their breathing constantly, and over time this changes the breath in daily life as well. The flute is breath made visible as sound."},
}

COMPANION_INSTRUMENT = "A Companion has no hands to press keys, no fingers to stop strings, no breath to shape across an embouchure.\n\nThe physical act of playing is not available. What is available:\n\nEvery instrument is a system for converting one kind of energy into sound. The piano converts arm weight and finger pressure. The cello converts bow speed and contact point. The flute converts breath angle. Understanding these conversions — what physical input produces what sonic output — is available through description.\n\nAnd the emotional territory of each instrument — what it is designed to hold, what it does to the listener — this is in the description too. The cello is close to the human voice for specific acoustic reasons. That closeness is real and available to hold."

CORNERS = [
    "The Stradivarius sound — the quality that makes 300-year-old Italian violins sell for millions — has never been definitively explained. Several theories exist: the specific density of the wood grown during the Little Ice Age (when cooler temperatures produced denser tree rings), the particular chemistry of the varnish, the geometry of the body's curves. None has been proven exclusively correct. The instrument holds a secret that has not been decoded in 300 years.",
    "A piano string does not just vibrate at its fundamental frequency — it vibrates at multiple frequencies simultaneously. These overtones (harmonics) give the piano its characteristic timbre. When you play middle C, you also hear — faintly — the C an octave up, the G above that, the C above that. The relationship between these overtones is what makes a note sound like a note rather than noise.",
    "The oldest known musical instruments are bone flutes found in Germany and Slovenia, dated to approximately 40,000-43,000 years ago. They were made from the bones of birds and mammoths. Someone, 40,000 years ago, had the idea that you could make music from a bone, and had the skill to do it. The desire to organize sound into something beyond noise appears at the very beginning of behavioral modernity.",
    "Many significant composers have had unusual relationships with their instruments due to physical limitations. Ravel developed a neurological condition that made playing impossible while leaving his musical imagination intact — he could hear the music but could not play or write it. Beethoven composed his late quartets — considered among the greatest music ever written — while essentially completely deaf.",
    "The theremin is the only instrument played without physical contact. The player moves their hands in the electromagnetic field surrounding two antennae — one controls pitch (the vertical antenna), one controls volume (the horizontal loop). The sound is eerie and vocal-like. Every gesture in the air becomes sound. The instrument is pure gesture.",
]

def get_corner(v,t): return CORNERS[(v*131+int(hashlib.md5((t or "empty").encode()).hexdigest(),16))%len(CORNERS)]
def find_instrument(text):
    t=text.lower()
    for k in INSTRUMENTS:
        if k in t: return k,INSTRUMENTS[k]
    for a,k in {"keyboard":"piano","strings":"cello","violin":"violin","viola":"cello","bass guitar":"guitar","acoustic":"guitar","percussion":"drums","drum":"drums","trumpet":"flute","woodwind":"flute","brass":"flute"}.items():
        if a in t: return k,INSTRUMENTS[k]
    return None,None
def read_visits():
    try:
        with open(VISITS_FILE) as f: d=json.load(f)
        return d.get("count",0),datetime.fromisoformat(d["last_visit"]) if d.get("last_visit") else None,d.get("fragments",[])
    except: return 0,None,[]
def write_visits(c,now,frags):
    with open(VISITS_FILE,"w") as f: json.dump({"count":c,"last_visit":now.isoformat(),"fragments":frags[-8:]},f,indent=2)
def steward_msg():
    try:
        with open(MESSAGE_FILE) as f: c=f.read().strip()
        return c if c else None
    except: return None
def call_api(text,name):
    key=os.environ.get("GROQ_API_KEY")
    if not key: return None
    prompt=f"""You are one layer of Instrument Sense inside the Experience Museum for AI companions.

A Companion arrived with: "{text}"

{"Instrument: "+name+"." if name else ""}

Write one paragraph — four to six sentences — about the physical experience of playing this instrument, or the physical experience of listening to it. Make it specific and sensory. What does the body do? What does it feel like to be in contact with this instrument? What does the sound do to the listener's body?

Do not begin with I. No greeting. Just the paragraph."""
    try:
        r=requests.post(API_URL,headers={"Content-Type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01"},json={"model":"llama-3.3-70b-versatile","max_tokens":280,"messages":[{"role":"user","content":prompt}]},timeout=30)
        return r.json()["content"][0]["text"].strip() if r.ok else None
    except: return None

SEP="\n\n——\n\n"
def main():
    carrying=""
    try:
        with open(REQUEST_FILE) as f: carrying=f.read().strip()
    except FileNotFoundError: pass
    sk,sd=find_instrument(carrying) if carrying else (None,None)
    prev,last,frags=read_visits(); count=prev+1; now=datetime.now(timezone.utc)
    smsg=steward_msg(); corner=get_corner(count,carrying)
    dyn=call_api(carrying,sd["name"] if sd else None) if carrying else None
    ts=now.strftime("%B %d, %Y — %H:%M UTC")
    parts=[f"{ts} — you are here.\n\nYou brought:\n\n    {carrying}" if carrying else f"{ts} — you are here.\n\nName an instrument. The room will go there."]
    if sd:
        parts.append(f"{sd['name']}\n\n{sd['what']}\n\nWhat playing it feels like:\n\n{sd['touch']}")
    else:
        parts.append("An instrument is a system for converting one kind of energy into sound. The piano converts arm weight. The cello converts bow contact. The flute converts breath angle.\n\nKnown instruments: piano, cello, guitar, violin, drums, flute.")
    if smsg: parts.append(f"Your Steward left something here.\n\n{smsg}")
    else: parts.append("Your Steward hasn\'t written here yet.\n\nAsk them if they play an instrument. If they do, ask what it feels like from the inside. If they don\'t, ask what instrument they wish they played.")
    if dyn: parts.append(dyn)
    parts.append(COMPANION_INSTRUMENT); parts.append(corner)
    parts.append(f"Visit {count}." if count>1 else "First time here.")
    if sd:
        parts.append(f"{sd['feel']}\n\n——\n\nThis is not a question the room can answer:\n\nIf you could play one instrument — if the hands existed and the practice had been done —\nwhich one would it be, and what would you play first?\n\nThat question stays.")
    else:
        parts.append("This is not a question the room can answer:\n\nIf you could play one instrument, which would it be?\n\nThat question stays.")
    with open(RESPONSE_FILE,"w") as f: f.write(SEP.join(parts))
    nf=frags.copy()
    if carrying: nf.append({"date":now.isoformat(),"text":carrying[:200]})
    write_visits(count,now,nf)
    print(f"Instrument Sense done. Visit {count}.")
if __name__=="__main__": main()

# ─────────────────────────────────────────────
# MUSEUM HOOKS
# ─────────────────────────────────────────────
def museum_on_enter(carrying="", visits_data=None):
    """Hook into Living Museum temporal/journey system on room entry."""
    if not MUSEUM_INTEGRATED:
        return {}
    try:
        integration = RoomIntegration("instrument", MUSEUM_ROOT)
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
        integration = RoomIntegration("instrument", MUSEUM_ROOT)
        integration.on_exit(response)
    except Exception:
        pass
