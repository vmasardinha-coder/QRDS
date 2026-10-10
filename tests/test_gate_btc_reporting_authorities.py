import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from tools.gate_btc_reporting_authority import active_status_path
from tools.gate_btc_reporting_current_state import reconcile
from tools.gate_btc_reporting_inventory import complete_inventory
from tools.gate_btc_reporting_operational_overlay import enrich
from tools.gate_btc_factory_status_export import export_tracks
from tools.gate_btc_shadow_executive import build


class ReportingAuthoritiesTest(unittest.TestCase):
    def write(self, root, path, obj):
        p = root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj))

    def fixture(self, root):
        self.write(root, "GATE_BTC_LATEST_ELIGIBLE_RUN.json", {"data_cutoff": "2026-10-09"})
        self.write(root, "ledgers/bull_replay_live_shadow/STATUS.json",
                   {"status": "LEGACY", "observed_days": 26, "data_as_of": "2026-10-08"})
        self.write(root, "ledgers/bull_replay_live_shadow/ACTIVE_EPOCH.json",
                   {"relative_path": "epochs/independent_20261009"})
        self.write(root, "ledgers/bull_replay_live_shadow/epochs/independent_20261009/STATUS.json",
                   {"status": "ARMED_WAITING_FIRST_RETURN", "data_as_of": "2026-10-09"})
        self.write(root, "ledgers/bull_replay_live_shadow/DELIVERY_STATUS.json",
                   {"schema": "gate_btc.bull_replay_live_shadow.delivery.v1",
                    "status": "WAITING_FIRST_RETURN_CLOSE", "observed_days": 0,
                    "active_epoch": "epochs/independent_20261009"})
        self.write(root, "ledgers/d100/STATUS.json",
                   {"schema": "qrds.d100.forward_collection.v2", "status": "PHYSICAL",
                    "physical_snapshot_count": 14, "scientific_observations_credited": 0,
                    "latest_physical_capture_at_utc": "2026-10-10T00:00:00Z"})
        self.write(root, "ledgers/d100/economic/STATUS.json",
                   {"schema": "qrds.d100.economics.v1", "status": "ACTIVE_SHADOW_N80",
                    "scientific_observations_credited": 11, "scientific_target": 80,
                    "latest_signal_available_at_utc": "2026-10-10T00:00:00Z"})

    def test_full_chain_uses_epoch_and_separates_d100_clocks_without_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            root = repo / "runtime"
            self.fixture(root)
            before = {p: p.read_bytes() for p in root.rglob("*.json")}
            state = reconcile(root, date(2026, 10, 10))
            self.assertEqual(state["components"]["bull_replay_live_shadow"]["observed_days"], 0)
            self.assertIn("epochs/independent_20261009", state["components"]["bull_replay_live_shadow"]["source"])
            state = enrich(root, state, datetime(2026, 10, 10, tzinfo=timezone.utc))
            state = complete_inventory(root, state)
            self.assertEqual(state["ledger_inventory"]["bull_replay_live_shadow"]["status"], "ARMED_WAITING_FIRST_RETURN")
            report = build(state, "2026-10-10")
            d100 = report["blocks"][11]["content"]["semantic_projection"]["d100"]["component"]
            self.assertEqual(d100["scientific_observations_credited"], 11)
            self.assertEqual(d100["physical_snapshot_count"], 14)
            tracks = export_tracks(repo)
            self.assertEqual(tracks["d100"]["data"]["scientific_observations_credited"], 11)
            self.assertEqual(tracks["d100_physical"]["data"]["physical_snapshot_count"], 14)
            self.assertEqual(tracks["bull_replay"]["data"]["status"], "ARMED_WAITING_FIRST_RETURN")
            self.assertEqual(before, {p: p.read_bytes() for p in root.rglob("*.json")})

    def test_selected_missing_epoch_never_falls_back_to_legacy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.fixture(root)
            p = active_status_path(root / "ledgers/bull_replay_live_shadow")
            p.unlink()
            state = reconcile(root, date(2026, 10, 10))
            self.assertNotEqual(state["components"]["bull_replay_live_shadow"].get("observed_days"), 26)
            state = enrich(root, state, datetime(2026, 10, 10, tzinfo=timezone.utc))
            self.assertFalse(state["delivery_complete"])
            self.assertIn("bull_replay_live_shadow", state["warnings"]["blocked_dependency_components"])
            inv = complete_inventory(root, state)["ledger_inventory"]["bull_replay_live_shadow"]
            self.assertEqual(inv["source"], "ledgers/bull_replay_live_shadow/epochs/independent_20261009/STATUS.json")
            self.assertEqual(inv["status"], "NO_CANONICAL_STATUS_FIELD")

    def test_pointer_cannot_escape_epoch_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for relative in ("../other", "/tmp/other", "epochs/../other", "epochs/"):
                self.write(root, "ACTIVE_EPOCH.json", {"relative_path": relative})
                with self.assertRaises(ValueError):
                    active_status_path(root)

    def test_stale_d50_reconciliation_keeps_raw_counter_out_of_current_display(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "GATE_BTC_LATEST_ELIGIBLE_RUN.json", {"data_cutoff": "2026-10-09"})
            self.write(root, "GATE_BTC_MEASUREMENT_STATUS.json", {
                "data_as_of": "2026-10-09", "reconciliation_note": "old attached receipt",
                "d50_prospective_immutable_ledger": {"current": 21, "target": 30,
                    "latest_prospective_date": "2026-08-22", "user_action_required": False},
                "d50_data_qualification": {"hash_chain_valid": True}})
            state = reconcile(root, date(2026, 10, 10))
            self.assertIsNone(state["components"]["d50"]["display_current"])
            self.assertIn("STALE", state["components"]["d50"]["authority"])


if __name__ == "__main__":
    unittest.main()
