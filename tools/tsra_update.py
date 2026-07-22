#!/usr/bin/env python3
"""Compatibility verifier for the static TSRA application shell.

The former felt/elapsed watch mutator is intentionally retired. Reviewed
sequence data is verified by ``tools/tsra_build.py``; private observations are
entered through the browser's device-local Ledger notebook and never mutate the
official dataset or application source.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence


def die(message: str) -> None:
    raise SystemExit(f"tsra_update: {message}")


def read_text(path: Path) -> str:
    if not path.exists():
        die(f"missing file: {path}")
    return path.read_text(encoding="utf-8")


def extract_service_worker_version(service_worker: str) -> str:
    match = re.search(r"const TSRA_CACHE_VERSION = '([^']+)';", service_worker)
    if not match:
        die("service worker cache version marker not found")
    return match.group(1)


def verify_report(report: str, service_worker: str) -> list[str]:
    errors: list[str] = []
    required_report_markers = [
        "id='tab-sequence'",
        "id='tab-releases'",
        "id='tab-method'",
        "id='tab-archive'",
        "id='sequence-root'",
        "id='release-branch-list'",
        "id='significant-release-body'",
        "id='method-threshold-body'",
        "id='method-original-body'",
        "id='official-ledger-body'",
        "id='official-ledger-status'",
        "id='ledger-magnitude-filter'",
        "id='ledger-branch-filter'",
        "id='observation-log-body'",
        "data-tab='archive'",
        "legacy-surface-boundary",
        "Archived language and graphics may contain obsolete assumptions",
        "openPrivateObservationRecorder()",
        "tsraObservationLedger.v1",
        "href='/data/sequence-v0.3/events.csv'",
        "href='/assets/tsra-sequence.css'",
        "src='/assets/tsra-sequence.js'",
        "source-certainty-register",
        "--kuro-field-ground: #0d0c0a",
        "--old-brass: #b89455",
        "--moss: #7f9878",
        "rel='icon' type='image/png' sizes='64x64' href='/duality-icon-64.png'",
        "rel='apple-touch-icon' href='/duality-icon-192.png'",
        "class='brand-mark'",
        "brand-mark-quiet",
        "brand-title",
        "data-evidence-type",
        "evidence-mini",
        "tsraFieldMemory.v1",
        "TSRA_APP_VERSION",
        "TSRA_VERSION_URL",
        "checkForRemoteAppVersion",
        "refreshInstalledApp",
        "refresh-page-button",
        "app-update-notice",
        "pageshow",
        "TSRA_UPDATE_CHECK_INTERVAL",
        "TSRA_AUTO_FIELD_MEMORY_INTERVAL",
        "autoCacheFieldMemory",
        "field-memory-auto-save-requested",
        "registration.update()",
        "controllerchange",
        "not a certified warning system",
    ]
    for marker in required_report_markers:
        if marker not in report:
            errors.append(f"missing report marker: {marker}")

    forbidden_report_markers = [
        "id='tab-now'",
        "id='tab-rhythm'",
        "id='tab-calibration'",
        "id='tab-forecast'",
        "id='pending-table'",
        "data-tab='chart'",
        "data-tab='field-report'",
        "data-tab='learning'",
        "data-tab='origin'",
        "function updateCountdowns()",
        "setInterval(updateCountdowns",
        "openOutcomeRecorder(this)",
        "Active Observation Window",
        "Next Observation Window",
    ]
    for marker in forbidden_report_markers:
        if marker in report:
            errors.append(f"retired active-surface marker found: {marker}")

    navigation_tabs = re.findall(
        r"<button class='tab-btn(?: active)?' data-tab='([^']+)'",
        report,
    )
    expected_navigation = ["sequence", "releases", "events", "method", "archive"]
    if navigation_tabs != expected_navigation:
        errors.append(f"primary navigation mismatch: {navigation_tabs!r}")
    note_classes = re.findall(r"class='([^']*)' role='note'", report)
    legacy_boundaries = [
        classes for classes in note_classes if "legacy-surface-boundary" in classes.split()
    ]
    if len(legacy_boundaries) != 4:
        errors.append("expected four historical surface boundaries")

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
        "'/assets/tsra-sequence.css'",
        "'/assets/tsra-sequence.js'",
        "'/data/sequence-v0.3/summary.json'",
        "TSRA_VERSION_REQUEST",
        "TSRA_VERSION_RESPONSE",
        "'/duality-logo.png'",
        "'/duality-icon-512.png'",
    ]
    for marker in required_sw_markers:
        if marker not in service_worker:
            errors.append(f"missing service worker marker: {marker}")
    return errors


def extract_inline_script(report: str, output: Path) -> None:
    blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", report, re.S | re.I)
    if not blocks:
        die("could not extract inline script")
    output.write_text("\n".join(blocks), encoding="utf-8")


def run_command(command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        die(f"command failed: {' '.join(command)}")


def run_verification(
    report_path: Path,
    service_worker_path: Path,
    version_path: Path,
    repo_root: Path,
) -> None:
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
        run_command(
            ["git", "diff", "--check", "--", str(report_path), str(service_worker_path), str(version_path)],
            repo_root,
        )
    else:
        print("verify: skipped git diff --check outside a git worktree")
    print("verify: ok")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the TSRA application shell. Legacy watch mutation is retired."
    )
    parser.add_argument("--report", type=Path, default=Path("seismic_report.html"))
    parser.add_argument("--service-worker", type=Path, default=Path("service-worker.js"))
    parser.add_argument("--version-file", type=Path, default=Path("tsra-version.json"))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify", help="Verify HTML, PWA, version, and retired-surface boundaries.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "verify":
        return 2
    repo_root = args.repo_root.resolve()
    report_path = args.report if args.report.is_absolute() else repo_root / args.report
    service_worker_path = (
        args.service_worker if args.service_worker.is_absolute() else repo_root / args.service_worker
    )
    version_path = args.version_file if args.version_file.is_absolute() else repo_root / args.version_file
    run_verification(report_path, service_worker_path, version_path, repo_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
