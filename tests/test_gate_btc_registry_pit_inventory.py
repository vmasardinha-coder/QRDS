import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from tools.gate_btc_registry_pit_inventory import inventory


class RegistryInventoryTest(unittest.TestCase):
    def snapshot(self, root, identity, loaded=137):
        obj = {"snapshot_id": identity, "source_data_as_of": "2026-10-09",
               "schema": "gate_btc.v2a_point_in_time_data_snapshot.v1",
               "research_only": True, "shadow_only": True, "not_approved": True,
               "feeds_frozen_engine": False, "promotion_allowed": False,
               "orders_generated": 0, "real_capital_used": 0,
               "backfill_performed": False, "retrospective_reconstruction": False,
               "attempted_symbols": 137, "loaded_symbols": loaded, "failed_symbols": 137-loaded,
               "selected_sources": {str(i): {} for i in range(137)}}
        obj["record_sha256"] = hashlib.sha256((json.dumps(obj, sort_keys=True, separators=(",", ":"))+"\n").encode()).hexdigest()
        path = root / "snapshots" / (identity + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj))
        return path

    def test_multiple_runs_same_day_are_not_economic_days(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "STATUS.json").write_text('{"snapshot_count":1}')
            self.snapshot(root, "run1")
            self.snapshot(root, "run2", 135)
            before = {p:p.read_bytes() for p in root.rglob('*.json')}
            result = inventory(root)
            self.assertEqual(result["integrity_valid_unique_snapshot_count"], 2)
            self.assertEqual(result["distinct_source_date_count"], 1)
            self.assertEqual(result["complete_source_snapshot_count"], 1)
            self.assertEqual(result["incomplete_source_snapshot_count"], 1)
            self.assertEqual(result["artifact_status_snapshot_count_preserved"], 1)
            self.assertEqual(result["scientific_credit"], 0)
            self.assertEqual(before, {p:p.read_bytes() for p in root.rglob('*.json')})

    def test_changed_snapshot_is_not_counted_as_integrity_valid(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = self.snapshot(root, "run1")
            d = json.loads(p.read_text()); d["loaded_symbols"] = 1
            p.write_text(json.dumps(d))
            result = inventory(root)
            self.assertEqual(result["integrity_valid_unique_snapshot_count"], 0)
            self.assertEqual(result["status"], "INVENTORY_INTEGRITY_BLOCKED")

