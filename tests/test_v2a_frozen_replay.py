import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.v2a_frozen_replay import _load_source


class V2AFrozenReplaySafetyTests(unittest.TestCase):
    def _source(
        self,
        path: Path,
        *,
        operational_status: str = "NOT_APPROVED",
        orders: int = 0,
    ) -> None:
        manifest = {
            "technical_status": "PASS",
            "operational_status": operational_status,
            "real_orders": orders,
            "capital_used": 0,
        }
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "data/processed/qos_v2a_master_daily.csv",
                "date,symbol,close_usd,volume_usd,source\n2026-07-31,BTC,1,1,test\n",
            )
            archive.writestr(
                "data/raw/coingecko_current_universe_v04.csv",
                "symbol\nBTC\n",
            )
            archive.writestr(
                "outputs/download_failures_v2a.csv",
                "symbol,error\n",
            )
            archive.writestr(
                "outputs/v2a_run_manifest.json",
                json.dumps(manifest),
            )

    def test_safe_source_is_admitted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "safe.zip"
            self._source(package)
            loaded = _load_source(package)
            self.assertEqual(loaded["run_manifest"]["operational_status"], "NOT_APPROVED")
            self.assertEqual(len(loaded["member_hashes"]), 3)

    def test_operational_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "unsafe.zip"
            self._source(package, operational_status="APPROVED", orders=1)
            with self.assertRaisesRegex(RuntimeError, "operational status"):
                _load_source(package)

    def test_corrupt_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "corrupt.zip"
            package.write_bytes(b"not-a-zip")
            with self.assertRaises(zipfile.BadZipFile):
                _load_source(package)


if __name__ == "__main__":
    unittest.main()
