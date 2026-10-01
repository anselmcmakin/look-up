# look-up v2 | tonight.py: one night's sky for the user's hours: windows (sunset/dark/predawn keywords), passes, moon, planets, daytime sights, meteors, aurora, comets, eclipses, gear extras.
import math, os, sys
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C, events as E
from sky import PLAN, UTC
def resolve(sk, loc, d, cfg):
 """The user's windows for the night of d as local datetimes. Clock times before noon belong to the next morning."""
 tz = ZoneInfo(loc["tz"]); top = sk.observer(loc); sun = sk.sun_times(top, d, tz); base = datetime.combine(d, datetime.min.time(), tz)
 def at(v):
  if v == "sunset": return sun.get("sunset") or base + timedelta(hours=20)
  if v == "dark": return sun.get("astro_dusk") or sun.get("nautical_dusk") or sun.get("sunset") or base + timedelta(hours=21)
  if v == "sunrise": return sun.get("sunrise") or base + timedelta(hours=30)
  if v == "predawn": return (sun.get("sunrise") or base + timedelta(hours=30)) - timedelta(minutes=100)
  h, m = map(int, v.split(":")); return base + timedelta(days=1 if h < 12 else 0, hours=h, minutes=m)
 out = []
 for w in cfg["windows"]:
  st, en = at(w["start"]), at(w["end"])
  if en <= st: en = st + timedelta(hours=1)  # e.g. sunset after the end time in high-latitude summer
  out.append((st, en))
 return sorted(out), sun, top
def tonight(sk, loc, cfg, d=None, now=None):
 tz = ZoneInfo(loc["tz"]); now = now or datetime.now(tz); d = d or now.date(); wins, sun, top = resolve(sk, loc, d, cfg)
 cl = sk.clouds(loc); ev = []; o = sk.earth + top; g = E.rank(cfg); PL = dict(PLAN)
 T = sk.ts.from_datetimes([t for st, en in wins for t in (st + timedelta(minutes=10 * i) for i in range(int((en - st).total_seconds() // 600) + 1))])
 sa = sk.sun_alt(top, T); dts = [x.astimezone(tz) for x in T.utc_datetime()]
 dk = [t for t, a in zip(dts, sa) if a < -12] or [t for t, a in zip(dts, sa) if a < -6]
 mid = dk[len(dk) // 2] if dk else dts[len(dts) // 2]; tm = sk.ts.from_datetime(mid)
 for st, en in wins:
  ev += sk.passes(top, sk.ts.from_datetime(st), sk.ts.from_datetime(en), cfg); ev += sk.rockets(loc, st.astimezone(UTC), en.astimezone(UTC))
 mo = sk.moon_now(top, tm); pl = sk.planets_now(top, tm); best = {}
 for nm, key in PLAN:  # best moment per bright planet across the windows
  a, z, _ = o.at(T).observe(sk.eph[key]).apparent().altaz(); ok = (a.degrees > 10) & (sa < (-3 if nm in ("Venus", "Mercury") else -8))
  p = next(x for x in pl if x["name"] == nm)
  if ok.any() and p["mag"] < (0.5 if nm == "Mercury" else 1.6):
   i = int(np.argmax(np.where(ok, a.degrees, -99))); f = int(np.argmax(ok))
   ev.append({"id": f"planet-{nm}-{d:%Y%m%d}", "kind": "planet", "name": nm, "mag": p["mag"], "start_utc": dts[f].astimezone(UTC).isoformat(), "peak_utc": dts[i].astimezone(UTC).isoformat(),
    "start": {"az": round(z.degrees[f]), "alt": round(a.degrees[f])}, "peak": {"az": round(z.degrees[i]), "alt": round(a.degrees[i])}, "confirm": p["confirm"]})
  day = (sa > -0.833) & (a.degrees > 15)
  if nm == "Venus" and day.any() and p["elong"] > 25 and p["mag"] < -3.9:
   i = int(np.argmax(np.where(day, a.degrees, -99)))
   ev.append({"id": f"dayvenus-{d:%Y%m%d}", "kind": "dayvenus", "name": "Venus in daylight", "mag": p["mag"], "elong": p["elong"], "start_utc": dts[i].astimezone(UTC).isoformat(),
    "peak_utc": dts[i].astimezone(UTC).isoformat(), "peak": {"az": round(z.degrees[i]), "alt": round(a.degrees[i])}})
 ma, mz, _ = o.at(T).observe(sk.moon).apparent().altaz(); dm = (sa > -0.833) & (ma.degrees > 15)
 if dm.any():
  i = int(np.argmax(np.where(dm, ma.degrees, -99))); ph, il = sk.phase(T[i])
  if 8 <= il <= 95: ev.append({"id": f"daymoon-{d:%Y%m%d}", "kind": "daymoon", "name": "Daytime moon", "phase": ph, "illum": il, "start_utc": dts[i].astimezone(UTC).isoformat(),
    "peak_utc": dts[i].astimezone(UTC).isoformat(), "peak": {"az": round(mz.degrees[i]), "alt": round(ma.degrees[i])}})
 vis_pl = [p for p in pl if p["alt"] > 8]; ob = o.at(tm)
 for i, p in enumerate(vis_pl):  # close pairings at mid-evening
  pp = ob.observe(sk.eph[PL[p["name"]]])
  pairs = ([("Moon", ob.observe(sk.moon), 6)] if mo["alt"] > 3 else []) + [(q["name"], ob.observe(sk.eph[PL[q["name"]]]), 4) for q in vis_pl[i + 1:]]
  for qn, qq, lim in pairs:
   sep = pp.separation_from(qq).degrees
   if sep < lim: ev.append({"id": f"conj-{qn}-{p['name']}-{d:%Y%m%d}", "kind": "conjunction", "name": f"{'The Moon' if qn == 'Moon' else qn} and {p['name']}", "sep": round(sep, 1),
     "start_utc": mid.astimezone(UTC).isoformat(), "peak_utc": mid.astimezone(UTC).isoformat(), "peak": {"az": round(p["az"]), "alt": round(p["alt"])}})
 import stars as SX
 for sh in E.showers_near(d, 1):
  if not (sh["days_from_peak"] in (0, 1) or (sh["days_from_peak"] == -1 and sh["zhr"] >= 50)): continue  # peak night, night before, or night after a big one
  ra, dc = sh["radiant"]; hrs = []
  for h in range(0, 15):
   tt = datetime.combine(d, datetime.min.time(), tz) + timedelta(hours=17 + h); t1 = sk.ts.from_datetime(tt); a, z = SX.altaz(o, t1, ra, dc)
   if sk.sun_alt(top, t1) < -15 and a > 10: hrs.append((tt, a, z, sk.moon_now(top, t1)))
  if not hrs: continue
  b = max(hrs, key=lambda x: x[1]); good = [x[0] for x in hrs if x[1] > 30] or [b[0]]; m = b[3]
  mf = 1 - 0.7 * m["illum"] / 100 if m["alt"] > 0 else 1.0; dark = sh["zhr"] * math.sin(math.radians(b[1])) * mf
  ev.append({"id": f"meteor-{sh['name'].replace(' ', '')}-{d:%Y%m%d}", "kind": "meteor", "name": sh["name"], "zhr": sh["zhr"], "major": sh["zhr"] >= 50,
   "days_from_peak": sh["days_from_peak"], "start_utc": good[0].astimezone(UTC).isoformat(), "peak_utc": b[0].astimezone(UTC).isoformat(),
   "best_from_local": good[0].isoformat(), "best_to_local": (good[-1] + timedelta(hours=1)).isoformat(), "peak": {"az": round(b[2]), "alt": round(b[1])},
   "moon_illum": m["illum"], "moon_up": m["alt"] > 0, "rate_dark": max(1, round(dark)), "rate_suburban": max(1, round(dark / 4)), "parent": sh["parent"], "note": sh["note"],
   "in_window": any(st < good[-1] + timedelta(hours=1) and good[0] < en for st, en in wins)})
 need, gm = sk.kp_needed(loc); kps = [k for k in sk.kp() if any(st - timedelta(hours=3) <= k[0] <= en for st, en in wins)]
 if kps and sun.get("nautical_dusk"):
  mx = max(kps, key=lambda k: k[1]); phone = g == 0 and need - 1 <= mx[1] < need
  if mx[1] >= need or phone:
   ev.append({"id": f"aurora-{d:%Y%m%d}", "kind": "aurora", "name": "Aurora chance", "kp": mx[1], "kp_needed": need, "phone_only": phone, "geomag_lat": gm,
    "start_utc": max(mx[0], (sun.get("astro_dusk") or sun["nautical_dusk"]).astimezone(UTC)).isoformat(), "peak_utc": mx[0].isoformat(), "peak": {"az": 0 if loc["lat"] >= 0 else 180, "alt": 10}, "major": not phone})
 if cfg["alerts"].get("comets", True) and dk:
  for c in E.comets(sk, loc, tm, E.LIMIT[g]):
   if c["alt"] > 10: ev.append({"id": f"comet-{c['name'].split('(')[0].strip().replace('/', '').replace(' ', '')}-{d:%Y%m%d}", "kind": "comet", **c, "start_utc": mid.astimezone(UTC).isoformat(),
     "peak_utc": mid.astimezone(UTC).isoformat(), "peak": {"az": c["az"], "alt": c["alt"]}})
 if cfg["alerts"].get("eclipses", True):
  t0 = datetime.combine(d, datetime.min.time(), tz) + timedelta(hours=6)
  for x in E.eclipses(sk, loc, t0.astimezone(UTC), (t0 + timedelta(hours=30)).astimezone(UTC)):
   lo = x["local"]; pk = lo.get("max_utc") or x["greatest_utc"]
   ev.append({"id": f"eclipse-{x['kind']}-{d:%Y%m%d}", "kind": "eclipse", "name": f"{(lo.get('local_type') or x['type']).capitalize()} {x['kind']} eclipse", "eclipse": x["kind"], "type": lo.get("local_type") or x["type"],
    "major": x["type"] != "penumbral", "start_utc": lo.get("start_utc") or pk, "peak_utc": pk, "end_utc": lo.get("end_utc"), "local": lo,
    "peak": {"az": lo.get("sun_az_at_max", lo.get("moon_az_at_max")), "alt": lo.get("sun_alt_at_max", lo.get("moon_alt_at_max"))}})
 moonless = bool(mo["alt"] < 0 or mo["illum"] < 30)
 ex = E.extras(sk, loc, tm, cfg, moonless) if dk else []
 seen = set(); out = []
 for e in sorted(ev, key=lambda e: e["start_utc"]):
  if e["id"] in seen: continue
  seen.add(e["id"]); out.append(e); pt = sk.ts.from_datetime(datetime.fromisoformat(e["peak_utc"]))
  e["light"], e["sun_alt"] = sk.light(top, pt); e["cloud"] = sk.cloud_at(cl, datetime.fromisoformat(e["peak_utc"]))
  e["clear"] = e["cloud"] is None or e["cloud"] <= cfg["cloud"]["ok"]
  for k in ("start_utc", "peak_utc", "end_utc"):
   if e.get(k): e[k.replace("_utc", "_local")] = datetime.fromisoformat(e[k]).astimezone(tz).isoformat()
 hrs = [sk.cloud_at(cl, st + timedelta(hours=h)) for st, en in wins for h in range(0, int((en - st).total_seconds() // 3600) + 1)]
 hrs = [h for h in hrs if h is not None]; avg = round(sum(hrs) / len(hrs)) if hrs else None
 wx = {"avg_cloud": avg, "min_cloud": min(hrs) if hrs else None, "verdict": "unknown" if avg is None else "clear" if avg <= cfg["cloud"]["ok"] else "cloudy" if avg >= cfg["cloud"]["bad"] else "partly cloudy"}
 mr = [{"at_local": x[0].astimezone(tz).isoformat(), "what": x[1], "dir": C.compass(x[2], True)} for x in sk.rise_set(top, sk.moon, sk.ts.from_datetime(wins[0][0] - timedelta(hours=8)))]
 return {"location": {k: loc.get(k) for k in ("label", "lat", "lon", "tz", "is_travel")}, "date": d.isoformat(), "gear": cfg.get("gear", "eye"),
  "windows": [[st.isoformat(), en.isoformat()] for st, en in wins], "window": [wins[0][0].isoformat(), wins[-1][1].isoformat()],
  "sun": {k: v.isoformat() for k, v in sun.items()}, "dark_from": dk[0].isoformat() if dk else None, "mid": mid.isoformat(), "weather": wx,
  "moon": {**{k: (round(v) if isinstance(v, float) else v) for k, v in mo.items()}, "at_local": mid.isoformat(), "where": C.where(mo["az"], mo["alt"]), "rise_set": mr},
  "moonless": moonless, "extras": ex, "events": out, "data_notes": sk.data_notes, "computed_at": now.isoformat()}
