# TSRA Decay-and-Branching Refactor Plan v0.1

**Status:** implemented in the uncommitted v0.2 working tree; final device/browser review pending  
**Prepared:** 2026-07-17  
**Repository:** `/Users/lesz/Developer/Mother-Ana`  
**Evidence snapshot:** `tsra_observation_window_update_v0_2`  
**Claim ceiling:** descriptive and inferential; no earthquake prediction capability

## Product decision

Refactor TSRA from a 35.55-minute countdown dashboard into a static, evidence-bearing **sequence observatory**.

The public surface will make punctuated aftershock decay, spatially distinct subclusters, significant releases, source status, and capture freshness primary. The original clock remains inspectable as a historical hypothesis but no longer generates active watches, countdowns, or operational status.

## Product soul

TSRA turns a bounded earthquake sequence into one inspectable view of what changed, where stronger releases concentrated, which claims are source-backed, and what remains unresolved—without presenting a fitted historical rhythm as a warning or prediction.

This rejects:

- active countdown windows;
- “imminent” event states;
- deterministic fault-clock language;
- calibration percentages without the null expectation;
- automatic cycle advancement from felt or no-shake observations.

## Raw situation

Chief needs to inspect how the June 2026 Sarangani–Cotabato sequence evolved through a bounded July 17 capture, distinguish numerous small events from stronger offshore releases, preserve source provenance, and record private local observations without converting them into official seismic evidence.

## Representation analysis

### Current representation — fitted temporal clock

**Type:** homomorphic, lossy compression.

- **Operations cheap:** generate watch times, compare selected intervals with fitted multiples, maintain a countdown.
- **Operations expensive:** inspect completeness, source revisions, spatial branches, magnitude hierarchy, capture freshness, and chance alignment.
- **Invariant exposed:** some events cluster in time.
- **Invariants hidden:** rate changes by day; strong and small events have different spatial distributions; final bulletin values differ from preliminary reports; AOI membership is not sequence association.
- **Search burden:** encourages repeatedly searching for the next matching interval.

### Alternative A — decay-only timeline

**Type:** homomorphic temporal summary.

- **Operations cheap:** see rate decay and renewed activity after stronger events.
- **Operations expensive:** identify spatially separate populations.
- **Invariant exposed:** event rate declines unevenly.
- **Invariant hidden:** four of five M5+ events occur in the south-offshore branch.
- **Transformation cost:** low.

### Alternative B — spatially branching sequence observatory

**Type:** layered representation: isomorphic source ledger plus homomorphic daily/spatial summaries.

- **Operations cheap:** separate microevent density from stronger releases, inspect source status, see capture limits, compare daily rate, and open final bulletins.
- **Operations expensive:** derive one emotionally simple countdown number.
- **Invariants exposed:** northern event-count concentration, southern strong-release concentration, episodic resets, and source-specific revisions.
- **Invariant hidden:** no single pulse dominates the first view.
- **Transformation cost:** moderate; requires versioned data assets and new rendering logic.

### Alternative C — geographic map first

**Type:** spatial projection.

- **Operations cheap:** inspect exact epicentral geometry.
- **Operations expensive:** understand temporal decay and evidence status without additional controls.
- **Invariant exposed:** spatial clustering.
- **Invariant hidden:** sequence evolution through time.
- **Transformation cost:** high if a basemap, map library, offline tiles, or accessibility fallback is introduced.

### Recommendation

Use **Alternative B** as the primary representation. Add a lightweight geographic plot later only if the three-branch summary fails the acceptance test or exact epicentral inspection becomes a recurring operator need.

This representation reduces search because the operator no longer has to reconcile a countdown, selected event log, and external catalog manually. The source ledger and derived summaries become one inspectable path while preserving their distinction.

## User-visible transformation

Before:

> “What is the next model window, and did something happen near it?”

After:

> “What state is the sequence in, what evidence supports that judgment, where are stronger releases concentrated, and how current is this snapshot?”

## Real object of design

An **evidence-bearing sequence state**, not a forecast timer.

The key operator judgments are:

1. Is activity broadly decaying, renewing, or accelerating in the bounded window?
2. Are stronger events distributed like the microevent field or concentrated elsewhere?
3. Which significant events have final PHIVOLCS association statements?
4. What data cutoff and completeness limitations constrain the view?
5. Why is the historical 35.55-minute model not validated as a predictive clock?

## Interface consequence

### Primary navigation

Replace the nine-item top-level search surface with:

1. **Sequence** — default state and daily evolution.
2. **Releases** — significant-event timeline and spatial branches.
3. **Ledger** — official rows, filters, source links, and private local notes kept separate.
4. **Method** — historical model audit, null expectation, threshold results, and claim boundary.
5. **Archive** — origin, learning media, field report, and TMCH convergence-gate links.

### Sequence surface

Top evidence strip:

- `Captured Jul 17 · 12:23 PM PHT`
- `Coverage Jun 30 · 08:00 AM → Jul 17 partial`
- `Last core row Jul 17 · 07:02 AM`
- `AOI 4.2–6.2°N · 124.5–126.0°E`
- `AOI inclusion ≠ official sequence association`

Primary verdict:

> Punctuated aftershock decay with spatially distinct subclusters.

Primary metrics:

- `982` bounded PHIVOLCS rows;
- `35` M4+;
- `5` M5+;
- `2` M6+.

Primary visual:

- 18-day daily activity series;
- stacked or layered by `<M2`, `M2–2.9`, `M3–3.9`, `M4–4.9`, and `M5+`;
- partial-day markers on June 30 and July 17;
- significant-release markers on July 4, 6, 11, and 14.

### Releases surface

Three branch rails:

| Branch | Events | M4+ | M5+ | Median depth |
|---|---:|---:|---:|---:|
| South offshore | 149 | 16 | 4 | 24 km |
| Balut central | 267 | 15 | 1 | 27 km |
| Glan–Maasim north | 566 | 4 | 0 | 19 km |

Significant-release ledger:

- 12 final PHIVOLCS M4.5+ bulletins;
- final magnitude type/value, depth, location, maximum reported intensity, association statement, and direct source URL;
- revision notes kept source-specific rather than merged.

### Ledger surface

Official ledger:

- downloadable 982-row CSV;
- in-page filter by date, magnitude threshold, and research branch;
- source link per row;
- persistent note that row-level sequence association was not checked for small events.

Private notebook:

- preserve the existing `tsraObservationLedger.v1` localStorage key;
- allow independent local observation entry by time, confidence, source, and note;
- remove required linkage to a generated watch window;
- never count private rows as official events or sequence-fit evidence.

### Method surface

Historical hypothesis card:

- original 35.55-minute baseline;
- original 11-event selected record;
- ±12-minute band;
- null occupancy `24 / 35.55 = 67.5%`;
- threshold-specific results for M2+, M3+, M4+, M4.5+, and M5+;
- conclusion: no threshold-stable, validated single-period clock.

The method surface must not contain a countdown, next window, imminent state, new-cycle action, or “keep observing because fit ≥80%” verdict.

## Taste constraints

- Instrument over dashboard: every metric must alter interpretation or expose provenance.
- Proof before pitch: source capture, coverage, and direct bulletins precede explanatory flourish.
- Calm density: one sequence verdict, one daily visual, three branch rails, then deeper ledgers.
- Status colors carry evidence meaning only; no warning palette for model-generated states.
- Preserve the current warm dark/light material system where contrast remains accessible.
- No map, animation, or additional panel unless it improves an operator judgment.
- Capture freshness remains visible in offline mode; atmosphere must not imply liveness.

## Cuts

Remove from active production behavior:

- `Now` countdown panel;
- `Rhythm` pending-window table;
- generated 1× / 3.5× / 7× / 9.5× watches;
- `Active Observation Window`, `Next Observation Window`, `Imminent`, and `Pending` temporal states;
- auto-advancing cycles from elapsed or felt observations;
- 35.55 minutes as a top-level metric;
- 88.9% as a top-level model-fit metric;
- nearest-phase “coherent enough to keep observing” verdict;
- viewer count, because it does not change scientific judgment;
- local-observation linkage that requires a model window.

## Integrations

- Integrate capture freshness with the primary verdict so stale data cannot masquerade as current state.
- Integrate significant events with their direct final-bulletin provenance.
- Integrate spatial branch summaries with magnitude hierarchy so event volume and strong-release concentration are not confused.
- Integrate the historical clock with its null expectation and threshold tests.
- Keep official data and private observations separate; do not collapse that trust boundary.

## Data and system consequence

### New versioned public data bundle

Add:

```text
data/
  sequence-v0.2/
    manifest.json
    summary.json
    events.csv
    significant-events.csv
```

`manifest.json` owns:

- artifact version;
- capture timestamp;
- analysis cutoff;
- coverage boundaries;
- AOI and its meaning;
- source classes;
- claim boundary;
- file row counts and checksums.

`summary.json` owns only derived UI data:

- magnitude counts;
- daily series;
- spatial-zone summaries;
- significant-event summaries;
- interval-test/null metrics;
- standing interpretation.

`events.csv` remains the loss-minimized source ledger for download and optional in-browser filtering.

### Rendering boundary

Keep the no-build static architecture for this refactor.

Extract production logic from the monolithic report into:

```text
assets/tsra.css
assets/tsra-app.js
seismic_report.html
```

The HTML owns semantic structure and fallback copy. The JavaScript loads versioned local JSON, validates required fields, renders derived surfaces, and shows an explicit blocked-data state if loading fails.

Do not add React, a backend, a database, WebSocket state, or a map library in this pass.

### Legacy boundary

Move or mark as legacy/non-authoritative:

- `gemini-code-1781025686774.py`;
- `pattern-v3.py`;
- `pattern.md`;
- `Rythmic-Seismic-Discharge.md`;
- old generated phase chart assets where retained only as historical provenance.

A prominent legacy README must state that these artifacts cannot regenerate production.

### Tooling boundary

Replace the operational role of `tools/tsra_update.py` with deterministic tooling:

```text
tools/tsra_build.py verify
tools/tsra_build.py render
tools/tsra_build.py bump-version
```

Minimum verifier invariants:

- events row count = 982;
- significant final-bulletin row count = 12;
- magnitude bins sum to 982;
- daily counts sum to 982;
- spatial-zone counts sum to 982;
- summary capture and manifest capture match;
- every significant event has a valid PHIVOLCS final-bulletin URL;
- no active countdown or watch-generation markers in production HTML/JS;
- local observation storage key preserved;
- report, app script, service worker, and viewer server pass `node --check` where applicable;
- service-worker, report, and `tsra-version.json` versions match;
- `git diff --check` passes.

## File-level plan

### Create

- `docs/tsra_decay_branching_refactor_plan_v0_1.md`
- `data/sequence-v0.2/manifest.json`
- `data/sequence-v0.2/summary.json`
- `data/sequence-v0.2/events.csv`
- `data/sequence-v0.2/significant-events.csv`
- `assets/tsra.css`
- `assets/tsra-app.js`
- `tools/tsra_build.py`
- `legacy/README.md`

### Modify

- `seismic_report.html`
- `service-worker.js`
- `tsra-version.json`
- `manifest.webmanifest`
- `README.md`
- `TSRA_SESSION_STATE.md`
- `vercel.json` only if explicit static data headers are needed

### Move or archive

- `gemini-code-1781025686774.py`
- `pattern-v3.py`
- `pattern.md`
- `Rythmic-Seismic-Discharge.md`

Do not archive research files until references and deployment paths have been checked. A first implementation may instead add deprecation headers and remove them from operational documentation.

## Migration order

1. **Import and validate data**
   - Copy the reviewed v0.2 snapshot into the versioned public data bundle.
   - Generate manifest checksums and verify conservation invariants.

2. **Add characterization checks**
   - Preserve localStorage key and service-worker version behavior.
   - Record current route, theme, offline shell, and archive-link behavior.

3. **Build the new Sequence and Releases surfaces**
   - Render from `summary.json`.
   - Add explicit load-failure and stale-snapshot states.

4. **Build Ledger and Method**
   - Add bounded official ledger and private notebook separation.
   - Add historical hypothesis audit with null expectation.

5. **Cut active clock behavior**
   - Remove countdown DOM, timers, phase generation, active-window states, and cycle advancement.
   - Preserve historical clock content only in Method.

6. **Resolve source-of-truth conflict**
   - Replace operational updater/generator documentation.
   - Add deterministic build verification.

7. **Update PWA cache**
   - Cache versioned summary and core assets.
   - Keep full 982-row CSV optional or explicitly cacheable to control payload.
   - Surface snapshot age when offline.

8. **Verify and preview**
   - Run structural/data verification.
   - Inspect desktop, mobile, dark, light, online, offline, missing-data, and preserved-local-ledger states.

## Rejected paths

### Patch copy only

Rejected because the page’s failure is structural: the countdown and calibration logic continue to create authority even if disclaimers improve.

### Keep countdown as a secondary live widget

Rejected for this release because “secondary” still implies an operational forecast surface. The historical model belongs in Method until it demonstrates held-out improvement over a decay/branching baseline.

### Full framework migration

Rejected because the product requires a corrected representation, not a new application platform. A framework would increase migration and offline risk without improving the current scientific judgment.

### Geographic map in the first pass

Deferred because branch-level spatial separation already exposes the decisive invariant. A map becomes justified when exact epicentral geometry changes a recurring decision.

## Tradeoff

The refactor loses the immediacy and emotional simplicity of one countdown. It also introduces a versioned data bundle and a more explicit manual snapshot-update process.

In return, TSRA gains:

- a faithful representation of the expanded evidence;
- visible provenance and capture limits;
- a stable boundary between official records and private observations;
- fewer opportunities for stale or selected data to look predictive;
- a maintainable source-of-truth path.

## Production and rollback

- Implement as coherent, reviewable commits: data layer, interface, tooling/docs, PWA cache.
- Do not deploy until data invariants and browser states pass.
- Rollback is a Git revert of the refactor commits; local `tsraObservationLedger.v1` data is not migrated or deleted.
- Bump the service-worker cache only after the complete new shell is internally consistent, preventing mixed old/new assets.
- No automatic external catalog fetch is introduced, so network failure cannot partially mutate the snapshot.

## Acceptance check

The refactor is accepted when a first-time reader can answer all five questions within approximately ten seconds of opening the page:

1. What is the current bounded interpretation of the sequence?
2. How current is the snapshot, and which days are partial?
3. Where did most events occur versus most M5+ releases?
4. Which significant events are directly associated by final PHIVOLCS bulletins?
5. Why is 35.55 minutes not presented as a predictive clock?

Additional hard checks:

- no active countdown exists;
- no model window is labeled imminent, pending, expected, or next;
- all displayed aggregate counts conserve to the source snapshot;
- every significant-event source link is inspectable;
- local private observations remain available after update;
- offline mode clearly exposes snapshot age;
- missing summary data produces an explicit blocked state, not fabricated zeroes;
- keyboard navigation and contrast remain usable in both themes.

## Immediate implementation move

Create and verify `data/sequence-v0.2/manifest.json` and `summary.json` from the reviewed v0.2 artifact before changing the page. That establishes the new source of truth and prevents the interface refactor from becoming another hand-authored data fork.
