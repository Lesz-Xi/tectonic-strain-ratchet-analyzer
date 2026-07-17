# TSRA — Tectonic Strain Ratchet Analyzer

TSRA is a **static, source-bounded sequence observatory** for public PHIVOLCS earthquake bulletin rows in the Sarangani–Cotabato research area.

It began as an investigation of an apparent 35.55-minute aftershock rhythm. The expanded catalog does **not** validate a continuing single-period clock. The current representation centers sequence decay, spatial branching, significant releases, provenance, capture limits, and uncertainty.

> **Safety boundary:** TSRA is not an earthquake warning system, prediction service, magnitude forecast, or substitute for PHIVOLCS advisories and civil-defense instructions.

## Current Evidence Snapshot

Dataset: `tsra-sarangani-cotabato-sequence-v0.2`

- **982** deduplicated public PHIVOLCS rows
- **12** directly reviewed final PHIVOLCS bulletins at M4.5+
- **35** M4+ rows
- **5** M5+ rows
- **2** M6+ rows
- **18** daily activity records
- **3** research branches

Coverage is deliberately bounded:

- Area of interest: `4.2–6.2°N, 124.5–126.0°E`
- Start: June 30, 2026 at 08:00 PHT
- Capture: July 17, 2026 at 12:23 PHT
- Last included core-area row: July 17, 2026 at 07:02 PHT

“All data” means all deduplicated public PHIVOLCS rows found inside that declared area and interval. It does not mean all earthquakes everywhere, an officially complete sequence, or automatic official aftershock association.

## What the Application Shows

### Sequence

The reviewed snapshot, capture boundaries, daily activity, evidence totals, and current interpretation:

> **Punctuated aftershock decay with spatially distinct microevent and strong-release populations; no validated single-period clock.**

### Releases

Branch-level summaries and the 12 directly inspected final M4.5+ PHIVOLCS bulletins. PHIVOLCS and USGS values remain source-specific; TSRA does not create hybrid event solutions.

### Ledger

A lazy-loaded, filterable view of all 982 official rows. The complete CSV stays outside the initial PWA shell.

The Ledger also contains a device-local **Private observation notebook**. These records:

- remain under `tsraObservationLedger.v1` in browser storage;
- are user-entered and private to the device;
- are not submitted to PHIVOLCS;
- are never counted as official events or automatic sequence evidence;
- do not need to reference a model window.

### Method

An inspectable audit of the original clock hypothesis:

- fitted historical baseline: **35.552 minutes**;
- rounded null-test baseline: **35.55 minutes**;
- inherited tolerance: **±12 minutes**;
- null occupancy: `24 / 35.55 = 67.5%`;
- original selected-event result: **8/9 intervals inside tolerance**;
- threshold-specific catalog tests and limitations;
- preserved 11-event investigation with explicit provenance boundaries.

The historical fit is retained as a falsifiable research trace, not operational authority.

### Archive

The original chart, field report, learning modules, origin disclosure, and TMCH Slab2 convergence-gate artifact remain inspectable behind an explicit historical boundary. Archived claims may be obsolete and do not govern the current instrument.

## Architecture

TSRA intentionally remains small and static:

| Layer | Implementation |
|---|---|
| Application shell | `seismic_report.html` |
| Sequence rendering | `assets/tsra-sequence.js` |
| Sequence styles | `assets/tsra-sequence.css` |
| Reviewed evidence | `data/sequence-v0.2/` |
| Dataset contract | `tools/tsra_build.py` |
| Shell/PWA contract | `tools/tsra_update.py verify` |
| Offline shell | `service-worker.js` |
| Tests | Node test runner + Python `unittest` |

There is no application database, map library, framework, automatic PHIVOLCS ingestion, or server-side evidence mutation.

## Run Locally

The application fetches reviewed JSON and CSV files, so serve the repository over HTTP rather than opening the HTML through `file://`.

```bash
cd /Users/lesz/Developer/Mother-Ana
python3 -m http.server 8000
```

Then open:

```text
http://localhost:8000/seismic_report.html
```

The optional `viewer-server.js` is not part of the evidence pipeline.

## Verification

Run the complete contract before shipping:

```bash
python3 tools/tsra_build.py verify
python3 tools/tsra_update.py verify
npm test
git diff --check
```

Or:

```bash
npm run verify
```

The verifiers check dataset integrity, counts, chronology, area bounds, conservation totals, significant-event provenance, historical-method invariants, claim boundaries, retired clock surfaces, JavaScript syntax, PWA version synchronization, and tests.

## Updating Reviewed Evidence

The production snapshot is intentionally not mutated by a live scraper.

A new version requires a reviewed evidence bundle:

1. capture and preserve source material;
2. deduplicate rows using an explicit key;
3. keep preliminary and final source revisions distinct;
4. calculate summaries from the new catalog;
5. create a new versioned dataset directory;
6. update file sizes and SHA-256 values in its manifest;
7. extend the verifier for any new contract fields;
8. run the full verification suite;
9. advance the synchronized PWA cache version.

Do not regenerate `seismic_report.html` with `gemini-code-1781025686774.py` or `pattern-v3.py`. Those scripts encode the retired countdown-first representation and are preserved only as historical source artifacts.

## Legacy Material

The following files are non-authoritative historical artifacts:

- `gemini-code-1781025686774.py`
- `pattern-v3.py`
- `pattern.md`
- `Rythmic-Seismic-Discharge.md`

They document how the original hypothesis formed. They must not overwrite the reviewed application shell or be cited as validation of a deterministic fault clock.

## License

ISC, as declared in `package.json`.
