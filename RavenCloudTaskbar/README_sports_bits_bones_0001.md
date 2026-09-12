# FR0333.SPORTS.BITS.BONES.0001

Purpose: convert sports-event observations into a reference-point metric rail without collapsing live score, final result, media views, television audience, schedule, and standings into one metric class.

## Core model

`BONES = SPORT + LEAGUE + TEAM + EVENT + DATE + VENUE + SERIES + SCHEDULE`

`BITS = SCORE + INNING + TIME + RESULT + STANDINGS + PITCHER.DATA + AUDIENCE.DATA + MEDIA.VIEWS + VIDEO.RUNTIME`

`EVENT → SOURCE → REFERENCE.POINT → SCORE → TIME → RESULT → AUDIENCE → MEDIA.VIEWS → STANDINGS → DELTA → RECEIPT`

## Reference-point fixture

Fixture: `RP.FIXTURE.MLB.SUBWAY.SERIES.2026.09.12.0001`

Source class: user-provided screenshot plus transcribed Google Sports data.

Observed reference points:

- `RP.01.CURRENT.GAME` — Mets vs. Yankees, 2026-09-12, Yankee Stadium, observed score Mets 3 / Yankees 0, game state `ONGOING`, final result `UNKNOWN`.
- `RP.02.COMPLETED.ROWS` — four listed completed games. Derived record from those rows only: Mets 2 wins / Yankees 2 wins.
- `RP.03.NEXT.GAME` — Mets at Yankees, 2026-09-13, scheduled 13:35 EDT, result not yet observed.
- `RP.04.MEDIA.VIDEO` — MLB YouTube highlight listing observed at 165,000 views, 15 hours age, runtime 15:09. This is a media-view metric, not a television rating.

## Reference-point law

`REFERENCE.POINT = SOURCE + METRIC.CLASS + OBSERVED.VALUE + OBSERVED.STATE + TIME.CONTEXT`

Deltas are valid only when the comparison preserves the metric class and the observation window.

Examples:

`LIVE.SCORE.DELTA` may compare score snapshots from the same game.

`MEDIA.VIEW.DELTA` may compare view counts for the same media object across known observation times.

`VIDEO.VIEWS` must not be compared directly to `TV.RATINGS` as though they were the same audience measure.

## Evidence boundaries

- `SCREENSHOT.OBSERVED != INDEPENDENT.VERIFICATION`
- `ONGOING.SCORE != FINAL.RESULT`
- `VIDEO.VIEWS != TV.RATINGS`
- `VIDEO.VIEWS != TOTAL.GAME.REACH`
- `SEARCH.VISIBILITY != AUDIENCE.SIZE`
- `SCHEDULED.EVENT != COMPLETED.EVENT`
- `UNKNOWN != ZERO != PASS`
- `DERIVED.RECORD != SOURCE.REPORTED.RECORD`

## Terminal control

The specification and internal reference-point derivation can pass while unresolved event outcomes remain on hold:

`SPECIFICATION = T.20.PASS`

`CURRENT.GAME.FINAL = U.21.HOLD`

`NEXT.GAME.RESULT = U.21.HOLD`

`TV.AUDIENCE = U.21.HOLD`

`EXTERNAL.RUNTIME = NOT.CLAIMED`

## Validation

Run:

```bash
python RavenCloudTaskbar/fr0333_sports_bits_bones_genius.py
python RavenCloudTaskbar/test_fr0333_sports_bits_bones_genius.py
```

Expected validator state: `T.20.PASS` with four reference points, four completed historical rows, a derived 2-2 record limited to those rows, and unresolved current-game final / television-audience states preserved as `U.21.HOLD`.
