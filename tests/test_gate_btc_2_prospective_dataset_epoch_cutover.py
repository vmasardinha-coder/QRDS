import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_2_prospective_dataset_epoch_cutover import (
    D0_SCHEMA,
    EPOCH_ID,
    PREREG_COMMIT,
    REGISTRY_SCHEMA,
    assess,
    write_d0_if_eligible,
)


class ProspectiveDatasetEpochCutoverTests(unittest.TestCase):
    def _write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _status(self, snapshot_id: str, attempted: int, loaded: int, failed: int, coverage: float, survivorship: bool) -> dict:
        return {
            "latest_snapshot_id": snapshot_id,
            "latest_attempted_symbols": attempted,
            "latest_loaded_symbols": loaded,
            "latest_failed_symbols": failed,
            "latest_coverage_ratio": coverage,
            "survivorship_bias_present": survivorship,
            "future_point_in_time_only": True,
            "retrospective_backfill_allowed": False,
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "promotion_allowed": False,
            "orders_generated": 0,
            "real_capital_used": 0,
            "feeds_frozen_engine": False,
        }

    def _snapshot(self, snapshot_id: str, run_utc: str, attempted: int, loaded: int, failed: int, coverage: float, survivorship: bool) -> dict:
        return {
            "snapshot_id": snapshot_id,
            "source_run_utc": run_utc,
            "attempted_symbols": attempted,
            "loaded_symbols": loaded,
            "failed_symbols": failed,
            "coverage_ratio": coverage,
            "survivorship_bias_present": survivorship,
            "retrospective_reconstruction": False,
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "promotion_allowed": False,
            "orders_generated": 0,
            "real_capital_used": 0,
            "feeds_frozen_engine": False,
            "record_sha256": "r" * 64,
            "source_hashes": {
                "manifest_sha256": "m" * 64,
                "universe_sha256": "u" * 64,
                "quality_sha256": "q" * 64,
            },
        }

    def _registry(self, symbols: list[str]) -> dict:
        return {
            "schema": REGISTRY_SCHEMA,
            "epoch_id": EPOCH_ID,
            "entries": [
                {
                    "symbol": symbol,
                    "qualification": "QUALIFIED_EXACT_SOURCE",
                    "source_identity": f"official:{symbol}",
                    "source_symbol": f"{symbol}-USD",
                    "provenance_sha256": (symbol.lower()[:1] or "a") * 64,
                }
                for symbol in symbols
            ],
        }

    def test_pre_prereg_incomplete_snapshot_cannot_start_d0(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sid = "pre"
            status = root / "STATUS.json"
            snaps = root / "snapshots"
            registry = root / "registry.json"
            self._write(status, self._status(sid, 150, 94, 56, 94 / 150, True))
            self._write(snaps / f"{sid}.json", self._snapshot(sid, "2026-09-03T04:23:49Z", 150, 94, 56, 94 / 150, True))
            result = assess(status, snaps, registry)
            self.assertFalse(result["cutover_eligible"])
            self.assertIn("SNAPSHOT_NOT_STRICTLY_POST_PREREGISTRATION", result["blockers"])
            self.assertIn("V2A_SYMBOL_LOAD_GAP", result["blockers"])
            self.assertIn("V2A_SURVIVORSHIP_BIAS_PRESENT", result["blockers"])
            self.assertIn("FULL_QUALIFIED_EXACT_SOURCE_REGISTRY_NOT_MATERIALIZED", result["blockers"])
            self.assertEqual(result["historical_credit"], 0)
            self.assertEqual(result["prospective_credit_before_d0"], 0)

    def test_complete_post_prereg_snapshot_with_full_qualified_registry_is_eligible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sid = "post"
            status = root / "STATUS.json"
            snaps = root / "snapshots"
            registry = root / "registry.json"
            symbols = ["A", "B"]
            self._write(status, self._status(sid, 2, 2, 0, 1.0, False))
            self._write(snaps / f"{sid}.json", self._snapshot(sid, "2026-09-03T09:00:00Z", 2, 2, 0, 1.0, False))
            self._write(registry, self._registry(symbols))
            result = assess(status, snaps, registry)
            self.assertTrue(result["cutover_eligible"], result["blockers"])
            self.assertEqual(result["state"], "CUTOVER_ELIGIBLE")

            d0 = root / "D0.json"
            self.assertTrue(write_d0_if_eligible(result, d0))
            frozen = json.loads(d0.read_text(encoding="utf-8"))
            self.assertEqual(frozen["schema"], D0_SCHEMA)
            self.assertEqual(frozen["epoch_id"], EPOCH_ID)
            self.assertEqual(frozen["preregistration_commit_sha"], PREREG_COMMIT)
            self.assertEqual(frozen["historical_credit"], 0)
            self.assertFalse(frozen["backfill_performed"])
            self.assertFalse(write_d0_if_eligible(result, d0))

    def test_incomplete_registry_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sid = "post"
            status = root / "STATUS.json"
            snaps = root / "snapshots"
            registry = root / "registry.json"
            self._write(status, self._status(sid, 2, 2, 0, 1.0, False))
            self._write(snaps / f"{sid}.json", self._snapshot(sid, "2026-09-03T09:00:00Z", 2, 2, 0, 1.0, False))
            self._write(registry, self._registry(["A"]))
            result = assess(status, snaps, registry)
            self.assertFalse(result["cutover_eligible"])
            self.assertIn("QUALIFIED_SOURCE_REGISTRY_NOT_FULL_UNIVERSE", result["blockers"])


if __name__ == "__main__":
    unittest.main()
