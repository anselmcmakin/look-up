# look-up v2 | highlight.py: "your first big one". Scans the next 7 (up to 14) nights for the single best sight, ranked by wow, weather-checked, with its one-shot.
import os, sys, json
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C, events as E
from sky import PLAN, UTC
# wow tiers (lower is better): 1 bright high ISS, 2 Starlink train, 3 meteor peak, 4 eclipse, 5 close pairing, 5.5 good ISS / high Tiangong pass, 6 bright planet, 6.5 ordinary station pass, 7 thin crescent, 8 constellation
# Generic satellites are deliberately never a highlight: faint, brief and easy to miss for a first-timer.
PLANET_WOW = {"Saturn": "It looks like a steady, golden star; even a small telescope at 25x or more shows its rings.",
 "Jupiter": "It is the brightest star-like point in that part of the sky, and steady binoculars show up to four of its large moons beside it.",
 "Venus": "It is the brightest object in the night sky after the Moon, and binoculars show its phase.",
 "Mars": "Look for a steady, orange-red point that does not twinkle.",
 "Mercury": "The innermost planet is rarely this easy to catch, so it is worth the effort."}
OUT_OF_HOURS = 2.5  # a sight outside the user's hours drops this many tiers
def _night(dt):
 return (dt - timedelta(days=1)).date() if dt.hour < 12 else dt.date()
def _when(dt, now):
 n, t0 = _night(dt), _night(now); h = C.hhmm(dt)
 if n == t0: return f"tonight at {h}" if dt.hour >= 12 else f"early tomorrow at {h}"
 if n == t0 + timedelta(days=1): return f"tomorrow night at {h}" if dt.hour >= 12 else f"{dt:%A} morning at {h}"
 return (f"{dt:%A}" if (n - t0).days < 7 else f"{dt:%A, %b} {dt.day}") + (f" at {h}" if dt.hour >= 12 else f" morning at {h}")
def candidates(sk, loc, cfg, now, days):
 from tonight import resolve
 tz = ZoneInfo(loc["tz"]); top = sk.observer(loc); o = sk.earth + top; out = []
 t0, t1 = sk.ts.from_datetime(now), sk.ts.from_datetime(now + timedelta(days=days)); wins = {}
 def inw(dt):
  n = _night(dt)
  if n not in wins: wins[n] = resolve(sk, loc, n, cfg)[0]
  return any(a <= dt <= b for a, b in wins[n])
 def add(tier, dt, kind, what, q=0.0, **kw): out.append({"tier": tier + (0 if inw(dt) else OUT_OF_HOURS), "at": dt, "kind": kind, "what": what, "q": q, "night": _night(dt).isoformat(), **kw})
 al = cfg["alerts"]; on = lambda k: (k in cfg["only"]) if cfg.get("only") else al.get(k, True)
 kinds = (["iss", "station"] if on("iss") else []) + (["starlink"] if on("starlink") else [])
 for e in sk.passes(top, t0, t1, cfg, kinds=kinds) if kinds else []:
  if e["blocked"]: continue
  dt = datetime.fromisoformat(e["start_utc"]).astimezone(tz); pk = e["peak"]
  if e["kind"] == "starlink": add(2, dt, "starlink", f"a fresh Starlink train, a line of dots moving together, rises in the {C.compass(e['start']['az'], True)}. Trains fade within days of launch, so treat this as a best estimate", e=e); continue
  hp = "almost directly overhead" if pk["alt"] >= 75 else f"high in the {C.compass(pk['az'], True)}" if pk["alt"] >= 55 else f"about halfway up in the {C.compass(pk['az'], True)}"
  br = "as bright as it ever gets" if e["mag"] <= -3.3 else "brighter than any star" if e["mag"] <= -2 else "as bright as the brightest stars" if e["mag"] <= -1 else "similar to a bright star"
  tg = e["kind"] == "station" and ("tiangong" in e["name"].lower() or "css" in e["name"].lower()); iss = e["kind"] == "iss"
  who = "the International Space Station" if iss else "China's Tiangong space station" if tg else f"the {e['name']}"
  tier = (1 if iss and e["mag"] <= -2 and pk["alt"] >= 45 else 5.5 if (iss and e["mag"] <= -1 and pk["alt"] >= 40) or (tg and e["mag"] <= -0.5 and pk["alt"] >= 45)
   else 6.5 if e["mag"] <= -1 else 9)
  add(tier, dt, "iss" if iss else "station", f"{who} passes {hp}, {br}", q=-e["mag"] + pk["alt"] / 30, e=e, fk={"kind": e["kind"], "name": e["name"]})
 d0 = _night(now)
 for i in range(days):
  d = d0 + timedelta(days=i); sun = sk.sun_times(top, d, tz)
  if not sun.get("nautical_dusk"): continue
  ev = max(sun["nautical_dusk"] + timedelta(minutes=30), now + timedelta(minutes=30)) if i == 0 else sun["nautical_dusk"] + timedelta(minutes=30)
  if ev.date() != d and ev.hour >= 3: continue
  t = sk.ts.from_datetime(ev); ob = o.at(t); pl = [p for p in sk.planets_now(top, t) if p["alt"] > 10 and p["mag"] < 1.6]
  mo = sk.moon_now(top, t)
  if on("meteors"):
   for sh in E.showers_near(d, 0):
    if sh["days_from_peak"] == 0 and sh["zhr"] >= 15: add(3, ev, "meteor", f"the {sh['name']} meteor shower reaches its peak", q=sh["zhr"] / 50, shower=sh["name"], fk={"kind": "meteor", "name": sh["name"]})
  if on("planets"):
   bod = {n: ob.observe(sk.eph[k]) for n, k in PLAN}
   for j, p in enumerate(pl):
    if mo["alt"] > 5:
     s = bod[p["name"]].separation_from(ob.observe(sk.moon)).degrees
     if s < 5: add(5, ev, "conjunction", f"the Moon appears close to {p['name']}, about {s:.0f}° apart, in the {C.compass(p['az'], True)}", q=5 - s, fk={"kind": "planet", "name": p["name"]})
    for p2 in pl[j + 1:]:
     s = bod[p["name"]].separation_from(bod[p2["name"]]).degrees
     if s < 3: add(5, ev, "conjunction", f"{p['name']} and {p2['name']} appear close together, about {s:.1f}° apart, in the {C.compass(p['az'], True)}", q=3 - s, fk={"kind": "planet", "name": p2["name"]})
   for p in pl:  # best-placed moment in the user's hours: sample through the evening
    if p["mag"] > 0.8: continue
    tries = [(ev + timedelta(minutes=m)) for m in (0, 90, 180)]; tries = [x for x in tries if inw(x)] or [ev]
    alt, at, pp = max((q["alt"], x, q) for x in tries for q in sk.planets_now(top, sk.ts.from_datetime(x)) if q["name"] == p["name"])
    if alt >= 20: add(6, at, "planet", f"{p['name']} is well placed in the {C.where(pp['az'], alt)}. {PLANET_WOW[p['name']]}", q=-p["mag"] + alt / 45, planet=p["name"], fk={"kind": "planet", "name": p["name"]})
  if on("moon") and 3 <= mo["illum"] <= 22 and "waxing" in mo["phase"] and mo["alt"] > 5:
   add(7, ev, "crescent", f"a thin crescent Moon sits low in the {C.compass(mo['az'], True)}. Look for earthshine, the faint glow on its unlit side", q=-mo["illum"] / 10, fk={"kind": "moon", "phase": "waxing crescent"})
 if on("eclipses"):
  for x in E.eclipses(sk, loc, now.astimezone(UTC), (now + timedelta(days=days)).astimezone(UTC)):
   if x["type"] == "penumbral": continue
   lo = x["local"]; dt = datetime.fromisoformat(lo.get("max_utc") or x["greatest_utc"]).astimezone(tz)
   add(4, dt, "eclipse", f"a {lo.get('local_type') or x['type']} {x['kind']} eclipse" + (f" covers about {lo['obscuration_pct']}% of the Sun. View it only through certified eclipse glasses" if x["kind"] == "solar" else " dims the Moon and can turn it a coppery red"), q=1, fk={"kind": "eclipse", "eclipse": x["kind"]})
 return out
def weather(sk, loc, dt):
 cl = sk.cloud_at(sk.clouds(loc), dt)
 if cl is None: return "The cloud forecast does not reach that far yet; I'll check it that afternoon.", None
 return (f"The forecast currently shows clear skies (about {cl:.0f}% cloud)." if cl < 40 else f"Some cloud is forecast (about {cl:.0f}%); I'll check again that afternoon." if cl < 70
  else f"The forecast currently looks cloudy (about {cl:.0f}%); I'll keep watching it."), cl
def highlight(sk, loc, cfg, now, days=7):
 """Pick the single best sight in the next `days` nights (extends to 14 if nothing beats a bright planet). Returns text + data."""
 cs = candidates(sk, loc, cfg, now, days)
 if not any(c["tier"] <= 5.5 for c in cs) and days < 14: cs = candidates(sk, loc, cfg, now, 14); days = 14
 cs = [c for c in cs if c["at"] > now]
 if not cs:
  import stars as SX
  tz = ZoneInfo(loc["tz"]); top = sk.observer(loc); sun = sk.sun_times(top, _night(now), tz); ev = max((sun.get("nautical_dusk") or now) + timedelta(minutes=45), now)
  cw = SX.cotw(sk, loc, ev)
  if not cw: return None
  cs = [{"tier": 8, "at": ev, "kind": "constellation", "what": f"find {cw['name']}, {cw['where']}. {cw['find']}", "q": 0, "night": _night(ev).isoformat(), "fk": {"kind": "constellation", "name": cw["name"]}}]
 b = sorted(cs, key=lambda c: (c["tier"], -c["q"] + 0.5 * (c["at"] - now).total_seconds() / 86400))[0]  # same tier: sooner wins unless clearly better
 wx, cl = weather(sk, loc, b["at"]); rem = b["kind"] in ("iss", "station", "starlink", "meteor", "eclipse", "conjunction", "planet")
 import facts as F; w = _when(b["at"], now); fl = F.line(F.key_for(b.get("fk") or {"kind": b["kind"]}))
 text = f"Your first big one: **{w[0].upper() + w[1:]}**, {b['what'].rstrip('.')}." + fl + f"\n{wx}" + (" I'll send you a reminder beforehand." if rem else "")
 return {"text": text, "kind": b["kind"], "tier": b["tier"], "at_local": b["at"].isoformat(), "night": b["night"], "cloud": cl, "remind": rem, "pass_id": b.get("e", {}).get("id"),
  "planet": b.get("planet"), "shower": b.get("shower"), "days_scanned": days}
def reminders(sk, loc, cfg, now, h):
 """The normal one-shot(s) for the highlight: same names the daily check would use, so it never doubles up."""
 if not h or not h["remind"]: return []
 import night as N
 from tonight import tonight
 d = date.fromisoformat(h["night"]); tn = tonight(sk, loc, cfg, d, now); tz = ZoneInfo(loc["tz"]); at0 = datetime.fromisoformat(h["at_local"])
 m = {"iss": ("iss",), "station": ("station",), "starlink": ("starlink",), "meteor": ("meteor",), "eclipse": ("eclipse",), "conjunction": ("conjunction",), "planet": ("planet",)}[h["kind"]]
 ev = [e for e in tn["events"] if e["kind"] in m and abs((datetime.fromisoformat(e["start_utc"]) - at0.astimezone(UTC)).total_seconds()) < 3 * 3600
  and (h["kind"] != "planet" or e["name"] == h["planet"]) and (h["kind"] != "meteor" or e["name"] == h["shower"])]
 if not ev: return []
 e = min(ev, key=lambda e: abs((datetime.fromisoformat(e["start_utc"]) - at0.astimezone(UTC)).total_seconds()))
 if e["kind"] in ("iss", "station", "starlink", "eclipse"):
  e = {**e, "clear": True}; p = N.plan({**tn, "events": [e]}, {**cfg, "only": None, "alerts": {**cfg["alerts"], N.CAT[e["kind"]]: True}}, now, {})
  return [r for r in p["reminders"] if e["id"] in r["events"]]
 st = datetime.fromisoformat(e.get("best_from_local") or e["start_local"]); at = st - timedelta(minutes=20)
 if at < now + timedelta(minutes=20): return []
 mi = at.minute - 1 if at.minute in (0, 30) else at.minute; dl = st + timedelta(hours=2)
 return [{"name": f"Look Up one-shot {tn['date']} {at:%H%M} reminder", "cron": f"CRON_TZ={tz.key} {mi} {at.hour} {at.day} {at.month} *", "at_local": at.isoformat(), "events": [e["id"]],
  "prompt": f"Look Up one-shot (reminder) for the night of {tn['date']}: run the look-up-live skill's 'reminder' step for events {e['id']}. "
   f"Then delete this routine. If it is already past {dl:%H:%M} {tz.key} on {dl:%Y-%m-%d}, delete it without sending anything."}]
if __name__ == "__main__":
 from sky import Sky
 import argparse
 ap = argparse.ArgumentParser(); ap.add_argument("--at"); ap.add_argument("--days", type=int, default=7); a = ap.parse_args()
 cfg = C.cfg(); loc = C.active(cfg)
 if not loc: print(json.dumps({"error": "no location set"})); sys.exit()
 tz = ZoneInfo(loc["tz"]); now = datetime.fromisoformat(a.at).astimezone(tz) if a.at else datetime.now(tz); sk = Sky(); h = highlight(sk, loc, cfg, now, a.days)
 print(json.dumps({"highlight": h, "reminders": reminders(sk, loc, cfg, now, h)}, indent=1, default=str))
