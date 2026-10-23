import copy
import json
import math
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_momentum_identity import (
    MomentumIdentityConflict,
    assert_new_cutoff_monotonic,
    canonical_bytes,
    compare_scientific_identity,
    load_strict_predecessor,
    resolve_existing_snapshot,
    scientific_sha256,
)


def sample_payload():
    return {
        "schema": "gate-btc-momentum-m1m2-prospective-snapshot-v1",
        "cutoff": "2026-08-26",
        "classification": "PROSPECTIVE_SHADOW",
        "source": {"member": "data/processed/qos_v2a_master_daily.csv", "member_sha256": "a" * 64,
                   "rows": 100, "v2a_zip_sha256": "b" * 64},
        "m1": {"summary": {"breadth_pct_m1_gt_zero": 50.0, "delta_breadth_pct_points": 2.0},
               "rows": [{"asset": "BTC", "rank_m1": 2, "m1": 1.0},
                        {"asset": "ETH", "rank_m1": 1, "m1": 2.0}]},
        "m2": {"summary": {"breadth_pct_m2_gt_zero": 25.0, "delta_breadth_pct_points": -1.0},
               "rows": [{"asset": "BTC", "rank_m2": 1, "m2": 0.3},
                        {"asset": "ETH", "rank_m2": 2, "m2": -0.1}]},
        "safety": {"research_only": True, "shadow_only": True, "not_approved": True,
                   "engine_feed": False, "allocation_weight": 0, "orders": 0,
                   "real_capital": 0, "automatic_tuning": False},
    }


class MomentumIdentityTests(unittest.TestCase):
    def test_a_same_cutoff_same_data_same_hash(self):
        a = sample_payload(); b = copy.deepcopy(a)
        self.assertEqual(canonical_bytes(a), canonical_bytes(b))
        self.assertEqual(scientific_sha256(a), scientific_sha256(b))

    def test_b_nonsemantic_row_order_same_hash(self):
        a = sample_payload(); b = copy.deepcopy(a)
        b["m1"]["rows"].reverse(); b["m2"]["rows"].reverse()
        self.assertEqual(scientific_sha256(a), scientific_sha256(b))

    def test_c_operational_archive_metadata_not_identity(self):
        a = sample_payload(); b = copy.deepcopy(a)
        b["source"]["member_sha256"] = "c" * 64
        b["source"]["v2a_zip_sha256"] = "d" * 64
        self.assertEqual(scientific_sha256(a), scientific_sha256(b))

    def test_d_real_data_change_changes_hash(self):
        a = sample_payload(); b = copy.deepcopy(a); b["m1"]["rows"][0]["m1"] = 1.0001
        self.assertNotEqual(scientific_sha256(a), scientific_sha256(b))

    def test_e_duplicate_same_scientific_identity_is_idempotent_noop(self):
        existing = sample_payload(); existing["snapshot_sha256"] = "e" * 64
        candidate = copy.deepcopy(existing); candidate["source"]["v2a_zip_sha256"] = "f" * 64; candidate.pop("snapshot_sha256")
        result = resolve_existing_snapshot(existing, candidate)
        self.assertEqual(result["status"], "ALREADY_RECORDED")
        self.assertEqual(result["result"], "IDEMPOTENT_SUCCESS")
        self.assertEqual(result["snapshot_sha256"], "e" * 64)
        self.assertTrue(result["raw_provenance_changed"])

    def test_f_duplicate_different_scientific_identity_hard_fails(self):
        existing = sample_payload(); existing["snapshot_sha256"] = "e" * 64
        candidate = copy.deepcopy(existing); candidate.pop("snapshot_sha256")
        candidate["m2"]["summary"]["breadth_pct_m2_gt_zero"] = 26.0
        with self.assertRaises(MomentumIdentityConflict):
            resolve_existing_snapshot(existing, candidate)
        same, detail = compare_scientific_identity(existing, candidate)
        self.assertFalse(same); self.assertTrue(detail["differences"])

    def test_g_nonfinite_partial_numeric_payload_fails_closed(self):
        p = sample_payload(); p["m1"]["rows"][0]["m1"] = math.nan
        with self.assertRaises(ValueError): scientific_sha256(p)

    def test_predecessor_is_strict_and_ignores_target_and_future(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for c, h in (("2026-08-25", "1"), ("2026-08-26", "2"), ("2026-08-27", "3")):
                p = sample_payload(); p["cutoff"] = c; p["snapshot_sha256"] = h * 64
                (root / f"{c}.json").write_text(json.dumps(p), encoding="utf-8")
            prior = load_strict_predecessor(root, "2026-08-26")
            self.assertEqual(prior["cutoff"], "2026-08-25")

    def test_new_retroactive_cutoff_still_hard_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = sample_payload(); p["cutoff"] = "2026-08-27"; p["snapshot_sha256"] = "3" * 64
            (root / "2026-08-27.json").write_text(json.dumps(p), encoding="utf-8")
            with self.assertRaises(MomentumIdentityConflict): assert_new_cutoff_monotonic(root, "2026-08-26")

    def test_h_safety_contract_identity_and_no_protected_economics(self):
        p = sample_payload()
        self.assertFalse(p["safety"]["engine_feed"]); self.assertEqual(p["safety"]["orders"], 0)
        self.assertEqual(p["safety"]["real_capital"], 0); self.assertNotIn("h1_economics", json.dumps(p).lower())
        changed = copy.deepcopy(p); changed["safety"]["engine_feed"] = True
        self.assertNotEqual(scientific_sha256(p), scientific_sha256(changed))


if __name__ == "__main__": unittest.main()
