# Look Up

The sky engine behind the **Look Up** Grok Bot template: a backyard stargazing guide that tells you when something is worth stepping outside for, such as a bright space station pass, a fresh Starlink train, planets, meteor showers, eclipses or aurora, and exactly where to look.

The template's skills hold only instructions. On first run they download the Python files in `engine/` from a tagged release of this repo, check each file against a pinned SHA-256 list, and install them into `/workspace/look-up/`.

## What's here

| Path | Purpose |
| --- | --- |
| `engine/core.py` | Settings, location (photo EXIF GPS, map pins, coordinates, ZIP or town), caching |
| `engine/sky.py` | Satellite passes, Moon, planets, aurora outlook, clouds, launches |
| `engine/tonight.py`, `engine/night.py` | One night's sky, the daily plan, reminders, previews |
| `engine/highlight.py` | "Your first big one": the best sight in the next 1 to 2 weeks |
| `engine/events.py` | Comets, eclipses (2026 to 2030), meteor showers, binocular and telescope targets |
| `engine/stars.py` | Bright stars, constellations, "what am I looking at?" |
| `engine/words.py` | Message wording |
| `engine/facts.py`, `engine/facts_sky.py` | Fact library (one rotating fact per message) |
| `engine/card.py`, `engine/hours.py` | Sky-map PNG cards; parsing of viewing hours |
| `install.py` | Reference installer (download, SHA-256 check, `core.py init`) |
| `SHA256SUMS` | Checksums for the files in `engine/` |

Install by hand: `python3 install.py`. Set `LOOKUP_DIR` to install somewhere other than `/workspace/look-up`, and `LOOKUP_BASE_URL` to download from a mirror or a local server.

Requirements: Python 3.10+, plus `skyfield timezonefinder Pillow pillow-heif exifread matplotlib requests` (the installer adds them if they're missing).

## Data sources

All are free and public. Requests are low-volume, cached, and back off on refusals.

- [CelesTrak](https://celestrak.org): GP orbital elements (stations, bright satellites, recent launches)
- NASA JPL DE421 planetary ephemeris, via [Skyfield](https://rhodesmill.org/skyfield/) (downloaded once, about 17 MB)
- [NOAA SWPC](https://www.swpc.noaa.gov): planetary Kp forecast
- [Open-Meteo](https://open-meteo.com): hourly cloud cover
- [The Space Devs Launch Library 2](https://thespacedevs.com): upcoming launches
- [Minor Planet Center](https://minorplanetcenter.net): comet orbital elements
- [OpenStreetMap Nominatim](https://nominatim.openstreetmap.org) and [Zippopotam.us](https://zippopotam.us): place names and ZIP codes
- Meteor shower data follow the IMO calendar; facts are drawn from NASA, ESA, NOAA and IAU material

## Licence

MIT. See [LICENSE](LICENSE). Copyright 2026 Ansel McMakin.
