# TSRA — Current Session State

**Last updated:** 2026-07-17
**Repository:** `/Users/lesz/Developer/Mother-Ana`
**Branch:** `main` tracking `origin/main`
**Application state:** reviewed static sequence observatory
**Dataset:** `tsra-sarangani-cotabato-sequence-v0.2`

## 1. Governing Interpretation

The current evidence supports:

> **Punctuated aftershock decay with spatially distinct microevent and strong-release populations; no validated single-period clock.**

The 35.55-minute model remains visible only in **Method** and **Archive** as historical provenance. It must not drive countdowns, alerts, pending windows, automatic cycle advancement, or safety-facing state.

## 2. Evidence Boundary

The reviewed snapshot contains all deduplicated public PHIVOLCS rows captured inside:

- latitude: `4.2–6.2°N`
- longitude: `124.5–126.0°E`
- interval start: June 30, 2026 at 08:00 PHT
- capture time: July 17, 2026 at 12:23 PHT

The July 17 capture is partial. The last included core-area row is 07:02 PHT.

Current totals:

| Measure | Value |
|---|---:|
| Deduplicated PHIVOLCS rows | 982 |
| Directly reviewed final M4.5+ bulletins | 12 |
| M4+ rows | 35 |
| M5+ rows | 5 |
| M6+ rows | 2 |
| Daily records | 18 |
| Research branches | 3 |

The area-of-interest filter is a TSRA research inclusion rule, not an official PHIVOLCS associated-aftershock designation. Only directly inspected final bulletins are labeled officially associated.

## 3. Spatial Result

| Research branch | Rows | M4+ | M5+ | Median depth |
|---|---:|---:|---:|---:|
| South offshore | 149 | 16 | 4 | 24 km |
| Balut central | 267 | 15 | 1 | 27 km |
| Glan–Maasim north | 566 | 4 | 0 | 19 km |

Key invariant:

> **57.6% of rows occur in Glan–Maasim north, while 4 of 5 M5+ releases occur south offshore.**

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
| `data/sequence-v0.2/manifest.json` | dataset identity, files, hashes, row metadata |
| `data/sequence-v0.2/summary.json` | reviewed sequence summaries and Method audit |
| `data/sequence-v0.2/events.csv` | complete 982-row official ledger |
| `data/sequence-v0.2/significant-events.csv` | 12 reviewed final M4.5+ bulletins |
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
- 8 Python tests
- 16 total

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
