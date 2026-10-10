import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from tools.gate_btc_reporting_authority import active_status_path, system12_summary, closed_v12_status
from tools.gate_btc_reporting_current_state import reconcile
from tools.gate_btc_reporting_inventory import complete_inventory
from tools.gate_btc_reporting_operational_overlay import enrich
from tools.gate_btc_factory_status_export import export_tracks
from tools.gate_btc_shadow_executive import build


class ReportingAuthoritiesTest(unittest.TestCase):
    def test_h1_canonical_and_structural_counters_are_never_added(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            root = repo / "runtime"
            self.fixture(root)
            self.write(root, "ledgers/b3_h1/STATUS.json", {"status": "ACTIVE_STRUCTURAL_COLLECTION", "valid_observation_count": 8, "latest_valid_date": "2026-10-08"})
            self.write(root, "ledgers/b3_h1/CANONICAL_STATUS.json", {"status": "H1_13_OF_20_CANONICAL", "qualified": 13, "remaining": 7, "last_qualified_session": "2026-10-08", "economics_locked": True})
            before = {p: p.read_bytes() for p in root.rglob("*.json")}
            state = complete_inventory(root, enrich(root, reconcile(root, date(2026, 10, 10))))
            h1 = state["components"]["b3_h1"]
            self.assertEqual(h1["valid_observation_count"], 13)
            self.assertEqual(h1["structural_observation_count"], 8)
            self.assertEqual(h1["freshness"], "STALE")
            self.assertTrue(h1["economics_locked"])
            self.assertEqual(state["ledger_inventory"]["b3_h1"]["canonical_checkpoint_count"], 13)
            self.assertEqual(export_tracks(repo)["h1"]["data"]["qualified"], 13)
            self.assertEqual(before, {p: p.read_bytes() for p in root.rglob("*.json")})

    def test_v12_terminal_decision_does_not_reopen_or_rewrite_ledger(self):
        raw = {"status": "ACTIVE_PROSPECTIVE_SHADOW", "observed_days": 12}
        out = closed_v12_status(raw)
        self.assertEqual(raw["status"], "ACTIVE_PROSPECTIVE_SHADOW")
        self.assertEqual(out["status"], "CLOSED_NO_FURTHER_OBSERVATIONS_POSSIBLE")
        self.assertEqual(out["raw_status_preserved"], raw["status"])
        self.assertEqual(out["scientific_credit"], 0)
        with self.assertRaises(ValueError):
            closed_v12_status({**raw, "observed_days": 13})

    def test_system12_readiness_alone_never_claims_replication(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write(root, "READINESS.json", {"status": "STRUCTURAL_READY"})
            out = system12_summary(root)
            self.assertFalse(out["implementation_replication_pass"])
            self.assertFalse(out["system12_complete"])

    def test_system12_bound_parity_does_not_release_adjudication_gate(self):
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            contract = {"schema": "gate_btc.2_0.system12_implementation_replication_contract.v1", "bindings": {"dataset": "fixed"}, "required_scenario_count": 300}
            h = hashlib.sha256(json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            names = ("all_events_compared", "dataset_gate", "deterministic_independent_executor", "event_parity", "minimum_executions", "reference_semantic_digest", "scenario_count", "scenario_parity", "size_monotonicity")
            report = {"schema": "gate_btc.2_0.system12_implementation_replication.v1", "contract_sha256": h, "bindings": contract["bindings"], "status": "PASS_IMPLEMENTATION_PARITY_PENDING_INDEPENDENT_ADJUDICATION", "implementation_replication_pass": True, "independent_replication_executed": True, "event_mismatches": 0, "scenario_mismatches": [], "scenario_count": 300, "checks": dict.fromkeys(names, True), "system12_complete": False, "system13_dependency_released": False, "independent_adjudication_executed": False, "scientific_credit": 0, "orders": 0, "real_capital_brl": 0, "engine_feed": False}
            self.write(root, "IMPLEMENTATION_REPLICATION_CONTRACT.json", contract)
            self.write(root, "IMPLEMENTATION_REPLICATION.json", report)
            out = system12_summary(root)
            self.assertTrue(out["implementation_replication_pass"])
            self.assertFalse(out["system13_dependency_released"])
            self.assertFalse(out["independent_adjudication_executed"])
            for broken in ({**report, "contract_sha256": "changed"}, {**report, "checks": {}}, {**report, "orders": 1}):
                self.write(root, "IMPLEMENTATION_REPLICATION.json", broken)
                self.assertFalse(system12_summary(root)["implementation_replication_pass"])

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
