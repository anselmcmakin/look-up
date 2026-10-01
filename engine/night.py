# look-up v2 | night.py: plan (heads-up, one-shot reminders), preview, weekly rundown, moon note, next passes. CLI entry point.
import json, os, sys, argparse
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C, events as E
from sky import Sky, UTC
from tonight import tonight, resolve
CAT = {"iss": "iss", "station": "satellites", "satellite": "satellites", "starlink": "starlink", "planet": "planets", "conjunction": "planets", "dayvenus": "planets",
 "meteor": "meteors", "aurora": "aurora", "rocket": "rockets", "moon": "moon", "daymoon": "moon", "comet": "comets", "eclipse": "eclipses"}
def enabled(cfg, kind):
 c = CAT[kind]; return (c in cfg["only"]) if cfg.get("only") else cfg["alerts"].get(c, True)
def akey(e): return e["name"] if e["kind"] == "comet" else e.get("local", {}).get("max_utc") or e["peak_utc"]
def triggers(tn, cfg, now, st=None):
 """Events worth an afternoon heads-up on their own (planets, the daytime moon, and gear extras never trigger; they ride along)."""
 out = []; ann = (st or C.state()).get("announced", {}); g = E.rank(cfg)
 for e in tn["events"]:
  if not enabled(cfg, e["kind"]) or e.get("blocked"): continue
  if (e.get("end_utc") or e["peak_utc"]) < now.astimezone(UTC).isoformat(): continue  # already over
  if e["kind"] in ("iss", "station") or e["kind"] == "starlink" or (e["kind"] == "satellite" and e["mag"] <= 1.5) or e["kind"] in ("conjunction", "aurora", "rocket"): out.append(e)
  elif e["kind"] == "meteor" and (e["major"] or e["days_from_peak"] == 0): out.append(e)
  elif e["kind"] == "comet" and e["mag"] <= E.COMET_ALERT[g] and (now.date() - date.fromisoformat(ann.get(akey(e), "2000-01-01"))).days >= 7: out.append(e)
  elif e["kind"] == "eclipse" and akey(e) not in ann: out.append(e)
 sats = [e for e in out if e["kind"] == "satellite"]
 keep = {e["id"] for e in sorted(sats, key=lambda e: e["mag"])[:1]}
 return [e for e in out if e["kind"] != "satellite" or e["id"] in keep]
def plan(tn, cfg, now, st=None, tag=""):
 """Decide tonight: heads-up text, one-shot reminder routines (cron in the location's zone), extras."""
 import words as W
 tz = ZoneInfo(tn["location"]["tz"]); tr = triggers(tn, cfg, now, st); clear = [e for e in tr if e["clear"]]; cloudy = [e for e in tr if not e["clear"]]
 extras = [e for e in tn["events"] if e["kind"] in ("planet", "daymoon", "dayvenus") and enabled(cfg, e["kind"]) and e["clear"] and e["id"] not in [x["id"] for x in tr]
  and (e.get("end_utc") or e["peak_utc"]) > now.astimezone(UTC).isoformat()]
 res = {"paused": cfg["paused"], "send_headsup": False, "headsup": None, "reminders": [], "triggers": [e["id"] for e in tr]}
 if cfg["paused"]: return res
 if clear:
  res["send_headsup"] = True; res["headsup"] = tag + W.headsup(tn, clear, extras, cfg, now)
  rem = []; mx = cfg.get("max_reminders", 3); sched = {i for r in (st or C.state())["reminders"] if r["date"] == tn["date"] for i in r.get("events", [])}
  for e in clear:
   if e["kind"] not in ("iss", "station", "satellite", "starlink", "rocket", "eclipse"): continue
   st = datetime.fromisoformat(e["start_local"]); at = st - timedelta(minutes=30)
   if at > now + timedelta(minutes=20) and e["id"] not in sched:  # sched: already nudged by an earlier one-shot (e.g. onboarding's first big one)
    if rem and rem[-1]["type"] == "heads" and (st - datetime.fromisoformat(rem[-1]["first_start"])) < timedelta(minutes=40): rem[-1]["events"].append(e["id"])
    else: rem.append({"type": "heads", "at": at, "events": [e["id"]], "first_start": st.isoformat()})
   if e["kind"] == "iss" and st - timedelta(minutes=2) > now + timedelta(minutes=10): rem.append({"type": "look-now", "at": st - timedelta(minutes=2), "events": [e["id"]], "first_start": st.isoformat()})
  rem = sorted(rem, key=lambda r: (r["type"] != "look-now", r["at"]))[:mx]
  for r in sorted(rem, key=lambda r: r["at"]):
   at = r["at"].astimezone(tz); m = at.minute - 1 if at.minute in (0, 30) else at.minute; dl = (datetime.fromisoformat(r["first_start"]) + timedelta(minutes=10)).astimezone(tz)
   step = "look-now" if r["type"] == "look-now" else "reminder"
   res["reminders"].append({"name": f"Look Up one-shot {tn['date']} {at:%H%M} {step}", "cron": f"CRON_TZ={tz.key} {m} {at.hour} {at.day} {at.month} *", "at_local": at.isoformat(), "events": r["events"],
    "prompt": f"Look Up one-shot ({step}) for the night of {tn['date']}: run the look-up-live skill's '{step}' step for events {','.join(r['events'])}. "
      f"Then delete this routine. If it is already past {dl:%H:%M} {tz.key} on {dl:%Y-%m-%d}, delete it without sending anything."})
  if not res["reminders"]: res["headsup"] = res["headsup"].replace("\nI'll send a reminder about 30 minutes beforehand.", "")
 elif cloudy and any(e.get("major") or e["kind"] in ("rocket", "comet") for e in cloudy): res["send_headsup"] = True; res["headsup"] = tag + W.clouded(tn, cloudy)
 return res
def find(tn, eid):
 k, obj, ts_ = eid.split("-")[0], eid.split("-")[1], eid.split("-")[-1]
 want = datetime.strptime(ts_, "%Y%m%d%H%M").replace(tzinfo=UTC) if len(ts_) == 12 else None
 for e in tn["events"]:
  if e["id"] == eid: return e
  if want and e["kind"] == k and e["id"].split("-")[1] == obj and abs((datetime.fromisoformat(e["start_utc"]) - want).total_seconds()) < 900: return e
def main(argv):
 import words as W, card as K
 from stars import field as SXF
 ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["tonight", "plan", "test", "week", "moon", "reminder", "look-now", "mark", "card", "cleanup", "next", "preview"])
 ap.add_argument("args", nargs="*"); ap.add_argument("--date"); ap.add_argument("--events"); ap.add_argument("--at"); ap.add_argument("--place"); ap.add_argument("--brief", action="store_true")
 a = ap.parse_args(argv); cfg = C.cfg(); st = C.state()
 if a.cmd == "test": import facts; facts.DRY = True  # test runs never use up facts
 if a.cmd == "mark":  # mark headsup <date> | mark reminder <date> <name> | mark moon <date>
  k = a.args[0]
  if k == "reminder": st["reminders"].append({"date": a.args[1], "name": " ".join(a.args[2:]), "events": [i for i in (a.events or "").split(",") if i]})
  else: st["sent"][f"{k}:{a.args[1]}"] = datetime.now(UTC).isoformat()
  C.save_state(st); print(json.dumps({"ok": True})); return
 loc = C.resolve(a.place) if a.place else C.active(cfg)
 if not loc or "error" in loc: print(json.dumps({"error": "no location set; run look-up-getting-started"})); return
 tz = ZoneInfo(loc["tz"]); now = datetime.fromisoformat(a.at).astimezone(tz) if a.cmd == "preview" and a.at else datetime.now(tz); d = date.fromisoformat(a.date) if a.date else now.date()
 if not a.date and now.hour < 12: d -= timedelta(days=1)  # before noon we're still in last night (its morning window)
 if a.cmd == "cleanup":  # one-shots from earlier nights that should already be gone
  old = [r for r in st["reminders"] if r["date"] < now.date().isoformat()]; st["reminders"] = [r for r in st["reminders"] if r not in old]; C.save_state(st)
  print(json.dumps({"delete_these_routines_if_they_still_exist": [r["name"] for r in old]}, indent=1)); return
 sk = Sky()
 if a.cmd == "moon":
  t = datetime.combine(d, datetime.strptime(a.at or cfg["moon_note"]["time"], "%H:%M").time(), tz); top = sk.observer(loc)
  m = sk.moon_now(top, sk.ts.from_datetime(t)); rs = sk.rise_set(top, sk.moon, sk.ts.from_datetime(t), 24); cl = sk.cloud_at(sk.clouds(loc), t)
  sk_ = not cfg["moon_note"]["on"] or cfg["paused"]
  print(json.dumps({"skip": sk_, "text": None if sk_ else W.moon_note(m, rs, cl, t, tz, cfg), "moon": m, "cloud": cl}, indent=1, default=str)); return
 if a.cmd == "week":
  days = []; nm = []
  from skyfield import almanac
  t0 = sk.ts.from_datetime(now); tt, y = almanac.find_discrete(t0, sk.ts.tt_jd(t0.tt + 7), almanac.moon_phases(sk.eph))
  nm = [{"at_local": x.utc_datetime().astimezone(tz).isoformat(), "phase": almanac.MOON_PHASES[v]} for x, v in zip(tt, y)]
  for i in range(7): days.append(tonight(sk, loc, cfg, d + timedelta(days=i), now))
  import stars as SX
  wk = f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"; hist = [v for k, v in st["cotw"].items() if k != wk][-4:]; ev = days[0]["window"][0]; ev = datetime.fromisoformat(ev) + timedelta(hours=1)
  if days[0]["dark_from"]: ev = max(ev, datetime.fromisoformat(days[0]["dark_from"]) + timedelta(minutes=45))
  cw = SX.cotw(sk, loc, ev, hist, st["cotw"].get(wk))
  if cw: st["cotw"][wk] = cw["name"]; C.save_state(st)
  ecl = E.eclipses(sk, loc, now.astimezone(UTC), (now + timedelta(days=30)).astimezone(UTC)) if cfg["alerts"].get("eclipses", True) else []
  out = {"now": now.astimezone(UTC).isoformat(), "days": days, "moon_phases": nm, "cotw": cw, "eclipses": ecl, "extras": days[0]["extras"], "kp_needed": sk.kp_needed(loc)[0], "kp_max_3day": max([k[1] for k in sk.kp() if k[2] == "predicted"] or [0])}
  out["text"] = W.week(out, cfg); out["card"] = K.constellation(cw, loc, C.D + f"/cards/cotw-{wk}.png") if cw else None; out["card_url"] = C.url(out["card"])
  if cw: out["cotw"] = {k: v for k, v in cw.items() if k not in ("field", "stars", "lines")}
  if a.brief: out["days"] = [{"date": x["date"], "weather": x["weather"], "events": [e["id"] for e in x["events"]]} for x in days]
  print(json.dumps(out, indent=1, default=str)); return
 if a.cmd == "next":  # next visible passes of a kind (default ISS), any dark hour, 10 days; flags which fall in the user's hours
  kd = (a.args or ["iss"])[0]; c2 = json.loads(json.dumps(cfg)); top = sk.observer(loc)
  ps = sk.passes(top, sk.ts.from_datetime(now), sk.ts.from_datetime(now + timedelta(days=10)), c2, kinds=["iss", "station"] if kd == "stations" else [kd])
  out = []
  for e in ps[:6]:
   st_ = datetime.fromisoformat(e["start_utc"]).astimezone(tz); wins = resolve(sk, loc, st_.date() - timedelta(days=1 if st_.hour < 12 else 0), cfg)[0]
   out.append({"when": st_.strftime("%a %b %d, ") + C.hhmm(st_), "who": e["name"], "start": C.compass(e["start"]["az"], True), "peak": C.where(e["peak"]["az"], e["peak"]["alt"]),
    "end": C.compass(e["end"]["az"], True), "mag": e["mag"], "in_your_hours": any(a_ <= st_ <= b_ for a_, b_ in wins), "blocked": e["blocked"]})
  print(json.dumps({"location": loc["label"], "passes": out, "note": "cloud forecast not applied; ask again that afternoon", "data_notes": sk.data_notes}, indent=1)); return
 tn = tonight(sk, loc, cfg, d, now)
 if a.cmd == "tonight": print(json.dumps(tn, indent=1, default=str)); return
 if a.cmd == "preview":  # "From your yard tonight": first-impression summary + tonight's sky-map card
  c2 = json.loads(json.dumps(cfg)); top = sk.observer(loc)
  ps = [e for e in sk.passes(top, sk.ts.from_datetime(now), sk.ts.from_datetime(now + timedelta(days=10)), c2, kinds=["iss"]) if not e["blocked"]]
  nxt = ps[0] if ps else None
  if nxt:
   for k in ("start_utc", "peak_utc", "end_utc"): nxt[k.replace("_utc", "_local")] = datetime.fromisoformat(nxt[k]).astimezone(tz).isoformat()
  tonight_pass = nxt if nxt and datetime.fromisoformat(nxt["start_utc"]) < datetime.fromisoformat(tn["window"][1]) + timedelta(hours=1) else None
  when = datetime.fromisoformat(tn["mid"])
  card = (K.pass_card(tonight_pass, tn, C.D + f"/cards/{tonight_pass['id']}.png", SXF(sk, loc, datetime.fromisoformat(tonight_pass["peak_local"]))) if tonight_pass
   else K.sky_card(SXF(sk, loc, when), f"Your sky tonight, {C.hhmm(when)}", when.strftime("%A %b %d").replace(" 0", " ") + f"  |  {tn['weather']['verdict']}", loc, C.D + f"/cards/tonight-{tn['date']}.png"))
  import highlight as H
  hl = H.highlight(sk, loc, cfg, now); hr = H.reminders(sk, loc, cfg, now, hl)
  pv = W.preview(tn, nxt, now, cfg)
  if hl and nxt and hl.get("pass_id") == nxt["id"]: pv = "\n".join("- The space station makes an excellent pass tonight; details below." if x.startswith("- The space station's next") else x for x in pv.split("\n"))
  print(json.dumps({"text": pv + (f"\n\n{hl['text']}" if hl else ""), "card": card, "card_url": C.url(card), "highlight": hl, "highlight_reminders": hr, "label": loc["label"], "tz": loc["tz"], "next_iss": nxt and nxt["id"], "data_notes": sk.data_notes}, indent=1, default=str)); return
 if a.cmd in ("plan", "test"):
  if a.cmd == "test":  # simulate the afternoon check so the whole night shows (unless it's still before then)
   sim = datetime.fromisoformat(tn["window"][0]) - timedelta(hours=4, minutes=13); now = min(now, sim)
  if a.cmd == "test": st = json.loads(json.dumps(st)); st["announced"] = {}
  p = plan(tn, cfg, now, st, "[TEST] " if a.cmd == "test" else ""); best = next((e for k in ("iss", "station", "starlink", "satellite") for e in tn["events"] if e["kind"] == k and e["id"] in p["triggers"] and e.get("path")), None)
  p["card"] = K.pass_card(best, tn, C.D + f"/cards/{best['id']}.png", SXF(sk, loc, datetime.fromisoformat(best["peak_local"]))) if best else None; p["card_url"] = C.url(p["card"])
  if a.cmd == "test":
   p["note"] = f"TEST: simulated as the {C.hhmm(now)} afternoon check. Nothing was scheduled; these are the routines a real run would create."
   p["sample_reminders"] = ["[TEST] " + W.reminder([find(tn, i) for i in r["events"]], tn) for r in p["reminders"] if "reminder" in r["name"]]
   p["sample_look_now"] = ["[TEST] " + W.look_now(find(tn, r["events"][0]), tn) for r in p["reminders"] if "look-now" in r["name"]]
   m = sk.moon_now(tn and sk.observer(loc), sk.ts.from_datetime(datetime.combine(d, datetime.strptime(cfg["moon_note"]["time"], "%H:%M").time(), tz)))
   tm = datetime.combine(d, datetime.strptime(cfg["moon_note"]["time"], "%H:%M").time(), tz)
   p["sample_moon_note"] = "[TEST] " + W.moon_note(m, sk.rise_set(sk.observer(loc), sk.moon, sk.ts.from_datetime(tm), 24), sk.cloud_at(sk.clouds(loc), tm), tm, tz, cfg)
   p["all_events"] = [{k: e.get(k) for k in ("id", "name", "start_local", "mag", "peak", "cloud", "blocked")} for e in tn["events"]]
  p["weather"] = tn["weather"]; p["data_notes"] = tn["data_notes"]; p["date"] = tn["date"]
  p["already_sent"] = f"headsup:{tn['date']}" in st["sent"]; p["already_scheduled"] = [r["name"] for r in st["reminders"] if r["date"] == tn["date"]]
  if C.cfg().get("just_returned_home"): p["say_back_home"] = f"Welcome back. Alerts are using {loc['label']} again."
  if a.cmd == "plan" and p["send_headsup"]:  # remember comets/eclipses we told them about
   for e in tn["events"]:
    if e["id"] in p["triggers"] and e["kind"] in ("comet", "eclipse"): st.setdefault("announced", {})[akey(e)] = now.date().isoformat()
   C.save_state(st)
  print(json.dumps(p, indent=1, default=str)); return
 evs = [find(tn, i) for i in (a.events or "").split(",") if i]; live = [e for e in evs if e]
 if a.cmd == "card": cd = K.pass_card(live[0], tn, C.D + f"/cards/{live[0]['id']}.png", SXF(sk, loc, datetime.fromisoformat(live[0]["peak_local"]))) if live else None; print(json.dumps({"card": cd, "card_url": C.url(cd)})); return
 if not live: print(json.dumps({"send": False, "reason": "event no longer predicted (orbit update or schedule change)", "text": W.gone(evs, a.events)})); return
 cl = sk.cloud_at(sk.clouds(loc), now)
 if a.cmd == "reminder":
  if cfg["paused"]: print(json.dumps({"send": False, "reason": "paused"})); return
  txt = W.reminder(live, tn) if (cl is None or cl < cfg["cloud"]["bad"]) else W.cloudy_now(live, cl)
  cd = K.pass_card(live[0], tn, C.D + f"/cards/{live[0]['id']}.png", SXF(sk, loc, datetime.fromisoformat(live[0]["peak_local"]))) if live[0].get("path") else None
  print(json.dumps({"send": True, "text": txt, "card": cd, "card_url": C.url(cd), "cloud_now": cl}, default=str)); return
 if a.cmd == "look-now":
  e = live[0]; wait = (datetime.fromisoformat(e["start_utc"]) - datetime.now(UTC)).total_seconds()
  print(json.dumps({"send": not cfg["paused"] and (cl is None or cl < cfg["cloud"]["bad"]), "sleep_seconds": max(0, int(wait) - 20), "text": W.look_now(e, tn)})); return
if __name__ == "__main__": main(sys.argv[1:])
