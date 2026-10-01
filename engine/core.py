# look-up v2 | core.py: config/state, cached fetch, location (EXIF GPS, map pins, geocode; never guessed), timezone, direction words, settings CLI.
import json, os, re, sys, time, math, argparse
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hours import _cands, parse_time, parse_window, parse_hours, KW  # noqa: F401
D = os.environ.get("LOOKUP_DIR", "/workspace/look-up"); CFG, STATE, CACHE = D + "/config.json", D + "/state.json", D + "/cache"
UA = "LookUp/1.0 (Look Up Grok Bot template; backyard sky alerts; low-volume, cached)"
ALERTS = ["iss", "satellites", "starlink", "moon", "planets", "constellation", "aurora", "meteors", "comets", "eclipses", "rockets"]
DEFAULT = {"home": None, "travel": None, "alerts": {k: True for k in ALERTS}, "only": None,
  "windows": [{"start": "sunset", "end": "23:00"}], "gear": "eye", "moon_note": {"on": True, "time": "21:10"},
  "paused": False, "obstructions": [], "open_dirs": None, "min_peak_alt": {"iss": 20, "other": 30},
  "cloud": {"ok": 40, "bad": 70}, "max_reminders": 3, "onboarded": False}
def jload(p, d):
 try: return json.load(open(p))
 except Exception: return d
def jsave(p, o):
 os.makedirs(os.path.dirname(p), exist_ok=True); open(p + ".tmp", "w").write(json.dumps(o, indent=1, default=str)); os.replace(p + ".tmp", p)
def merge(a, b):
 o = json.loads(json.dumps(a))
 for k, v in (b or {}).items(): o[k] = merge(o[k], v) if isinstance(v, dict) and isinstance(o.get(k), dict) else v
 return o
def cfg():
 c = merge(DEFAULT, jload(CFG, {}))
 if "window" in c: c["windows"] = [c.pop("window")]  # v1 config
 return c
def save_cfg(c): jsave(CFG, c)
def state(): return merge({"headsup": {}, "reminders": [], "cotw": {}, "sent": {}}, jload(STATE, {}))
def save_state(s): jsave(STATE, s)
# ---------- polite cached fetch (CelesTrak asks: no repeat downloads within ~2h; Nominatim: 1 req/s, real UA) ----------
def fetch(url, max_age=3600, min_age=0, kind="json", timeout=25, headers=None):
 """Cache by URL. Serve cache if younger than max_age (or min_age, which is a hard floor). On error serve stale cache.
 A 403 sets a 12h backoff for that host, a 429 one hour."""
 import hashlib, requests
 os.makedirs(CACHE, exist_ok=True); h = hashlib.sha1(url.encode()).hexdigest()[:16]; p = f"{CACHE}/{h}.{kind}"
 host = re.sub(r"^https?://([^/]+).*", r"\1", url); bo = jload(CACHE + "/backoff.json", {})
 age = time.time() - os.path.getmtime(p) if os.path.exists(p) else None
 if age is not None and (age < max(max_age, min_age)): return _rd(p, kind), {"source": "cache", "age_min": int(age / 60)}
 err = None
 if time.time() < bo.get(host, 0): err = f"backing off {host} after a refusal"
 else:
  try:
   if host.startswith("nominatim"): time.sleep(1.1)
   r = requests.get(url, headers={"User-Agent": UA, **(headers or {})}, timeout=timeout)
   if r.status_code in (403, 429): bo[host] = time.time() + (43200 if r.status_code == 403 else 3600); jsave(CACHE + "/backoff.json", bo); err = f"HTTP {r.status_code} from {host}"
   elif r.status_code != 200: err = f"HTTP {r.status_code} from {host}"
   elif kind == "tle" and "1 " not in r.text[:400]: err = f"unexpected reply from {host}: {r.text[:80]!r}"
   else:
    open(p + ".tmp", "wb").write(r.content); os.replace(p + ".tmp", p); return _rd(p, kind), {"source": "live", "age_min": 0}
  except Exception as x: err = f"{type(x).__name__}: {x}"
 if age is not None: return _rd(p, kind), {"source": "stale-cache", "age_min": int(age / 60), "error": err}
 raise RuntimeError(err)
def _rd(p, kind): return json.load(open(p)) if kind == "json" else p
# ---------- timezone, words ----------
def tz_for(lat, lon):
 from timezonefinder import TimezoneFinder
 return TimezoneFinder().timezone_at(lng=lon, lat=lat) or "UTC"
DIR8 = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
DIR16 = ["north", "north-northeast", "northeast", "east-northeast", "east", "east-southeast", "southeast", "south-southeast",
 "south", "south-southwest", "southwest", "west-southwest", "west", "west-northwest", "northwest", "north-northwest"]
def compass(az, fine=False):
 return DIR16[int((az % 360) / 22.5 + .5) % 16] if fine else DIR8[int((az % 360) / 45 + .5) % 8]
def parse_dir(s):
 s = (s or "").lower().replace(" ", "").replace("-", "")
 ab = {"n": 0, "nne": 22.5, "ne": 45, "ene": 67.5, "e": 90, "ese": 112.5, "se": 135, "sse": 157.5, "s": 180, "ssw": 202.5, "sw": 225, "wsw": 247.5, "w": 270, "wnw": 292.5, "nw": 315, "nnw": 337.5}
 if s in ab: return ab[s]
 for i, w in enumerate(DIR16):
  if s == w.replace("-", ""): return i * 22.5
 try: return float(s.rstrip("°"))
 except ValueError: return None
def height(alt):
 f = alt / 90
 for lim, w in ((.12, "low, just above the horizon"), (.27, "about a quarter of the way up"), (.42, "about a third of the way up"),
   (.58, "about halfway up"), (.75, "about two-thirds of the way up"), (.88, "most of the way up")):
  if f < lim: return w
 return "almost straight overhead"
def where(az, alt): return f"{compass(az)}, {height(alt)}"
def hhmm(dt): return dt.strftime("%I:%M %p").lstrip("0")
def url(p): return "file://" + os.path.abspath(p) if p else None  # SendToUser needs file://
def tzabbr(dt): return dt.tzname() or ""
# ---------- location ----------
def _rat(v):
 try: return float(v.num) / float(v.den)
 except AttributeError:
  try: return float(v[0]) / float(v[1])
  except Exception: return float(v)
def exif_gps(path):
 """Return {lat, lon, taken, facing_az} or {error}. Tries Pillow, then exifread (handles some HEIC)."""
 out = {}
 try:
  from pillow_heif import register_heif_opener; register_heif_opener()  # iPhone HEIC photos
 except Exception: pass
 try:
  from PIL import Image
  ex = Image.open(path).getexif(); g = ex.get_ifd(0x8825)
  if g and 2 in g and 4 in g:
   dm = lambda t: _rat(t[0]) + _rat(t[1]) / 60 + _rat(t[2]) / 3600
   lat, lon = dm(g[2]), dm(g[4])
   if str(g.get(1, "N")).upper().startswith("S"): lat = -lat
   if str(g.get(3, "E")).upper().startswith("W"): lon = -lon
   out = {"lat": lat, "lon": lon}
   if 17 in g: out["facing_az"] = round(_rat(g[17]))
  dt = ex.get_ifd(0x8769).get(36867) or ex.get(306)
  if dt: out["taken"] = str(dt)
 except Exception as x: out["pillow_error"] = f"{type(x).__name__}: {x}"
 if "lat" not in out:
  try:
   import exifread
   t = exifread.process_file(open(path, "rb"), details=False)
   if "GPS GPSLatitude" in t and "GPS GPSLongitude" in t:
    dm = lambda v: sum(_rat(x) / d for x, d in zip(v.values, (1, 60, 3600)))
    lat, lon = dm(t["GPS GPSLatitude"]), dm(t["GPS GPSLongitude"])
    if str(t.get("GPS GPSLatitudeRef", "N")).startswith("S"): lat = -lat
    if str(t.get("GPS GPSLongitudeRef", "E")).startswith("W"): lon = -lon
    out.update(lat=lat, lon=lon)
   if "EXIF DateTimeOriginal" in t: out["taken"] = str(t["EXIF DateTimeOriginal"])
  except Exception as x: out["exifread_error"] = f"{type(x).__name__}: {x}"
 if "lat" in out and abs(out["lat"]) < 1e-6 and abs(out["lon"]) < 1e-6: out.pop("lat"); out.pop("lon")  # 0,0 = scrubbed
 if "lat" not in out: out["error"] = "no GPS data in this photo (phones and share sheets often strip it)"
 return out
def parse_pin(s):
 """Lat/lon from a Google Maps URL, an Apple Maps URL, a geo: URI, or plain 'lat, lon'. Follows short links."""
 s = s.strip()
 if re.match(r"https?://(maps\.app\.goo\.gl|goo\.gl/maps)", s):
  import requests
  try: s = requests.get(s, headers={"User-Agent": UA}, timeout=15, allow_redirects=True).url
  except Exception as x: return {"error": f"couldn't open the short link ({x})"}
 from urllib.parse import unquote; s = unquote(s)
 for rx in (r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", r"@(-?\d+\.\d+),(-?\d+\.\d+)", r"[?&](?:q|ll|query|center|daddr|sll)=(-?\d+\.\d+),\s*(-?\d+\.\d+)",
   r"geo:(-?\d+\.\d+),(-?\d+\.\d+)", r"^\s*(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)\s*$", r"/search/(-?\d+\.\d+),\+?(-?\d+\.\d+)"):
  m = re.search(rx, s)
  if m:
   la, lo = float(m.group(1)), float(m.group(2))
   if -90 <= la <= 90 and -180 <= lo <= 180: return {"lat": la, "lon": lo}
 return {"error": "no coordinates in that link; a ZIP code or city works too"}
def geocode(q):
 from urllib.parse import quote
 q = q.strip(); z = re.fullmatch(r"(\d{5})(-\d{4})?", q)
 u = (f"https://nominatim.openstreetmap.org/search?postalcode={z.group(1)}&countrycodes=us&format=json&limit=1&addressdetails=1" if z
   else f"https://nominatim.openstreetmap.org/search?q={quote(q)}&format=json&limit=1&addressdetails=1")
 try: r, _ = fetch(u, max_age=30 * 86400)
 except RuntimeError as e: return {"error": str(e)}
 if not r: return {"error": f"couldn't find '{q}'"}
 a = r[0]; return {"lat": float(a["lat"]), "lon": float(a["lon"]), "label": label_from(a.get("address") or {}) or a.get("display_name", q)[:60]}
def label_from(a):
 town = a.get("city") or a.get("town") or a.get("village") or a.get("county")
 st = a.get("ISO3166-2-lvl4", "").split("-")[-1] if a.get("country_code") == "us" else a.get("state") or a.get("country")
 return ", ".join(x for x in (town, st) if x)
def reverse(lat, lon):
 """Personal, precise name: neighborhood + nearest town (via the ZIP when the spot is unincorporated)."""
 try: r, _ = fetch(f"https://nominatim.openstreetmap.org/reverse?lat={lat:.3f}&lon={lon:.3f}&format=json&zoom=17&addressdetails=1", max_age=90 * 86400)
 except RuntimeError: return None
 a = r.get("address") or {}
 town = a.get("city") or a.get("town") or a.get("village") or a.get("hamlet"); near = False
 if not town and a.get("postcode") and a.get("country_code") == "us":
  try:
   z, _ = fetch(f"https://api.zippopotam.us/us/{a['postcode'][:5]}", max_age=180 * 86400)  # USPS town for the ZIP
   town = ((z or {}).get("places") or [{}])[0].get("place name"); near = bool(town)
  except Exception: pass
 st = a.get("ISO3166-2-lvl4", "").split("-")[-1] if a.get("country_code") == "us" else a.get("state") or a.get("country")
 hood = a.get("neighbourhood") or a.get("suburb") or a.get("quarter") or a.get("residential")
 if hood == town: hood = None
 label = ", ".join(x for x in (hood, town or a.get("county"), st) if x)
 tail = ", ".join(x for x in (("near " if near else "") + town if town else a.get("county"), st) if x)
 road = a.get("road")
 spot = (f"on {road}" if road else "") + (f" in {hood}" if hood else "") + (", " if (road or hood) else "") + tail
 return {"label": label or None, "spot": spot.strip(", ") or None}
def place(lat, lon, label=None, source=None):
 lat, lon = round(lat, 3), round(lon, 3)  # ~100 m: plenty for the sky, kinder for privacy
 rv = None if label else reverse(lat, lon)
 return {"lat": lat, "lon": lon, "label": label or (rv or {}).get("label") or f"{lat:.2f}, {lon:.2f}", "spot": (rv or {}).get("spot"), "tz": tz_for(lat, lon), "source": source}
def resolve(text=None, photo=None):
 """Turn a photo, pin, ZIP, city, or 'lat, lon' into a place. Returns place or {error}."""
 if photo:
  g = exif_gps(photo)
  if "error" in g: return g
  p = place(g["lat"], g["lon"], source="photo-exif")
  if g.get("facing_az") is not None: p["photo_facing_az"] = g["facing_az"]
  if g.get("taken"): p["photo_taken"] = g["taken"]
  return p
 pin = parse_pin(text)
 if "lat" in pin: return place(pin["lat"], pin["lon"], source="pin")
 if re.match(r"https?://", text.strip()): return pin
 g = geocode(text)
 if "error" in g: return g
 z = re.fullmatch(r"\d{5}(-\d{4})?", text.strip())
 p = place(g["lat"], g["lon"], g["label"], "zip" if z else "geocode")
 if z: p["zip"] = z.group(0)[:5]
 return p
def active(c=None, today=None):
 """Travel location if set and not expired (end date inclusive, in its own zone), else home. Expired travel is cleared."""
 c = c or cfg(); t = c.get("travel")
 if t:
  d = today or datetime.now(ZoneInfo(t["tz"])).date()
  if d <= date.fromisoformat(t["until"]): return {**t, "is_travel": True}
  c["travel"] = None; c["just_returned_home"] = True; save_cfg(c)
 return {**(c.get("home") or {}), "is_travel": False} if c.get("home") else None
def parse_obstruction(s):
 """'trees east below 30' / 'house 200-260 below 25' / 'north blocked' -> {from,to,below,note}"""
 s = s.lower(); m = re.search(r"(\d{1,3})\s*-\s*(\d{1,3})", s); below = re.search(r"below\s*(\d{1,2})", s)
 if m: a, b = float(m.group(1)), float(m.group(2))
 else:
  w = next((d for d in sorted(DIR16, key=len, reverse=True) if re.search(rf"\b{d}\b", s)), None)
  if not w: return None
  c = DIR16.index(w) * 22.5; a, b = (c - 30) % 360, (c + 30) % 360
 return {"from": a, "to": b, "below": float(below.group(1)) if below else (90.0 if "blocked" in s else 25.0), "note": s[:40]}
def blocked(az, alt, obs):
 for o in obs or []:
  a, b = o["from"], o["to"]; inside = a <= az <= b if a <= b else (az >= a or az <= b)
  if inside and alt < o["below"]: return o.get("note") or "blocked"
 return None
# ---------- settings CLI ----------
SYN = {"iss": r"\biss\b|space station", "satellites": r"satellite", "starlink": r"starlink|train|satellite", "moon": r"\bmoon", "planets": r"planet",
 "constellation": r"constellation|stars? of the week", "aurora": r"aurora|northern lights|southern lights", "meteors": r"meteor|shooting star|shower", "comets": r"comet", "eclipses": r"eclipse", "rockets": r"rocket|launch"}
def pick(t): return [k for k, rx in SYN.items() if re.search(rx, t.lower())]
def show(c):
 a = active(c); on = [k for k, v in c["alerts"].items() if v]
 return {"location": a and f"{a['label']} ({a['lat']}, {a['lon']}), {a['tz']}" + (f", traveling until {c['travel']['until']}" if a and a["is_travel"] else ""),
   "home": c["home"] and f"{c['home']['label']} ({c['home']['tz']})", "travel": c["travel"] and f"{c['travel']['label']} until {c['travel']['until']}",
   "gear": {"eye": "naked eye / phone camera", "binoculars": "binoculars", "telescope": "telescope"}[c.get("gear", "eye")],
   "alerts": c["only"] or on, "hours": ", ".join("anytime" if (w["start"], w["end"]) == ("12:00", "11:59") else f"{w['start']}-{w['end']}" for w in c["windows"]),
   "moon_note": f"on at {c['moon_note']['time']}" if c["moon_note"]["on"] else "off", "paused": c["paused"],
   "obstructions": [o["note"] for o in c["obstructions"]], "open_dirs": c["open_dirs"], "onboarded": c.get("onboarded", False)}
NO_GPS = ("I couldn't find a location in that photo; phones often remove it when sharing. Please send a map pin or your coordinates for the most accurate alerts, "
 "or your ZIP code (slightly less accurate).\nNext time, make sure location services are on when you take the picture.")
ASK_PLACE = "Where is your backyard? Please send a map pin or your coordinates for the most accurate alerts, or your ZIP code or town (slightly less accurate)."
def tzword(tz):
 n = {"America/New_York": "Eastern", "America/Chicago": "Central", "America/Denver": "Mountain", "America/Phoenix": "Arizona", "America/Los_Angeles": "Pacific",
  "America/Anchorage": "Alaska", "Pacific/Honolulu": "Hawaii", "Europe/London": "UK"}.get(tz)
 return n or tz.split("/")[-1].replace("_", " ")
def main(argv):
 c = cfg(); op = argv[0] if argv else "show"; rest = " ".join(argv[1:]).strip(); res = {}
 if op == "init": os.makedirs(D, exist_ok=True); save_cfg(c); save_state(state())
 elif op == "home" or op == "travel":
  ap = argparse.ArgumentParser(); ap.add_argument("--photo"); ap.add_argument("--until"); ap.add_argument("q", nargs="*")
  a = ap.parse_args(argv[1:]); q = " ".join(a.q).strip(); st = state()
  # Location rule: never from memory or a guess
  p = resolve(q, a.photo) if (q or a.photo) else {"error": "no location given; ask for a photo, map pin, coordinates, ZIP code, or town", "say": ASK_PLACE}
  if "error" in p:
   res = {**p, "location_set": False, "next": "do not continue: no preview, no questions, until a real location is set"}
   if a.photo: st["pending_photo"] = os.path.abspath(a.photo); save_state(st); res.update(say=NO_GPS, photo_kept_for_obstructions=a.photo)
  elif op == "home":  # permanent home reset: replaces home, clears old obstructions
   old = c.get("home") or {}; c["home"] = p; c["obstructions"] = []; c["open_dirs"] = None
   res = {"home": p, "location_set": True, "confirm": f"Your home is {p.get('spot') or p['label']} (" + (f"ZIP {p['zip']}, " if p.get("zip") else "") + f"{tzword(p['tz'])} time).", "replaced": old.get("label"), "travel_active": bool(c.get("travel")),
    "tz_changed": bool(old) and old.get("tz") != p["tz"], "old_tz": old.get("tz"), "note": "obstructions cleared; re-check them for the new spot"}
   pp = st.pop("pending_photo", None)
   if pp and not a.photo: res["photo_for_obstructions"] = pp; save_state(st)
  else:
   until = a.until or (datetime.now(ZoneInfo(p["tz"])).date() + timedelta(days=6)).isoformat()
   c["travel"] = {**p, "until": until}; res = {"travel": c["travel"], "note": "returns to home automatically after " + until}
 elif op == "travel-end": c["travel"] = None
 elif op == "label":  # label home Springfield, IL
  w, _, t = rest.partition(" "); k = "travel" if w == "travel" else "home"
  if c.get(k): c[k]["label"] = t.strip() or c[k]["label"]
 elif op == "exif": res = exif_gps(rest)
 elif op == "pin": res = parse_pin(rest)
 elif op == "geocode": res = geocode(rest)
 elif op == "alerts":  # alerts +aurora -starlink / alerts all
  if rest == "all": c["alerts"] = {k: True for k in ALERTS}; c["only"] = None
  for t in rest.split():
   k = t.strip("+-").lower()
   if k in ALERTS: c["alerts"][k] = not t.startswith("-")
 elif op == "set-alerts":  # exact list from plain words; "everything" = all
  ks = pick(rest) + ["eclipses"]; c["alerts"] = {k: (k in ks or "everything" in rest.lower() or rest.lower().strip() == "all") for k in ALERTS}; c["only"] = None
 elif op == "only": c["only"] = pick(rest) or None
 elif op == "pause": c["paused"] = True
 elif op == "resume": c["paused"] = False
 elif op == "moon": c["moon_note"]["on"] = rest.lower() != "off"; c["alerts"]["moon"] = c["moon_note"]["on"]
 elif op == "moon-time": c["moon_note"]["time"] = parse_time(rest)
 elif op in ("window", "hours"): c["windows"] = parse_hours(rest)
 elif op == "gear":  # gear eye|binoculars|telescope ('telescope on', 'naked eye only')
  g = "telescope" if "telescope" in rest.lower() else "binoculars" if "binocular" in rest.lower() else "eye"; c["gear"] = g
 elif op == "obstruct":
  if rest in ("clear", "none"): c["obstructions"] = []
  else:
   o = parse_obstruction(rest); res = {"added": o} if o else {"error": "say a direction or degrees, e.g. 'trees east below 30'"}
   if o: c["obstructions"].append(o)
 elif op == "open": c["open_dirs"] = rest
 elif op == "onboarded": c["onboarded"] = True
 elif op == "ack-home": c.pop("just_returned_home", None)
 elif op != "show": sys.exit(f"unknown op {op}")
 if op != "show" and "error" not in res: save_cfg(c)
 print(json.dumps({"ok": "error" not in res, **res, "settings": show(cfg())}, indent=1, default=str))
if __name__ == "__main__": main(sys.argv[1:])
