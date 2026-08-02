import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.compare_v2a_outputs import DETERMINISTIC_MEMBERS, compare


class V2AFrozenInputParityTests(unittest.TestCase):
    def _package(
        self,
        path: Path,
        *,
        snapshot: str = "snapshot-a",
        mismatch: bool = False,
    ) -> None:
        run_manifest = {
            "technical_status": "PASS",
            "operational_status": "NOT_APPROVED",
            "real_orders": 0,
            "capital_used": 0,
            "mode": "frozen_public_input_no_network",
            "data_as_of": "2026-07-31",
        }
        input_manifest = {"input_snapshot_id": snapshot}
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("outputs/v2a_run_manifest.json", json.dumps(run_manifest))
            archive.writestr("outputs/v2a_input_manifest.json", json.dumps(input_manifest))
            for index, member in enumerate(DETERMINISTIC_MEMBERS):
                content = f"member-{index}\n"
                if mismatch and member == "outputs/qos_v2a_summary.csv":
                    content = "different\n"
                archive.writestr(member, content)

    def test_identical_frozen_input_and_outputs_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.zip"
            replay = root / "replay.zip"
            self._package(reference)
            self._package(replay)
            result = compare(reference, replay)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["equivalence_claim"])
            self.assertEqual(
                result["deterministic_members_matched"],
                len(DETERMINISTIC_MEMBERS),
            )

    def test_output_difference_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.zip"
            replay = root / "replay.zip"
            self._package(reference)
            self._package(replay, mismatch=True)
            result = compare(reference, replay)
            self.assertEqual(result["status"], "ERROR")
            self.assertFalse(result["equivalence_claim"])
            self.assertIn(
                "outputs/qos_v2a_summary.csv",
                result["mismatched_members"],
            )

    def test_input_snapshot_difference_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.zip"
            replay = root / "replay.zip"
            self._package(reference, snapshot="snapshot-a")
            self._package(replay, snapshot="snapshot-b")
            result = compare(reference, replay)
            self.assertEqual(result["status"], "ERROR")
            self.assertFalse(result["matched_input_snapshot"])


if __name__ == "__main__":
    unittest.main()
