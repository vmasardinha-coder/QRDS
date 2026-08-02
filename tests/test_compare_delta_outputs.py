import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.compare_delta_outputs import DETERMINISTIC_MEMBERS, compare


class DeltaFrozenInputParityTests(unittest.TestCase):
    def _package(
        self,
        path: Path,
        *,
        snapshot: str = "same",
        mismatch: bool = False,
    ) -> None:
        run_manifest = {
            "technical_status": "PASS",
            "operational_status": "NOT_APPROVED",
            "real_orders": 0,
            "capital_used": 0,
            "data_as_of": "2026-07-31",
        }
        input_manifest = {"input_snapshot_id": snapshot}
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "outputs/delta_v11_run_manifest.json",
                json.dumps(run_manifest),
            )
            archive.writestr(
                "outputs/delta_input_manifest.json",
                json.dumps(input_manifest),
            )
            for index, member in enumerate(DETERMINISTIC_MEMBERS):
                value = (
                    "different\n"
                    if mismatch and member.endswith("delta_summary.csv")
                    else f"member-{index}\n"
                )
                archive.writestr(member, value)

    def test_identical_outputs_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.zip"
            replay = root / "replay.zip"
            self._package(reference)
            self._package(replay)
            result = compare(reference, replay)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(
                result["deterministic_members_matched"],
                len(DETERMINISTIC_MEMBERS),
            )

    def test_output_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.zip"
            replay = root / "replay.zip"
            self._package(reference)
            self._package(replay, mismatch=True)
            result = compare(reference, replay)
            self.assertEqual(result["status"], "ERROR")
            self.assertIn(
                "outputs/delta_summary.csv",
                result["mismatched_members"],
            )

    def test_snapshot_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.zip"
            replay = root / "replay.zip"
            self._package(reference, snapshot="a")
            self._package(replay, snapshot="b")
            result = compare(reference, replay)
            self.assertEqual(result["status"], "ERROR")
            self.assertFalse(result["matched_input_snapshot"])


if __name__ == "__main__":
    unittest.main()
