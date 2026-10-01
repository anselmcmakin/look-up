# look-up v2 | stars.py: bright stars, constellation-of-the-week table, and the "what am I looking at?" matcher.
import json, sys, math, argparse, re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import core as C
# name: (RA hours J2000, Dec deg, mag, color note)
STARS = {"Sirius": (6.752, -16.716, -1.46, "blue-white"), "Canopus": (6.399, -52.696, -0.74, "white"), "Arcturus": (14.261, 19.182, -0.05, "orange"),
 "Rigil Kentaurus": (14.660, -60.834, -0.27, "yellow"), "Vega": (18.616, 38.784, 0.03, "blue-white"), "Capella": (5.278, 45.998, 0.08, "yellow"),
 "Rigel": (5.242, -8.202, 0.13, "blue-white"), "Procyon": (7.655, 5.225, 0.34, "white"), "Betelgeuse": (5.919, 7.407, 0.5, "orange-red"),
 "Achernar": (1.629, -57.237, 0.46, "blue-white"), "Hadar": (14.064, -60.373, 0.61, "blue-white"), "Altair": (19.846, 8.868, 0.76, "white"),
 "Acrux": (12.443, -63.099, 0.76, "blue-white"), "Aldebaran": (4.599, 16.509, 0.86, "orange"), "Antares": (16.490, -26.432, 0.96, "red-orange"),
 "Spica": (13.420, -11.161, 0.97, "blue-white"), "Pollux": (7.755, 28.026, 1.14, "orange"), "Fomalhaut": (22.961, -29.622, 1.16, "white"),
 "Deneb": (20.690, 45.280, 1.25, "white"), "Mimosa": (12.795, -59.689, 1.25, "blue-white"), "Regulus": (10.139, 11.967, 1.35, "blue-white"),
 "Adhara": (6.977, -28.972, 1.5, "blue-white"), "Castor": (7.577, 31.888, 1.58, "white"), "Shaula": (17.560, -37.104, 1.62, "blue-white"),
 "Bellatrix": (5.419, 6.350, 1.64, "blue-white"), "Elnath": (5.438, 28.608, 1.65, "blue-white"), "Alnilam": (5.604, -1.202, 1.69, "blue-white"),
 "Alioth": (12.900, 55.960, 1.77, "white"), "Dubhe": (11.062, 61.751, 1.79, "orange"), "Mirfak": (3.405, 49.861, 1.79, "yellow-white"),
 "Polaris": (2.530, 89.264, 1.98, "yellow-white"), "Alpheratz": (0.140, 29.091, 2.06, "blue-white"), "Hamal": (2.120, 23.462, 2.0, "orange"),
 "Kochab": (14.845, 74.156, 2.08, "orange"), "Denebola": (11.818, 14.572, 2.14, "white"), "Alphecca": (15.578, 26.715, 2.23, "white"),
 "Schedar": (0.675, 56.537, 2.24, "orange"), "Sadr": (20.370, 40.257, 2.23, "yellow-white"), "Mizar": (13.399, 54.925, 2.23, "white")}
# constellation: stars [(ra,dec)], lines [(i,j)], find-it hint, short myth/fact. Index 0 = anchor star.
CONS = {
 "Cygnus": ([(20.690, 45.280), (20.370, 40.257), (19.512, 27.960), (19.750, 45.131), (20.770, 33.970)], [(0, 1), (1, 2), (3, 1), (1, 4)],
  "Find Deneb, the top of the Summer Triangle; the Swan's long neck runs from Deneb down the Milky Way to Albireo.", "Also called the Northern Cross. Albireo at the beak is a gold-and-blue double star in binoculars or a small telescope."),
 "Lyra": ([(18.616, 38.784), (18.746, 37.605), (18.908, 36.899), (18.982, 32.690), (18.835, 33.363)], [(0, 1), (1, 2), (2, 3), (3, 4), (4, 1)],
  "Start at Vega, the brightest star high overhead on late-summer evenings; the little parallelogram hangs just beside it.", "The lyre of Orpheus. Vega was the North Star about 12,000 years ago and will be again around the year 13,700."),
 "Aquila": ([(19.846, 8.868), (19.771, 10.613), (19.922, 6.407), (19.090, 13.863), (19.425, 3.115), (19.104, -4.882), (20.188, -0.821)], [(1, 0), (0, 2), (0, 3), (0, 4), (4, 5), (4, 6)],
  "Altair is the southern corner of the Summer Triangle, with a fainter star on each side of it like a short line.", "The eagle that carried Zeus's thunderbolts. Altair spins so fast it bulges at its equator."),
 "Cassiopeia": ([(0.675, 56.537), (0.153, 59.150), (0.945, 60.717), (1.430, 60.235), (1.907, 63.670)], [(1, 0), (0, 2), (2, 3), (3, 4)],
  "Look north for a bright W (or M) of five stars, on the opposite side of Polaris from the Big Dipper.", "The vain queen of Ethiopia, placed in the sky to circle the pole, upside down half the time."),
 "Pegasus": ([(23.079, 15.205), (23.063, 28.083), (0.140, 29.091), (0.221, 15.184)], [(0, 1), (1, 2), (2, 3), (3, 0)],
  "Look for the Great Square: four medium-bright stars making a big box, about the width of your fist held out, times two.", "The winged horse. The Square's corner star Alpheratz actually belongs to Andromeda."),
 "Andromeda": ([(0.140, 29.091), (0.655, 30.861), (1.162, 35.621), (2.065, 42.330)], [(0, 1), (1, 2), (2, 3)],
  "From the top-left corner of the Great Square, follow a chain of stars up toward Perseus.", "Two stars up from Mirach, a faint smudge is the Andromeda Galaxy, 2.5 million light-years away and visible without a telescope from dark skies."),
 "Perseus": ([(3.405, 49.861), (3.136, 40.956), (3.715, 47.788), (3.964, 40.010), (3.080, 53.506), (3.902, 31.884)], [(4, 0), (0, 2), (2, 3), (3, 5), (0, 1)],
  "Below Cassiopeia's W, look for an arc of stars led by Mirfak.", "The hero who slew Medusa. Algol, her 'demon eye', visibly dims every 2.87 days as a companion star passes in front."),
 "Taurus": ([(4.599, 16.509), (5.438, 28.608), (5.627, 21.142), (4.330, 15.628), (4.477, 19.180), (3.791, 24.105)], [(3, 0), (0, 2), (3, 4), (4, 1)],
  "Follow Orion's Belt up and to the right to orange Aldebaran, the bull's eye; the Pleiades cluster sits a bit farther on.", "The bull's face is the Hyades cluster. The Pleiades, the Seven Sisters, are a young cluster about 440 light-years away."),
 "Orion": ([(5.919, 7.407), (5.419, 6.350), (5.679, -1.943), (5.604, -1.202), (5.533, -0.299), (5.796, -9.670), (5.242, -8.202)], [(0, 1), (0, 2), (1, 4), (2, 3), (3, 4), (2, 5), (4, 6)],
  "Look for three evenly spaced stars in a short straight line, the Belt, with orange Betelgeuse above and blue-white Rigel below.", "The hunter. The fuzzy patch below the Belt is the Orion Nebula, a star nursery you can see in binoculars."),
 "Gemini": ([(7.755, 28.026), (7.577, 31.888), (6.629, 16.399), (6.732, 25.131), (6.383, 22.514), (7.335, 21.982)], [(1, 3), (3, 4), (0, 5), (5, 2)],
  "Two bright stars side by side, Castor and Pollux, up and to the left of Orion.", "The twins Castor and Pollux. Castor is actually six stars bound together."),
 "Canis Major": ([(6.752, -16.716), (6.378, -17.956), (6.977, -28.972), (7.140, -26.393), (7.402, -29.303)], [(1, 0), (0, 3), (3, 2), (3, 4)],
  "Follow Orion's Belt down and to the left to Sirius, the brightest star in the night sky.", "Orion's big dog. Sirius is only 8.6 light-years away, one of our closest neighbors."),
 "Auriga": ([(5.278, 45.998), (5.992, 44.948), (5.995, 37.213), (5.438, 28.608), (4.950, 33.166)], [(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)],
  "Bright yellow Capella marks the top of a lopsided pentagon, high in the northeast on autumn and winter evenings.", "The charioteer. Capella is a pair of yellow giant stars orbiting each other."),
 "Ursa Major": ([(11.062, 61.751), (11.031, 56.382), (11.897, 53.695), (12.257, 57.033), (12.900, 55.960), (13.399, 54.925), (13.792, 49.313)], [(0, 1), (1, 2), (2, 3), (3, 0), (3, 4), (4, 5), (5, 6)],
  "Look north for the Big Dipper's bowl and bent handle. The two stars at the end of the bowl point to Polaris.", "The Great Bear. Mizar in the handle has a faint partner, Alcor, an old test of good eyesight."),
 "Ursa Minor": ([(2.530, 89.264), (17.537, 86.586), (16.766, 82.037), (15.734, 77.795), (14.845, 74.156), (15.345, 71.834)], [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)],
  "Follow the Big Dipper's pointer stars to Polaris, the end of the Little Dipper's handle.", "Polaris barely moves all night. Its height above your horizon equals your latitude."),
 "Bootes": ([(14.261, 19.182), (14.750, 27.074), (15.258, 33.315), (15.032, 40.390), (14.535, 38.308), (13.911, 18.398)], [(0, 1), (1, 2), (2, 3), (3, 4), (4, 0), (0, 5)],
  "Follow the arc of the Big Dipper's handle to Arcturus ('arc to Arcturus'); Bootes is the kite shape above it.", "The herdsman. Arcturus is an orange giant about 37 light-years away."),
 "Leo": ([(10.139, 11.967), (10.122, 16.763), (10.333, 19.842), (10.278, 23.417), (9.764, 23.774), (11.235, 20.524), (11.818, 14.572), (11.237, 15.430)], [(0, 1), (1, 2), (2, 3), (3, 4), (2, 5), (5, 6), (6, 7), (7, 0)],
  "Look for a backward question mark (the Sickle) ending in Regulus, with a triangle of stars marking the tail.", "The Nemean lion. The Leonid meteors stream out of the Sickle every November."),
 "Scorpius": ([(16.490, -26.432), (16.006, -22.622), (16.091, -19.806), (16.836, -34.293), (16.864, -38.047), (17.622, -42.998), (17.708, -39.030), (17.560, -37.104)], [(2, 1), (1, 0), (0, 3), (3, 4), (4, 5), (5, 6), (6, 7)],
  "Low in the south on summer evenings: red Antares with a curving hook of stars below it.", "The scorpion that chased Orion. They are never in the sky at the same time."),
 "Sagittarius": ([(18.403, -34.385), (18.921, -26.297), (19.044, -29.880), (18.350, -29.828), (18.466, -25.422), (18.761, -26.991), (18.097, -30.424)], [(0, 3), (3, 6), (6, 0), (0, 2), (2, 5), (5, 1), (5, 4), (4, 3), (3, 5)],
  "Low in the south, east of Scorpius, look for a teapot shape; the Milky Way rises from its spout like steam.", "The center of our galaxy lies just beyond the spout, about 26,000 light-years away."),
 "Hercules": ([(16.688, 31.603), (16.715, 38.922), (17.251, 36.809), (17.005, 30.926), (16.504, 21.490)], [(0, 1), (1, 2), (2, 3), (3, 0), (0, 4)],
  "Between Vega and Arcturus, look for the Keystone: a lopsided box of four modest stars.", "On one side of the Keystone is M13, a ball of several hundred thousand stars, a faint smudge in binoculars."),
 "Corona Borealis": ([(15.578, 26.715), (15.464, 29.106), (15.549, 31.359), (15.713, 26.296), (15.827, 26.068), (15.960, 26.878)], [(2, 1), (1, 0), (0, 3), (3, 4), (4, 5)],
  "Just east of Arcturus, look for a small semicircle of stars, a tiara with one bright gem.", "Home of T Coronae Borealis, a star that flares up about every 80 years."),
 "Crux": ([(12.443, -63.099), (12.795, -59.689), (12.519, -57.113), (12.252, -58.749)], [(0, 2), (1, 3)],
  "Low in the south from the southern hemisphere: a small, bright cross beside the two Pointer stars.", "The Southern Cross. It's on the flags of Australia, New Zealand, Brazil, and others."),
}
def star_obj(ra, dec):
 from skyfield.api import Star
 return Star(ra_hours=ra, dec_degrees=dec)
def altaz(obs, t, ra, dec):
 a, z, _ = obs.at(t).observe(star_obj(ra, dec)).apparent().altaz(); return a.degrees, z.degrees
def field(sk, loc, when):
 """Real bright stars, constellation stars, planets and moon above the horizon at `when`, for sky-map cards."""
 top = sk.observer(loc); obs = sk.earth + top; t = sk.ts.from_datetime(when); out, seen = [], set()
 for n, (ra, dec, mag, _) in STARS.items():
  a, z = altaz(obs, t, ra, dec); seen.add((ra, dec))
  if a > 0: out.append({"name": n, "alt": a, "az": z, "mag": mag, "kind": "star"})
 for st, *_ in CONS.values():
  for ra, dec in st:
   if (ra, dec) in seen: continue
   seen.add((ra, dec)); a, z = altaz(obs, t, ra, dec)
   if a > 0: out.append({"name": None, "alt": a, "az": z, "mag": 3.0, "kind": "star"})
 out += [{**p, "kind": "planet"} for p in sk.planets_now(top, t) if p["alt"] > 0]
 m = sk.moon_now(top, t)
 if m["alt"] > 0: out.append({"name": f"Moon ({m['illum']}%)", "alt": m["alt"], "az": m["az"], "mag": -10, "kind": "moon"})
 return out
def cotw(sk, loc, evening, hist=(), force=None):
 """Pick a well-placed constellation for an evening datetime. Prefers 40-75 deg up, skips recently used."""
 obs = sk.earth + sk.observer(loc); t = sk.ts.from_datetime(evening); best = []
 for n, (st, ln, hint, fact) in CONS.items():
  ra = sum(s[0] for s in st) / len(st) if max(s[0] for s in st) - min(s[0] for s in st) < 12 else st[0][0]
  dec = sum(s[1] for s in st) / len(st); al, az = altaz(obs, t, ra, dec)
  score = -abs(al - 55) - (40 if n in hist else 0) - (25 if n in ("Ursa Minor",) else 0)
  if force == n: score = 999
  if al > 25: best.append((score, n, al, az))
 best.sort(reverse=True)
 if not best: return None
 _, n, al, az = best[0]; st, ln, hint, fact = CONS[n]
 anchor = next((k for k, v in STARS.items() if (v[0], v[1]) == st[0]), None)
 return {"name": n, "anchor": anchor, "alt": round(al), "az": round(az), "where": C.where(az, al), "find": hint, "fact": fact, "at": evening.isoformat(), "field": field(sk, loc, evening),
   "stars": [list(altaz(obs, t, *s)) for s in st], "lines": ln}
def display(c):
 """How a candidate is named in a sentence."""
 n = c["name"]
 if c["kind"] != "satellite": return n
 return ("the International Space Station" if re.search(r"\biss\b|zarya", n, re.I) else "China's Tiangong space station" if re.search(r"tiangong|\bcss\b", n, re.I)
  else "the Hubble Space Telescope" if re.search(r"hubble|\bhst\b", n, re.I) else f"a spent rocket stage ({n})" if re.search(r"r/b", n, re.I)
  else f"a Starlink satellite ({n})" if "starlink" in n.lower() else f"a satellite ({n})")
def answer(top):
 """The polished what-is-that reply: answer, where, how to confirm, an alternative if unsure, one fact, and the method."""
 import facts as F
 if not top: return "I could not find a bright planet, star or satellite that matches. It may be an aircraft, which I cannot track.\nI am matching by your location and the time, not by recognizing the light itself."
 c = top[0]; nm = display(c); cf = c.get("confidence", "low")
 if c["kind"] == "moon": s = f"That is the Moon, a {c['confirm']}, in the **{c['where']}**."
 else:
  s = {"high": "That is almost certainly", "medium": "That is most likely"}.get(cf, "My best match is") + f" **{nm}**, in the **{c['where']}**. To confirm: {c['confirm']}."
 if cf != "high" and len(top) > 1: a = top[1]; s += f" If that does not fit, it may be {display(a)}, in the {a['where']}."
 return s + F.line(F.key_for(c)) + "\nI am matching by your location and the time, not by recognizing the light itself."
def identify(sk, loc, when, dirn=None, alt=None, moving=None, bright=None):
 """Rank what's above the horizon at loc/when. Returns candidates with confidence and how to confirm."""
 top = sk.observer(loc); obs = sk.earth + top; t = sk.ts.from_datetime(when); tzz = ZoneInfo(loc["tz"]); cands = []
 sun_alt = sk.sun_alt(top, t)
 for n, (ra, dec, mag, col) in STARS.items():
  a, z = altaz(obs, t, ra, dec)
  if a > 5 and mag < 1.7: cands.append({"name": n, "kind": "star", "alt": a, "az": z, "mag": mag, "moving": False,
    "confirm": f"it twinkles, looks {col}, and keeps its place among the other stars, drifting slowly west over the hours"})
 for p in sk.planets_now(top, t):
  if p["alt"] > 2: cands.append({**p, "kind": "planet", "moving": False, "confirm": p["confirm"]})
 m = sk.moon_now(top, t)
 if m["alt"] > -1: cands.append({"name": "the Moon", "kind": "moon", "alt": m["alt"], "az": m["az"], "mag": -10, "moving": False, "phase": m["phase"], "confirm": f"{m['phase']}, {m['illum']}% lit"})
 if sun_alt < -4:
  for s in sk.sats_now(top, t):
   s["confirm"] = (f"it moves steadily, without blinking, toward the {C.compass(s['fade_az'])} and should " + ("fade into Earth's shadow" if s["fade_reason"] == "enters Earth's shadow" else "sink out of view") + f" there in about {max(1, round(s['fade_in_min']))} minute" + ("s" if round(s['fade_in_min']) > 1 else "")
    if s.get("fade_in_min") is not None else f"it moves steadily, without blinking, toward the {C.compass(s['to_az'])}")
   cands.append({**s, "kind": "satellite", "moving": True})
 dz = C.parse_dir(dirn) if dirn else None
 for c in cands:
  sc = 0.0
  if dz is not None: d = abs((c["az"] - dz + 180) % 360 - 180); sc -= d / 15
  if alt is not None: sc -= abs(c["alt"] - alt) / 12
  if moving is not None: sc += 3 if c["moving"] == moving else -6
  if bright == "very": sc -= max(0, c["mag"] + 0.5)
  elif bright == "faint": sc -= max(0, 1 - c["mag"]) / 2
  else: sc -= max(0, c["mag"]) / 2
  c["score"] = sc; c["where"] = C.where(c["az"], c["alt"])
 cands.sort(key=lambda c: -c["score"]); top = cands[:4]
 for i, c in enumerate(top):
  gap = c["score"] - (top[i + 1]["score"] if i + 1 < len(top) else c["score"] - 5)
  c["confidence"] = ("high" if gap > 2.5 and dz is not None else "medium" if gap > 1 else "low") if i == 0 else "alternative"
  for k in ("alt", "az", "mag", "score"): c[k] = round(c[k], 1)
 return {"at_local": when.astimezone(tzz).strftime("%a %b %d, %I:%M %p ") + C.tzabbr(when.astimezone(tzz)), "location": loc["label"],
   "sun_alt": round(sun_alt, 1), "candidates": top, "text": answer(top),
   "note": "Matched by location and time only. Blinking red/green lights are aircraft, which I can't track."}
def main(argv):
 import sky as S
 ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["now", "cotw", "showers"]); ap.add_argument("--place"); ap.add_argument("--photo")
 ap.add_argument("--dir"); ap.add_argument("--alt", type=float); ap.add_argument("--moving", choices=["yes", "no"]); ap.add_argument("--bright", choices=["very", "normal", "faint"])
 ap.add_argument("--at", help="local time HH:MM today, or ISO datetime"); a = ap.parse_args(argv)
 loc = C.resolve(a.place, a.photo) if (a.place or a.photo) else C.active()
 if not loc or "error" in loc: print(json.dumps({"error": (loc or {}).get("error", "no location set")})); return
 tzz = ZoneInfo(loc["tz"]); when = datetime.now(tzz)
 if a.photo and loc.get("photo_taken") and not a.at:
  try: when = datetime.strptime(loc["photo_taken"][:19], "%Y:%m:%d %H:%M:%S").replace(tzinfo=tzz)
  except ValueError: pass
 if a.at: when = datetime.fromisoformat(a.at).replace(tzinfo=tzz) if "T" in a.at or "-" in a.at else datetime.combine(when.date(), datetime.strptime(a.at, "%H:%M").time(), tzz)
 sk = S.Sky()
 if a.cmd == "now": print(json.dumps(identify(sk, loc, when, a.dir, a.alt, None if a.moving is None else a.moving == "yes", a.bright), indent=1, default=str))
 elif a.cmd == "cotw": print(json.dumps(cotw(sk, loc, when), indent=1))
 else: import events as E; print(json.dumps(E.showers_near(when.date(), 30), indent=1))
if __name__ == "__main__": main(sys.argv[1:])
