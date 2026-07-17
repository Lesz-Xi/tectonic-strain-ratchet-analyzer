from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tsra_update", ROOT / "tools" / "tsra_update.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load tools/tsra_update.py")
TSRA_UPDATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TSRA_UPDATE)


class TsraShellVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = (ROOT / "seismic_report.html").read_text(encoding="utf-8")
        cls.service_worker = (ROOT / "service-worker.js").read_text(encoding="utf-8")

    def test_reviewed_shell_passes(self) -> None:
        self.assertEqual(TSRA_UPDATE.verify_report(self.report, self.service_worker), [])

    def test_direct_legacy_navigation_is_rejected(self) -> None:
        changed = self.report.replace(
            "data-tab='archive'",
            "data-tab='chart'",
            1,
        )

        errors = TSRA_UPDATE.verify_report(changed, self.service_worker)

        self.assertIn("missing report marker: data-tab='archive'", errors)
        self.assertIn("retired active-surface marker found: data-tab='chart'", errors)

    def test_archive_claim_boundary_is_required(self) -> None:
        changed = self.report.replace(
            "Archived language and graphics may contain obsolete assumptions",
            "Historical graphics are retained",
            1,
        )

        errors = TSRA_UPDATE.verify_report(changed, self.service_worker)

        self.assertIn(
            "missing report marker: Archived language and graphics may contain obsolete assumptions",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
