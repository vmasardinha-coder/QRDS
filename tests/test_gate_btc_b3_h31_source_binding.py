from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


class H31SourceBindingTests(unittest.TestCase):
    def test_contract_is_explicitly_approved_and_safe(self):
        c = json.loads((TOOLS / "gate_btc_b3_h31_source_binding_contract_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(c["approval_status"], "APPROVED_FOR_SEPARATE_PROSPECTIVE")
        self.assertEqual(c["first_eligible_date"], "2026-08-25")
        self.assertTrue(c["backfill_forbidden"])
        self.assertTrue(c["late_reconstruction_forbidden"])
        self.assertTrue(c["retune_forbidden"])
        self.assertTrue(c["partial_prospective_feedback_forbidden"])
        self.assertFalse(c["h1_economics_read"])
        self.assertEqual(c["orders"], 0)
        self.assertEqual(c["real_capital"], 0)
        self.assertFalse(c["engine_feed"])
        self.assertTrue(c["not_approved"])

    def test_rule_matches_frozen_h31(self):
        c = json.loads((TOOLS / "gate_btc_b3_h31_source_binding_contract_v1.json").read_text(encoding="utf-8"))
        f = json.loads((TOOLS / "gate_btc_b3_h31_prospective_freeze.json").read_text(encoding="utf-8"))
        self.assertEqual(c["freeze_rule_hash_sha256"], f["rule_hash_sha256"])
        r = c["rule"]
        self.assertEqual(r["signal_asset"], "WDO")
        self.assertEqual(r["observation_minutes"], 30)
        self.assertEqual(r["trigger_abs_z_gte"], 1.5)
        self.assertEqual(r["traded_asset"], "WIN")
        self.assertEqual(r["direction"], "opposite_signal")
        self.assertEqual(r["execution"], "next_bar_open")
        self.assertEqual(r["hold_minutes"], 120)
        self.assertEqual(r["reference_roundtrip_cost_bp"], 2.0)
        self.assertEqual(r["stress_roundtrip_cost_bp"], 3.0)

    def test_runtime_path_is_isolated(self):
        c = json.loads((TOOLS / "gate_btc_b3_h31_source_binding_contract_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(c["runtime_ledger_dir"], "runtime/ledgers/b3_h31_prospective")
        self.assertNotIn("b3_h1", c["runtime_ledger_dir"].lower())


if __name__ == "__main__":
    unittest.main()
