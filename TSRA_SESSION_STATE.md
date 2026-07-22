# TSRA — Current Session State

**Last updated:** 2026-07-22
**Repository:** `/Users/lesz/Developer/Mother-Ana`
**Branch:** `main` tracking `origin/main`
**Application state:** reviewed static sequence observatory
**Dataset:** `tsra-sarangani-cotabato-sequence-v0.3`

## 1. Governing Interpretation

The current evidence supports:

> **Punctuated aftershock decay with spatially distinct microevent and strong-release populations; no validated single-period clock.**

The 35.55-minute model remains visible only in **Method** and **Archive** as historical provenance. It must not drive countdowns, alerts, pending windows, automatic cycle advancement, or safety-facing state.

## 2. Evidence Boundary

The reviewed snapshot contains official public PHIVOLCS rows inside:

- latitude: `4.2–6.2°N`
- longitude: `124.5–126.0°E`
- sequence anchor: June 8, 2026 at 07:37 PHT — directly reviewed Mw7.8 mainshock only
- explicit no-data gap: June 9–29, 2026
- continuous catalog start: June 30, 2026 at 08:00 PHT
- capture time: July 22, 2026 at 23:53 PHT
- last included core-area row: July 22, 2026 at 23:14 PHT

Current totals:

| Measure | Value |
|---|---:|
| Deduplicated PHIVOLCS rows | 1,202 |
| Directly reviewed June 8 mainshock anchors | 1 |
| Directly reviewed final M4.5+ aftershock bulletins | 17 |
| M4+ rows | 42 |
| M5+ rows | 9 |
| M6+ rows | 3 |
| Calendar-day chart records | 45 |
| Explicit no-data gap days | 21 |
| Research branches | 3 |

The area-of-interest filter is a TSRA research inclusion rule, not an official PHIVOLCS associated-aftershock designation. The June 8 anchor is separately identified as the mainshock; only directly inspected final aftershock bulletins are labeled officially associated.

### July 22 felt-event match

The strongest source-grounded match for Chief’s afternoon report is:

- origin time: `2026-07-22 17:47:11 PHT`
- magnitude: `Mw 5.1`
- location: `024 km S 25° E of Balut Island`
- coordinates: `5.21°N, 125.51°E`
- final depth: `16 km`
- PHIVOLCS classification: aftershock of the June 2026 Mw7.8 Offshore Sarangani and Mw6.5 Offshore Davao Occidental earthquakes
- instrumental intensity: IV at Sarangani, Davao Occidental; II at Malapatan and General Santos City

This is a likely match, not a claim that the felt report and bulletin are identical without Chief’s exact felt time and location.

## 3. Spatial Result

| Research branch | Rows | M4+ | M5+ | Median depth |
|---|---:|---:|---:|---:|
| South offshore | 183 | 19 | 5 | 25 km |
| Balut central | 328 | 18 | 3 | 27 km |
| Glan–Maasim north | 691 | 5 | 1 | 19 km |

Key invariant:

> **57.5% of rows occur in Glan–Maasim north, while 5 of 9 M5+ releases occur south offshore. The June 8 Mw7.8 mainshock is the one M5+ anchor in the north branch.**

The branches are research summaries, not named faults or official tectonic source assignments.

## 4. Product Surfaces

Primary navigation is intentionally limited to:

1. **Sequence** — reviewed state, capture limits, totals, daily activity, and claim ceiling.
2. **Releases** — branch rails and directly reviewed significant bulletins.
3. **Ledger** — lazy-loaded official catalog plus private device-local observations.
4. **Method** — historical clock audit, threshold tests, selected-event provenance, and limitations.
5. **Archive** — explicit access boundary for superseded chart, report, media, origin, and TMCH material.

The following active surfaces no longer exist:

- Legacy Watch
- Rhythm
- Calibration
- pending-window table
- countdown runtime
- active/imminent/pending model states
- automatic cycle advancement

Archived legacy panels remain inspectable only through Archive and carry a visible superseded/historical boundary.

## 5. Private Observation Contract

Private notes remain in browser local storage under:

```text
tsraObservationLedger.v1
```

They are:

- private to the local device;
- user-entered;
- not submitted;
- independent of model windows by default;
- separate from the official PHIVOLCS ledger;
- excluded from evidence totals and sequence claims.

Older records retain their historical fields when normalized so existing local notebooks are not destroyed.

## 6. Source-of-Truth Files

| Path | Authority |
|---|---|
| `data/sequence-v0.3/manifest.json` | dataset identity, files, hashes, row metadata, and source-capture checksum |
| `data/sequence-v0.3/summary.json` | reviewed sequence summaries, explicit gap days, and Method audit |
| `data/sequence-v0.3/events.csv` | complete 1,202-row official ledger including the June 8 anchor |
| `data/sequence-v0.3/significant-events.csv` | 17 reviewed final M4.5+ aftershock bulletins |
| `data/sequence-v0.3/sources/phivolcs-2026-07-22T235324+0800.tar.gz` | preserved July 22 public table and six reviewed final bulletins |
| `tools/tsra_build.py` | dataset integrity and claim-boundary verifier |
| `assets/tsra-sequence.js` | browser validation and rendering |
| `seismic_report.html` | static application shell |
| `service-worker.js` | versioned offline application shell |
| `tsra-version.json` | deployed application version signal |

`tools/tsra_update.py` is now a compatibility verifier only. Its former felt/elapsed source mutation commands are retired.

## 7. Historical Clock Audit

Method preserves both baseline values because they served different roles:

- `35.552` minutes — original fitted baseline;
- `35.55` minutes — rounded baseline used for the published null calculation;
- `±12` minutes — inherited tolerance;
- `24 / 35.55 = 67.5%` — null occupancy of each cycle.

The original selected investigation preserves 11 displayed entries, 9 standard intervals, 8 intervals inside tolerance, an 8/9 selected alignment fraction, and a 4.6-minute median absolute offset.

These displayed timestamps are historical page provenance, not replacements for the verified PHIVOLCS catalog.

## 8. Legacy Files

These files are preserved but non-authoritative:

- `gemini-code-1781025686774.py`
- `pattern-v3.py`
- `pattern.md`
- `Rythmic-Seismic-Discharge.md`

Do not run the Python generators to regenerate production. They encode the retired countdown-first model and can overwrite reviewed claims.

## 9. Verification

Run before shipping:

```bash
cd /Users/lesz/Developer/Mother-Ana
python3 tools/tsra_build.py verify
python3 tools/tsra_update.py verify
npm test
git diff --check
```

Expected current test inventory:

- 8 JavaScript tests
- 9 Python tests
- 17 total

The synchronized PWA cache version must match across:

- `service-worker.js`
- `seismic_report.html`
- `tsra-version.json`

## 10. Remaining Work

Before commit:

- inspect Archive and legacy boundaries at desktop and mobile widths;
- inspect dark and light themes;
- verify offline shell behavior after cache-version advance;
- verify missing-data blocked state;
- preserve an existing `tsraObservationLedger.v1` record through reload;
- review the full diff for accidental source or claim drift.

Deferred by design:

- automatic PHIVOLCS ingestion;
- a geographic map;
- official association inference beyond inspected bulletins;
- NAMRIA product purchase;
- alerting, prediction, or safety-state machinery.
