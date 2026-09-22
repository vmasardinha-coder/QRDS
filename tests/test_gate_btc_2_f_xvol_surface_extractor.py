from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "gate_btc_2_f_xvol_surface_extractor.py"
spec = importlib.util.spec_from_file_location("xvol", MODULE_PATH)
xvol = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(xvol)


class XVolSurfaceTests(unittest.TestCase):
    def test_black76_forward_delta_signs(self):
        call = xvol.black76_forward_delta("call", 100.0, 100.0, 0.50, 30.0 / 365.0)
        put = xvol.black76_forward_delta("put", 100.0, 100.0, 0.50, 30.0 / 365.0)
        self.assertGreater(call, 0.5)
        self.assertLess(put, 0.0)
        self.assertAlmostEqual(call - put, 1.0, places=12)

    def test_quantile_linear(self):
        self.assertEqual(xvol.quantile([1.0], 0.75), 1.0)
        self.assertAlmostEqual(xvol.quantile([1.0, 2.0, 3.0, 4.0], 0.25), 1.75)
        self.assertAlmostEqual(xvol.quantile([1.0, 2.0, 3.0, 4.0], 0.75), 3.25)

    @staticmethod
    def _expiry_rows(expiry: int, atm_iv: float, forward: float = 100.0):
        strikes = [70.0, 80.0, 90.0, 100.0, 110.0, 120.0, 130.0]
        rows = []
        t = 30.0 / 365.0 if expiry == 2_000_000_000_000 else 60.0 / 365.0
        for option_type in ("call", "put"):
            for strike in strikes:
                iv = atm_iv + abs(strike - 100.0) * 0.10
                delta = xvol.black76_forward_delta(option_type, forward, strike, iv / 100.0, t)
                rows.append({
                    "instrument_name": f"BTC-{expiry}-{int(strike)}-{option_type[0].upper()}",
                    "option_type": option_type,
                    "expiration_timestamp": expiry,
                    "strike": strike,
                    "forward": forward,
                    "mark_iv_pct": iv,
                    "time_years": t,
                    "forward_delta": delta,
                    "abs_log_moneyness": abs(math.log(strike / forward)),
                })
        return rows

    def test_surface_snapshot_emits_frozen_features(self):
        near_expiry = 2_000_000_000_000
        far_expiry = 2_100_000_000_000
        rows = self._expiry_rows(near_expiry, 50.0) + self._expiry_rows(far_expiry, 55.0)
        snap = xvol.build_surface_snapshot(rows, 1_900_000_000_000)
        self.assertTrue(snap["eligible"])
        self.assertEqual(snap["family_id"], "F-XVOL-SURFACE")
        self.assertEqual(snap["near_expiration_timestamp"], near_expiry)
        self.assertEqual(snap["far_expiration_timestamp"], far_expiry)
        self.assertAlmostEqual(snap["features"]["atm_iv_near"], 50.0)
        self.assertAlmostEqual(snap["features"]["atm_iv_far"], 55.0)
        self.assertAlmostEqual(snap["features"]["term_slope"], 5.0)
        for key in (
            "put_25d_iv_near",
            "call_25d_iv_near",
            "risk_reversal_25d",
            "butterfly_25d",
            "surface_dispersion_near",
        ):
            self.assertTrue(math.isfinite(snap["features"][key]))

    def test_duplicate_identity_abstains(self):
        rows = self._expiry_rows(2_000_000_000_000, 50.0) + self._expiry_rows(2_100_000_000_000, 55.0)
        rows.append(dict(rows[0]))
        snap = xvol.build_surface_snapshot(rows, 1_900_000_000_000)
        self.assertFalse(snap["eligible"])
        self.assertEqual(snap["reason"], "duplicate_instrument_identity")

    def test_one_eligible_expiry_abstains(self):
        rows = self._expiry_rows(2_000_000_000_000, 50.0)
        snap = xvol.build_surface_snapshot(rows, 1_900_000_000_000)
        self.assertFalse(snap["eligible"])
        self.assertEqual(snap["reason"], "fewer_than_two_eligible_expiries")

    def test_static_safety_boundary(self):
        text = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn('"economic_claim_authorized": False', text)
        self.assertIn('"factory_migration_authorized": False', text)
        self.assertIn('"factory_runtime_untouched": True', text)
        self.assertIn('"no_backfill": True', text)
        self.assertIn('"orders": 0', text)


if __name__ == "__main__":
    unittest.main()
