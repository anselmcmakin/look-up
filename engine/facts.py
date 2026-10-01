# look-up v2 | facts.py: vetted one-line space facts (NASA/ESA-level numbers, no live data), rotated per user so none repeats within ~2 weeks.
import os, sys, re
from datetime import date, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C
DRY = False  # test mode: pick facts without recording them
F = {
"iss": ["The ISS travels at about 17,500 mph and circles Earth roughly every 90 minutes, so its crew sees about 16 sunrises a day.",
 "The station has been continuously crewed since November 2000, the longest unbroken human presence in space.",
 "End to end, including its solar arrays, the ISS is about the length of a football field.",
 "The ISS orbits about 250 miles (400 km) up. What you see is sunlight reflecting off its solar arrays and modules.",
 "The station weighs almost a million pounds, assembled piece by piece over more than a decade.",
 "Astronauts on the ISS exercise about two hours a day to limit the muscle and bone loss that comes with weightlessness.",
 "More than 270 people from over 20 countries have visited the ISS.",
 "Its pressurized space is larger than a six-bedroom house.",
 "The first module, Russia's Zarya, launched in November 1998.",
 "The ISS is a partnership of five space agencies: NASA, Roscosmos, ESA, JAXA, and the Canadian Space Agency.",
 "At about 5 miles per second, the ISS could cross the continental United States in roughly 10 minutes.",
 "Thin air at its altitude slowly drags the ISS lower, so visiting spacecraft periodically fire engines to boost it back up.",
 "About 98% of the station's water is recovered and recycled, including moisture from the crew's breath and sweat.",
 "NASA plans to retire the ISS around 2030 and guide it down over a remote stretch of the Pacific Ocean.",
 "At its brightest, the ISS outshines every star in the night sky."],
"tiangong": ["Tiangong means \"Heavenly Palace.\" It is China's space station, and it has hosted rotating crews since 2021.",
 "Tiangong is built from three main modules: Tianhe, Wentian, and Mengtian.",
 "Tiangong orbits a little lower than the ISS, at roughly 240 miles (about 390 km).",
 "Tiangong has roughly a quarter of the mass of the ISS.",
 "Crews of three typically live aboard Tiangong for about six months at a time.",
 "Like the ISS, Tiangong circles Earth about every 90 minutes."],
"hubble": ["Hubble launched in 1990 aboard the Space Shuttle Discovery.",
 "Hubble is about the size of a school bus, and its main mirror is 2.4 meters (7.9 feet) across.",
 "Astronauts visited Hubble five times on Space Shuttle missions to repair and upgrade it.",
 "Hubble has made more than 1.5 million observations since launch.",
 "Hubble orbits a little over 300 miles up, above most of the atmosphere's blurring.",
 "Hubble's measurements helped pin down how fast the universe is expanding."],
"starlink": ["Starlink is SpaceX's internet constellation, with thousands of satellites in low Earth orbit.",
 "A fresh Starlink train looks like a string of pearls because the satellites have not yet spread out along their orbits.",
 "New Starlink satellites are released low and use small electric thrusters to climb to their working orbit, around 340 miles (550 km) up.",
 "Starlink trains fade within days as the satellites raise their orbits and turn their panels edge-on.",
 "SpaceX has used coatings and design changes to make newer Starlink satellites dimmer after concerns from astronomers.",
 "Each Starlink launch typically carries a few dozen satellites."],
"satellite": ["Satellites shine only by reflected sunlight. After dusk they are still in sunshine high above you while the ground is already dark.",
 "When a satellite fades out in the middle of the sky, it has slipped into Earth's shadow.",
 "More than 10,000 active satellites now orbit Earth.",
 "Most low-orbit satellites take about 90 to 100 minutes to circle Earth once.",
 "A steady light with no blinking sets a satellite apart from an aircraft.",
 "The first artificial satellite, Sputnik 1, launched in October 1957.",
 "Low-orbit satellites are easiest to see in the first couple of hours after dusk and before dawn.",
 "Space surveillance networks track tens of thousands of objects in orbit, including debris."],
"rocket_body": ["Spent rocket stages left in orbit often tumble, which can make them flicker as they pass.",
 "Old upper stages are among the largest pieces of debris in orbit, and many have been up there for decades.",
 "Soviet-era upper stages are among the most common bright rocket bodies still circling Earth.",
 "Drag from the thin upper atmosphere slowly lowers old rocket stages until they burn up on reentry.",
 "A rocket body reflects sunlight the same way a satellite does; it has no lights of its own."],
"mercury": ["Mercury circles the Sun every 88 days, faster than any other planet.",
 "Mercury never strays far from the Sun in our sky, so it is only seen low in twilight.",
 "Despite being closest to the Sun, Mercury is not the hottest planet. Venus is, because of its thick atmosphere.",
 "On Mercury, one sunrise to the next takes about 176 Earth days.",
 "Mercury is only a little larger than our Moon.",
 "NASA's MESSENGER spacecraft found water ice in permanently shadowed craters near Mercury's poles."],
"venus": ["Venus is the brightest planet because thick, reflective clouds cover it completely.",
 "The surface of Venus is about 870°F (465°C), hot enough to melt lead.",
 "Venus spins backward compared with most planets, and one rotation takes longer than its year.",
 "Venus is nearly Earth's twin in size.",
 "Through a telescope, Venus shows phases like the Moon. Galileo used this as evidence that planets orbit the Sun.",
 "The clouds of Venus are made largely of sulfuric acid droplets."],
"mars": ["Mars gets its red color from iron oxide, essentially rust, in its dust.",
 "Olympus Mons on Mars is the largest volcano in the solar system, about two and a half times the height of Mount Everest.",
 "A day on Mars lasts about 24 hours and 37 minutes.",
 "Mars has two small moons, Phobos and Deimos.",
 "The brightness of Mars changes a lot because its distance from Earth ranges from about 35 to 250 million miles.",
 "NASA's Curiosity and Perseverance rovers are exploring the surface of Mars."],
"jupiter": ["Jupiter is more than twice as massive as all the other planets combined.",
 "Jupiter's Great Red Spot is a storm wider than Earth.",
 "Binoculars held steady can show up to four of Jupiter's largest moons, the ones Galileo discovered in 1610.",
 "A day on Jupiter lasts under 10 hours, the shortest of any planet.",
 "About 1,300 Earths could fit inside Jupiter.",
 "Jupiter's moon Europa likely hides a salty ocean beneath its icy crust."],
"saturn": ["Saturn's rings are mostly water ice, in pieces ranging from tiny grains to chunks as large as mountains.",
 "Saturn's main rings span about 175,000 miles but are typically only about 30 feet thick.",
 "Saturn is less dense than water. In a large enough bathtub, it would float.",
 "Sunlight reflected from Saturn takes more than an hour to reach your eyes.",
 "Saturn's largest moon, Titan, is bigger than the planet Mercury and has a thick atmosphere.",
 "Saturn is about nine and a half times farther from the Sun than Earth is.",
 "Even a small telescope at about 30x magnification shows Saturn's rings."],
"uranus": ["Uranus rolls around the Sun on its side, tilted about 98 degrees.",
 "Uranus was the first planet discovered with a telescope, by William Herschel in 1781.",
 "Methane in its atmosphere gives Uranus its blue-green color.",
 "Uranus takes 84 Earth years to orbit the Sun once.",
 "Under very dark skies, Uranus sits right at the edge of naked-eye visibility."],
"neptune": ["Neptune was predicted mathematically from its pull on Uranus before it was first seen in 1846.",
 "Neptune has the fastest winds measured in the solar system, over 1,200 mph.",
 "Neptune takes about 165 years to orbit the Sun and completed its first orbit since discovery in 2011.",
 "Voyager 2 is the only spacecraft to have visited Neptune, flying past in 1989.",
 "Neptune's largest moon, Triton, orbits backward and is probably a captured object."],
"moon": ["The Moon is about 239,000 miles (384,000 km) away on average.",
 "We always see the same side of the Moon because it spins exactly once for each trip around Earth.",
 "The Moon is drifting away from Earth by about 1.5 inches (3.8 cm) a year.",
 "Twelve astronauts walked on the Moon between 1969 and 1972.",
 "Moonlight is reflected sunlight, and the lunar surface is about as dark as worn asphalt.",
 "The Moon is a little more than a quarter of Earth's width.",
 "The Moon most likely formed from debris thrown out when a Mars-sized body struck the young Earth.",
 "With almost no atmosphere, the Moon keeps its craters for billions of years.",
 "The Moon's gravity drives most of Earth's ocean tides.",
 "The lunar surface swings from about 250°F (120°C) in sunlight to about -208°F (-130°C) at night."],
"moon_new": ["At new Moon, the Moon sits between Earth and the Sun with its lit side facing away from us.",
 "Solar eclipses can happen only at new Moon.",
 "New Moon nights are the darkest of the month, the best time for the Milky Way and faint meteors."],
"moon_crescent": ["The faint glow on the dark part of a crescent is earthshine, sunlight reflected from Earth onto the Moon and back.",
 "Leonardo da Vinci correctly explained earthshine about 500 years ago.",
 "An evening crescent sets a few hours after the Sun; a morning crescent rises a few hours before it."],
"moon_quarter": ["Near quarter phase, long shadows along the line between light and dark show craters in sharp relief, a fine view in binoculars.",
 "A quarter Moon is only about a tenth as bright as a full Moon, not half.",
 "A half-lit Moon is called a quarter because the Moon has traveled a quarter, or three quarters, of its orbit since new Moon."],
"moon_gibbous": ["A gibbous Moon is more than half lit; the word comes from a Latin root meaning \"hump.\"",
 "A waning gibbous Moon rises later each night, by roughly 50 minutes.",
 "A waxing gibbous Moon is up in the afternoon and evening, often visible in daylight."],
"moon_full": ["A full Moon rises around sunset and sets around sunrise.",
 "The full Moon looks larger near the horizon, but that is an illusion; its size in the sky barely changes.",
 "The full Moon sits opposite the Sun, which is why lunar eclipses can only happen then."],
"sun": ["Sunlight takes about 8 minutes and 20 seconds to reach Earth.",
 "About 1.3 million Earths could fit inside the Sun.",
 "Civil, nautical, and astronomical twilight end when the Sun is 6, 12, and 18 degrees below the horizon.",
 "The visible surface of the Sun is about 10,000°F (5,500°C).",
 "The Sun holds about 99.8% of all the mass in the solar system.",
 "Never look at the Sun directly or through binoculars or a telescope without a certified solar filter; it can permanently damage your eyes."],
"comet": ["Comets are leftover ice and dust from the formation of the solar system.",
 "A comet's tail always points away from the Sun, pushed by sunlight and the solar wind.",
 "A comet's solid nucleus is usually only a few miles across, yet its tail can stretch millions of miles.",
 "Many long-period comets come from the distant Oort Cloud, far beyond Neptune.",
 "Comet brightness is hard to predict; some fade unexpectedly and others brighten beyond forecasts."],
"aurora": ["Auroras form when charged particles from the Sun strike gases in the upper atmosphere, roughly 60 to 200 miles up.",
 "Green aurora comes from oxygen; deep red from oxygen higher up; blue and purple from nitrogen.",
 "Phone cameras often capture aurora colors that the eye sees only as a faint gray glow.",
 "Strong solar storms push the aurora toward the equator. In May 2024 it was seen across much of the United States.",
 "The Kp index runs from 0 to 9; the higher it climbs, the farther from the poles the aurora can be seen.",
 "The Sun's activity rises and falls over a cycle of roughly 11 years."],
"eclipse_solar": ["A total solar eclipse is possible because the Sun is about 400 times wider than the Moon and also about 400 times farther away.",
 "Even with 99% of the Sun covered, the sky stays surprisingly bright; only totality turns day into night.",
 "The next total solar eclipse visible from the contiguous United States is in August 2044.",
 "Solar eclipses happen only at new Moon, when the Moon passes directly between Earth and the Sun.",
 "During a partial eclipse, gaps between tree leaves project dozens of small crescent suns on the ground."],
"eclipse_lunar": ["A totally eclipsed Moon turns coppery red because Earth's atmosphere bends red sunlight into the shadow.",
 "Lunar eclipses are safe to watch with your eyes, binoculars, or a telescope.",
 "A lunar eclipse is visible from the entire night side of Earth at the same time.",
 "Totality during a lunar eclipse can last up to about an hour and 45 minutes.",
 "Ancient Greek astronomers saw Earth's curved shadow on the eclipsed Moon as evidence that Earth is round."],
"rocket": ["A rocket must reach about 17,500 mph to stay in low Earth orbit.",
 "After sunset, a rocket's exhaust plume can catch sunlight high above you and glow like a jellyfish.",
 "Most rockets launch eastward to borrow speed from Earth's rotation.",
 "SpaceX regularly lands Falcon 9 first stages on drone ships or landing pads so they can fly again.",
 "From hundreds of miles away, a launch looks like a bright star climbing slowly, sometimes splitting as stages separate."],
"star": ["Stars twinkle because their light passes through moving layers of air; planets, which show tiny disks, shine more steadily.",
 "The starlight you see tonight left those stars years, centuries, or even millennia ago.",
 "A star's color shows its temperature: red stars are cooler, blue-white stars much hotter.",
 "The Sun is an ordinary star; many stars you see at night are far larger and brighter."],
}
LEADS = ["", "Worth knowing: ", "", "For context: ", ""]
def key_for(e):
 """Map an engine event (or a what-is-that candidate) to a fact key."""
 k, n = e.get("kind"), (e.get("name") or "")
 if k == "iss": return "iss"
 if k in ("station", "satellite"):
  if re.search(r"tiangong|\bcss\b", n, re.I): return "tiangong"
  if re.search(r"hubble|\bhst\b", n, re.I): return "hubble"
  if re.search(r"\biss\b|zarya", n, re.I): return "iss"
  return "rocket_body" if re.search(r"r/b|rocket", n, re.I) else "satellite"
 if k == "starlink": return "starlink"
 if k in ("planet", "dayvenus"): return "venus" if k == "dayvenus" else n.lower()
 if k == "conjunction": return [w.lower() for w in re.findall(r"Mercury|Venus|Mars|Jupiter|Saturn", n)][-1] if re.search(r"Mercury|Venus|Mars|Jupiter|Saturn", n) else "moon"
 if k in ("moon", "daymoon"): return moon_key(e.get("phase", ""))
 if k == "meteor": return "shower:" + n
 if k == "eclipse": return "eclipse_" + e.get("eclipse", "lunar")
 if k in ("aurora", "comet", "rocket"): return k
 if k == "constellation": return "cons:" + n
 if k == "star": return "star:" + n
 return None
def moon_key(phase):
 p = phase.lower()
 return "moon_new" if "new" in p else "moon_full" if "full" in p else "moon_crescent" if "crescent" in p else "moon_quarter" if "quarter" in p else "moon_gibbous" if "gibbous" in p else "moon"
def pool(key):
 if not key: return []
 if key.startswith(("cons:", "star:", "shower:")):
  import facts_sky as FS; return FS.lookup(key) + (F["star"] if key.startswith("star:") else [])
 if key.startswith("moon_"): return F[key] + F["moon"]
 return F.get(key, [])
def pick(key, today=None):
 """One fact for `key`, never one used in the last 14 days if avoidable (least recently used otherwise). Records use in state."""
 fs = pool(key)
 if not fs: return None
 st = C.state(); used = st.setdefault("facts_used", {}); today = today or date.today()
 age = lambda f: (today - date.fromisoformat(used[f])).days if f in used else 10 ** 6
 f = max(fs, key=lambda x: (min(age(x), 15), -fs.index(x)))  # unused or 2+ weeks old first, in list order
 if not DRY:
  used[f] = today.isoformat(); st["facts_n"] = st.get("facts_n", 0) + 1
  if len(used) > 400: [used.pop(k) for k in sorted(used, key=used.get)[:100]]
  C.save_state(st)
 return f
def line(key, today=None):
 """The fact as its own line, with a varied, natural lead-in (or none)."""
 f = pick(key, today)
 if not f: return ""
 n = C.state().get("facts_n", 0); return "\n" + LEADS[n % len(LEADS)] + f
def lib_check():
 """Every object the engine can mention has at least 4 facts."""
 import facts_sky as FS
 short = {k: len(v) for k, v in F.items() if len(v) < 3 or (not k.startswith("moon_") and len(v) < 4)}
 return {"objects": len(F), "facts": sum(len(v) for v in F.values()) + FS.count(), "short": short, **FS.check()}
