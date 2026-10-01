# look-up v2 | events.py: viewing gear, meteor showers, eclipses 2026-2030 (local circumstances computed), bright comets (MPC), binocular/telescope targets.
import json, math, os, sys, argparse
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C
UTC = timezone.utc
GEAR = {"eye": 0, "binoculars": 1, "telescope": 2}; GNAME = {0: "naked eye or phone", 1: "binoculars", 2: "a telescope"}
LIMIT = {0: 4.0, 1: 6.5, 2: 9.0}  # roughly what each setup shows from a backyard
COMET_ALERT = {0: 4.0, 1: 6.0, 2: 9.0}
def rank(cfg): return GEAR.get(cfg.get("gear", "eye"), 0)
def need(mag):
 """Gear rank needed to see an object of this magnitude."""
 return 0 if mag <= LIMIT[0] else 1 if mag <= LIMIT[1] else 2
# meteor showers: (name, month, day of the evening the peak night begins, ZHR, radiant RA h, Dec, parent, note)
SHOWERS = [("Quadrantids", 1, 2, 110, 15.3, 49, "asteroid 2003 EH1", "a sharp peak only a few hours long"),
 ("Lyrids", 4, 21, 18, 18.1, 34, "Comet Thatcher", "occasional bright fireballs"), ("Eta Aquariids", 5, 5, 50, 22.5, -1, "Halley's Comet", "best before dawn, better from the south"),
 ("Southern Delta Aquariids", 7, 29, 25, 22.7, -16, "Comet 96P/Machholz", "faint and steady"), ("Perseids", 8, 12, 100, 3.2, 58, "Comet Swift-Tuttle", "the summer favorite, lots of bright ones"),
 ("Draconids", 10, 8, 10, 17.5, 54, "Comet Giacobini-Zinner", "best in the evening, usually modest"), ("Orionids", 10, 20, 20, 6.3, 16, "Halley's Comet", "fast meteors, best after midnight"),
 ("Southern Taurids", 11, 4, 5, 3.5, 13, "Comet Encke", "slow, sometimes bright fireballs"), ("Northern Taurids", 11, 11, 5, 3.9, 22, "Comet Encke", "slow, sometimes bright fireballs"),
 ("Leonids", 11, 16, 15, 10.2, 22, "Comet Tempel-Tuttle", "fast meteors, best before dawn"), ("Geminids", 12, 13, 150, 7.5, 33, "asteroid 3200 Phaethon", "the year's best, good even before midnight"),
 ("Ursids", 12, 21, 10, 14.5, 76, "Comet Tuttle", "modest, near the Little Dipper")]
def showers_near(d, days=1):
 out = []
 for s in SHOWERS:
  for y in (d.year - 1, d.year, d.year + 1):
   pk = date(y, s[1], s[2]); dd = (pk - d).days
   if -days <= dd <= days: out.append({"name": s[0], "peak": pk.isoformat(), "days_from_peak": dd, "zhr": s[3], "radiant": (s[4], s[5]), "parent": s[6], "note": s[7]})
 return out
# eclipses 2026-2030: (greatest eclipse UTC, kind, type, where it's generally visible). Local circumstances are computed, not taken from here.
ECLIPSES = [("2026-02-17T12:12", "solar", "annular", "Antarctica; partial in far southern Africa and South America"),
 ("2026-03-03T11:33", "lunar", "total", "East Asia, Australia, the Pacific, the Americas"), ("2026-08-12T17:46", "solar", "total", "Greenland, Iceland, northern Spain; partial in Europe, North Africa, northeast North America"),
 ("2026-08-28T04:13", "lunar", "partial", "the Americas, Europe, Africa"), ("2027-02-06T16:00", "solar", "annular", "Chile, Argentina, the Atlantic, West Africa"),
 ("2027-02-20T23:13", "lunar", "penumbral", "the Americas, Europe, Africa, Asia"), ("2027-07-18T16:03", "lunar", "penumbral", "Asia, Australia, the Pacific"),
 ("2027-08-02T10:07", "solar", "total", "Spain, North Africa, Egypt, Arabia; partial in Europe, Africa, the Middle East"), ("2027-08-17T07:14", "lunar", "penumbral", "the Pacific, the Americas"),
 ("2028-01-12T04:13", "lunar", "partial", "the Americas, Europe, Africa"), ("2028-01-26T15:08", "solar", "annular", "Ecuador, Peru, Brazil, then Portugal and Spain at sunset"),
 ("2028-07-06T18:20", "lunar", "partial", "Europe, Africa, Asia, Australia"), ("2028-07-22T02:56", "solar", "total", "Australia (including Sydney), New Zealand"),
 ("2028-12-31T16:52", "lunar", "total", "Europe, Africa, Asia, Australia"), ("2029-01-14T17:13", "solar", "partial", "North America"),
 ("2029-06-12T04:06", "solar", "partial", "the Arctic, Scandinavia, northern Russia, Alaska, northern Canada"), ("2029-06-26T03:22", "lunar", "total", "the Americas, Europe, Africa, the Middle East"),
 ("2029-07-11T15:37", "solar", "partial", "southern Chile and Argentina"), ("2029-12-05T15:03", "solar", "partial", "southern South America, Antarctica"),
 ("2029-12-20T22:42", "lunar", "total", "the Americas, Europe, Africa, Asia"), ("2030-06-01T06:29", "solar", "annular", "North Africa, Greece, Turkey, Russia, northern Japan"),
 ("2030-06-15T18:33", "lunar", "partial", "Europe, Africa, Asia, Australia"), ("2030-11-25T06:51", "solar", "total", "Namibia, Botswana, South Africa, southern Australia"),
 ("2030-12-09T22:28", "lunar", "penumbral", "the Americas, Europe, Africa, Asia")]
def _overlap(d, r1, r2):
 if d >= r1 + r2: return 0.0
 if d <= abs(r1 - r2): return math.pi * min(r1, r2) ** 2
 a = r1 * r1 * math.acos((d * d + r1 * r1 - r2 * r2) / (2 * d * r1)) + r2 * r2 * math.acos((d * d + r2 * r2 - r1 * r1) / (2 * d * r2))
 return a - .5 * math.sqrt((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2))
def solar_local(sk, loc, tg):
 top = sk.observer(loc); o = sk.earth + top; T = sk.ts.from_datetimes([tg + timedelta(seconds=s) for s in range(-4 * 3600, 4 * 3600 + 1, 60)])
 su, mo = o.at(T).observe(sk.sun).apparent(), o.at(T).observe(sk.moon).apparent()
 sep = su.separation_from(mo).radians; rs = np.arcsin(696000 / su.distance().km); rm = np.arcsin(1737.4 / mo.distance().km); alt = su.altaz()[0].degrees
 vis = (sep < rs + rm) & (alt > -0.5)
 if not vis.any(): return {"visible": False}
 i = np.where(vis)[0]; k = i[int(np.argmin(sep[i]))]; d = T.utc_datetime()
 typ = "total" if rm[k] > rs[k] and sep[k] < rm[k] - rs[k] else "annular" if rs[k] > rm[k] and sep[k] < rs[k] - rm[k] else "partial"
 return {"visible": True, "local_type": typ, "start_utc": d[i[0]].isoformat(), "max_utc": d[k].isoformat(), "end_utc": d[i[-1]].isoformat(),
  "obscuration_pct": round(100 * _overlap(sep[k], rs[k], rm[k]) / (math.pi * rs[k] ** 2)), "sun_alt_at_max": round(float(alt[k])),
  "sun_az_at_max": round(float(su.altaz()[1].degrees[k])), "in_progress_at_sunrise": bool(alt[i[0]] < 2 and i[0] > 0 and alt[i[0] - 1] < -0.5),
  "in_progress_at_sunset": bool(alt[i[-1]] < 2 and i[-1] < len(alt) - 1 and alt[i[-1] + 1] < -0.5)}
def lunar_local(sk, loc, tg):
 top = sk.observer(loc); hrs = [-2, -1, 0, 1, 2]; T = sk.ts.from_datetimes([tg + timedelta(hours=h) for h in hrs])
 a, z, _ = (sk.earth + top).at(T).observe(sk.moon).apparent().altaz(); al = a.degrees
 return {"visible": bool((al[1:4] > 0).any()), "moon_alt_at_max": round(float(al[2])), "moon_az_at_max": round(float(z.degrees[2])),
  "up_hours_of_5": int((al > 0).sum()), "moonset_during": bool(al[0] > 0 and al[-1] < 0), "moonrise_during": bool(al[0] < 0 and al[-1] > 0)}
def eclipses(sk, loc, t0, t1, only_visible=True):
 out = []
 for g, kind, typ, where in ECLIPSES:
  tg = datetime.fromisoformat(g).replace(tzinfo=UTC)
  if not (t0 - timedelta(hours=5) <= tg <= t1 + timedelta(hours=5)): continue
  lo = solar_local(sk, loc, tg) if kind == "solar" else lunar_local(sk, loc, tg)
  if lo["visible"] or not only_visible: out.append({"kind": kind, "type": typ, "greatest_utc": tg.isoformat(), "where": where, "local": lo})
 return out
# bright comets from the MPC comet elements file (free; fetched at most every 3 days)
MPC = "https://www.minorplanetcenter.net/iau/MPCORB/CometEls.txt"
def comets(sk, loc, t, maxmag):
 from skyfield.keplerlib import _KeplerOrbit
 from skyfield.data.spice import inertial_frames
 from skyfield.constants import GM_SUN_Pitjeva_2005_km3_s2 as GM
 try: p, _ = C.fetch(MPC, max_age=3 * 86400, min_age=86400, kind="txt")
 except RuntimeError as e: sk.data_notes.append(f"comet list unavailable: {e}"); return []
 out = []; top = sk.observer(loc); o = (sk.earth + top).at(t); now = t.utc_datetime()
 for ln in open(p, encoding="latin-1"):
  try:
   y, mth, dy = int(ln[14:18]), int(ln[19:21]), float(ln[22:29]); q, e = float(ln[30:39]), float(ln[41:49]); H, K = float(ln[91:95]), float(ln[96:100])
   peri, node, inc, name = float(ln[51:59]), float(ln[61:69]), float(ln[71:79]), ln[102:158].strip()
  except ValueError: continue
  tp = datetime(y, mth, 1, tzinfo=UTC) + timedelta(days=dy - 1)
  if q > 3.5 or abs((tp - now).days) > 400 or H > 16: continue
  pp = q * 2 if e == 1 else q / (1 - e) * (1 - e * e)
  if e > 1.2: continue
  orb = _KeplerOrbit._from_periapsis(pp, e, inc, node, peri, sk.ts.tt(y, mth, dy), GM, 10, name); orb._rotation = inertial_frames["ECLIPJ2000"].T
  try:
   ast = o.observe(sk.sun + orb); r = float(np.linalg.norm(orb.at(t).position.au))
   dlt = ast.distance().au; m = H + 5 * math.log10(dlt) + 2.5 * K * math.log10(r)
  except Exception: continue
  if m > maxmag: continue
  a, z, _ = ast.apparent().altaz(); el = ast.separation_from(o.observe(sk.sun)).degrees
  out.append({"name": name, "mag": round(m, 1), "alt": round(a.degrees), "az": round(z.degrees), "elong": round(el), "r_au": round(r, 2), "delta_au": round(float(dlt), 2),
   "perihelion": tp.date().isoformat(), "gear": need(m)})
 return sorted(out, key=lambda c: c["mag"])
# binocular / telescope targets: (name, RA h, Dec, min gear rank, needs moonless sky, note)
TARGETS = [("the Pleiades", 3.79, 24.1, 1, False, "a tight little dipper of blue stars; binoculars show dozens"),
 ("the Andromeda Galaxy", 0.712, 41.27, 1, True, "a soft oval glow 2.5 million light-years away"), ("the Orion Nebula", 5.588, -5.39, 1, True, "a misty glow in Orion's sword; a telescope shows the four Trapezium stars"),
 ("the Double Cluster", 2.33, 57.13, 1, True, "two star clusters side by side between Perseus and Cassiopeia"), ("the Beehive Cluster", 8.67, 19.67, 1, True, "a swarm of stars in Cancer"),
 ("the Lagoon Nebula", 18.06, -24.38, 1, True, "a glowing cloud just above the Teapot's spout"), ("Mizar and Alcor", 13.399, 54.93, 1, False, "the bend of the Big Dipper's handle splits into two stars; a telescope splits Mizar again"),
 ("Albireo", 19.512, 27.96, 2, False, "a gold-and-blue double star at the head of Cygnus"), ("the Hercules Cluster", 16.695, 36.46, 2, True, "a ball of several hundred thousand stars"),
 ("the Ring Nebula", 18.893, 33.03, 2, True, "a tiny smoke ring between the two lower stars of Lyra")]
def extras(sk, loc, t, cfg, moonless):
 """What binoculars or a telescope add tonight at time t: targets, planet details, the moon's terminator."""
 g = rank(cfg); out = []
 if g == 0: return out
 import stars as SX
 o = sk.earth + sk.observer(loc); tg = []
 for p in sk.planets_now(sk.observer(loc), t):  # planet details first: they're the showpieces
  if p["alt"] < 15: continue
  if p["name"] == "Jupiter": out.append({"name": "Jupiter's moons", "alt": round(p["alt"]), "az": round(p["az"]), "gear": 1, "note": "up to four tiny points in a line beside the planet; they shift night to night"})
  if p["name"] == "Saturn" and g >= 2: out.append({"name": "Saturn's rings", "alt": round(p["alt"]), "az": round(p["az"]), "gear": 2, "note": "visible at even low power; look for the moon Titan nearby"})
  if p["name"] == "Venus" and g >= 1: out.append({"name": "Venus's phase", "alt": round(p["alt"]), "az": round(p["az"]), "gear": 1 if p["elong"] < 30 else 2, "note": "it shows a shape like a tiny moon"})
 m = sk.moon_now(sk.observer(loc), t)
 if m["alt"] > 15 and 12 <= m["illum"] <= 88: out.append({"name": "the Moon's terminator", "alt": round(m["alt"]), "az": round(m["az"]), "gear": 1, "note": "craters and mountains stand out in long shadows along the line between light and dark"})
 for n, ra, dec, mg, dark, note in TARGETS:
  if mg > g or (dark and not moonless): continue
  a, z = SX.altaz(o, t, ra, dec)
  if a > 25: tg.append({"name": n, "alt": round(a), "az": round(z), "gear": mg, "note": note})
 return out + sorted(tg, key=lambda x: -x["alt"])[:max(0, 6 - len(out))]
def main(argv):
 from sky import Sky
 ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["eclipses", "comets", "showers", "extras"]); ap.add_argument("--place"); ap.add_argument("--years", type=float, default=5); ap.add_argument("--all", action="store_true")
 a = ap.parse_args(argv); loc = C.resolve(a.place) if a.place else C.active(); sk = Sky(); now = datetime.now(UTC); cfg = C.cfg()
 if a.cmd == "eclipses": r = eclipses(sk, loc, now, now + timedelta(days=365 * a.years), not a.all)
 elif a.cmd == "comets": r = comets(sk, loc, sk.ts.from_datetime(now), LIMIT[rank(cfg)] + (3 if a.all else 0))
 elif a.cmd == "extras": r = extras(sk, loc, sk.ts.from_datetime(now), cfg, True)
 else: r = showers_near(now.date(), 60)
 print(json.dumps({"location": loc["label"], "result": r, "data_notes": sk.data_notes}, indent=1, default=str))
if __name__ == "__main__": main(sys.argv[1:])
