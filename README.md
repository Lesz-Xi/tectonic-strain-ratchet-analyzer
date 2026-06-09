# TSRA — Tectonic Strain Ratchet Analyzer

A field-built aftershock forecasting tool derived from personal observation during the **June 8–10, 2026 earthquake sequence** along the Cotabato Subduction Zone, Sarangani Segment, Philippines.

Built from intuition first. Formalized into physics second.

---

## What It Does

TSRA fits a **stick-slip physics model** to a manually-recorded timeline of seismic events and forecasts the next aftershock release windows. The core idea: tectonic faults don't release stress randomly — they follow a rhythm. Find the baseline pulse period, and the next windows become predictable.

The model identified a **~35.5-minute baseline pulse** in this fault segment. Subsequent aftershocks arrived at 1×, 3.5×, 7×, and 9.5× multiples of that pulse — with 87.7% predictive alignment across 9 confirmed events.

---

## Features

- **Stick-slip model fitting** — derives baseline pulse from observed event intervals
- **Live countdown dashboard** — pending windows update every second in-browser
- **Dark / Light theme** — warm charcoal dark, washi-paper light, toggle persists via localStorage
- **Clickable stat cards** — expand any metric into a plain-language modal explanation
- **Chart explainer** — sawtooth waveform described in plain terms for general audiences
- **Live viewer count** — real-time cross-machine viewer tracking via WebSocket server; falls back to BroadcastChannel for same-browser tabs
- **Origin disclosure** — honest account of the intuition and manual observation that started this

---

## Stack

| Layer | Tech |
|---|---|
| Analysis | Python 3 (`matplotlib`) |
| Dashboard | Vanilla HTML / CSS / JS — zero framework |
| Live viewers | Node.js + `ws` WebSocket server |
| Deployment | Vercel (static) |

---

## Local Setup

**Python analysis (regenerate chart + HTML):**

```bash
cd "Earth py"
python3 -m venv .venv
source .venv/bin/activate
pip install matplotlib
python3 gemini-code-1781025686774.py
open seismic_report.html
```

**Live viewer server (optional — cross-machine viewer count):**

```bash
npm install
node viewer-server.js
```

Server runs on `ws://localhost:5173`. Open the dashboard on any machine on the same network and the viewer count updates live.

---

## Deploy to Vercel

The dashboard (`seismic_report.html`) is a fully self-contained static file. No build step required.

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/Lesz-Xi/tectonic-strain-ratchet-analyzer)

Or via CLI:

```bash
npm i -g vercel
vercel
```

> **Note:** The WebSocket viewer server (`viewer-server.js`) requires a persistent Node.js environment and cannot run on Vercel's serverless infrastructure. On Vercel, the dashboard will automatically fall back to BroadcastChannel-based tab counting within the same browser session.

---

## Event Log

| # | Label | Time (PHT) | Interval | Multiplier |
|---|---|---|---|---|
| 0 | Mainshock | Jun 8 · 07:37 AM | — | — |
| 1 | A1 | Jun 8 · 01:12 PM | 334.3 min | 9.5× |
| 2 | A2 | Jun 8 · 05:16 PM | 244.0 min | 7.0× |
| 3 | A3 | Jun 8 · 05:51 PM | 35.0 min | 1.0× |
| 4 | A4 | Jun 8 · 06:26 PM | 35.0 min | 1.0× |
| 5 | A5 | Jun 8 · 10:30 PM | 244.0 min | 7.0× |
| 6 | A6 | Jun 10 · 12:36 AM | 126.0 min | 3.5× |
| 7 | A7 | Jun 10 · 02:12 AM | 96.0 min | ~3.5× early |
| 8 | A8 | Jun 10 · 02:55 AM | 43.0 min | 1.0× |
| 9 | A9 | Jun 10 · 03:26 AM | 31.0 min | 1.0× |
| 10 | A10 | Jun 10 · 03:36 AM | 10.0 min | sub-pulse |

---

## Disclosure

This tool was not built from a textbook. It began as intuition on the morning of June 8, 2026 — a feeling that the aftershocks were not arriving randomly, that there was a rhythm underneath the noise. I started recording times manually. The intervals started lining up: 35 minutes, then 7× that, then 9.5× that. The model is the formalization of that observation.

This is an **observational field tool**, not a certified scientific instrument. It should not replace official PHIVOLCS advisories, civil defense protocols, or professional seismological guidance. The pattern observed is consistent with well-documented stick-slip tectonic mechanics — but earthquake behavior is never fully deterministic.

---

*Last updated: June 10, 2026 · Cotabato Subduction Zone, Sarangani Segment*
