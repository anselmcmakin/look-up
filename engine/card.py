# look-up v2 | card.py: sky-map PNG cards (map view: north up, east right, center = straight overhead). Deep navy sky, soft star glow.
import math, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo
import core as C
NAVY, INK, GOLD, SOFT = "#0a1430", "#dfe7ff", "#ffd27a", "#8fa3d6"
def _base(title, sub, loc):
 fig = plt.figure(figsize=(6, 7.2), dpi=150, facecolor=NAVY); ax = fig.add_axes([0.1, 0.15, 0.8, 0.67], projection="polar", facecolor="none")
 bg = fig.add_axes([0, 0, 1, 1], zorder=-1); bg.axis("off")
 y, x = np.mgrid[-1:1:300j, -1:1:300j]; r = np.sqrt(x ** 2 + (y + .1) ** 2)
 bg.imshow(np.clip(1 - r * .7, 0, 1), cmap=matplotlib.colors.LinearSegmentedColormap.from_list("n", ["#050a1c", "#0d1c45"]), extent=[0, 1, 0, 1], aspect="auto")
 ax.set_theta_zero_location("N"); ax.set_theta_direction(-1); ax.set_ylim(0, 90); ax.set_yticks([30, 60]); ax.set_yticklabels([]); ax.grid(color=SOFT, alpha=.18, ls=":")
 ax.set_xticks(np.radians(range(0, 360, 45))); ax.set_xticklabels(["N", "NE", "E", "SE", "S", "SW", "W", "NW"], color=INK, fontsize=11, fontweight="bold")
 ax.spines["polar"].set_color(SOFT); ax.spines["polar"].set_alpha(.6)
 for o in C.cfg().get("obstructions") or []:
  a, b = o["from"], o["to"] if o["to"] >= o["from"] else o["to"] + 360; t = np.radians(np.linspace(a, b, 40))
  ax.fill_between(t, 90 - o["below"], 90, color="#1e2a1e", alpha=.75, lw=0); ax.text(np.radians((a + b) / 2), 90 - o["below"] / 2, _olab(o.get("note", "")), color="#9fb59f", fontsize=7, ha="center")
 fig.text(.5, .94, title, color=INK, fontsize=15, ha="center", fontweight="bold"); fig.text(.5, .895, sub, color=SOFT, fontsize=10, ha="center")
 fig.text(.5, .035, f"Look Up  |  {loc}  |  map view: center is straight overhead, edge is the horizon", color=SOFT, fontsize=7.5, ha="center")
 return fig, ax
def _field(ax, pts, skip=()):
 """Real stars (size by brightness), planets labeled, brightest stars labeled. No decorative fake stars."""
 for p in pts or []:
  if p.get("name") in skip: continue
  if p["kind"] == "moon": _glow(ax, p["az"], p["alt"], p["name"], "#f2f2e6", 90); continue
  if p["kind"] == "planet": _glow(ax, p["az"], p["alt"], p["name"], "#ffe9b8", 28); continue
  sz = max(1.5, 14 * (10 ** (-0.4 * p["mag"])) ** .5)
  ax.scatter([math.radians(p["az"])], [90 - p["alt"]], s=sz * 5, c="#9fb4ff", alpha=.08, lw=0); ax.scatter([math.radians(p["az"])], [90 - p["alt"]], s=sz, c="white", alpha=.85, lw=0)
  if p.get("name") and p["mag"] < 0.9 and p["alt"] > 8: ax.annotate(p["name"], (math.radians(p["az"]), 90 - p["alt"]), xytext=(4, -9), textcoords="offset points", color=SOFT, fontsize=7)
def _olab(n):
 w = (n.split() or ["blocked"])[0]; return "blocked" if w[0].isdigit() or w.lower() in ("north", "south", "east", "west", "n", "s", "e", "w", "ne", "nw", "se", "sw") else w
def _glow(ax, az, alt, label, color=GOLD, size=60):
 for k, a in ((6, .05), (3, .12), (1.6, .3)): ax.scatter([math.radians(az)], [90 - alt], s=size * k, c=color, alpha=a, lw=0)
 ax.scatter([math.radians(az)], [90 - alt], s=size * .5, c=color, lw=0, zorder=5)
 if label:
  rt = 30 < az % 360 < 150 and alt < 35  # near the east rim: put the label inside so it doesn't hit the compass letter
  ax.annotate(label, (math.radians(az), 90 - alt), xytext=(-7, 7) if rt else (7, 7), ha="right" if rt else "left", textcoords="offset points", color=INK, fontsize=8.5)
def pass_card(e, tn, path, pts=None):
 tz = ZoneInfo(tn["location"]["tz"]); t = lambda k: C.hhmm(datetime.fromisoformat(e[k]).astimezone(tz))
 nm = {"iss": "The ISS", "station": e["name"], "starlink": "Starlink train"}.get(e["kind"], e["name"])
 fig, ax = _base(f"{nm}, {t('start_local')}", datetime.fromisoformat(e["start_local"]).strftime("%A %b %d") + f"  |  peak {t('peak_local')}, {C.where(e['peak']['az'], e['peak']['alt'])}", tn["location"]["label"])
 pa = np.array(e.get("path") or [[e["start"]["az"], e["start"]["alt"]], [e["peak"]["az"], e["peak"]["alt"]]])
 th, r = np.radians(pa[:, 0]), 90 - pa[:, 1]
 for w, a in ((9, .08), (5, .15)): ax.plot(th, r, color=GOLD, lw=w, alpha=a, solid_capstyle="round")
 ax.plot(th, r, color=GOLD, lw=2); i = max(1, len(th) - 3)
 ax.annotate("", xy=(th[-1], r[-1]), xytext=(th[i - 1], r[i - 1]), arrowprops=dict(arrowstyle="-|>", color=GOLD, lw=2))
 for k, lab in (("start", f"appears {t('start_local')}"), ("peak", f"peak {t('peak_local')}"), ("end", ("fades " if e.get("fades_in_shadow") else "sets ") + t("end_local"))):
  if e.get(k): _glow(ax, e[k]["az"], e[k]["alt"], lab, size=30 if k != "peak" else 55)
 _field(ax, pts)
 os.makedirs(os.path.dirname(path), exist_ok=True); fig.savefig(path, facecolor=NAVY); plt.close(fig); return path
def constellation(c, loc, path):
 fig, ax = _base(f"{c['name']}: constellation of the week", datetime.fromisoformat(c["at"]).strftime("%a %b %d, %I:%M %p").replace(" 0", " ") + f"  |  {c['where']}", loc["label"])
 _field(ax, c.get("field"), skip=(c.get("anchor"),)); st = c["stars"]
 for i, j in c["lines"]:
  ax.plot([math.radians(st[i][1]), math.radians(st[j][1])], [90 - st[i][0], 90 - st[j][0]], color=SOFT, lw=1.2, alpha=.8)
 for k, (al, az) in enumerate(st): _glow(ax, az, al, (c.get("anchor") if k == 0 else None), "#ffffff" if k else GOLD, 40 if k else 70)
 import textwrap; fig.text(.5, .075, "\n".join(textwrap.wrap(c["find"], 88)[:3]), color=INK, fontsize=8, ha="center", va="center")
 os.makedirs(os.path.dirname(path), exist_ok=True); fig.savefig(path, facecolor=NAVY); plt.close(fig); return path
def sky_card(pts, title, sub, loc, path):
 """Tonight overview: real bright stars, planets and moon at one moment."""
 fig, ax = _base(title, sub, loc["label"]); _field(ax, pts)
 for p in pts:
  if p["kind"] == "star" and p.get("name") and 0.9 <= p["mag"] < 1.4 and p["alt"] > 15: ax.annotate(p["name"], (math.radians(p["az"]), 90 - p["alt"]), xytext=(4, -9), textcoords="offset points", color=SOFT, fontsize=7)
 os.makedirs(os.path.dirname(path), exist_ok=True); fig.savefig(path, facecolor=NAVY); plt.close(fig); return path
