# look-up v2 | words.py: message templates in the Look Up voice: a calm, precise planetarium guide. Complete sentences, times and directions in bold, one fact per message.
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import core as C
def T(s, tz): return C.hhmm(datetime.fromisoformat(s).astimezone(tz))
def B(x): return f"**{x}**"
def hw(az, alt):
 h = C.height(alt); return f"low in the {C.compass(az)}, just above the horizon" if h.startswith("low") else f"{h} in the {C.compass(az)}"
def andj(xs): return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]
GEARW = {1: "binoculars", 2: "a telescope"}
def gear_note(n): return f" You will need {GEARW[n]}." if n else ""
def lab(e): return f" ({e['light']})" if e.get("light") else ""
def day(s, tz): return datetime.fromisoformat(s).astimezone(tz).strftime("%a")
def wday(s, tz): return datetime.fromisoformat(s).astimezone(tz).strftime("%A")
def fact(e):
 import facts as F; return F.line(F.key_for(e))
def bright(m):
 for lim, w in ((-3, "very bright, outshining every star"), (-1.5, "brighter than any star"), (-0.5, "as bright as the brightest stars"), (0.8, "about as bright as a first-magnitude star"), (2.2, "similar in brightness to an ordinary star")):
  if m <= lim: return w
 return "faint, like a dim star"
PRIO = ["iss", "station", "eclipse", "meteor", "comet", "aurora", "rocket", "starlink", "conjunction", "planet", "dayvenus", "daymoon", "satellite"]
def lead_ev(evs): return min(evs, key=lambda e: PRIO.index(e["kind"]) if e["kind"] in PRIO else 99)
def who(e, cap=False):
 n = e.get("name", ""); k = e["kind"]
 w = ("the ISS" if k == "iss" else "China's Tiangong space station" if "tiangong" in n.lower() or "css" in n.lower() else f"the {n}" if k == "station" else
  "a fresh Starlink train" if k == "starlink" else f"a spent rocket stage ({n.upper()})" if "r/b" in n.lower() else f"a bright satellite ({n})")
 return w[0].upper() + w[1:] if cap else w
def pass_line(e, tz, short=False):
 s, p, x = e["start"], e["peak"], e["end"]
 if short: return f"{B(T(e['start_local'], tz))} — {who(e, True)}, rising in the {C.compass(s['az'])} and reaching {C.height(p['alt']).split(',')[0]} in the {C.compass(p['az'])}."
 long_ = (datetime.fromisoformat(e["end_utc"]) - datetime.fromisoformat(e["peak_utc"])).total_seconds() > 50
 tail = ((f"then fades into Earth's shadow in the {C.compass(x['az'], True)}" if e.get("fades_in_shadow") else f"then sets in the {C.compass(x['az'], True)}") + f" by {T(e['end_local'], tz)}" if long_
  else "then fades into Earth's shadow")
 out = f"{B(T(e['start_local'], tz))}{lab(e)} — {who(e, True)} rises in the {C.compass(s['az'], True)}, reaches the {B(C.where(p['az'], p['alt']))} at {T(e['peak_local'], tz)}, and {tail}."
 if e["kind"] == "starlink": return out + " Look for a line of dots moving together. Trains fade quickly after launch, so treat this as a best estimate."
 return out + f" It will be {bright(e['mag'])}, a steady light that does not blink" + ("." if e["kind"] in ("iss", "station") else " (brightness estimated).")
def line(e, tz):
 k = e["kind"]; wh = C.where(e["peak"]["az"], e["peak"]["alt"]) if e.get("peak") and e["peak"].get("alt") is not None else ""
 if k in ("iss", "station", "satellite", "starlink"): return pass_line(e, tz)
 if k == "planet": return f"{B(T(e['peak_local'], tz))}{lab(e)} — {e['name']} is well placed in the {B(wh)}."
 if k == "conjunction": return f"{B(T(e['peak_local'], tz))} — {e['name']} appear close together in the {B(wh)}, about {e['sep']}° apart. A finger held at arm's length covers about 1°."
 if k == "daymoon": return f"{B(T(e['peak_local'], tz))} (daytime) — The Moon, a {e['phase']} ({e['illum']}% lit), is visible in daylight in the {B(wh)}."
 if k == "dayvenus": return (f"{B(T(e['peak_local'], tz))} (daytime) — Venus can be found in daylight in the {B(wh)}, about {e['elong']}° from the Sun. "
  "Stand in the shadow of a building so the Sun is blocked, and never look directly at the Sun.")
 if k == "meteor":
  nt = "peak night" if e["days_from_peak"] == 0 else "the night before the peak" if e["days_from_peak"] == 1 else "the night after the peak"
  moon = (f"The Moon is {e['moon_illum']}% lit and up during those hours, so it will wash out the fainter meteors." if e["moon_up"] and e["moon_illum"] > 40 else
   f"The Moon is {e['moon_illum']}% lit" + (" and will have little effect." if e["moon_up"] else " and below the horizon, so it will not interfere."))
  return (f"The {e['name']}, {nt} ({e['light']}) — Best viewing is {B(T(e['best_from_local'], tz) + ' to ' + T(e['best_to_local'], tz))}, with the radiant in the {B(wh)}. "
   f"Expect up to about {e['rate_dark']} meteors an hour from a dark site, or around {e['rate_suburban']} from a suburban yard. {moon} Look anywhere in the sky and allow 20 minutes for your eyes to adjust."
   + ("" if e["in_window"] else " The best hours fall outside your usual viewing window."))
 if k == "aurora":
  if e.get("phone_only"): return (f"Aurora is possible but unlikely to be visible to the eye: NOAA forecasts Kp {e['kp']:.0f}, just below the level of about {e['kp_needed']:.0f} needed at your latitude. "
   "A phone in night mode, pointed low toward the north, may record a glow your eyes cannot see.")
  return (f"Aurora is possible tonight: NOAA forecasts Kp {e['kp']:.0f}, and about {e['kp_needed']:.0f} is needed at your latitude. Once it is fully dark, look low toward the {B('north' if e['peak']['az'] == 0 else 'south')}. "
   "A phone camera in night mode often detects it before your eyes do.")
 if k == "comet":
  return (f"{B(T(e['peak_local'], tz))}{lab(e)} — Comet {e['name']} is in the {B(wh)}, at an estimated magnitude of {e['mag']:g} (comet brightness is difficult to predict)."
   + (" It should be visible to the eye from a dark site; binoculars will show the tail better." if e["gear"] == 0 else gear_note(e["gear"])))
 if k == "eclipse":
  lo = e["local"]
  if e["eclipse"] == "solar":
   return (f"{e['name']} (daytime) — It begins at {B(T(lo['start_utc'], tz))}, peaks at {B(T(lo['max_utc'], tz))} with about {lo['obscuration_pct']}% of the Sun covered, and ends at {T(lo['end_utc'], tz)}, "
    f"with the Sun in the {C.compass(lo['sun_az_at_max'])}. View it only through certified eclipse glasses or a pinhole projector, never directly.")
  return (f"{e['name']} ({e['light']}) — Greatest eclipse is at {B(T(e['peak_utc'], tz))}, with the Moon in the {B(wh)}. It is safe to watch with your eyes"
   + (", and the Moon will turn a coppery red." if e["type"] == "total" else "; part of the Moon will darken." if e["type"] == "partial" else ", although the shading is subtle.")
   + (" The Moon rises while the eclipse is under way." if lo.get("moonrise_during") else " The Moon sets while the eclipse is under way." if lo.get("moonset_during") else ""))
 if k == "rocket":
  return (f"{B(T(e['start_local'], tz))}{lab(e)} — {e['name']} is scheduled to launch from {e['pad']}, about {round(e['dist_km'] * .621, -1):,.0f} miles ({e['dist_km']:,} km) away. If it launches on time, "
   f"look low toward the {B(C.compass(e['bearing'], True))} two to four minutes after liftoff. Launch times often change, so I will confirm before reminding you.")
 return e["name"]
def gear_line(ex, at=None, tz=None):
 if not ex: return ""
 g = max(x["gear"] for x in ex)
 return f"\nWith {GEARW[g]}" + (f", around {B(T(at, tz))}" if at else "") + ", look for " + "; ".join(f"{x['name']} in the {C.compass(x['az'])} ({x['note']})" for x in ex[:3]) + "."
def sky_phrase(w):
 c = f" (about {w['avg_cloud']}% cloud)" if w.get("avg_cloud") is not None else ""
 return {"clear": f"skies look clear{c}", "partly cloudy": f"expect some clouds{c}, with clear breaks likely", "unknown": "a cloud forecast is not yet available"}.get(w["verdict"], f"it looks mostly cloudy{c}, although these times should have breaks")
def moon_sentence(tn, tz):
 m = tn["moon"]; rise = next((r for r in m["rise_set"] if r["what"] == "rise" and any(a <= r["at_local"] <= b for a, b in tn["windows"])), None); ph = f"The Moon, a {m['phase']} ({m['illum']}% lit),"
 if m["alt"] > 3: return f"{ph} is in the {m['where']} during the evening."
 return f"{ph} rises in the {rise['dir']} at {B(T(rise['at_local'], tz))}." if rise else f"{ph} stays below the horizon during your viewing hours."
def headsup(tn, evs, extras, cfg, now=None):
 tz = ZoneInfo(tn["location"]["tz"]); where = tn["location"]["label"]
 out = [f"Tonight from {where}: {sky_phrase(tn['weather'])}. Worth stepping outside for:"] + ["- " + line(e, tz) for e in evs]
 xt = [e for e in extras if e["name"] not in " ".join(x["name"] for x in evs)]
 if xt: out.append("Also visible: " + "; ".join(f"{e['name']}, {hw(e['peak']['az'], e['peak']['alt'])} around {B(T(e['peak_local'], tz))}" if e["kind"] == "planet" else line(e, tz).rstrip(".") for e in xt) + ".")
 g = gear_line(tn.get("extras"), tn.get("mid"), tz).strip()
 if g: out.append(g)
 if cfg["alerts"].get("moon") and tn["moon"]["illum"] >= 3: out.append(moon_sentence(tn, tz))
 f = fact(lead_ev(evs)).strip()
 if f: out.append(f)
 if any(e["kind"] in ("iss", "station", "satellite", "starlink", "rocket", "eclipse") for e in evs): out.append("I'll send a reminder about 30 minutes beforehand.")
 return "\n".join(out)
def clouded(tn, evs):
 e = max(evs, key=lambda e: (e.get("major", False), -(e["cloud"] or 0)))
 nm = {"meteor": f"the {e['name']}", "aurora": "tonight's aurora chance", "rocket": f"the {e['name']} launch", "eclipse": f"the {e['name'].lower()}", "comet": f"Comet {e['name']}"}.get(e["kind"], e["name"])
 return f"Clouds are likely to hide {nm} tonight; the forecast shows about {e['cloud']}% cover. I'll keep watching for the next clear opportunity."
def reminder(evs, tn):
 tz = ZoneInfo(tn["location"]["tz"]); e = evs[0]
 if len(evs) == 1:
  if e["kind"] == "eclipse": return "Starting in about 30 minutes: " + line(e, tz) + fact(e)
  if e["kind"] in ("meteor", "planet", "conjunction"): return "Coming up shortly: " + line(e, tz) + fact(e)
  if e["kind"] == "rocket": return (f"Reminder: {e['name']} is still {e['status']} for {B(T(e['start_local'], tz))}. Face {B(C.compass(e['bearing'], True))} and watch low on the horizon "
   "two to four minutes after liftoff." + fact(e))
  return (f"Reminder: {who(e)} passes over at {B(T(e['start_local'], tz))}. Step outside a few minutes early and face {B(C.compass(e['start']['az'], True))}; "
   f"by {T(e['peak_local'], tz)} it will be {hw(e['peak']['az'], e['peak']['alt'])}." + fact(e))
 return ("Coming up within the hour:\n" + "\n".join("- " + pass_line(x, tz, True) if x["kind"] != "rocket" else f"- {B(T(x['start_local'], tz))} — {x['name']} launch, low toward the {C.compass(x['bearing'])}" for x in evs)
  + fact(lead_ev(evs)))
def look_now(e, tn):
 n = max(1, round((datetime.fromisoformat(e["peak_utc"]) - datetime.fromisoformat(e["start_utc"])).total_seconds() / 60))
 return (f"Look {B(C.compass(e['start']['az'], True))} now: {who(e)} is rising. In about {n} minute{'s' if n > 1 else ''} it will be {hw(e['peak']['az'], e['peak']['alt'])}, then "
  + ("fade into Earth's shadow" if e.get("fades_in_shadow") else "set") + f" in the {C.compass(e['end']['az'], True)}." + fact(e))
def cloudy_now(evs, cl):
 nm = who(evs[0]) if evs[0]["kind"] != "rocket" else f"the {evs[0]['name']} launch"
 return f"Update on {nm}: clouds have moved in (about {cl}% cover), so it will probably be hidden. If you see breaks, it is still worth a look."
def gone(evs, ids): return "Update: after a fresh orbit update, that pass is no longer predicted, so there will be nothing to see at that time."
def moon_note(m, rs, cl, t, tz, cfg):
 import facts as F
 hd = f"Tonight's Moon ({C.hhmm(t)}): "; nxt = lambda w: next(((x[0], x[2]) for x in rs if x[1] == w), None); fl = F.line(F.moon_key(m["phase"]))
 if m["phase"] == "new moon" or m["illum"] < 3: return hd + "it is a new Moon, so the sky is as dark as it gets, ideal for faint stars and the Milky Way." + fl
 if m["alt"] > 0:
  st = nxt("set"); s = hd + f"it is a {m['phase']}, {m['illum']}% lit, in the {B(C.where(m['az'], m['alt']))}."
  if st: x = st[0].astimezone(tz); s += f" It sets at {C.hhmm(x)}" + (" tomorrow" if x.date() > t.date() and x.hour >= 5 else "") + "."
  if cl is not None and cl >= cfg["cloud"]["bad"]: s += f" Clouds (about {cl}%) will probably hide it tonight."
  return s + fl
 r = nxt("rise")
 return hd + "it is below the horizon now." + (f" It rises at {B(C.hhmm(r[0].astimezone(tz)))} in the {C.compass(r[1], True)} as" if r else " It is") + f" a {m['phase']}, {m['illum']}% lit." + fl
def week(o, cfg):
 d0 = o["days"][0]; tz = ZoneInfo(d0["location"]["tz"]); out = [f"This week from {d0['location']['label']}:"]
 now = o.get("now", ""); iss = sorted([e for d in o["days"] for e in d["events"] if e["kind"] in ("iss", "station") and not e.get("blocked") and e["end_utc"] > now], key=lambda e: (-e["peak"]["alt"]))[:3]
 if iss: out.append("- Best station passes: " + "; ".join(f"{B(day(e['start_local'], tz) + ' ' + T(e['start_local'], tz))}, {who(e)}, {C.where(e['peak']['az'], e['peak']['alt'])}"
  + (f" (forecast {e['cloud']}% cloud)" if e["cloud"] is not None and e["cloud"] > cfg["cloud"]["ok"] else "") for e in sorted(iss, key=lambda e: e["start_utc"])) + ".")
 m = d0["moon"]
 out.append("- " + (f"The Moon reaches " + ", then ".join(f"{p['phase'].lower()} on {B(wday(p['at_local'], tz))}" for p in o["moon_phases"]) + f". Tonight it is a {m['phase']}, {m['illum']}% lit." if o["moon_phases"]
  else f"The Moon is a {m['phase']}, {m['illum']}% lit, tonight."))
 pl = [e for e in d0["events"] if e["kind"] == "planet"]
 if pl: out.append("- " + "; ".join(f"{e['name']} is well placed in the {B(C.where(e['peak']['az'], e['peak']['alt']))} around {T(e['peak_local'], tz)}" for e in pl) + ". Planets shine steadily, while stars twinkle.")
 for e in [e for e in d0["events"] if e["kind"] == "comet"][:2]: out.append(f"- Comet {e['name']} is in the {C.compass(e['az'])} in the evening, at an estimated magnitude of {e['mag']:g}" + (f"; you will need {GEARW[e['gear']]}." if e["gear"] else "."))
 for x in o.get("eclipses") or []:
  lo = x["local"]; t0 = lo.get("max_utc") or x["greatest_utc"]
  out.append(f"- A {lo.get('local_type') or x['type']} {x['kind']} eclipse is visible from here on {B(datetime.fromisoformat(t0).astimezone(tz).strftime('%A, %b %d'))}" + (f", with about {lo['obscuration_pct']}% of the Sun covered. Use certified eclipse glasses only." if x["kind"] == "solar" else "."))
 gl = gear_line(o.get("extras")).strip()
 if gl: out.append("- " + gl.replace("With ", "This week with ", 1))
 mt = {e["name"]: (d["date"], e) for d in o["days"] for e in d["events"] if e["kind"] == "meteor" and e["days_from_peak"] == 0}
 for n, (dd, e) in mt.items(): out.append(f"- The {n} peak on {B(datetime.fromisoformat(dd).strftime('%A'))} night: up to about {e['rate_suburban']} meteors an hour from a suburban yard, or {e['rate_dark']} from a dark site.")
 au = [e for d in o["days"] for e in d["events"] if e["kind"] == "aurora"]
 out.append(f"- Aurora is possible on {', '.join(B(day(e['start_local'], tz)) for e in au)}: NOAA forecasts Kp {max(e['kp'] for e in au):.0f}, and about {o['kp_needed']:.0f} is needed here. I'll confirm that afternoon." if au
  else f"- Aurora is unlikely: NOAA's three-day forecast peaks near Kp {o['kp_max_3day']:.0f}, and about Kp {o['kp_needed']:.0f} is needed at your latitude.")
 cl = [(x["date"], x["weather"]["avg_cloud"]) for x in o["days"] if x["weather"]["avg_cloud"] is not None]
 good = [datetime.fromisoformat(d).strftime("%A") for d, v in cl if v <= cfg["cloud"]["ok"]]
 out.append("- " + (f"The clearest evenings look like {andj(good[:4])}." if good else "The week looks mostly cloudy so far.") + " Forecasts beyond two days change often, so I'll confirm each afternoon.")
 c = o.get("cotw")
 if c:
  out.append(f"This week's constellation is {B(c['name'])}, in the {c['where']} during the evening. {c['find']}")
  import facts as F; f = F.line("cons:" + c["name"]).strip() or c.get("fact", "")
  if f: out.append(f)
 return "\n".join(out)
def preview(tn, nxt, now, cfg):
 """The first-impression 'Tonight from <home>' message. Full sentences; the ISS line is dropped when there's no good pass."""
 tz = ZoneInfo(tn["location"]["tz"]); s = tn["sun"]; m = tn["moon"]; out = [f"Tonight from {tn['location']['label']}: {sky_phrase(tn['weather'])}."]
 def when(r): x = datetime.fromisoformat(r["at_local"]); return T(r["at_local"], tz) + (" tomorrow" if x.date() > now.date() and x.hour >= 5 else "")
 if s.get("sunset") and s["sunset"] > now.isoformat(): out.append(f"- The Sun sets at {B(T(s['sunset'], tz))}" + (f", and the sky is fully dark by {B(T(s['astro_dusk'], tz))}." if s.get("astro_dusk") else "; at this time of year the sky never becomes fully dark."))
 elif s.get("sunset") and (not s.get("sunrise") or now.isoformat() < s["sunrise"]): out.append(f"- It is already dark; the Sun set at {T(s['sunset'], tz)}.")
 rs = [r for r in m["rise_set"] if r["at_local"] > now.isoformat()]; nr = next((r for r in rs if r["what"] == "rise"), None); ns = next((r for r in rs if r["what"] == "set"), None)
 mt = (f" It is up now and sets at {B(when(ns))} in the {ns['dir']}." if ns and (not nr or ns["at_local"] < nr["at_local"]) else f" It rises at {B(when(nr))} in the {nr['dir']}." if nr else "")
 out.append(f"- The Moon is a {m['phase']}, {m['illum']}% lit.{mt}")
 if nxt:
  dd = datetime.fromisoformat(nxt["start_local"]); wd = "tonight" if dd.date() == now.date() or (dd - now) < timedelta(hours=14) else dd.strftime("%A, %b ") + str(dd.day)
  out.append(f"- The space station's next good pass is {B(wd + ' at ' + T(nxt['start_local'], tz))}, reaching the {C.where(nxt['peak']['az'], nxt['peak']['alt'])}; it will be {bright(nxt['mag']).split(',')[0]}.")
 for e in [e for e in tn["events"] if e["kind"] == "planet"]: out.append(f"- {e['name']} is well placed in the {B(C.where(e['peak']['az'], e['peak']['alt']))} by {T(e['peak_local'], tz)}.")
 return "\n".join(out)
