# look-up v2 | hours.py: outside-hours parsing ("8pm-11pm", "dusk to 11", "early mornings too", "anytime") into windows. Pure functions.
import re
def _cands(x):
 m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|a|p)?", x.strip())
 if not m: raise ValueError(f"can't read the time '{x}'")
 h, mi, ap = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "")[:1]
 if ap: return [((h % 12) + (12 if ap == "p" else 0)) * 60 + mi]
 if h > 12 or h == 0: return [h % 24 * 60 + mi]
 return [(h % 12) * 60 + mi, (h % 12 + 12) * 60 + mi]
def parse_time(x):
 c = _cands(x.lower()); v = c[-1] if len(c) == 2 and 5 <= int(x.split(":")[0]) <= 11 else c[0]
 return f"{v // 60:02d}:{v % 60:02d}"
KW = {"dusk": "sunset", "sunset": "sunset", "dark": "dark", "nightfall": "dark", "sunrise": "sunrise", "dawn": "predawn", "predawn": "predawn", "midnight": "00:00", "noon": "12:00"}
def parse_window(s):
 """'8pm-11pm', '9 to 12:30am', 'dusk to 11pm', '5am-sunrise' -> {start, end}. Ambiguous hours pick the shortest night-time window.
 Keywords: sunset/dusk, dark (end of astronomical twilight), predawn (100 min before sunrise), sunrise."""
 parts = re.split(r"\s*(?:-|–|—|\bto\b|\buntil\b|\btill\b|\bthrough\b)\s*", s.lower().strip())
 if len(parts) != 2: raise ValueError("use a range like 8pm-11pm, 20:00-23:00, or dusk to 11pm")
 parts = [re.sub(r"^(?:from|after|around|about|at|by|before)\s+|\s*\(default\)$", "", p.strip()).removeprefix("the ") for p in parts]
 k = [KW.get(p) for p in parts]
 if any(x and ":" not in x for x in k):
  def f(i):
   if k[i]: return k[i]
   c = _cands(parts[i]); o = k[1 - i]
   if len(c) == 2 and o in ("sunrise", "predawn", "sunset", "dark"): v = c[0] if o in ("sunrise", "predawn") else c[1]; return f"{v // 60:02d}:{v % 60:02d}"
   return parse_time(parts[i])
  return {"start": f(0), "end": f(1)}
 parts = [k[i] or parts[i] for i in range(2)]
 best = None
 for a in _cands(parts[0]):
  for b in _cands(parts[1]):
   dur = (b - a) % 1440
   if dur == 0: continue
   key = (dur, 0 if (a >= 17 * 60 or a < 7 * 60) else 1)
   if best is None or key < best[0]: best = (key, a, b)
 if not best: raise ValueError("start and end are the same")
 f = lambda v: f"{v // 60:02d}:{v % 60:02d}"; return {"start": f(best[1]), "end": f(best[2])}
def parse_hours(s):
 """Widget answers or free text -> list of windows. 'Dusk to 11pm' / 'Early mornings too' / 'Anytime' / '8-11pm and 5-6am'."""
 t = s.lower().strip()
 if "anytime" in t or "any time" in t or "all day" in t: return [{"start": "12:00", "end": "11:59"}]
 if "early morning" in t or "mornings too" in t: return [{"start": "sunset", "end": "23:00"}, {"start": "predawn", "end": "sunrise"}]
 if re.fullmatch(r"(dusk|sunset) to 11 ?pm( \(default\))?", t): return [{"start": "sunset", "end": "23:00"}]
 return [parse_window(p) for p in re.split(r"\s*(?:,|\band\b|\bplus\b|;)\s*", t) if p]
