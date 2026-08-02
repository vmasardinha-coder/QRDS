import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.compare_cross_platform_outputs import compare


SAFE_RUN = {
    "technical_status": "PASS",
    "operational_status": "NOT_APPROVED",
    "real_orders": 0,
    "capital_used": 0,
    "data_as_of": "2026-07-31",
    "data_cutoff": "2026-07-31",
}


class CrossPlatformSemanticParityTests(unittest.TestCase):
    def _write_zip(self, path: Path, members: dict[str, str | bytes]) -> None:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, payload in members.items():
                archive.writestr(name, payload)

    def _v2a_package(
        self,
        path: Path,
        *,
        output_value: str = "1.0",
        universe_value: str = "1",
        crlf: bool = False,
        reverse_rows: bool = False,
    ) -> None:
        from tools import compare_cross_platform_outputs as module

        newline = "\r\n" if crlf else "\n"
        rows = ["1,a", "2,b"]
        if reverse_rows:
            rows.reverse()
        generic = newline.join(["value,label", *rows]) + newline
        numeric_generic = newline.join(
            ["value,label", f"{output_value},a", "2.0,b"]
        ) + newline
        master = newline.join(
            ["date,symbol,close_usd", "2026-07-31,BTC,1.0"]
        ) + newline
        universe = newline.join(
            ["symbol,rank", f"BTC,{universe_value}"]
        ) + newline
        failures = "symbol,error" + newline
        members: dict[str, str] = {
            "outputs/v2a_run_manifest.json": json.dumps(SAFE_RUN),
            "outputs/v2a_input_manifest.json": json.dumps({
                "input_snapshot_id": "snapshot-v2a",
                "data_cutoff": "2026-07-31",
                "data_as_of": "2026-07-31",
                "attempted_symbols": 1,
                "loaded_symbols": 1,
            }),
            "data/processed/qos_v2a_master_daily.csv": master,
            "data/raw/coingecko_current_universe_v04.csv": universe,
            "outputs/download_failures_v2a.csv": failures,
        }
        for suffix in module.V2A_OUTPUT_MEMBERS:
            if suffix in members:
                continue
            members[suffix] = (
                numeric_generic
                if suffix == "outputs/qos_v2a_summary.csv"
                else generic
            )
        self._write_zip(path, members)

    def _delta_package(
        self,
        path: Path,
        *,
        output_value: str = "1.0",
        crlf: bool = False,
    ) -> None:
        from tools import compare_cross_platform_outputs as module

        newline = "\r\n" if crlf else "\n"
        generic = newline.join(
            ["value,label", f"{output_value},a", "2.0,b"]
        ) + newline
        members: dict[str, str] = {
            "outputs/delta_v11_run_manifest.json": json.dumps(SAFE_RUN),
            "outputs/delta_input_manifest.json": json.dumps({
                "input_snapshot_id": "snapshot-delta",
                "data_cutoff": "2026-07-31",
                "data_as_of": "2026-07-31",
                "loaded_assets": 1,
            }),
        }
        for suffix in module.DELTA_OUTPUT_MEMBERS:
            if suffix.endswith(".json"):
                members[suffix] = json.dumps({
                    "path": "folder/file",
                    "value": float(output_value),
                })
            else:
                members[suffix] = generic
        self._write_zip(path, members)

    def _delta_snapshot(
        self,
        path: Path,
        *,
        ohlc_close: str = "1.0",
        crlf: bool = False,
    ) -> None:
        newline = "\r\n" if crlf else "\n"
        members = {
            "delta_input_snapshot_manifest.json": json.dumps({
                **SAFE_RUN,
                "input_snapshot_id": "platform-specific-bytes-allowed",
                "loaded_assets": 1,
            }),
            "inputs/delta_ohlc_daily.csv": newline.join([
                "date,symbol,open,high,low,close,volume,source",
                f"2026-07-31,BTC,1.0,1.0,1.0,{ohlc_close},1.0,public",
            ]) + newline,
            "inputs/delta_funding_events.csv": newline.join([
                "date,symbol,funding_rate",
                "2026-07-31,BTC,0.001",
            ]) + newline,
            "inputs/data_quality_by_asset.csv": newline.join([
                "symbol,rows",
                "BTC,1",
            ]) + newline,
            "inputs/download_failures.csv": "symbol,error" + newline,
        }
        self._write_zip(path, members)

    def test_v2a_tiny_float_and_crlf_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.zip"
            replay = root / "replay.zip"
            self._v2a_package(reference, output_value="1.0")
            self._v2a_package(
                replay,
                output_value="1.000000000000001",
                crlf=True,
            )
            result = compare("v2a", reference, replay)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(
                result["output_members_matched"],
                result["output_members_checked"],
            )
            self.assertTrue(result["input_semantic_match"])

    def test_v2a_material_numeric_difference_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.zip"
            replay = root / "replay.zip"
            self._v2a_package(reference, output_value="1.0")
            self._v2a_package(replay, output_value="1.000001")
            result = compare("v2a", reference, replay)
            self.assertEqual(result["status"], "ERROR")
            self.assertFalse(result["output_semantic_match"])

    def test_v2a_row_order_difference_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.zip"
            replay = root / "replay.zip"
            self._v2a_package(reference)
            self._v2a_package(replay, reverse_rows=True)
            result = compare("v2a", reference, replay)
            self.assertEqual(result["status"], "ERROR")
            self.assertFalse(result["output_semantic_match"])

    def test_delta_cross_platform_serialization_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.zip"
            replay = root / "replay.zip"
            reference_snapshot = root / "reference-input.zip"
            replay_snapshot = root / "replay-input.zip"
            self._delta_package(reference, output_value="1.0")
            self._delta_package(
                replay,
                output_value="1.0000000000000002",
                crlf=True,
            )
            self._delta_snapshot(reference_snapshot)
            self._delta_snapshot(replay_snapshot, crlf=True)
            result = compare(
                "delta",
                reference,
                replay,
                reference_snapshot,
                replay_snapshot,
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["output_members_matched"], 15)
            self.assertEqual(result["input_members_matched"], 4)

    def test_delta_input_numeric_difference_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.zip"
            replay = root / "replay.zip"
            reference_snapshot = root / "reference-input.zip"
            replay_snapshot = root / "replay-input.zip"
            self._delta_package(reference)
            self._delta_package(replay)
            self._delta_snapshot(reference_snapshot, ohlc_close="1.0")
            self._delta_snapshot(
                replay_snapshot,
                ohlc_close="1.0000000000000002",
            )
            result = compare(
                "delta",
                reference,
                replay,
                reference_snapshot,
                replay_snapshot,
            )
            self.assertEqual(result["status"], "ERROR")
            self.assertFalse(result["input_semantic_match"])


if __name__ == "__main__":
    unittest.main()
