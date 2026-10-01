# look-up v2 | sky.py: sky engine. Satellite passes (CelesTrak GP + skyfield), moon, planets, NOAA Kp, Open-Meteo clouds, rockets (LL2).
import json, os, sys, math, argparse
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C
CT = "https://celestrak.org/NORAD/elements/gp.php?GROUP={}&FORMAT={}"
STD = {25544: -1.8, 48274: 0.4, 20580: 2.2}  # standard mag at 1000 km, half lit (ISS, Tiangong, Hubble); tuned vs heavens-above
NICK = {25544: "the ISS", 48274: "China's Tiangong station", 20580: "the Hubble Space Telescope"}
PLAN = [("Mercury", "mercury"), ("Venus", "venus"), ("Mars", "mars"), ("Jupiter", "jupiter barycenter"), ("Saturn", "saturn barycenter")]
PCONF = {"Venus": "it is far brighter than any star, shines steadily, and always stays fairly close to where the Sun set or will rise",
 "Jupiter": "it is very bright, steady and cream-colored, and binoculars held still show up to four of its moons in a line",
 "Mars": "it shines steadily with a clear orange-red color", "Saturn": "it shines steadily with a pale gold color, and a small telescope shows its rings",
 "Mercury": "it is a steady point low in the twilight, visible for less than an hour"}
UTC = timezone.utc
class Sky:
 def __init__(s):
  from skyfield.api import Loader
  L = Loader(C.D + "/data", verbose=False); s.ts = L.timescale(); s.eph = L("de421.bsp")
  s.sun, s.moon, s.earth = s.eph["sun"], s.eph["moon"], s.eph["earth"]; s._sats = None; s.data_notes = []
 def observer(s, loc):
  from skyfield.api import wgs84
  return wgs84.latlon(loc["lat"], loc["lon"], elevation_m=loc.get("elev", 100))
 def sun_alt(s, top, t): return (s.earth + top).at(t).observe(s.sun).apparent().altaz()[0].degrees
 # ---------- satellites ----------
 def sats(s):
  if s._sats is not None: return s._sats
  from skyfield.iokit import parse_tle_file
  from skyfield.api import EarthSatellite
  out = {}
  for g, df in (("stations", 3.5), ("visual", 3.5)):
   try:
    p, m = C.fetch(CT.format(g, "tle"), max_age=8 * 3600, min_age=2 * 3600, kind="tle")
    if m["source"] == "stale-cache": s.data_notes.append(f"CelesTrak {g}: using {m['age_min'] // 60}h-old data ({m.get('error')})")
    for x in parse_tle_file(open(p, "rb"), s.ts):
     n = x.model.satnum
     if g == "stations" and n not in STD: continue  # only the crewed stations from this group
     out[n] = {"sat": x, "std": STD.get(n, df), "kind": "iss" if n == 25544 else "station" if n in STD else "satellite", "name": NICK.get(n, x.name.strip().title())}
   except RuntimeError as e: s.data_notes.append(f"CelesTrak {g} unavailable: {e}")
  try:  # Starlink trains: only launches from the last ~5 days, one representative object per launch
   cat, _ = C.fetch("https://celestrak.org/satcat/records.php?GROUP=last-30-days&FORMAT=json", max_age=12 * 3600, min_age=2 * 3600)
   now = datetime.now(UTC).date(); fresh = {}
   for r in cat:
    if "STARLINK" in r.get("OBJECT_NAME", "") and r.get("LAUNCH_DATE") and (now - date.fromisoformat(r["LAUNCH_DATE"])).days <= int(os.environ.get("LOOKUP_STARLINK_DAYS", 5)):
     fresh.setdefault(r["OBJECT_ID"][:8], r["LAUNCH_DATE"])
   if fresh:
    gp, _ = C.fetch(CT.format("last-30-days", "json"), max_age=8 * 3600, min_age=2 * 3600)
    for lid, ld in fresh.items():
     grp = sorted([r for r in gp if r["OBJECT_ID"].startswith(lid)], key=lambda r: r["OBJECT_ID"])
     if grp:
      x = EarthSatellite.from_omm(s.ts, grp[len(grp) // 2])
      out[x.model.satnum] = {"sat": x, "std": 3.0, "kind": "starlink", "name": f"Starlink train (launched {ld}, {len(grp)} satellites)", "launch": ld}
  except RuntimeError as e: s.data_notes.append(f"Starlink launch list unavailable: {e}")
  s._sats = out; return out
 def mag(s, std, sat_km, obs_km, sun_km):
  r = np.linalg.norm(obs_km - sat_km, axis=0); a, b = sun_km - sat_km, obs_km - sat_km
  ph = np.arccos(np.clip(np.sum(a * b, axis=0) / (np.linalg.norm(a, axis=0) * r), -1, 1))
  f = (np.sin(ph) + (math.pi - ph) * np.cos(ph)) / math.pi
  return std + 5 * np.log10(r / 1000) - 2.5 * np.log10(np.maximum(f * math.pi, 1e-4))
 def passes(s, top, t0, t1, cfg, kinds=None):
  out = []; obs = cfg.get("obstructions") or []; mp = cfg["min_peak_alt"]
  for n, o in s.sats().items():
   if kinds and o["kind"] not in kinds: continue
   sat = o["sat"]
   try: tt, ev = sat.find_events(top, t0, t1, altitude_degrees=10.0)
   except Exception: continue
   i = 0
   while i < len(ev):
    if ev[i] != 0: i += 1; continue
    j = i + 1
    while j < len(ev) and ev[j] != 2: j += 1
    if j >= len(ev): break
    tr, tset = tt[i], tt[j]; i = j + 1
    k = max(8, int((tset.tt - tr.tt) * 86400 / 5)); T = s.ts.tt_jd(np.linspace(tr.tt, tset.tt, k))
    alt, az, dist = (sat - top).at(T).altaz(); alt, az = alt.degrees, az.degrees
    lit = sat.at(T).is_sunlit(s.eph); sa = s.sun_alt(top, T)
    vis = lit & (sa < -6) & (alt >= 10)
    if not vis.any(): continue
    clear = vis & np.array([not C.blocked(z, a, obs) for z, a in zip(az, alt)])
    idx = np.where(vis)[0]; a0, a1 = idx[0], idx[-1]
    m = s.mag(o["std"], sat.at(T).position.km, top.at(T).position.km, (s.sun - s.earth).at(T).position.km)
    pk = a0 + int(np.argmax(np.where(vis[a0:a1 + 1], alt[a0:a1 + 1], -99)))
    need = mp["iss"] if o["kind"] in ("iss", "station") else mp["other"]
    if alt[pk] < need: continue
    dts = T.utc_datetime(); step = max(1, (a1 - a0) // 24)
    e = {"id": f"{o['kind']}-{n}-{dts[a0].strftime('%Y%m%d%H%M')}", "kind": o["kind"], "norad": n, "name": o["name"],
     "start_utc": dts[a0].isoformat(), "peak_utc": dts[pk].isoformat(), "end_utc": dts[a1].isoformat(), "duration_s": int((dts[a1] - dts[a0]).total_seconds()),
     "start": {"az": round(az[a0]), "alt": round(alt[a0])}, "peak": {"az": round(az[pk]), "alt": round(alt[pk])}, "end": {"az": round(az[a1]), "alt": round(alt[a1])},
     "mag": round(float(np.min(m[vis])), 1), "fades_in_shadow": bool(not lit[min(a1 + 1, len(lit) - 1)] and alt[a1] > 12),
     "path": [[round(float(az[q]), 1), round(float(alt[q]), 1)] for q in range(a0, a1 + 1, step)] + [[round(float(az[a1]), 1), round(float(alt[a1]), 1)]],
     "blocked": None if clear.any() and alt[clear].max() >= need else (C.blocked(az[pk], alt[pk], obs) or "low behind obstructions")}
    if o.get("launch"): e["launch"] = o["launch"]
    out.append(e)
  return sorted(out, key=lambda e: e["start_utc"])
 def sats_now(s, top, t):
  out = []; T = s.ts.tt_jd(t.tt + np.arange(0, 601, 15) / 86400)
  for n, o in s.sats().items():
   sat = o["sat"]; a, z, _ = (sat - top).at(t).altaz()
   if a.degrees < 8: continue
   if not sat.at(t).is_sunlit(s.eph): continue
   al, az, _ = (sat - top).at(T).altaz(); lit = sat.at(T).is_sunlit(s.eph); ok = lit & (al.degrees > 8)
   gone = int(np.argmin(ok)) if not ok.all() else None
   m = s.mag(o["std"], sat.at(t).position.km.reshape(3, 1), top.at(t).position.km.reshape(3, 1), (s.sun - s.earth).at(t).position.km.reshape(3, 1))[0]
   if m > 4.5: continue
   out.append({"name": o["name"], "norad": n, "alt": a.degrees, "az": z.degrees, "mag": float(m), "to_az": float(az.degrees[min(8, len(T) - 1)]),
     "fade_in_min": round(gone * 15 / 60, 1) if gone else None, "fade_az": float(az.degrees[gone - 1]) if gone else None,
     "fade_reason": None if gone is None else ("enters Earth's shadow" if not lit[gone] else "sets")})
  return out
 # ---------- moon, planets ----------
 def phase(s, t):
  from skyfield import almanac
  d = almanac.moon_phase(s.eph, t).degrees; il = round(100 * almanac.fraction_illuminated(s.eph, "moon", t))
  nm = ("new moon" if d < 8 or d > 352 else "waxing crescent" if d < 82 else "first quarter" if d < 98 else "waxing gibbous" if d < 172
   else "full moon" if d < 188 else "waning gibbous" if d < 262 else "last quarter" if d < 278 else "waning crescent")
  return nm, il
 def moon_now(s, top, t):
  a, z, _ = (s.earth + top).at(t).observe(s.moon).apparent().altaz(); nm, il = s.phase(t)
  return {"alt": a.degrees, "az": z.degrees, "phase": nm, "illum": il}
 def rise_set(s, top, body, t0, hours=30):
  from skyfield import almanac
  f = almanac.risings_and_settings(s.eph, body, top); tt, y = almanac.find_discrete(t0, s.ts.tt_jd(t0.tt + hours / 24), f)
  return [(x.utc_datetime(), "rise" if v else "set", (s.earth + top).at(x).observe(body).apparent().altaz()[1].degrees) for x, v in zip(tt, y)]
 def planets_now(s, top, t):
  from skyfield.magnitudelib import planetary_magnitude
  out = []; ob = (s.earth + top).at(t)
  for nm, k in PLAN:
   ast = ob.observe(s.eph[k]); a, z, _ = ast.apparent().altaz()
   try: mg = float(planetary_magnitude(ast))
   except Exception: mg = {"Venus": -4, "Jupiter": -2.3, "Mars": 0.5, "Saturn": 0.7, "Mercury": 0}[nm]
   el = ast.separation_from(ob.observe(s.sun)).degrees
   out.append({"name": nm, "alt": a.degrees, "az": z.degrees, "mag": round(mg, 1), "elong": round(el), "confirm": PCONF[nm]})
  return out
 # ---------- sun: day, twilight, night ----------
 def sun_times(s, top, d, tz):
  """Sunset/dusk on the evening of d and dawn/sunrise the next morning (local datetimes). Missing keys = sun never got there (polar)."""
  from skyfield import almanac
  t0 = s.ts.from_datetime(datetime.combine(d, datetime.min.time(), tz) + timedelta(hours=12)); t1 = s.ts.tt_jd(t0.tt + 1)
  f = almanac.dark_twilight_day(s.eph, top); tt, yy = almanac.find_discrete(t0, t1, f); prev = int(f(t0)); out = {}
  names = {(4, 3): "sunset", (3, 2): "civil_dusk", (2, 1): "nautical_dusk", (1, 0): "astro_dusk", (0, 1): "astro_dawn", (1, 2): "nautical_dawn", (2, 3): "civil_dawn", (3, 4): "sunrise"}
  for x, y in zip(tt, yy):
   n = names.get((prev, int(y)))
   if n: out.setdefault(n, x.utc_datetime().astimezone(tz))
   prev = int(y)
  return out
 def light(s, top, t):
  a = float(s.sun_alt(top, t)); return ("daytime" if a > -0.833 else "twilight" if a > -18 else "night"), round(a, 1)
 # ---------- outside data ----------
 def clouds(s, loc):
  u = f"https://api.open-meteo.com/v1/forecast?latitude={loc['lat']:.2f}&longitude={loc['lon']:.2f}&hourly=cloud_cover&forecast_days=8&timezone=GMT"
  try: r, m = C.fetch(u, max_age=3600)
  except RuntimeError as e: s.data_notes.append(f"cloud forecast unavailable: {e}"); return {}
  return {datetime.fromisoformat(t).replace(tzinfo=UTC): v for t, v in zip(r["hourly"]["time"], r["hourly"]["cloud_cover"]) if v is not None}
 def cloud_at(s, cl, dt):
  if not cl: return None
  k = dt.astimezone(UTC).replace(minute=0, second=0, microsecond=0) + (timedelta(hours=1) if dt.minute >= 30 else timedelta())
  return cl.get(k)
 def kp(s):
  try: r, _ = C.fetch("https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json", max_age=3 * 3600)
  except RuntimeError as e: s.data_notes.append(f"NOAA Kp forecast unavailable: {e}"); return []
  if r and isinstance(r[0], list): r = [dict(zip(r[0], x)) for x in r[1:]]
  return [(datetime.fromisoformat(x["time_tag"]).replace(tzinfo=UTC), float(x["kp"]), x["observed"]) for x in r]
 def kp_needed(s, loc):
  la, lo, pla, plo = map(math.radians, (loc["lat"], loc["lon"], 80.8, -72.7))
  gm = math.degrees(math.asin(math.sin(la) * math.sin(pla) + math.cos(la) * math.cos(pla) * math.cos(lo - plo)))
  return round(min(9.0, max(0.5, 5 + (53.5 - abs(gm)) / 3.0)), 1), round(gm, 1)  # calibrated to NOAA viewlines: ~Kp5 Minneapolis, ~Kp8+ near 35N
 def rockets(s, loc, t0, t1, max_age=6 * 3600):
  try: r, _ = C.fetch("https://ll.thespacedevs.com/2.3.0/launches/upcoming/?limit=25&mode=normal", max_age=max_age, min_age=900)
  except RuntimeError as e: s.data_notes.append(f"launch schedule unavailable: {e}"); return []
  out = []
  for x in r.get("results") or []:
   try:
    net = datetime.fromisoformat(x["net"].replace("Z", "+00:00")); pad = x.get("pad") or {}; pla, plo = float(pad["latitude"]), float(pad["longitude"])
   except Exception: continue
   if not (t0 <= net <= t1) or (x.get("status") or {}).get("abbrev") not in ("Go", "TBC"): continue
   la1, lo1, la2, lo2 = map(math.radians, (loc["lat"], loc["lon"], pla, plo))
   dist = 6371 * 2 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))
   if dist > 1100 or s.sun_alt(s.observer(loc), s.ts.from_datetime(net)) > -4: continue  # too far, or daylight
   brg = math.degrees(math.atan2(math.sin(lo2 - lo1) * math.cos(la2), math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1))) % 360
   out.append({"id": f"rocket-{x['id'][:8]}-{net.strftime('%Y%m%d%H%M')}", "kind": "rocket", "name": x.get("name"), "start_utc": net.isoformat(), "peak_utc": net.isoformat(),
    "end_utc": (net + timedelta(minutes=6)).isoformat(), "dist_km": round(dist), "bearing": round(brg), "status": x["status"]["abbrev"],
    "pad": pad.get("name"), "start": {"az": round(brg), "alt": 2 if dist > 400 else 10}, "peak": {"az": round(brg), "alt": max(2, round(math.degrees(math.atan2(140 - dist ** 2 / 12742, dist))))}})
  return out
