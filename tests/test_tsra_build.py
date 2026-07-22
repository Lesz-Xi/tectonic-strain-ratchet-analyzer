from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET = REPO_ROOT / "data" / "sequence-v0.3"
MODULE_PATH = REPO_ROOT / "tools" / "tsra_build.py"


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("tsra_build", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load tools/tsra_build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TSRA_BUILD = load_module()


class TsraBuildVerificationTests(unittest.TestCase):
    def copy_dataset(self, destination: Path) -> Path:
        copied = destination / "sequence-v0.3"
        shutil.copytree(DATASET, copied)
        return copied

    def test_reviewed_dataset_passes(self) -> None:
        self.assertEqual(TSRA_BUILD.verify_dataset(DATASET), [])

    def test_summary_total_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            dataset = self.copy_dataset(Path(temporary))
            summary_path = dataset / "summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["counts"]["officialPhivolcsRowsDeduplicated"] -= 1
            summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

            errors = TSRA_BUILD.verify_dataset(dataset)

            self.assertTrue(
                any("summary event total mismatch" in error for error in errors),
                errors,
            )
            self.assertIn("SHA-256 mismatch for summary.json", errors)

    def test_uncaptured_gap_must_remain_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            dataset = self.copy_dataset(Path(temporary))
            summary_path = dataset / "summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            gap_day = next(day for day in summary["dailyActivity"] if day["datePht"] == "2026-06-09")
            gap_day["coverage"] = "full_public_day"
            summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

            errors = TSRA_BUILD.verify_dataset(dataset)

            self.assertIn(
                "uncaptured gap day must be zero and marked not_captured: 2026-06-09",
                errors,
            )

    def test_original_method_provenance_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            dataset = self.copy_dataset(Path(temporary))
            summary_path = dataset / "summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["historicalClockAudit"]["originalInvestigation"]["insideToleranceCount"] = 9
            summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

            errors = TSRA_BUILD.verify_dataset(dataset)

            self.assertIn("original investigation inside-tolerance count changed", errors)
            self.assertIn("SHA-256 mismatch for summary.json", errors)

    def test_duplicate_event_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            dataset = self.copy_dataset(Path(temporary))
            events_path = dataset / "events.csv"
            with events_path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                fieldnames = reader.fieldnames
                rows = list(reader)
            self.assertIsNotNone(fieldnames)
            rows[1]["event_key"] = rows[0]["event_key"]
            with events_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            errors = TSRA_BUILD.verify_dataset(dataset)

            self.assertIn("event_key values are not unique", errors)
            self.assertIn("SHA-256 mismatch for events.csv", errors)

    def test_automatic_sequence_association_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            dataset = self.copy_dataset(Path(temporary))
            events_path = dataset / "events.csv"
            with events_path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                fieldnames = reader.fieldnames
                rows = list(reader)
            self.assertIsNotNone(fieldnames)
            rows[0]["sequence_association_status"] = "officially_associated"
            with events_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            errors = TSRA_BUILD.verify_dataset(dataset)

            self.assertTrue(
                any("missing AOI-only association boundary" in error for error in errors),
                errors,
            )


if __name__ == "__main__":
    unittest.main()
