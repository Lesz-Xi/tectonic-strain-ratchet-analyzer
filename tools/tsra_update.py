#!/usr/bin/env python3
"""TSRA local observation updater.

Layer 1 updater for the static TSRA report. It intentionally patches only the
known report surfaces and preserves the core safety boundary:
confirmed seismic events, felt observations, elapsed local outcomes, and model
watch windows remain separate.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

BASELINE_MINUTES = 35.552
PHASES: tuple[tuple[str, float, str, str], ...] = (
    ("1.0", 1.0, "35.6 min", "First post-anchor observation watch"),
    ("3.5", 3.5, "124.4 min", "Phase-sensitive observation watch"),
    ("7.0", 7.0, "248.9 min", "Long-phase observation watch"),
    ("9.5", 9.5, "337.7 min", "Extended-phase observation watch"),
)
PHASE_LABELS: dict[str, str] = {
    "1": "1.0",
    "1.0": "1.0",
    "1x": "1.0",
    "1.0x": "1.0",
    "3.5": "3.5",
    "3.5x": "3.5",
    "7": "7.0",
    "7.0": "7.0",
    "7x": "7.0",
    "7.0x": "7.0",
    "9.5": "9.5",
    "9.5x": "9.5",
}
WATCH_NAMES: dict[str, str] = {
    "1.0": "1.0× post-anchor watch",
    "3.5": "3.5× phase-sensitive watch",
    "7.0": "7.0× long-phase watch",
    "9.5": "9.5× extended-phase watch",
}
WATCH_CLASSES: dict[str, str] = {
    "1.0": "First post-anchor observation watch",
    "3.5": "Phase-sensitive observation watch",
    "7.0": "Long-phase observation watch",
    "9.5": "Extended-phase observation watch",
}
CONFIRMED_LABELS = ["MS", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10"]

OutcomeKind = Literal["felt", "elapsed"]


@dataclass(frozen=True)
class PendingRow:
    phase: str
    arrival: datetime
    watch_label: str
    html: str


@dataclass(frozen=True)
class Outcome:
    kind: OutcomeKind
    report_time: datetime
    watch: str
    note: str
    duration: str | None
    advance_cycle: bool


def die(message: str) -> None:
    raise SystemExit(f"tsra_update: {message}")


def read_text(path: Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError:
        die(f"missing file: {path}")


def write_text(path: Path, text: str, dry_run: bool) -> None:
    if dry_run:
        return
    path.write_text(text)


def normalize_watch(raw: str) -> str:
    key = raw.strip().lower().replace("×", "x").replace(" ", "")
    if key not in PHASE_LABELS:
        die(f"unsupported watch {raw!r}; expected one of 1.0x, 3.5x, 7.0x, 9.5x")
    return PHASE_LABELS[key]


def parse_report_time(raw: str) -> datetime:
    value = raw.strip()
    candidates = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
    ]
    for fmt in candidates:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(
            "tsra_update: invalid --time; use 'YYYY-MM-DD HH:MM' or ISO local time"
        ) from exc


def month_label(dt: datetime, approximate: bool = False) -> str:
    prefix = "~" if approximate else ""
    return f"{dt.strftime('%b')} {dt.day:02d} &middot; {prefix}{dt.strftime('%I:%M %p')}"


def plain_month_label(dt: datetime, approximate: bool = False) -> str:
    prefix = "~" if approximate else ""
    return f"{dt.strftime('%b')} {dt.day:02d} · {prefix}{dt.strftime('%I:%M %p')}"


def time_label(dt: datetime, approximate: bool = False) -> str:
    prefix = "~" if approximate else ""
    return f"{prefix}{dt.strftime('%I:%M %p')}"


def iso_local(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def find_pending_rows(report: str) -> list[PendingRow]:
    table_match = re.search(r"<table id='pending-table'>.*?<tbody>(?P<body>.*?)</tbody>", report, re.S)
    if not table_match:
        die("could not find pending-table body")
    rows: list[PendingRow] = []
    for match in re.finditer(r"(?P<row><tr data-arrival='(?P<arr>[^']+)'[^>]*>.*?</tr>)", table_match.group("body"), re.S):
        row_html = match.group("row")
        phase_match = re.search(r"<span class='mult-badge'>(?P<phase>[0-9.]+)&times;</span>", row_html)
        watch_match = re.search(r"<td class='mono'>(?P<label>[^<]+)</td>", row_html)
        if not phase_match or not watch_match:
            continue
        rows.append(
            PendingRow(
                phase=normalize_watch(phase_match.group("phase")),
                arrival=parse_report_time(match.group("arr")),
                watch_label=watch_match.group("label"),
                html=row_html,
            )
        )
    if not rows:
        die("pending-table has no parseable rows")
    return rows


def find_watch_row(report: str, watch: str) -> PendingRow | None:
    rows = [row for row in find_pending_rows(report) if row.phase == watch]
    return rows[0] if rows else None


def relation_text(outcome: Outcome, row: PendingRow | None) -> str:
    if outcome.kind == "elapsed":
        return "Nothing happened during the watch"
    if row is None:
        return "Around the watch time"
    diff_minutes = round((outcome.report_time - row.arrival).total_seconds() / 60)
    if abs(diff_minutes) <= 6:
        return "Around the watch time"
    if diff_minutes < 0:
        return f"Before the watch time; ~{abs(diff_minutes)} min before anchor"
    return f"After the watch time; ~{diff_minutes} min after anchor"


def outcome_text(outcome: Outcome) -> str:
    safe_note = html.escape(outcome.note.strip())
    if outcome.kind == "elapsed":
        return safe_note or "No local shake observed"
    duration = f" for {html.escape(outcome.duration.strip())}" if outcome.duration else ""
    return f"{safe_note or 'Local shake felt'}{duration}"


def build_outcome_row(outcome: Outcome, row: PendingRow | None) -> str:
    source = "FELT" if outcome.kind == "felt" else "OBS"
    status_class = "observed-pill" if outcome.kind == "felt" else "elapsed-pill"
    status = "Felt-only" if outcome.kind == "felt" else "Elapsed"
    watch_label = WATCH_NAMES[outcome.watch]
    evidence_type = "local-felt" if outcome.kind == "felt" else "local-elapsed"
    certainty = "observational-low" if outcome.kind == "felt" else "observational-local"
    official_status = "not-confirmed" if outcome.kind == "felt" else "not-official"
    evidence_note = "Local felt-only · low certainty · pattern context" if outcome.kind == "felt" else "Local outcome · no-shake note · not official"
    return f"""                    <tr data-evidence-type='{evidence_type}' data-certainty='{certainty}' data-official-status='{official_status}'>
                        <td><span class='badge badge-as'>{source}</span><span class='evidence-mini'>{evidence_note}</span></td>
                        <td class='mono'>{month_label(outcome.report_time, approximate=outcome.kind == 'felt')}</td>
                        <td class='mono'>{watch_label}</td>
                        <td>{relation_text(outcome, row)}</td>
                        <td>{outcome_text(outcome)}</td>
                        <td><span class='pill {status_class}'>{status}</span></td>
                    </tr>
"""


def compact_html(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def append_outcome_log(report: str, row_html: str) -> str:
    if compact_html(row_html) in compact_html(report):
        return report
    marker = "                </tbody>\n            </table>\n        </div>\n    </div>\n\n    <div class='tab-panel' id='tab-rhythm'>"
    if marker not in report:
        die("could not locate end of Observation Outcome Log")
    return report.replace(marker, row_html + marker, 1)


def observed_label(outcome: Outcome) -> str:
    return "Felt-only observed" if outcome.kind == "felt" else "No local outcome"


def observed_report(outcome: Outcome) -> str:
    if outcome.kind == "felt":
        return f"felt {time_label(outcome.report_time, approximate=True)}"
    return f"no shake {time_label(outcome.report_time)}"


def mark_watch_observed(report: str, outcome: Outcome) -> str:
    row = find_watch_row(report, outcome.watch)
    if row is None:
        return report
    if "data-observed='true'" in row.html:
        return report
    row_open = re.search(r"<tr data-arrival='[^']+'", row.html)
    if not row_open:
        return report
    new_row = row.html.replace(
        row_open.group(0),
        f"{row_open.group(0)} data-observed='true' data-observed-report='{html.escape(observed_report(outcome), quote=True)}' data-observed-label='{observed_label(outcome)}'",
        1,
    )
    class_text = outcome_text(outcome) if outcome.kind == "felt" else "No local shake observed during watch"
    new_row = re.sub(r"<td>[^<]*(?:watch|report|observed)[^<]*</td>", f"<td>{class_text}</td>", new_row, count=1)
    return report.replace(row.html, new_row, 1)


def build_windows(anchor: datetime) -> list[tuple[str, float, str, str, datetime]]:
    return [(phase, multiplier, duration, klass, anchor + timedelta(minutes=BASELINE_MINUTES * multiplier)) for phase, multiplier, duration, klass in PHASES]


def band_label(center: datetime) -> str:
    start = center - timedelta(minutes=11)
    end = center + timedelta(minutes=12)
    return f"~{start.strftime('%I:%M')}&ndash;{end.strftime('%I:%M %p')}"


def band_label_plain(center: datetime) -> str:
    start = center - timedelta(minutes=11)
    end = center + timedelta(minutes=12)
    return f"~{start.strftime('%I:%M')}-{end.strftime('%I:%M %p')}"


def build_pending_rows(anchor: datetime) -> str:
    rows: list[str] = []
    for phase, _multiplier, duration, klass, arrival in build_windows(anchor):
        rows.append(f"""                        <tr data-arrival='{iso_local(arrival)}' data-evidence-type='model-window' data-certainty='generated-watch' data-official-status='not-official'>
                            <td><span class='mult-badge'>{phase}&times;</span></td>
                            <td>{duration}</td>
                            <td class='mono'>{month_label(arrival)}</td>
                            <td class='countdown' data-arrival='{iso_local(arrival)}'>&mdash;</td>
                            <td>{klass}<span class='evidence-mini'>Model window · generated · not warning</span></td>
                            <td class='status-cell' data-arrival='{iso_local(arrival)}'>&mdash;</td>
                            <td><button class='record-outcome-btn' type='button' onclick='openOutcomeRecorder(this)'>Record outcome</button></td>
                        </tr>""")
    return "\n".join(rows)


def replace_pending_body(report: str, anchor: datetime) -> str:
    pattern = r"(<table id='pending-table'>.*?<tbody>)(?P<body>.*?)(</tbody>\s*</table>)"
    replacement = lambda match: match.group(1) + "\n" + build_pending_rows(anchor) + "\n                    " + match.group(3)
    new_report, count = re.subn(pattern, replacement, report, count=1, flags=re.S)
    if count != 1:
        die("could not replace pending-table body")
    return new_report


def replace_exact_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        die(f"expected one {label}, found {count}")
    return text.replace(old, new, 1)


def replace_now_note(report: str, outcome: Outcome) -> str:
    if outcome.kind == "felt":
        mini = "Latest felt-only note"
        title = f"{time_label(outcome.report_time, approximate=True)} · {html.escape(outcome.note.strip() or 'local shake felt')}"
        duration = f" {html.escape(outcome.duration.strip())}" if outcome.duration else ""
        body = f"Felt{duration} and linked to the {WATCH_NAMES[outcome.watch]}. This remains a local felt observation, not a confirmed seismic event."
    else:
        mini = "Latest local outcome"
        title = f"{time_label(outcome.report_time)} · no local shake observed"
        body = f"The {WATCH_NAMES[outcome.watch]} elapsed without a locally felt shake. This is a local observation outcome, not an official confirmation or event record."
    pattern = r"<div class='now-note'>\s*<div class='now-mini-label'>.*?</div>\s*<div class='now-note-title'>.*?</div>\s*<div class='now-note-body'>.*?</div>\s*<div class='now-boundary'>Observation surface only · not a certified warning system</div>\s*</div>"
    new_block = f"""<div class='now-note'>
                        <div class='now-mini-label'>{mini}</div>
                        <div class='now-note-title'>{title}</div>
                        <div class='now-note-body'>{body}</div>
                        <div class='now-boundary'>Observation surface only · not a certified warning system</div>
                    </div>"""
    new_report, count = re.subn(pattern, new_block, report, count=1, flags=re.S)
    if count != 1:
        die("could not replace Now note")
    return new_report


def replace_now_and_hero(report: str, anchor: datetime) -> str:
    first = build_windows(anchor)[0]
    phase, _multiplier, _duration, klass, arrival = first
    now_old = re.search(
        r"<div class='now-kicker' id='now-status'>.*?</div>\s*<div class='now-time' id='now-time'>.*?</div>\s*<div class='now-phase' id='now-title'>.*?</div>\s*<div class='now-remain' id='now-remain'>.*?</div>",
        report,
        re.S,
    )
    if not now_old:
        die("could not find Now primary block")
    now_new = f"""<div class='now-kicker' id='now-status'>Next Observation Window</div>
                    <div class='now-time' id='now-time'>{time_label(arrival)}</div>
                    <div class='now-phase' id='now-title'>{phase}&times; · post-{time_label(anchor)} observation cycle</div>
                    <div class='now-remain' id='now-remain'>New watch opened</div>"""
    report = report.replace(now_old.group(0), now_new, 1)
    hero_old = re.search(
        r"<div class='hero-label' id='hero-label'>.*?</div>\s*<div class='hero-time' id='hero-time'>.*?</div>\s*<div class='hero-remain' id='hero-remain'>.*?</div>",
        report,
        re.S,
    )
    if not hero_old:
        die("could not find Rhythm hero block")
    hero_new = f"""<div class='hero-label' id='hero-label'>Next Observation Window</div>
                <div class='hero-time' id='hero-time'>{time_label(arrival)}</div>
                <div class='hero-remain' id='hero-remain'>Post-{time_label(anchor)} cycle</div>"""
    return report.replace(hero_old.group(0), hero_new, 1)


def replace_pending_note(report: str, anchor: datetime) -> str:
    pattern = r"<span>Provisional Observation Windows</span><span class='pending-card-note'>.*?</span>"
    new_text = f"<span>Provisional Observation Windows</span><span class='pending-card-note'>Post-{time_label(anchor)} cycle · new observation open</span>"
    new_report, count = re.subn(pattern, new_text, report, count=1, flags=re.S)
    if count != 1:
        die("could not replace pending-card note")
    return new_report


def replace_anchor(report: str, outcome: Outcome, anchor: datetime) -> str:
    first_arrival = build_windows(anchor)[0][4]
    source = f"Post-{time_label(anchor)} observation cycle · {'felt-only' if outcome.kind == 'felt' else 'elapsed watch'} anchor"
    relation = (
        f"{outcome_text(outcome)}; new observation pattern opened"
        if outcome.kind == "felt"
        else "No local shake observed; new observation pattern opened"
    )
    status_class = "observed-pill" if outcome.kind == "felt" else "pending-pill"
    status_text = "Felt-only anchor · new observation cycle" if outcome.kind == "felt" else "New observation cycle · local anchor"
    source_certainty = (
        "Local felt-only observation · low certainty · not confirmed · used only as a pattern anchor"
        if outcome.kind == "felt"
        else "Local elapsed/no-shake outcome · observational certainty · not official · used only as a pattern anchor"
    )
    anchor_evidence_type = "local-felt-anchor" if outcome.kind == "felt" else "local-elapsed-anchor"
    anchor_certainty = "observational-low" if outcome.kind == "felt" else "observational-local"
    anchor_official = "not-confirmed" if outcome.kind == "felt" else "not-official"
    replacements = [
        (r"<div class='anchor-value strong'>.*?</div>", f"<div class='anchor-value strong'>{source}</div>"),
        (r"<div class='anchor-value mono'>[^<]*</div>", f"<div class='anchor-value mono'>{plain_month_label(anchor, approximate=outcome.kind == 'felt')}</div>"),
        (r"<div class='anchor-label'>Window relation</div>\s*<div class='anchor-value'>.*?</div>", f"<div class='anchor-label'>Window relation</div>\n                        <div class='anchor-value'>{relation}</div>"),
        (r"<div class='anchor-label'>Next watch (?:band|center)</div>\s*<div class='anchor-value mono strong'>.*?</div>", f"<div class='anchor-label'>Next watch center</div>\n                        <div class='anchor-value mono strong'>{time_label(first_arrival)} · band {band_label(first_arrival)}</div>"),
        (r"<div class='anchor-label'>Evidence status</div>\s*<div class='anchor-value'><span class='pill [^']+'>.*?</span></div>", f"<div class='anchor-label'>Evidence status</div>\n                        <div class='anchor-value'><span class='pill {status_class}'>{status_text}</span></div>"),
        (r"<div class='anchor-field' data-evidence-type='[^']+' data-certainty='[^']+' data-official-status='[^']+'>\s*<div class='anchor-label'>(?:Source (?:&|&amp;) certainty|What this means)</div>\s*<div class='anchor-value'>.*?</div>\s*</div>", f"<div class='anchor-field' data-evidence-type='{anchor_evidence_type}' data-certainty='{anchor_certainty}' data-official-status='{anchor_official}'>\n                        <div class='anchor-label'>What this means</div>\n                        <div class='anchor-value'>{source_certainty}</div>\n                    </div>"),
    ]
    anchor_match = re.search(r"<div class='card-title'>Latest Observation Anchor</div>.*?</div>\s*</div>\s*</div>\s*</div>\s*<div class='tab-panel' id='tab-chart'>", report, re.S)
    if not anchor_match:
        die("could not locate Latest Observation Anchor block")
    block = anchor_match.group(0)
    new_block = block
    for pattern, replacement in replacements:
        new_block, count = re.subn(pattern, replacement, new_block, count=1, flags=re.S)
        if count != 1:
            die(f"could not update anchor field: {pattern}")
    return report.replace(block, new_block, 1)


def replace_raw_model(report: str, outcome: Outcome, anchor: datetime) -> str:
    windows = build_windows(anchor)
    relation = (
        f"{time_label(anchor, approximate=True)} local shake is logged as a felt-only outcome; new observation cycle opened from that local outcome anchor"
        if outcome.kind == "felt"
        else f"{time_label(anchor)} {WATCH_NAMES[outcome.watch]} elapsed with no local shake observed; new observation cycle opened from that local outcome anchor"
    )
    lines = [
        "                ================================================================================",
        f"                TECTONIC PHASE-OBSERVATION MODEL (POST-{time_label(anchor).replace(' ', ':').replace(':PM', ' PM').replace(':AM', ' AM')} NEW OBSERVATION CYCLE)",
        f"                Watch Schedule From Latest Local Outcome (Reference Time: {anchor.strftime('%Y-%m-%d %H:%M:%S')} local observation anchor)",
        "                ================================================================================",
        f"                - Fitted Baseline Pulse Period: {BASELINE_MINUTES:.3f} minutes",
        "                - Architecture Rule: no confirmed event is added; felt observations and elapsed local outcomes stay separate from confirmed seismic records",
        f"                - Operational Relation: {relation}",
        "",
        "                Phase | Observation Window | Watch Center | Operational Status",
        "                --------------------------------------------------------------------------------",
    ]
    for index, (phase, _multiplier, duration, klass, arrival) in enumerate(windows):
        status = f"NEXT WATCH -> observe {band_label_plain(arrival)}" if index == 0 else f"later {klass.lower()}"
        lines.append(f"                {phase}x phase | {duration.replace(' min', ' minutes')} | {arrival.strftime('%Y-%m-%d %H:%M:%S')} | {status}")
    lines.append("                ================================================================================")
    model_start = report.rfind("                TECTONIC PHASE-OBSERVATION MODEL (POST-")
    if model_start == -1:
        die("could not find latest raw model block")
    block_start = report.rfind("                ================================================================================", 0, model_start)
    block_end = report.find("                ================================================================================", model_start + 1)
    if block_start == -1 or block_end == -1:
        die("could not find raw model block boundaries")
    block_end += len("                ================================================================================")
    return report[:block_start] + "\n".join(lines) + report[block_end:]


def replace_modal_copy(report: str, outcome: Outcome, anchor: datetime) -> str:
    pattern = r"A10 remains the <strong>last confirmed event anchor</strong>\..*?</p>`"
    addition = (
        f"After the {time_label(anchor, approximate=outcome.kind == 'felt')} {'felt-only observation' if outcome.kind == 'felt' else 'no-shake outcome'}, TSRA opens a new post-{time_label(anchor)} observation cycle beginning around {time_label(build_windows(anchor)[0][4])}."
    )
    replacement = (
        "A10 remains the <strong>last confirmed event anchor</strong>. The operational observation surface now separates confirmed events from later local outcomes: elapsed watches and felt-only observations are logged outside the confirmed event log. "
        + addition
        + "</p>`"
    )
    new_report, count = re.subn(pattern, replacement, report, count=1, flags=re.S)
    if count != 1:
        die("could not replace anchor modal copy")
    return new_report


def extract_service_worker_version(service_worker: str) -> str:
    match = re.search(r"const TSRA_CACHE_VERSION = '(tsra-field-cache-v\d+)';", service_worker)
    if not match:
        die("could not find service worker cache version")
    return match.group(1)


def bump_service_worker(service_worker: str) -> str:
    pattern = r"const TSRA_CACHE_VERSION = 'tsra-field-cache-v(?P<num>\d+)';"
    match = re.search(pattern, service_worker)
    if not match:
        die("could not find service worker cache version")
    version = int(match.group("num")) + 1
    return re.sub(pattern, f"const TSRA_CACHE_VERSION = 'tsra-field-cache-v{version}';", service_worker, count=1)


def build_version_file(service_worker: str) -> str:
    payload = {
        "version": extract_service_worker_version(service_worker),
        "updatedAt": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "app": "TSRA",
    }
    return json.dumps(payload, indent=2) + "\n"


def replace_app_version(report: str, version: str) -> str:
    pattern = r"const TSRA_APP_VERSION = 'tsra-field-cache-v\d+';"
    new_report, count = re.subn(pattern, f"const TSRA_APP_VERSION = '{version}';", report, count=1)
    if count != 1:
        die("could not replace TSRA_APP_VERSION")
    new_report, count = re.subn(r"app v\d+ · sw —", f"app {version.replace('tsra-field-cache-', '')} · sw —", new_report, count=1)
    if count != 1:
        die("could not replace visible app version")
    return new_report


def apply_outcome(report: str, service_worker: str, outcome: Outcome) -> tuple[str, str]:
    row = find_watch_row(report, outcome.watch)
    report = append_outcome_log(report, build_outcome_row(outcome, row))
    report = mark_watch_observed(report, outcome)
    report = replace_now_note(report, outcome)
    if outcome.advance_cycle:
        report = replace_now_and_hero(report, outcome.report_time)
        report = replace_pending_note(report, outcome.report_time)
        report = replace_pending_body(report, outcome.report_time)
        report = replace_anchor(report, outcome, outcome.report_time)
        report = replace_raw_model(report, outcome, outcome.report_time)
        report = replace_modal_copy(report, outcome, outcome.report_time)
    service_worker = bump_service_worker(service_worker)
    report = replace_app_version(report, extract_service_worker_version(service_worker))
    return report, service_worker


def verify_report(report: str, service_worker: str) -> list[str]:
    errors: list[str] = []
    confirmed_match = re.search(r"<div class='card-title'>Confirmed Event Log</div>(?P<body>.*?)<div class='card' style='margin-top:1rem'>", report, re.S)
    if not confirmed_match:
        errors.append("confirmed event log not found")
    else:
        labels = re.findall(r"<span class='badge badge-(?:ms|as)'>(MS|A\d+)</span>", confirmed_match.group("body"))
        if labels != CONFIRMED_LABELS:
            errors.append(f"confirmed labels changed: {labels}")
    required_report_markers = [
        "id='tab-now'",
        "id='tab-calibration'",
        "id='pending-table'",
        "id='observation-log-body'",
        "calibration-hit-rate",
        "model-fit-stat",
        "field-report-fit-stat",
        "syncModelFitSurface",
        "renderCalibrationLedger",
        "source-certainty-register",
        "phase-curve",
        "viewBox='0 0 220 86'",
        "phaseBlink",
        "top: clamp(.92rem, 1.8vw, 1.28rem)",
        "M24 68 C 61 63",
        "updatePhaseCurveState",
        "What this means",
        "--kuro-field-ground: #0d0c0a",
        "--old-brass: #b89455",
        "--moss: #7f9878",
        "rel='icon' type='image/png' sizes='64x64' href='/rhythm-icon-64.png'",
        "rel='apple-touch-icon' href='/rhythm-icon-192.png'",
        "class='brand-mark' src='/rhythm-logo.png'",
        "brandFloat",
        "brand-title",
        "data-evidence-type",
        "evidence-mini",
        "tsraFieldMemory.v1",
        "TSRA_APP_VERSION",
        "TSRA_VERSION_URL",
        "checkForRemoteAppVersion",
        "refreshInstalledApp",
        "app-update-notice",
        "pageshow",
        "TSRA_UPDATE_CHECK_INTERVAL",
        "TSRA_AUTO_FIELD_MEMORY_INTERVAL",
        "autoCacheFieldMemory",
        "field-memory-auto-save-requested",
        "registration.update()",
        "controllerchange",
        "tsraObservationLedger.v1",
        "openOutcomeRecorder(this)",
        "not a certified warning system",
        "never enough for safety decisions by itself",
        "When did it happen?",
        "Nothing happened during the watch",
    ]
    for marker in required_report_markers:
        if marker not in report:
            errors.append(f"missing report marker: {marker}")
    if "capacity" in report.lower():
        errors.append("public capacity text found in report")
    if "87.7%" in report or "87.7% timing fit" in report:
        errors.append("stale static model-fit value found in report")
    if "background: radial-gradient(circle at 12% -10%" in report:
        errors.append("dark backdrop glow found in report")
    if "--bg: #11110f" in report:
        errors.append("old relic dark ground token found in report")
    if ">Cache core<" in report or ">Save field memory<" in report:
        errors.append("manual field-memory cache button text found in report")
    if ">Source & certainty<" in report or ">Source &amp; certainty<" in report:
        errors.append("technical source/certainty label found in report")
    if "<section class='offline-register'" in report or "<section class='felt-register'" in report:
        errors.append("removed field-access or felt-signal strip found in report")
    required_sw_markers = [
        "TSRA_CACHE_VERSION",
        "networkFirst(request, '/seismic_report.html')",
        "request.headers.has('range')",
        "buildRangeResponse",
        "TSRA_CACHE_FIELD_MEMORY",
        "TSRA_SKIP_WAITING",
        "client.navigate(client.url)",
        "'/tsra-version.json'",
        "TSRA_VERSION_REQUEST",
        "TSRA_VERSION_RESPONSE",
        "'/rhythm-logo.png'",
        "'/rhythm-icon-512.png'",
    ]
    for marker in required_sw_markers:
        if marker not in service_worker:
            errors.append(f"missing service worker marker: {marker}")
    return errors


def extract_inline_script(report: str, output: Path) -> None:
    start = report.find("<script>")
    end = report.rfind("</script>")
    if start == -1 or end == -1 or end <= start:
        die("could not extract inline script")
    output.write_text(report[start + len("<script>"):end])


def run_command(command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        die(f"command failed: {' '.join(command)}")


def run_verification(report_path: Path, service_worker_path: Path, version_path: Path, repo_root: Path) -> None:
    report = read_text(report_path)
    service_worker = read_text(service_worker_path)
    version_file = read_text(version_path)
    errors = verify_report(report, service_worker)
    try:
        version_payload = json.loads(version_file)
    except json.JSONDecodeError:
        version_payload = {}
        errors.append("version file is not valid JSON")
    expected_version = extract_service_worker_version(service_worker)
    if version_payload.get("version") != expected_version:
        errors.append(f"version file mismatch: {version_payload.get('version')!r} != {expected_version!r}")
    if f"const TSRA_APP_VERSION = '{expected_version}';" not in report:
        errors.append("report app version does not match service worker version")
    if errors:
        for error in errors:
            print(f"verify: {error}", file=sys.stderr)
        die("verification failed")
    inline_script = Path("/tmp/tsra-inline-script.js")
    extract_inline_script(report, inline_script)
    run_command(["node", "--check", str(inline_script)], repo_root)
    run_command(["node", "--check", str(service_worker_path)], repo_root)
    viewer = repo_root / "viewer-server.js"
    if viewer.exists():
        run_command(["node", "--check", str(viewer)], repo_root)
    if (repo_root / ".git").exists():
        run_command(["git", "diff", "--check", "--", str(report_path), str(service_worker_path), str(version_path)], repo_root)
    else:
        print("verify: skipped git diff --check outside a git worktree")
    print("verify: ok")


def commit_and_push(repo_root: Path, paths: list[Path], message: str, push: bool) -> None:
    run_command(["git", "add", *[str(path) for path in paths]], repo_root)
    run_command(["git", "diff", "--cached", "--stat"], repo_root)
    run_command(["git", "commit", "-m", message], repo_root)
    if push:
        run_command(["git", "push", "origin", "main"], repo_root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update TSRA local observation surfaces safely.")
    parser.add_argument("--report", type=Path, default=Path("seismic_report.html"))
    parser.add_argument("--service-worker", type=Path, default=Path("service-worker.js"))
    parser.add_argument("--version-file", type=Path, default=Path("tsra-version.json"))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify")
    for command in ("felt", "elapsed"):
        p = sub.add_parser(command)
        p.add_argument("--time", required=True, help="Local report time, e.g. '2026-06-10 23:15'")
        p.add_argument("--watch", required=True, help="Watch phase: 1.0x, 3.5x, 7.0x, or 9.5x")
        p.add_argument("--note", default="Local shake felt" if command == "felt" else "No local shake observed")
        p.add_argument("--duration", default=None, help="Felt duration, e.g. 'about 1 minute'")
        p.add_argument("--advance-cycle", action="store_true", help="Open the next 1x/3.5x/7x/9.5x cycle from this outcome time")
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--commit", action="store_true")
        p.add_argument("--push", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    report_path = args.report if args.report.is_absolute() else repo_root / args.report
    service_worker_path = args.service_worker if args.service_worker.is_absolute() else repo_root / args.service_worker
    version_path = args.version_file if args.version_file.is_absolute() else repo_root / args.version_file
    if args.command == "verify":
        run_verification(report_path, service_worker_path, version_path, repo_root)
        return
    kind: OutcomeKind = "felt" if args.command == "felt" else "elapsed"
    outcome = Outcome(
        kind=kind,
        report_time=parse_report_time(args.time),
        watch=normalize_watch(args.watch),
        note=args.note,
        duration=args.duration,
        advance_cycle=args.advance_cycle,
    )
    original_report = read_text(report_path)
    original_sw = read_text(service_worker_path)
    updated_report, updated_sw = apply_outcome(original_report, original_sw, outcome)
    updated_version = build_version_file(updated_sw)
    errors = verify_report(updated_report, updated_sw)
    if errors:
        for error in errors:
            print(f"verify: {error}", file=sys.stderr)
        die("refusing to write invalid report")
    write_text(report_path, updated_report, args.dry_run)
    write_text(service_worker_path, updated_sw, args.dry_run)
    write_text(version_path, updated_version, args.dry_run)
    if args.dry_run:
        print("dry-run: update would succeed")
        return
    run_verification(report_path, service_worker_path, version_path, repo_root)
    print("updated: seismic_report.html, service-worker.js, tsra-version.json")
    if args.commit or args.push:
        commit_message = f"fix: log {time_label(outcome.report_time).lower()} {kind} observation"
        commit_and_push(repo_root, [report_path, service_worker_path, version_path], commit_message, push=args.push)


if __name__ == "__main__":
    main()
