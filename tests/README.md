# Look Up tests
`python3 tests/run_tests.py` (85 checks: location from photo/pin/ZIP/town, settings parsing, travel mode, day/twilight/night, eclipses, comets, meteor showers, preview, what-is-that).
Fixtures: set `LOOKUP_FIXTURES` to a folder holding `test-piedmont/{data,cache}` and `tests/*.jpg`; the engine is read from `$LOOKUP_FIXTURES/engine`.
Known: 4 ISS-pass checks expect a pass at 8:05 PM against cached orbital data; they currently see 8:04 PM and fail. Freeze the clock or update the expected time before turning CI on.
