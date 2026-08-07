import gzip
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from tools.gate_btc_v2a_data_ledger import append


class V2ADataLedgerTests(unittest.TestCase):
    def fixture(self, root: Path, day="2026-08-06"):
        manifest = root / "manifest.json"
        universe = root / "universe.csv"
        quality = root / "quality.csv"
        failures = root / "failures.csv"
        manifest.write_text(json.dumps({
            "run_utc": "2026-08-07T01:02:03+00:00",
            "version": "QOS_V2A_INTEGRITY_0.4",
            "technical_status": "PASS",
            "evidence_status": "RESEARCH_ONLY_NOT_PROMOTED",
            "operational_status": "NOT_APPROVED",
            "real_orders": 0,
            "capital_used": 0,
            "data_as_of": day,
            "attempted_symbols": 3,
            "loaded_symbols": 1,
            "failed_symbols": 2,
            "coverage_ratio": 1 / 3,
        }), encoding="utf-8")
        universe.write_text(
            "id,symbol,name,market_cap_rank,standard_ticker,is_stable,is_blocked\n"
            "bitcoin,BTC,Bitcoin,1,True,False,False\n",
            encoding="utf-8",
        )
        quality.write_text(
            "data_as_of,attempted_symbols,loaded_symbols,failed_symbols,coverage_ratio,data_quality_status,survivorship_bias_present\n"
            f"{day},3,1,2,{1 / 3},PASS,True\n",
            encoding="utf-8",
        )
        failures.write_text(
            "symbol,reason\n"
            "AAA,okx: RuntimeError: OKX returned no candles\n"
            "BBB,okx: only 52 rows\n",
            encoding="utf-8",
        )
        return manifest, universe, quality, failures

    def args(self, root, manifest, universe, quality, failures, day="2026-08-06", run_id="123"):
        return Namespace(
            manifest=manifest,
            universe_csv=universe,
            quality_csv=quality,
            failures_csv=failures,
            snapshot_id=f"{day}-run-{run_id}",
            source_run_id=run_id,
            ledger_dir=root / "ledger",
        )

    def test_append_archives_exact_sources_and_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, universe, quality, failures = self.fixture(root)
            args = self.args(root, manifest, universe, quality, failures)
            self.assertEqual(append(args), 0)
            record = json.loads((root / "ledger/snapshots/2026-08-06-run-123.json").read_text(encoding="utf-8"))
            self.assertEqual(record["short_history_failure_count"], 1)
            self.assertEqual(record["no_candle_failure_count"], 1)
            self.assertFalse(record["feeds_frozen_engine"])
            for key, source in (
                ("universe_archive", universe),
                ("quality_archive", quality),
                ("failures_archive", failures),
            ):
                archive = root / "ledger" / record[key]["archive_path"]
                self.assertEqual(gzip.decompress(archive.read_bytes()), source.read_bytes())

    def test_identical_rerun_is_idempotent_and_changed_source_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, universe, quality, failures = self.fixture(root)
            args = self.args(root, manifest, universe, quality, failures)
            self.assertEqual(append(args), 0)
            frozen = (root / "ledger/STATUS.json").read_bytes()
            self.assertEqual(append(args), 0)
            self.assertEqual((root / "ledger/STATUS.json").read_bytes(), frozen)
            universe.write_text(
                universe.read_text(encoding="utf-8") + "ethereum,ETH,Ethereum,2,True,False,False\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "immutable V2A point-in-time source bytes changed"):
                append(args)

    def test_inconsistent_quality_counts_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, universe, quality, failures = self.fixture(root)
            failures.write_text("symbol,reason\nAAA,okx: RuntimeError: OKX returned no candles\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "failure rows differ"):
                append(self.args(root, manifest, universe, quality, failures))

    def test_retrospective_backfill_is_prohibited(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, universe, quality, failures = self.fixture(root, day="2026-08-06")
            self.assertEqual(
                append(self.args(root, manifest, universe, quality, failures, day="2026-08-06", run_id="9")),
                0,
            )
            manifest, universe, quality, failures = self.fixture(root, day="2026-08-05")
            with self.assertRaisesRegex(RuntimeError, "retrospective backfill is prohibited"):
                append(self.args(root, manifest, universe, quality, failures, day="2026-08-05", run_id="10"))


if __name__ == "__main__":
    unittest.main()
