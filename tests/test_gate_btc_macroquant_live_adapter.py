import csv
import json
import tempfile
import unittest
from pathlib import Path

from tools import gate_btc_macroquant_live_adapter as adapter

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "migration" / "reporting" / "bull_replay_contract.json"


def snap(path: Path, asof: str, nav: float, *, version: str = "v13.1", changed: bool = False, daily=None):
    payload = {
        "schema": "macroquant.daily_snapshot.v1",
        "strategy_name": "MacroQuant",
        "strategy_version": version,
        "methodology_changed_since_prior_snapshot": changed,
        "generated_at_utc": asof,
        "data_as_of_utc": asof,
        "nav_currency": "USD",
        "nav_net": nav,
        "daily_return_net": daily,
        "positions": [{"symbol": "BTC", "side": "LONG"}],
        "source_provenance": {
            "capture_method": "native export",
            "price_source": "native",
            "nav_type": "contabilidade nativa real"
        },
        "research_only": True,
        "orders_generated_for_gate_btc": 0,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


class MacroQuantLiveAdapterTests(unittest.TestCase):
    def test_predecision_snapshot_rejected_as_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            s = tmp / "s.json"
            snap(s, "2026-08-12T11:35:13Z", 3105.33)
            with self.assertRaises(adapter.MacroQuantAdapterError):
                adapter.anchor(s, CONTRACT, tmp / "out", "2026-08-13T18:22:00Z")

    def test_anchor_is_redacted(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            s = tmp / "s.json"
            snap(s, "2026-08-13T12:00:00Z", 3105.33)
            out = tmp / "out"
            result = adapter.anchor(s, CONTRACT, out, "2026-08-13T18:22:00Z")
            self.assertEqual(result["status"], "ANCHORED_WAITING_SECOND_SNAPSHOT")
            text = (out / "MACROQUANT_ANCHOR_REDACTED.json").read_text(encoding="utf-8")
            self.assertNotIn("3105.33", text)
            self.assertNotIn("positions", text)
            self.assertEqual(json.loads(text)["normalized_nav"], 1.0)

    def test_append_builds_normalized_index_without_private_nav(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            s0 = tmp / "s0.json"
            s1 = tmp / "s1.json"
            snap(s0, "2026-08-13T12:00:00Z", 3000.0)
            snap(s1, "2026-08-14T12:00:00Z", 3030.0, daily=0.01)
            out = tmp / "out"
            adapter.anchor(s0, CONTRACT, out, "2026-08-13T18:22:00Z")
            status = adapter.append(s0, s1, CONTRACT, out)
            self.assertEqual(status["observations"], 1)
            self.assertAlmostEqual(status["normalized_nav"], 1.01, 10)
            with (out / "MACROQUANT_NORMALIZED_LEDGER.csv").open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            text = (out / "MACROQUANT_NORMALIZED_LEDGER.csv").read_text(encoding="utf-8")
            self.assertNotIn("3000", text)
            self.assertNotIn("3030", text)
            self.assertNotIn("BTC", text)

    def test_methodology_change_requires_new_series(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            s0 = tmp / "s0.json"
            s1 = tmp / "s1.json"
            snap(s0, "2026-08-13T12:00:00Z", 3000.0, version="v13.1")
            snap(s1, "2026-08-14T12:00:00Z", 3030.0, version="v13.2", changed=True)
            out = tmp / "out"
            adapter.anchor(s0, CONTRACT, out, "2026-08-13T18:22:00Z")
            with self.assertRaises(adapter.MacroQuantAdapterError):
                adapter.append(s0, s1, CONTRACT, out)


if __name__ == "__main__":
    unittest.main()
