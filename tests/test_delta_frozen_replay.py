import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.delta_frozen_replay import _read_source


class DeltaFrozenReplaySafetyTests(unittest.TestCase):
    def _snapshot(self, path: Path, *, status: str = "NOT_APPROVED") -> None:
        files = {
            "inputs/delta_ohlc_daily.csv": (
                b"date,symbol,open,high,low,close,volume,source\n"
                b"2026-07-31,BTC,1,1,1,1,1,test\n"
            ),
            "inputs/delta_funding_events.csv": (
                b"date,symbol,funding_rate\n2026-07-31,BTC,0\n"
            ),
            "inputs/data_quality_by_asset.csv": b"symbol,ohlc_rows\nBTC,1\n",
            "inputs/download_failures.csv": b"symbol,layer,error\n",
        }
        manifest = {
            "technical_status": "PASS",
            "operational_status": status,
            "real_orders": 0,
            "capital_used": 0,
            "files_sha256": {
                name: hashlib.sha256(data).hexdigest()
                for name, data in files.items()
            },
        }
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
            archive.writestr(
                "delta_input_snapshot_manifest.json",
                json.dumps(manifest),
            )
            archive.writestr(
                "source_delta_run_manifest.json",
                json.dumps(manifest),
            )

    def test_safe_snapshot_is_admitted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "safe.zip"
            self._snapshot(package)
            loaded = _read_source(package, None)
            self.assertTrue(loaded["prior_input_manifest_verified"])

    def test_operational_snapshot_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "unsafe.zip"
            self._snapshot(package, status="APPROVED")
            with self.assertRaisesRegex(RuntimeError, "operational status"):
                _read_source(package, None)

    def test_missing_raw_inputs_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "output.zip"
            manifest = {
                "technical_status": "PASS",
                "operational_status": "NOT_APPROVED",
                "real_orders": 0,
                "capital_used": 0,
            }
            with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(
                    "outputs/delta_v11_run_manifest.json",
                    json.dumps(manifest),
                )
                archive.writestr(
                    "outputs/data_quality_by_asset.csv",
                    "symbol\n",
                )
                archive.writestr(
                    "outputs/download_failures.csv",
                    "symbol,layer,error\n",
                )
            with self.assertRaisesRegex(RuntimeError, "source-data-dir"):
                _read_source(package, None)


if __name__ == "__main__":
    unittest.main()
