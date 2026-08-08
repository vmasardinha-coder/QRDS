import gzip
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from tools.gate_btc_universe_ledger import append


class UniverseLedgerTests(unittest.TestCase):
    def fixture(self, root: Path, day: str = "2026-08-07", rows: str | None = None):
        raw = root / "scanner_top500_raw.csv"
        manifest = root / "manifest.json"
        status = root / "status.json"
        raw.write_text(rows or "base,cg_rank,cg_name,cg_market_cap,cg_volume\nBTC,1,Bitcoin,1,2\nETH,2,Ethereum,3,4\n", encoding="utf-8")
        manifest.write_text(json.dumps({
            "run_utc": f"{day}T01:02:03+00:00",
            "version": "QOS_V2A1_GATEWAY_SCANNER_0.10",
            "technical_status": "PASS",
            "data_quality_status": "PASS_PARTIAL_REDUNDANCY_WARNING",
            "operational_status": "NOT_APPROVED",
            "retrospective_performance_status": "PROHIBITED_CURRENT_COMPOSITION",
            "universe_rows": 2,
            "data_as_of": day,
        }), encoding="utf-8")
        status.write_text(json.dumps({
            "snapshot_status": "SNAPSHOT_USABLE_WITH_DATA_WARNINGS",
            "evidence_status": "SNAPSHOT_ONLY_NO_WALK_FORWARD_BACKTEST",
            "operational_status": "NOT_APPROVED",
            "warning_failed_checks": ["bybit_loaded"],
        }), encoding="utf-8")
        return raw, manifest, status

    def args(self, root: Path, raw: Path, manifest: Path, status: Path, day="2026-08-07", run_id="123"):
        return Namespace(
            raw_csv=raw,
            manifest=manifest,
            snapshot_status=status,
            snapshot_id=f"{day}-run-{run_id}",
            source_run_id=run_id,
            ledger_dir=root / "ledger",
        )

    def test_append_preserves_exact_bytes_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw, manifest, status = self.fixture(root)
            args = self.args(root, raw, manifest, status)
            original = raw.read_bytes()
            self.assertEqual(append(args), 0)
            record = json.loads((root / "ledger/snapshots/2026-08-07-run-123.json").read_text(encoding="utf-8"))
            archive = root / "ledger" / record["archive_path"]
            self.assertEqual(gzip.decompress(archive.read_bytes()), original)
            self.assertFalse(record["feeds_frozen_engine"])
            self.assertFalse(record["retrospective_reconstruction"])
            self.assertEqual(record["sequence"], 1)
            before = (root / "ledger/STATUS.json").read_bytes()
            self.assertEqual(append(args), 0)
            self.assertEqual((root / "ledger/STATUS.json").read_bytes(), before)

    def test_same_source_run_changed_bytes_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw, manifest, status = self.fixture(root)
            args = self.args(root, raw, manifest, status)
            self.assertEqual(append(args), 0)
            frozen_record = (root / "ledger/snapshots/2026-08-07-run-123.json").read_bytes()
            raw.write_text("base,cg_rank,cg_name,cg_market_cap,cg_volume\nBTC,1,Bitcoin,9,9\nETH,2,Ethereum,3,4\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "immutable universe snapshot bytes changed"):
                append(args)
            self.assertEqual((root / "ledger/snapshots/2026-08-07-run-123.json").read_bytes(), frozen_record)

    def test_retrospective_backfill_is_prohibited(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw, manifest, status = self.fixture(root, day="2026-08-07")
            self.assertEqual(append(self.args(root, raw, manifest, status, day="2026-08-07", run_id="123")), 0)

            raw2, manifest2, status2 = self.fixture(root, day="2026-08-06")
            with self.assertRaisesRegex(RuntimeError, "retrospective backfill is prohibited"):
                append(self.args(root, raw2, manifest2, status2, day="2026-08-06", run_id="124"))

    def test_same_day_numeric_run_ids_keep_contiguous_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw, manifest, status = self.fixture(root)
            for run_id in ("9", "10", "11"):
                self.assertEqual(append(self.args(root, raw, manifest, status, run_id=run_id)), 0)
            records = []
            for path in (root / "ledger/snapshots").glob("*.json"):
                records.append(json.loads(path.read_text(encoding="utf-8")))
            self.assertEqual(sorted(record["sequence"] for record in records), [1, 2, 3])
            latest = json.loads((root / "ledger/STATUS.json").read_text(encoding="utf-8"))
            self.assertEqual(latest["snapshot_count"], 3)
            self.assertEqual(latest["latest_source_run_id"], "11")

    def test_operational_boundary_change_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw, manifest, status = self.fixture(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["operational_status"] = "APPROVED"
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "operational status changed"):
                append(self.args(root, raw, manifest, status))


if __name__ == "__main__":
    unittest.main()
