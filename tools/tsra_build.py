#!/usr/bin/env python3
"""Build-time verification for versioned TSRA sequence datasets.

The verifier treats data as evidence, not presentation state. It checks file
integrity, schema identity, event conservation, chronology, AOI bounds, source
URLs, daily and spatial derivations, significant-event provenance, and the
historical-clock audit without modifying the dataset or production report.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any, Sequence

PHIVOLCS_URL_PREFIX = "https://earthquake.phivolcs.dost.gov.ph/"
EXPECTED_DATA_FILES = {"summary.json", "events.csv", "significant-events.csv"}
MAGNITUDE_BIN_KEYS = (
    "belowM2",
    "m2To2_9",
    "m3To3_9",
    "m4To4_4",
    "m4_5To4_9",
    "m5To5_9",
    "m6AndAbove",
)
HISTORICAL_THRESHOLDS = (2.0, 3.0, 4.0, 4.5, 5.0)

JsonObject = dict[str, Any]
CsvRow = dict[str, str]


def add_error(errors: list[str], message: str) -> None:
    if message not in errors:
        errors.append(message)


def read_json_object(path: Path, errors: list[str]) -> JsonObject:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        add_error(errors, f"missing file: {path.name}")
        return {}
    except json.JSONDecodeError as exc:
        add_error(errors, f"invalid JSON in {path.name}: {exc}")
        return {}
    if not isinstance(payload, dict):
        add_error(errors, f"expected JSON object in {path.name}")
        return {}
    return payload


def read_csv_rows(path: Path, errors: list[str]) -> list[CsvRow]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                add_error(errors, f"missing CSV header: {path.name}")
                return []
            return list(reader)
    except FileNotFoundError:
        add_error(errors, f"missing file: {path.name}")
        return []
    except csv.Error as exc:
        add_error(errors, f"invalid CSV in {path.name}: {exc}")
        return []


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mapping(value: Any, label: str, errors: list[str]) -> JsonObject:
    if isinstance(value, dict):
        return value
    add_error(errors, f"expected object: {label}")
    return {}


def json_array(value: Any, label: str, errors: list[str]) -> list[Any]:
    if isinstance(value, list):
        return value
    add_error(errors, f"expected array: {label}")
    return []


def integer(value: Any, label: str, errors: list[str]) -> int | None:
    if isinstance(value, bool):
        add_error(errors, f"expected integer: {label}")
        return None
    if isinstance(value, int):
        return value
    add_error(errors, f"expected integer: {label}")
    return None


def number(value: Any, label: str, errors: list[str]) -> float | None:
    if isinstance(value, bool):
        add_error(errors, f"expected number: {label}")
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    add_error(errors, f"expected finite number: {label}")
    return None


def csv_float(row: CsvRow, field: str, row_label: str, errors: list[str]) -> float | None:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError):
        add_error(errors, f"invalid {field} in {row_label}")
        return None
    if not math.isfinite(value):
        add_error(errors, f"non-finite {field} in {row_label}")
        return None
    return value


def csv_time(row: CsvRow, field: str, row_label: str, errors: list[str]) -> datetime | None:
    try:
        return datetime.fromisoformat(row[field])
    except (KeyError, TypeError, ValueError):
        add_error(errors, f"invalid {field} in {row_label}")
        return None


def close_enough(left: float, right: float, *, tolerance: float = 1e-9) -> bool:
    return math.isclose(left, right, rel_tol=tolerance, abs_tol=tolerance)


def verify_file_manifest(
    dataset_dir: Path,
    manifest: JsonObject,
    errors: list[str],
) -> dict[str, JsonObject]:
    entries = json_array(manifest.get("files"), "manifest.files", errors)
    files: dict[str, JsonObject] = {}
    for index, raw_entry in enumerate(entries):
        entry = mapping(raw_entry, f"manifest.files[{index}]", errors)
        name = entry.get("path")
        if not isinstance(name, str) or not name:
            add_error(errors, f"invalid path in manifest.files[{index}]")
            continue
        if name in files:
            add_error(errors, f"duplicate manifest file entry: {name}")
            continue
        files[name] = entry

    missing_entries = EXPECTED_DATA_FILES - set(files)
    extra_entries = set(files) - EXPECTED_DATA_FILES
    if missing_entries:
        add_error(errors, f"missing manifest entries: {', '.join(sorted(missing_entries))}")
    if extra_entries:
        add_error(errors, f"unexpected manifest entries: {', '.join(sorted(extra_entries))}")

    for name, entry in files.items():
        path = dataset_dir / name
        if not path.is_file():
            add_error(errors, f"missing manifested file: {name}")
            continue
        expected_bytes = integer(entry.get("bytes"), f"manifest.files[{name}].bytes", errors)
        if expected_bytes is not None and path.stat().st_size != expected_bytes:
            add_error(
                errors,
                f"byte-size mismatch for {name}: {path.stat().st_size} != {expected_bytes}",
            )
        expected_hash = entry.get("sha256")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            add_error(errors, f"invalid SHA-256 in manifest for {name}")
        elif sha256(path) != expected_hash:
            add_error(errors, f"SHA-256 mismatch for {name}")
    return files


def verify_source_capture(dataset_dir: Path, manifest: JsonObject, errors: list[str]) -> None:
    source_artifact = manifest.get("sourceArtifact")
    if not isinstance(source_artifact, dict):
        if manifest.get("artifactVersion") == "v0.3":
            add_error(errors, "v0.3 source artifact metadata is missing")
        return
    archive = source_artifact.get("captureArchive")
    if not isinstance(archive, dict):
        if manifest.get("artifactVersion") == "v0.3":
            add_error(errors, "v0.3 source capture metadata is missing")
        return
    relative = archive.get("path")
    if not isinstance(relative, str) or not relative:
        add_error(errors, "source capture path is invalid")
        return
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        add_error(errors, "source capture path must remain inside the dataset")
        return
    path = dataset_dir / relative_path
    if not path.is_file():
        add_error(errors, f"missing source capture: {relative}")
        return
    expected_bytes = integer(archive.get("bytes"), "sourceArtifact.captureArchive.bytes", errors)
    if expected_bytes is not None and path.stat().st_size != expected_bytes:
        add_error(errors, f"source capture byte-size mismatch: {path.stat().st_size} != {expected_bytes}")
    expected_hash = archive.get("sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        add_error(errors, "source capture SHA-256 is invalid")
    elif sha256(path) != expected_hash:
        add_error(errors, "source capture SHA-256 mismatch")


def magnitude_bins(magnitudes: Sequence[float]) -> dict[str, int]:
    return {
        "belowM2": sum(value < 2 for value in magnitudes),
        "m2To2_9": sum(2 <= value < 3 for value in magnitudes),
        "m3To3_9": sum(3 <= value < 4 for value in magnitudes),
        "m4To4_4": sum(4 <= value < 4.5 for value in magnitudes),
        "m4_5To4_9": sum(4.5 <= value < 5 for value in magnitudes),
        "m5To5_9": sum(5 <= value < 6 for value in magnitudes),
        "m6AndAbove": sum(value >= 6 for value in magnitudes),
    }


def branch_id(latitude: float) -> str:
    if latitude < 5.2:
        return "southOffshore"
    if latitude < 5.5:
        return "balutCentral"
    return "glanMaasimNorth"


def verify_identity(manifest: JsonObject, summary: JsonObject, errors: list[str]) -> None:
    if manifest.get("schemaVersion") != 1 or summary.get("schemaVersion") != 1:
        add_error(errors, "schemaVersion must equal 1 in manifest and summary")
    if manifest.get("datasetId") != summary.get("datasetId"):
        add_error(errors, "datasetId mismatch between manifest and summary")
    if manifest.get("artifactVersion") != summary.get("artifactVersion"):
        add_error(errors, "artifactVersion mismatch between manifest and summary")
    if manifest.get("capture") != summary.get("capture"):
        add_error(errors, "capture metadata mismatch between manifest and summary")
    if manifest.get("aoi") != summary.get("aoi"):
        add_error(errors, "AOI metadata mismatch between manifest and summary")

    capture = mapping(summary.get("capture"), "summary.capture", errors)
    if capture.get("isLive") is not False:
        add_error(errors, "summary.capture.isLive must be false for this static snapshot")
    status = manifest.get("status")
    if not isinstance(status, str) or "not live" not in status.lower():
        add_error(errors, "manifest status must explicitly state that the snapshot is not live")

    interpretation = mapping(summary.get("interpretation"), "summary.interpretation", errors)
    standing = interpretation.get("standing")
    if not isinstance(standing, str) or "no validated single-period clock" not in standing.lower():
        add_error(errors, "standing interpretation must preserve the clock non-validation boundary")
    classification = interpretation.get("classification")
    if not isinstance(classification, str) or "inference" not in classification.lower():
        add_error(errors, "standing interpretation must be classified as inference")

    source_boundaries = json_array(summary.get("sourceBoundaries"), "summary.sourceBoundaries", errors)
    boundary_text = " ".join(item for item in source_boundaries if isinstance(item, str)).lower()
    for required in (
        "aoi inclusion is not an official associated-aftershock flag",
        "private local observations remain separate",
        "not a warning or prediction surface",
    ):
        if required not in boundary_text:
            add_error(errors, f"missing source boundary: {required}")


def verify_events(
    manifest: JsonObject,
    summary: JsonObject,
    events: list[CsvRow],
    errors: list[str],
) -> tuple[list[datetime], list[float], list[float], list[float]]:
    invariants = mapping(manifest.get("invariants"), "manifest.invariants", errors)
    expected_rows = integer(invariants.get("officialEventRows"), "manifest.invariants.officialEventRows", errors)
    if expected_rows is not None and len(events) != expected_rows:
        add_error(errors, f"official event row mismatch: {len(events)} != {expected_rows}")

    counts = mapping(summary.get("counts"), "summary.counts", errors)
    summary_total = integer(
        counts.get("officialPhivolcsRowsDeduplicated"),
        "summary.counts.officialPhivolcsRowsDeduplicated",
        errors,
    )
    if summary_total is not None and len(events) != summary_total:
        add_error(errors, f"summary event total mismatch: {summary_total} != {len(events)}")

    keys: list[str] = []
    times: list[datetime] = []
    magnitudes: list[float] = []
    latitudes: list[float] = []
    depths: list[float] = []

    aoi = mapping(summary.get("aoi"), "summary.aoi", errors)
    lat_min = number(aoi.get("latitudeMin"), "summary.aoi.latitudeMin", errors)
    lat_max = number(aoi.get("latitudeMax"), "summary.aoi.latitudeMax", errors)
    lon_min = number(aoi.get("longitudeMin"), "summary.aoi.longitudeMin", errors)
    lon_max = number(aoi.get("longitudeMax"), "summary.aoi.longitudeMax", errors)
    meaning = aoi.get("meaning")
    if not isinstance(meaning, str) or "not official phivolcs sequence association" not in meaning.lower():
        add_error(errors, "AOI meaning must reject automatic sequence association")

    for index, row in enumerate(events, start=1):
        row_label = f"events.csv row {index}"
        key = row.get("event_key", "")
        if not key:
            add_error(errors, f"missing event_key in {row_label}")
        keys.append(key)

        time = csv_time(row, "time_pht", row_label, errors)
        magnitude = csv_float(row, "magnitude", row_label, errors)
        latitude = csv_float(row, "latitude", row_label, errors)
        longitude = csv_float(row, "longitude", row_label, errors)
        depth = csv_float(row, "depth_km", row_label, errors)
        if time is not None:
            times.append(time)
        if magnitude is not None:
            magnitudes.append(magnitude)
        if latitude is not None:
            latitudes.append(latitude)
        if depth is not None:
            depths.append(depth)
        if (
            latitude is not None
            and longitude is not None
            and None not in (lat_min, lat_max, lon_min, lon_max)
            and not (lat_min <= latitude <= lat_max and lon_min <= longitude <= lon_max)
        ):
            add_error(errors, f"event outside AOI: {key or index}")
        url = row.get("bulletin_url", "")
        if not url.startswith(PHIVOLCS_URL_PREFIX):
            add_error(errors, f"invalid PHIVOLCS bulletin URL: {key or index}")
        if row.get("source_class") != "official_phivolcs_public_bulletin_row":
            add_error(errors, f"invalid source_class: {key or index}")
        association = row.get("sequence_association_status", "")
        if "spatial_AOI_inclusion_only" not in association:
            add_error(errors, f"missing AOI-only association boundary: {key or index}")

    if len(set(keys)) != len(keys):
        add_error(errors, "event_key values are not unique")
    if len(times) == len(events) and times != sorted(times):
        add_error(errors, "events are not chronological")

    capture = mapping(summary.get("capture"), "summary.capture", errors)
    if times:
        if capture.get("firstIncludedEventPht") != times[0].isoformat():
            add_error(errors, "first included event does not match capture metadata")
        if capture.get("lastIncludedEventPht") != times[-1].isoformat():
            add_error(errors, "last included event does not match capture metadata")

    if len(magnitudes) == len(events):
        computed_bins = magnitude_bins(magnitudes)
        reported_bins = mapping(counts.get("magnitudeBins"), "summary.counts.magnitudeBins", errors)
        if set(reported_bins) != set(MAGNITUDE_BIN_KEYS):
            add_error(errors, "summary magnitude-bin keys do not match the schema")
        if computed_bins != reported_bins:
            add_error(errors, f"magnitude-bin mismatch: {reported_bins} != {computed_bins}")
        if sum(computed_bins.values()) != len(events):
            add_error(errors, "magnitude bins do not conserve to official event rows")
        threshold_counts = {
            "m4AndAbove": sum(value >= 4 for value in magnitudes),
            "m4_5AndAbove": sum(value >= 4.5 for value in magnitudes),
            "m5AndAbove": sum(value >= 5 for value in magnitudes),
            "m6AndAbove": sum(value >= 6 for value in magnitudes),
        }
        for name, expected in threshold_counts.items():
            if counts.get(name) != expected:
                add_error(errors, f"summary {name} mismatch: {counts.get(name)} != {expected}")

    return times, magnitudes, latitudes, depths


def verify_daily_activity(
    summary: JsonObject,
    events: list[CsvRow],
    errors: list[str],
) -> None:
    daily = json_array(summary.get("dailyActivity"), "summary.dailyActivity", errors)
    actual_counts = Counter(row.get("time_pht", "")[:10] for row in events)
    actual_max: dict[str, float] = {}
    for index, row in enumerate(events, start=1):
        date = row.get("time_pht", "")[:10]
        try:
            magnitude = float(row["magnitude"])
        except (KeyError, TypeError, ValueError):
            continue
        actual_max[date] = max(actual_max.get(date, magnitude), magnitude)

    seen_dates: set[str] = set()
    total = 0
    for index, raw_day in enumerate(daily):
        day = mapping(raw_day, f"summary.dailyActivity[{index}]", errors)
        date = day.get("datePht")
        if not isinstance(date, str) or not date:
            add_error(errors, f"invalid datePht in dailyActivity[{index}]")
            continue
        if date in seen_dates:
            add_error(errors, f"duplicate daily activity date: {date}")
        seen_dates.add(date)
        count = integer(day.get("eventCount"), f"dailyActivity[{date}].eventCount", errors)
        if count is None:
            continue
        total += count
        if actual_counts.get(date, 0) != count:
            add_error(errors, f"daily count mismatch for {date}: {count} != {actual_counts.get(date, 0)}")
        component_keys = ("belowM2", "m2To2_9", "m3To3_9", "m4To4_9", "m5AndAbove")
        components = [integer(day.get(key), f"dailyActivity[{date}].{key}", errors) for key in component_keys]
        if all(value is not None for value in components) and sum(value for value in components if value is not None) != count:
            add_error(errors, f"daily magnitude classes do not conserve for {date}")
        if date in actual_max:
            maximum = number(day.get("maxMagnitude"), f"dailyActivity[{date}].maxMagnitude", errors)
            if maximum is not None and not close_enough(maximum, actual_max[date]):
                add_error(errors, f"daily maximum mismatch for {date}: {maximum} != {actual_max[date]}")
        elif day.get("maxMagnitude") is not None:
            add_error(errors, f"daily maximum must be null without captured events: {date}")
        coverage = day.get("coverage")
        if not isinstance(coverage, str) or not coverage:
            add_error(errors, f"missing coverage status for {date}")
        if date not in actual_counts and (count != 0 or coverage != "not_captured"):
            add_error(errors, f"uncaptured gap day must be zero and marked not_captured: {date}")

    if total != len(events):
        add_error(errors, f"daily activity does not conserve: {total} != {len(events)}")
    if not set(actual_counts).issubset(seen_dates):
        add_error(errors, "daily activity is missing one or more event dates")


def verify_spatial_branches(
    summary: JsonObject,
    events: list[CsvRow],
    errors: list[str],
) -> None:
    reported = json_array(summary.get("spatialBranches"), "summary.spatialBranches", errors)
    reported_by_id: dict[str, JsonObject] = {}
    for index, raw_branch in enumerate(reported):
        branch = mapping(raw_branch, f"summary.spatialBranches[{index}]", errors)
        identifier = branch.get("id")
        if not isinstance(identifier, str) or not identifier:
            add_error(errors, f"invalid spatial branch id at index {index}")
            continue
        if identifier in reported_by_id:
            add_error(errors, f"duplicate spatial branch id: {identifier}")
        reported_by_id[identifier] = branch

    expected_ids = {"southOffshore", "balutCentral", "glanMaasimNorth"}
    if set(reported_by_id) != expected_ids:
        add_error(errors, "spatial branch IDs do not match the schema")

    computed: dict[str, list[tuple[float, float]]] = {identifier: [] for identifier in expected_ids}
    for index, row in enumerate(events, start=1):
        try:
            latitude = float(row["latitude"])
            magnitude = float(row["magnitude"])
            depth = float(row["depth_km"])
        except (KeyError, TypeError, ValueError):
            add_error(errors, f"cannot classify spatial branch for events.csv row {index}")
            continue
        computed[branch_id(latitude)].append((magnitude, depth))

    for identifier, rows in computed.items():
        branch = reported_by_id.get(identifier, {})
        expected_count = len(rows)
        if branch.get("eventCount") != expected_count:
            add_error(errors, f"spatial event count mismatch for {identifier}")
        expected_fraction = expected_count / len(events) if events else 0.0
        fraction = number(branch.get("fraction"), f"spatialBranches[{identifier}].fraction", errors)
        if fraction is not None and not close_enough(fraction, expected_fraction):
            add_error(errors, f"spatial fraction mismatch for {identifier}")
        if branch.get("m4AndAbove") != sum(magnitude >= 4 for magnitude, _ in rows):
            add_error(errors, f"M4+ spatial count mismatch for {identifier}")
        if branch.get("m5AndAbove") != sum(magnitude >= 5 for magnitude, _ in rows):
            add_error(errors, f"M5+ spatial count mismatch for {identifier}")
        expected_median = median(depth for _, depth in rows) if rows else None
        reported_median = number(branch.get("medianDepthKm"), f"spatialBranches[{identifier}].medianDepthKm", errors)
        if expected_median is not None and reported_median is not None and not close_enough(reported_median, expected_median):
            add_error(errors, f"median depth mismatch for {identifier}")

    if sum(len(rows) for rows in computed.values()) != len(events):
        add_error(errors, "spatial branches do not conserve to official event rows")


def verify_significant_events(
    manifest: JsonObject,
    summary: JsonObject,
    significant_rows: list[CsvRow],
    errors: list[str],
) -> None:
    invariants = mapping(manifest.get("invariants"), "manifest.invariants", errors)
    expected_rows = integer(
        invariants.get("significantFinalBulletinRows"),
        "manifest.invariants.significantFinalBulletinRows",
        errors,
    )
    if expected_rows is not None and len(significant_rows) != expected_rows:
        add_error(errors, f"significant row mismatch: {len(significant_rows)} != {expected_rows}")

    summary_events = json_array(summary.get("significantEvents"), "summary.significantEvents", errors)
    if len(summary_events) != len(significant_rows):
        add_error(errors, "significant summary length does not match significant-events.csv")

    summary_by_time: dict[str, JsonObject] = {}
    for index, raw_event in enumerate(summary_events):
        event = mapping(raw_event, f"summary.significantEvents[{index}]", errors)
        time = event.get("timePht")
        if isinstance(time, str):
            if time in summary_by_time:
                add_error(errors, f"duplicate significant summary time: {time}")
            summary_by_time[time] = event
        else:
            add_error(errors, f"invalid significant summary time at index {index}")

    for index, row in enumerate(significant_rows, start=1):
        row_label = f"significant-events.csv row {index}"
        time = row.get("time_pht_final", "")
        event = summary_by_time.get(time)
        if event is None:
            add_error(errors, f"missing significant summary event: {time or row_label}")
            continue
        magnitude = csv_float(row, "magnitude_final", row_label, errors)
        if magnitude is not None and magnitude < 4.5:
            add_error(errors, f"significant event below M4.5: {time}")
        if magnitude is not None and event.get("magnitude") != magnitude:
            add_error(errors, f"significant magnitude mismatch: {time}")
        comparisons = {
            "magnitudeType": row.get("magnitude_type"),
            "location": row.get("location"),
            "maxReportedIntensity": row.get("max_reported_intensity") or None,
            "officialSequenceStatement": row.get("official_sequence_statement"),
            "finalBulletinUrl": row.get("final_bulletin_url"),
        }
        for field, expected in comparisons.items():
            if event.get(field) != expected:
                add_error(errors, f"significant {field} mismatch: {time}")
        url = row.get("final_bulletin_url", "")
        if not url.startswith(PHIVOLCS_URL_PREFIX):
            add_error(errors, f"invalid significant PHIVOLCS URL: {time or row_label}")
        statement = row.get("official_sequence_statement", "")
        if "aftershock of June 2026" not in statement:
            add_error(errors, f"missing official sequence statement: {time or row_label}")


def verify_historical_clock(
    summary: JsonObject,
    events: list[CsvRow],
    errors: list[str],
) -> None:
    audit = mapping(summary.get("historicalClockAudit"), "summary.historicalClockAudit", errors)
    baseline = number(audit.get("baselineMinutes"), "historicalClockAudit.baselineMinutes", errors)
    null_baseline = number(
        audit.get("nullBaselineMinutes"),
        "historicalClockAudit.nullBaselineMinutes",
        errors,
    )
    tolerance = number(audit.get("toleranceMinutes"), "historicalClockAudit.toleranceMinutes", errors)
    null_probability = number(
        audit.get("uniformModuloNullProbability"),
        "historicalClockAudit.uniformModuloNullProbability",
        errors,
    )
    status = audit.get("status")
    if not isinstance(status, str) or "no validated single-period clock" not in status.lower():
        add_error(errors, "historical clock status must preserve non-validation")
    if baseline is None or null_baseline is None or tolerance is None or null_probability is None:
        return
    if baseline <= 0 or null_baseline <= 0 or tolerance <= 0 or tolerance >= min(baseline, null_baseline) / 2:
        add_error(errors, "historical clock baseline/tolerance is outside the supported range")
        return
    expected_null = (2 * tolerance) / null_baseline
    if not close_enough(null_probability, expected_null):
        add_error(errors, f"historical null probability mismatch: {null_probability} != {expected_null}")

    investigation = mapping(
        audit.get("originalInvestigation"),
        "historicalClockAudit.originalInvestigation",
        errors,
    )
    investigation_status = investigation.get("status")
    if not isinstance(investigation_status, str) or "historical" not in investigation_status.lower() or "not current catalog truth" not in investigation_status.lower():
        add_error(errors, "original investigation must be bounded as historical provenance")
    timestamp_boundary = investigation.get("timestampBoundary")
    if not isinstance(timestamp_boundary, str) or "not substituted" not in timestamp_boundary.lower():
        add_error(errors, "original investigation timestamp boundary is missing")
    original_events = json_array(
        investigation.get("events"),
        "historicalClockAudit.originalInvestigation.events",
        errors,
    )
    if investigation.get("selectedEventCount") != 11 or len(original_events) != 11:
        add_error(errors, "original investigation must preserve 11 selected events")
    labels = [event.get("label") for event in original_events if isinstance(event, dict)]
    expected_labels = ["MS", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10"]
    if labels != expected_labels:
        add_error(errors, f"original investigation labels changed: {labels}")
    standard_events = [
        event for event in original_events
        if isinstance(event, dict) and event.get("result") not in ("anchor", "excluded sub-pulse")
    ]
    inside_events = [event for event in standard_events if event.get("result") == "inside tolerance"]
    if investigation.get("standardIntervalCount") != len(standard_events) or len(standard_events) != 9:
        add_error(errors, "original investigation standard interval count changed")
    if investigation.get("insideToleranceCount") != len(inside_events) or len(inside_events) != 8:
        add_error(errors, "original investigation inside-tolerance count changed")
    selected_fraction = number(
        investigation.get("selectedAlignmentFraction"),
        "historicalClockAudit.originalInvestigation.selectedAlignmentFraction",
        errors,
    )
    if selected_fraction is not None and not close_enough(selected_fraction, 8 / 9):
        add_error(errors, "original investigation selected alignment fraction changed")
    offsets = [
        abs(float(event["offsetMinutes"]))
        for event in standard_events
        if isinstance(event.get("offsetMinutes"), (int, float))
    ]
    if len(offsets) != 9:
        add_error(errors, "original investigation offsets are incomplete")
    else:
        expected_original_median = median(offsets)
        reported_original_median = number(
            investigation.get("medianAbsoluteOffsetMinutes"),
            "historicalClockAudit.originalInvestigation.medianAbsoluteOffsetMinutes",
            errors,
        )
        if reported_original_median is not None and not close_enough(reported_original_median, expected_original_median):
            add_error(errors, "original investigation median offset changed")
        for event in standard_events:
            offset = event.get("offsetMinutes")
            result = event.get("result")
            if isinstance(offset, (int, float)):
                expected_result = "inside tolerance" if abs(float(offset)) <= tolerance else "outside tolerance"
                if result != expected_result:
                    add_error(errors, f"original investigation tolerance result changed for {event.get('label')}")

    capture = mapping(summary.get("capture"), "summary.capture", errors)
    analysis_start_raw = audit.get("analysisCoverageStartPht", capture.get("coverageStartPht"))
    try:
        analysis_start = datetime.fromisoformat(str(analysis_start_raw)).replace(tzinfo=None)
    except ValueError:
        analysis_start = None
        add_error(errors, "historical clock analysis coverage start is invalid")

    parsed_events: list[tuple[datetime, float]] = []
    for index, row in enumerate(events, start=1):
        time = csv_time(row, "time_pht", f"events.csv row {index}", errors)
        magnitude = csv_float(row, "magnitude", f"events.csv row {index}", errors)
        if time is not None and magnitude is not None and (analysis_start is None or time >= analysis_start):
            parsed_events.append((time, magnitude))

    threshold_entries = json_array(audit.get("thresholds"), "historicalClockAudit.thresholds", errors)
    by_threshold: dict[float, JsonObject] = {}
    for index, raw_entry in enumerate(threshold_entries):
        entry = mapping(raw_entry, f"historicalClockAudit.thresholds[{index}]", errors)
        threshold = number(entry.get("minimumMagnitude"), f"historicalClockAudit.thresholds[{index}].minimumMagnitude", errors)
        if threshold is not None:
            by_threshold[threshold] = entry
    if set(by_threshold) != set(HISTORICAL_THRESHOLDS):
        add_error(errors, "historical threshold set does not match the schema")

    for threshold in HISTORICAL_THRESHOLDS:
        entry = by_threshold.get(threshold)
        if entry is None:
            continue
        selected = [time for time, magnitude in parsed_events if magnitude >= threshold]
        intervals = [
            (selected[index] - selected[index - 1]).total_seconds() / 60
            for index in range(1, len(selected))
        ]
        alignment_count = 0
        for interval in intervals:
            remainder = interval % baseline
            distance = min(remainder, baseline - remainder)
            if distance <= tolerance:
                alignment_count += 1
        expected_median = median(intervals) if intervals else None
        checks = {
            "eventCount": len(selected),
            "intervalCount": len(intervals),
            "alignmentCount": alignment_count,
        }
        for field, expected in checks.items():
            if entry.get(field) != expected:
                add_error(errors, f"historical {field} mismatch at M≥{threshold:g}")
        reported_median = number(entry.get("medianIntervalMinutes"), f"historical threshold M≥{threshold:g} median", errors)
        if expected_median is not None and reported_median is not None and not close_enough(reported_median, expected_median):
            add_error(errors, f"historical median interval mismatch at M≥{threshold:g}")
        reported_fraction = number(entry.get("alignmentFraction"), f"historical threshold M≥{threshold:g} alignmentFraction", errors)
        expected_fraction = alignment_count / len(intervals) if intervals else 0.0
        if reported_fraction is not None and not close_enough(reported_fraction, expected_fraction):
            add_error(errors, f"historical alignment fraction mismatch at M≥{threshold:g}")
        entry_null = number(entry.get("uniformModuloNullProbability"), f"historical threshold M≥{threshold:g} null", errors)
        if entry_null is not None and not close_enough(entry_null, expected_null):
            add_error(errors, f"historical null mismatch at M≥{threshold:g}")
        p_value = number(entry.get("descriptiveOneSidedBinomialPValue"), f"historical threshold M≥{threshold:g} p-value", errors)
        if p_value is not None and not (0 <= p_value <= 1):
            add_error(errors, f"historical p-value outside [0,1] at M≥{threshold:g}")


def verify_manifest_row_metadata(
    files: dict[str, JsonObject],
    events: list[CsvRow],
    significant_rows: list[CsvRow],
    errors: list[str],
) -> None:
    expected_rows = {
        "events.csv": len(events),
        "significant-events.csv": len(significant_rows),
    }
    for name, expected in expected_rows.items():
        entry = files.get(name, {})
        if entry.get("dataRows") != expected:
            add_error(errors, f"manifest dataRows mismatch for {name}")


def verify_dataset(dataset_dir: Path) -> list[str]:
    errors: list[str] = []
    if not dataset_dir.is_dir():
        return [f"dataset directory does not exist: {dataset_dir}"]

    manifest = read_json_object(dataset_dir / "manifest.json", errors)
    summary = read_json_object(dataset_dir / "summary.json", errors)
    files = verify_file_manifest(dataset_dir, manifest, errors)
    verify_source_capture(dataset_dir, manifest, errors)
    events = read_csv_rows(dataset_dir / "events.csv", errors)
    significant_rows = read_csv_rows(dataset_dir / "significant-events.csv", errors)

    verify_identity(manifest, summary, errors)
    verify_events(manifest, summary, events, errors)
    verify_daily_activity(summary, events, errors)
    verify_spatial_branches(summary, events, errors)
    verify_significant_events(manifest, summary, significant_rows, errors)
    verify_historical_clock(summary, events, errors)
    verify_manifest_row_metadata(files, events, significant_rows, errors)
    return errors


def default_dataset_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "sequence-v0.3"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify versioned TSRA sequence data.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser("verify", help="Verify data integrity and claim boundaries.")
    verify.add_argument(
        "--dataset",
        type=Path,
        default=default_dataset_dir(),
        help="Dataset directory (default: data/sequence-v0.3).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "verify":
        return 2
    dataset_dir = args.dataset.resolve()
    errors = verify_dataset(dataset_dir)
    if errors:
        for error in errors:
            print(f"verify: {error}", file=sys.stderr)
        print(f"verify: failed with {len(errors)} error(s)", file=sys.stderr)
        return 1

    summary = json.loads((dataset_dir / "summary.json").read_text(encoding="utf-8"))
    counts = summary["counts"]
    print(f"verify: dataset={summary['datasetId']}")
    print(
        "verify: "
        f"events={counts['officialPhivolcsRowsDeduplicated']} "
        f"significant={len(summary['significantEvents'])} "
        f"daily={len(summary['dailyActivity'])} "
        f"branches={len(summary['spatialBranches'])}"
    )
    print("verify: integrity, conservation, provenance, and claim boundaries ok")
    print("verify: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
