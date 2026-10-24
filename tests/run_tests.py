# Look Up v2 test suite: location paths (JPEG + HEIC), settings parsing, hours keywords, gear, home reset vs travel, travel expiry, cron hygiene,
# day/twilight/night labels, eclipses, comets, meteor showers, preview, what-is-that from a photo.
import os, sys, json, shutil, tempfile
BASE = os.environ.get("LOOKUP_FIXTURES", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root by default; /workspace/look-up on the box
T = tempfile.mkdtemp(prefix="lookup-test-"); os.environ["LOOKUP_DIR"] = T
os.makedirs(T + "/data", exist_ok=True)
for f in os.listdir(BASE + "/test-piedmont/data"): os.symlink(f"{BASE}/test-piedmont/data/{f}", f"{T}/data/{f}")
shutil.copytree(BASE + "/test-piedmont/cache", T + "/cache")
sys.path.insert(0, os.environ.get("LOOKUP_SRC", os.path.join(BASE, "engine")))
import core as C
from datetime import date, timedelta, datetime
ok = lambda name, cond, extra="": print(("PASS " if cond else "FAIL ") + name, extra) or bool(cond)
R = []
g = C.exif_gps(BASE + "/tests/backyard_gps.jpg")
R.append(ok("EXIF GPS (Pillow)", abs(g["lat"] - 34.7012) < 1e-4 and abs(g["lon"] + 82.4623) < 1e-4 and g["facing_az"] == 225, g))
import PIL.Image as PI; _o = PI.open; PI.open = lambda *a, **k: (_ for _ in ()).throw(OSError("simulated HEIC"))
g2 = C.exif_gps(BASE + "/tests/backyard_gps.jpg"); PI.open = _o
R.append(ok("EXIF GPS (exifread fallback)", abs(g2["lat"] - 34.7012) < 1e-4 and abs(g2["lon"] + 82.4623) < 1e-4, {k: g2[k] for k in ("lat", "lon")}))
n = C.exif_gps(BASE + "/tests/backyard_nogps.jpg"); R.append(ok("no-GPS photo -> clear error", "error" in n and "lat" not in n, n["error"]))
p = C.resolve(photo=BASE + "/tests/backyard_gps.jpg")
R.append(ok("home from photo", p["source"] == "photo-exif" and p["tz"] == "America/New_York" and p["lat"] == 34.701, p))
for u, want in [("https://www.google.com/maps/place/Piedmont,+SC/@34.7023,-82.4646,14z/data=!3d34.7023!4d-82.4646", (34.7023, -82.4646)),
  ("https://www.google.com/maps?q=34.70,-82.46", (34.70, -82.46)), ("https://maps.apple.com/?ll=34.70,-82.46&q=Pin", (34.70, -82.46)),
  ("geo:34.70,-82.46", (34.70, -82.46)), ("34.70, -82.46", (34.70, -82.46)), ("https://www.google.com/maps/search/34.7012,+-82.4623", (34.7012, -82.4623))]:
 r = C.parse_pin(u); R.append(ok(f"pin {u[:48]}", (r.get("lat"), r.get("lon")) == want, r))
z = C.resolve("29673"); R.append(ok("ZIP fallback 29673", abs(z["lat"] - 34.70) < .1 and abs(z["lon"] + 82.46) < .1 and z["tz"] == "America/New_York", z))
c = C.resolve("Asheville, NC"); R.append(ok("city fallback", abs(c["lat"] - 35.6) < .2 and c["tz"] == "America/New_York", c))
b = C.resolve("https://example.com/nothing"); R.append(ok("bad link -> error", "error" in b, b))
for s, want in [("8pm-11pm", ("20:00", "23:00")), ("9 to 12:30am", ("21:00", "00:30")), ("20:00-23:00", ("20:00", "23:00")), ("5am-6:30am", ("05:00", "06:30")), ("7:45pm - 10", ("19:45", "22:00")), ("8-11", ("20:00", "23:00")), ("4-6", ("04:00", "06:00"))]:
 w = C.parse_window(s); R.append(ok(f"window '{s}'", (w["start"], w["end"]) == want, w))
o = C.parse_obstruction("trees east below 30"); R.append(ok("obstruction 'trees east below 30'", o["from"] == 60 and o["to"] == 120 and o["below"] == 30, o))
R.append(ok("blocked() inside/outside", C.blocked(90, 20, [o]) and not C.blocked(90, 35, [o]) and not C.blocked(200, 10, [o])))
cfg = C.cfg(); cfg["home"] = z; cfg["home"]["label"] = "Piedmont, SC"; cfg["travel"] = {**c, "until": (date.today() + timedelta(days=2)).isoformat()}; C.save_cfg(cfg)
a = C.active(); R.append(ok("travel active", a["is_travel"] and "Asheville" in a["label"]))
a2 = C.active(today=date.today() + timedelta(days=3)); R.append(ok("travel expires -> home", not a2["is_travel"] and C.cfg()["travel"] is None and C.cfg().get("just_returned_home")))
R.append(ok("compass/height words", C.where(225, 33) == "southwest, about a third of the way up", C.where(225, 33)))
# cron hygiene and plan on a simulated afternoon
import night as N
from sky import Sky
from zoneinfo import ZoneInfo
sk = Sky(); loc = C.active(); tz = ZoneInfo(loc["tz"]); cf = C.cfg()
tn = N.tonight(sk, loc, cf, date(2026, 9, 30), datetime(2026, 9, 30, 15, 47, tzinfo=tz))
pl = N.plan(tn, cf, datetime(2026, 9, 30, 15, 47, tzinfo=tz))
mins = [int(r["cron"].split()[1]) for r in pl["reminders"]]
R.append(ok("ISS pass found tonight 8:05 PM", any(e["kind"] == "iss" and e["start_local"][11:16] == "20:05" for e in tn["events"])))
R.append(ok("reminders: <= 3, no :00/:30, ISS look-now present", len(mins) <= 3 and not any(m in (0, 30) for m in mins) and any("look-now" in r["name"] for r in pl["reminders"]), [r["cron"] for r in pl["reminders"]]))
cf2 = json.loads(json.dumps(cf)); cf2["paused"] = True; R.append(ok("paused -> no heads-up", not N.plan(tn, cf2, datetime(2026, 9, 30, 15, 47, tzinfo=tz))["send_headsup"]))
cf3 = json.loads(json.dumps(cf)); cf3["only"] = ["iss"]; p3 = N.plan(tn, cf3, datetime(2026, 9, 30, 15, 47, tzinfo=tz))
R.append(ok("only ISS filter", all(i.startswith("iss") for i in p3["triggers"]) and p3["triggers"], p3["triggers"]))
cl = json.loads(json.dumps(tn)); [e.update(cloud=95, clear=False) for e in cl["events"]]
R.append(ok("cloudy night with no major event -> quiet", not N.plan(cl, cf, datetime(2026, 9, 30, 15, 47, tzinfo=tz))["send_headsup"]))
cl["events"].append({"id": "meteor-Orionids-20261021", "kind": "meteor", "name": "Orionids", "major": True, "days_from_peak": 0, "cloud": 95, "clear": False, "peak_utc": cl["events"][0]["peak_utc"]})
pm = N.plan(cl, cf, datetime(2026, 9, 30, 15, 47, tzinfo=tz)); R.append(ok("cloudy + major event -> one short line", pm["send_headsup"] and pm["headsup"].startswith("Clouds are likely to hide") and not pm["reminders"], pm["headsup"]))
import stars as S
w = S.identify(sk, {**p, "label": "photo spot"}, datetime(2026, 9, 30, 20, 7, 30, tzinfo=tz), "sw", None, True)
R.append(ok("what-is-that from photo time/place -> ISS", w["candidates"][0]["name"] == "the ISS", w["candidates"][0]["name"] + " / " + w["candidates"][0]["confidence"]))
# ---- v2 ----
import io, contextlib, events as E, words as W
def run(*a):
 b = io.StringIO()
 with contextlib.redirect_stdout(b): C.main(list(a))
 return json.loads(b.getvalue())
# HEIC with GPS EXIF (iPhone format) via pillow-heif
import pillow_heif; pillow_heif.register_heif_opener()
im = PI.open(BASE + "/tests/backyard_gps.jpg"); hp = T + "/backyard.heic"; im.save(hp, format="HEIF", exif=im.info["exif"])
gh = C.exif_gps(hp); R.append(ok("EXIF GPS from HEIC (pillow-heif)", abs(gh.get("lat", 0) - 34.7012) < 1e-4 and abs(gh.get("lon", 0) + 82.4623) < 1e-4, {k: gh.get(k) for k in ("lat", "lon", "facing_az", "error")}))
for s_, want in [("Dusk to 11pm", ["sunset-23:00"]), ("Early mornings too", ["sunset-23:00", "predawn-sunrise"]), ("Anytime", ["12:00-11:59"]), ("9 to 11 and 5 to 6:30 am", ["21:00-23:00", "05:00-06:30"]), ("after dark until midnight", ["dark-00:00"])]:
 hw = [f"{w['start']}-{w['end']}" for w in C.parse_hours(s_)]; R.append(ok(f"hours '{s_}'", hw == want, hw))
R.append(ok("default hours dusk-11pm, gear eye", C.DEFAULT["windows"] == [{"start": "sunset", "end": "23:00"}] and C.DEFAULT["gear"] == "eye"))
for s_, want in [("telescope on", "telescope"), ("Binoculars", "binoculars"), ("naked eye only", "naked eye / phone camera"), ("Just my eyes / phone camera", "naked eye / phone camera")]:
 R.append(ok(f"gear '{s_}'", run("gear", s_)["settings"]["gear"] == want))
r = run("set-alerts", "Space station, Meteor showers & comets, Visible rocket launches"); R.append(ok("Q2 widget labels -> alerts", set(r["settings"]["alerts"]) == {"iss", "meteors", "comets", "eclipses", "rockets"}, r["settings"]["alerts"]))
run("set-alerts", "Everything I can see")
run("obstruct", "trees east below 30"); r = run("home", "Denver, CO")
sh = run("show")["settings"]
R.append(ok("home reset: replaced, tz changed, obstructions cleared, travel kept separate", r["replaced"] == "Piedmont, SC" and r["tz_changed"] and r["old_tz"] == "America/New_York" and r["home"]["tz"] == "America/Denver" and not sh["obstructions"] and sh["travel"] is None, {k: r[k] for k in ("replaced", "tz_changed", "old_tz", "travel_active")}))
run("travel", "Asheville, NC", "--until", (date.today() + timedelta(days=3)).isoformat()); sh = run("show")["settings"]
R.append(ok("show settings: home + travel + gear", "Denver" in sh["home"] and "Asheville" in sh["travel"] and sh["gear"] and "location" in sh, {k: sh[k] for k in ("home", "travel", "gear")}))
r = run("home", "29673"); R.append(ok("reset back, same-zone move -> tz_changed false", r["tz_changed"] and run("home", "Greenville, SC")["tz_changed"] is False))
run("travel-end"); run("label", "home", "Piedmont, SC")
# sun times and light labels
top = sk.observer(loc); stt = {k: v.isoformat() for k, v in sk.sun_times(top, date(2026, 9, 30), tz).items() if v}
R.append(ok("sunset/twilight order + sunset ~7:15 PM", stt["sunset"] < stt["civil_dusk"] < stt["nautical_dusk"] < stt["astro_dusk"] < stt["astro_dawn"] < stt["sunrise"] and stt["sunset"][11:16] in ("19:14", "19:15", "19:16"), {k: v[11:16] for k, v in stt.items()}))
lb = [sk.light(top, sk.ts.from_datetime(datetime(2026, 9, 30, h, m, tzinfo=tz)))[0] for h, m in ((12, 0), (19, 45), (22, 0))]
R.append(ok("light labels noon/7:45 PM/10 PM", lb == ["daytime", "twilight", "night"], lb))
R.append(ok("every event tonight has a light label", all(e.get("light") in ("daytime", "twilight", "night") for e in tn["events"])))
# eclipses
from skyfield import eclipselib
t0, t1 = sk.ts.utc(2026, 1, 1), sk.ts.utc(2031, 1, 1); te, ye, de = eclipselib.lunar_eclipses(t0, t1, sk.eph)
lu = [g for g, k, *_ in E.ECLIPSES if k == "lunar"]
R.append(ok("lunar eclipse table matches skyfield (within 2 min)", len(lu) == len(te) and all(abs((datetime.fromisoformat(g).replace(tzinfo=None) - t.utc_datetime().replace(tzinfo=None)).total_seconds()) < 120 for g, t in zip(lu, te)), len(te)))
lx = E.solar_local(sk, {"lat": 25.69, "lon": 32.64}, datetime(2027, 8, 2, 10, 7, tzinfo=E.UTC)); R.append(ok("solar 2027-08-02 total at Luxor", lx.get("local_type") == "total", lx.get("local_type")))
ec = E.eclipses(sk, loc, datetime(2026, 1, 1, tzinfo=E.UTC), datetime(2030, 12, 31, tzinfo=E.UTC))
pz = [x for x in ec if x["kind"] == "solar" and x["greatest_utc"].startswith("2029-01-14")]
R.append(ok("Piedmont: 2029-01-14 partial solar ~42%", pz and 35 <= pz[0]["local"]["obscuration_pct"] <= 50, pz and pz[0]["local"]["obscuration_pct"]))
tnE = N.tonight(sk, loc, cf, date(2029, 6, 25), datetime(2029, 6, 25, 15, 47, tzinfo=tz)); el = [e for e in tnE["events"] if e["kind"] == "eclipse"]
R.append(ok("2029-06-25 total lunar eclipse in tonight's events (night)", el and el[0]["type"] == "total" and el[0]["light"] == "night", el and W.line(el[0], tz)))
# comets (MPC elements; nothing bright right now is normal) and a known bright one
cm = E.comets(sk, loc, sk.ts.now(), 9); R.append(ok("MPC comet list loads, gear-limited", isinstance(cm, list) and not any("comet" in n for n in sk.data_notes), (len(cm), sk.data_notes)))
ta = [c for c in E.comets(sk, loc, sk.ts.utc(2024, 10, 15, 23), 6) if "Tsuchinshan-ATLAS" in c["name"]]
R.append(ok("2024-10-15: Tsuchinshan-ATLAS bright, low in the west", ta and ta[0]["mag"] < 5 and 240 < ta[0]["az"] < 300, ta and ta[0]))
fake = {"id": "comet-X", "kind": "comet", "name": "C/2026 X1 (Test)", "mag": 5.2, "gear": 1, "clear": True, "cloud": 5, "peak_utc": "2026-10-01T01:00:00+00:00", "start_utc": "2026-10-01T01:00:00+00:00"}
tc = {**tn, "events": [fake]}; now_ = datetime(2026, 9, 30, 15, 47, tzinfo=tz)
R.append(ok("comet mag 5.2: quiet for eye, alert for binoculars (says binoculars)", not N.triggers(tc, {**cf, "gear": "eye"}, now_, {}) and N.triggers(tc, {**cf, "gear": "binoculars"}, now_, {}) and "binoculars" in W.line({**fake, "az": 280, "peak": {"az": 280, "alt": 20}, "peak_local": "2026-09-30T21:00:00-04:00", "light": "night"}, tz)))
# meteor shower details
tg = N.tonight(sk, loc, cf, date(2026, 12, 13), datetime(2026, 12, 13, 15, 47, tzinfo=tz)); gm = [e for e in tg["events"] if e["kind"] == "meteor"]
R.append(ok("Geminids 2026-12-13: peak night, best hours, dark > suburban, moon, radiant", gm and gm[0]["days_from_peak"] == 0 and gm[0]["rate_dark"] > gm[0]["rate_suburban"] and gm[0]["best_from_local"] and "radiant" in W.line(gm[0], tz), gm and W.line(gm[0], tz)))
# gear extras
tt = N.tonight(sk, loc, {**cf, "gear": "telescope"}, date(2026, 9, 30), datetime(2026, 9, 30, 15, 47, tzinfo=tz))
xn = [x["name"] for x in tt["extras"]]; R.append(ok("telescope extras include Saturn's rings", any("Saturn" in n for n in xn), xn))
te_ = N.tonight(sk, loc, {**cf, "gear": "eye"}, date(2026, 9, 30), datetime(2026, 9, 30, 15, 47, tzinfo=tz)); R.append(ok("eye gear: no gear extras", not te_["extras"], te_["extras"]))
# preview (WOW message) and overview card
ps = [e for e in sk.passes(top, sk.ts.from_datetime(datetime(2026, 9, 30, 17, 30, tzinfo=tz)), sk.ts.from_datetime(datetime(2026, 10, 10, tzinfo=tz)), cf, kinds=["iss"]) if not e["blocked"]]
for k in ("start_utc", "peak_utc", "end_utc"): ps[0][k.replace("_utc", "_local")] = datetime.fromisoformat(ps[0][k]).astimezone(tz).isoformat()
pv = W.preview(tn, ps[0], datetime(2026, 9, 30, 17, 30, tzinfo=tz), cf)
R.append(ok("preview: header, sunset, moon rise, ISS tonight 8:05 PM, planets", pv.startswith("Tonight from Piedmont, SC: skies look clear") and "The Sun sets at **7:15 PM**" in pv and "rises at **9:40 PM**" in pv and "tonight at 8:05 PM" in pv and "Saturn" in pv, pv))
import card as K
from stars import field as SXF
sc = K.sky_card(SXF(sk, loc, datetime(2026, 9, 30, 21, 0, tzinfo=tz)), "Your sky tonight, 9:00 PM", "test", loc, T + "/cards/tonight.png"); R.append(ok("tonight overview sky card PNG", os.path.getsize(sc) > 20000))
# ---- location never guessed (live bug: no-GPS photo, bot used a remembered town) ----
before = C.cfg()["home"]
r = run("home", "--photo", BASE + "/tests/backyard_nogps.jpg")
R.append(ok("no-GPS photo: location_set false, home untouched, plain 'couldn't find' ask with pin/coords/ZIP + iPhone tip", r["location_set"] is False and C.cfg()["home"] == before
 and r["say"].startswith("I couldn't find a location in that photo") and all(w in r["say"] for w in ("map pin", "coordinates", "ZIP", "location services")), r["say"]))
R.append(ok("no-GPS photo kept for the obstruction check", C.state().get("pending_photo", "").endswith("backyard_nogps.jpg")))
r = run("home"); R.append(ok("home with nothing given -> error, nothing set", r["location_set"] is False and C.cfg()["home"] == before, r.get("error")))
r = run("home", "29673"); R.append(ok("then a typed ZIP: set, confirmed by name, kept photo handed back", r["location_set"] and r["confirm"].startswith("Your home is ") and "ZIP 29673" in r["confirm"] and r.get("photo_for_obstructions", "").endswith("backyard_nogps.jpg"), r["confirm"]))
run("label", "home", "Piedmont, SC")
import glob, re as _re
sk_txt = {f: open(f).read() for f in glob.glob("/home/box/agent-data/workflows/look-up-*/SKILL.md")}
gs = sk_txt.get("/home/box/agent-data/workflows/look-up-getting-started/SKILL.md", "")
R.append(ok("skills: Location rule in every skill, no baked-in town, first ask has the share tip", len(sk_txt) >= 9 and all("## Location rule" in t and "Never from memories" in t for t in sk_txt.values())
 and not any(_re.search(r"Piedmont|29673", t.split("```python")[0]) for t in sk_txt.values()) and "location services are on" in gs.split("## 2)")[0], len(sk_txt)))
# ---- first big one ----
import highlight as H
hl = H.highlight(sk, loc, cf, datetime(2026, 9, 30, 17, 32, tzinfo=tz)); hr = H.reminders(sk, loc, cf, datetime(2026, 9, 30, 17, 32, tzinfo=tz), hl)
R.append(ok("first big one at 5:32 PM = tonight's bright ISS pass, weather line, remind", hl["kind"] == "iss" and hl["tier"] == 1 and hl["text"].startswith("Your first big one: **Tonight at 8:05 PM**, the International Space Station") and "forecast" in hl["text"] and hl["text"].endswith("I'll send you a reminder beforehand.") and len(hl["text"].split("\n")) == 3, hl["text"]))
R.append(ok("first big one reminders use the normal one-shot names/crons", hr and all(x["name"].startswith("Look Up one-shot 2026-09-30 ") and x["cron"].startswith("CRON_TZ=America/New_York ") and "iss-25544" in x["prompt"] for x in hr), [x["name"] for x in hr]))
h2 = H.highlight(sk, loc, cf, datetime(2026, 9, 30, 23, 0, tzinfo=tz))
R.append(ok("after tonight's pass: picks a later night, never empty", h2 and h2["at_local"] > "2026-09-30T23:00" and "tonight" not in h2["text"].split(" the ")[0] and h2["text"].startswith("Your first big one: "), h2 and h2["text"]))
_c = H.candidates; now_h = datetime(2026, 10, 1, 17, 0, tzinfo=tz); mk = lambda tier, dd, kind, q=0: {"tier": tier, "at": now_h + timedelta(days=dd, hours=3), "kind": kind, "what": kind, "q": q, "night": (now_h + timedelta(days=dd)).date().isoformat()}
H.candidates = lambda *a, **k: [mk(6, 0, "planet", 3), mk(3, 5, "meteor"), mk(5, 1, "conjunction"), mk(7, 0, "crescent")]
r1 = H.highlight(sk, loc, cf, now_h)["kind"]
H.candidates = lambda *a, **k: [mk(3, 2, "meteor"), mk(1, 6, "iss", 1), mk(2, 1, "starlink")]
r2 = H.highlight(sk, loc, cf, now_h)["kind"]
H.candidates = lambda *a, **k: [mk(6, 0, "planet", 2), mk(6, 9, "planet", 2.5)]
r3 = H.highlight(sk, loc, cf, now_h)["at_local"][:10]
H.candidates = _c
R.append(ok("wow ranking: meteor > pairing > planet > crescent; ISS > Starlink > meteor; same tier sooner wins", (r1, r2, r3) == ("meteor", "iss", "2026-10-01"), (r1, r2, r3)))
st2 = C.state(); st2["reminders"].append({"date": "2026-09-30", "name": hr[0]["name"], "events": hr[0]["events"]})
p2 = N.plan(tn, cf, datetime(2026, 9, 30, 15, 47, tzinfo=tz), st2)
R.append(ok("daily check doesn't double-nudge an event the first big one already scheduled", not any("iss-25544-202610010005" in x["events"] and "reminder" in x["name"] for x in p2["reminders"]), [(x["name"], x["events"]) for x in p2["reminders"]]))
# ---- v3: card URLs, facts, Q2 widget, highlight tiers, professional voice ----
import io, contextlib
def nm(*a):
 b = io.StringIO()
 with contextlib.redirect_stdout(b): N.main(list(a))
 return json.loads(b.getvalue())
pvj = nm("preview", "--at", "2026-09-30T17:30:00-04:00"); cdj = nm("card", "--events", "iss-25544-202610010005", "--date", "2026-09-30")
R.append(ok("card_url = file:// + absolute path (preview, card command); None when no card", all(x.get("card_url", "").startswith("file:///") and x["card_url"][7:] == os.path.abspath(x["card"]) and os.path.exists(x["card"]) for x in (pvj, cdj)) and C.url(None) is None, (pvj.get("card_url"), cdj.get("card_url"))))
_ns = open(os.path.join(os.path.dirname(N.__file__), "night.py")).read()
R.append(ok("every night.py output that returns a card also returns card_url", _ns.count('"card_url"') >= 4 and 'p["card_url"]' in _ns and 'out["card_url"]' in _ns))
R.append(ok("preview: highlight is tonight's pass -> one professional station line, then the first big one", "The space station makes an excellent pass tonight; details below." in pvj["text"] and "\n\nYour first big one: **Tonight at 8:05 PM**" in pvj["text"], pvj["text"]))
pv0 = W.preview(tn, None, datetime(2026, 9, 30, 17, 30, tzinfo=tz), cf)
R.append(ok("preview with no good ISS pass in 10 days: no ISS line at all", "space station" not in pv0.lower() and "ISS" not in pv0, pv0))
import facts as F, facts_sky as FS
lc = F.lib_check(); R.append(ok("fact library: every object 4+ facts (moon phases 3+), all 21 constellations and 12 showers covered", not lc["short"] and lc["constellations"] == 21 and lc["showers"] == 12 and not lc["short_cons"] and not lc["short_showers"] and lc["facts"] > 250, lc))
d0 = date(2027, 1, 1); seen = [F.pick("iss", d0 + timedelta(days=i)) for i in range(len(F.F["iss"]))]
R.append(ok("facts rotate: no repeat until the pool is used, and none within 14 days", len(set(seen)) == len(seen) and F.pick("iss", d0 + timedelta(days=len(seen))) == seen[0], len(seen)))
fu = dict(C.state().get("facts_used", {})); F.DRY = True; F.pick("saturn"); F.line("jupiter"); F.DRY = False
R.append(ok("test mode (facts.DRY) never uses up a fact", C.state().get("facts_used", {}) == fu))
_hu = N.plan(tn, cf, datetime(2026, 9, 30, 15, 47, tzinfo=tz))["headsup"] or ""
_facts = [x for v in F.F.values() for x in v]
R.append(ok("heads-up carries exactly one fact, on its own line, no 'Fun fact'", sum(1 for ln in _hu.split("\n") if any(f in ln for f in _facts)) == 1 and "fun fact" not in _hu.lower(), _hu))
ans = __import__("stars").answer([{"name": "Saturn", "kind": "planet", "where": "southeast, about halfway up", "confirm": "it shines steadily", "confidence": "high"}])
R.append(ok("what-is-that text: bold answer, confirm, one fact, method line", ans.startswith("That is almost certainly **Saturn**") and sum(1 for ln in ans.split("\n") if any(f in ln for f in F.F["saturn"])) == 1 and ans.endswith("not by recognizing the light itself."), ans))
q2 = {"Everything I can see": set(C.ALERTS), "Space station & satellites": {"iss", "satellites", "starlink", "eclipses"}, "Moon & planets": {"moon", "planets", "eclipses"},
 "Constellations": {"constellation", "eclipses"}, "Meteor showers, comets & eclipses": {"meteors", "comets", "eclipses"}, "Aurora & rocket launches": {"aurora", "rockets", "eclipses"}}
got = {}
for lab_, want in q2.items(): run("set-alerts", lab_); got[lab_] = {k for k, v in C.cfg()["alerts"].items() if v} == want
run("set-alerts", "Everything I can see")
R.append(ok("Q2 widget: six options map to the right alerts (Starlink rides with satellites)", all(got.values()) and len(q2) == 6, got))
H.candidates = lambda *a, **k: [mk(6, 0, "planet", 3), mk(5.5, 1, "station"), mk(9, 0, "satellite", 9)]
r4 = H.highlight(sk, loc, cf, now_h)["kind"]; H.candidates = _c
run("hours", "Early mornings too"); hc = [c for c in H.candidates(sk, loc, C.cfg(), datetime(2026, 9, 30, 17, 32, tzinfo=tz), 7) if c["kind"] == "station"]; run("hours", "Dusk to 11pm")
R.append(ok("tier 5.5: a high Tiangong pass outranks a bright planet; generic satellites never compete", r4 == "station" and any(c["tier"] == 5.5 and "Tiangong" in c["what"] for c in hc), (r4, [(c["tier"], c["what"][:40]) for c in hc][:4])))
R.append(ok("planet highlight is specific (Saturn: rings in a small telescope)", "rings" in H.PLANET_WOW["Saturn"] and "moons" in H.PLANET_WOW["Jupiter"]))
_all = _hu + pvj["text"] + ans
R.append(ok("voice: no slang or filler in engine text", not _re.search(r"Anytime it is|no promises|\bgonna\b|\bwow\b|!|Fun fact|Label:", _all), _re.findall(r"Anytime it is|no promises|!|Fun fact", _all)))
print(f"\n{sum(R)}/{len(R)} passed")
