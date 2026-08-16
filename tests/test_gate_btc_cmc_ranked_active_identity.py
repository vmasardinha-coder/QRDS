import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import gate_btc_cmc_ranked_active_identity as probe


class _Response:
    def __init__(self, data):
        self._data = data
    def raise_for_status(self):
        return None
    def json(self):
        return {"data": self._data}


class _Session:
    def __init__(self, data):
        self.data = data
        self.calls = []
    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params or {}), timeout))
        return _Response(self.data)


class CMCRankedActiveIdentityTests(unittest.TestCase):
    def test_fetch_is_explicitly_rank_sorted(self):
        s = _Session([{"symbol": "TRUMP", "slug": "official-trump", "name": "OFFICIAL TRUMP"}])
        rows = probe.fetch_ranked_active_rows(s)
        self.assertEqual(len(rows), 1)
        _, params, timeout = s.calls[0]
        self.assertEqual(params["listing_status"], "active")
        self.assertEqual(params["sort"], "cmc_rank")
        self.assertEqual(params["limit"], 5000)
        self.assertEqual(timeout, 45)

    def test_augment_uses_only_unambiguous_keys(self):
        rows = [
            {"symbol": "TRUMP", "slug": "official-trump", "name": "OFFICIAL TRUMP"},
            {"symbol": "ASTER", "slug": "aster", "name": "Aster"},
            {"symbol": "AAA", "slug": "collision", "name": "Collision One"},
            {"symbol": "BBB", "slug": "collision", "name": "Collision Two"},
        ]
        out, meta = probe.augment_cmc_identity_map({"btc": {"BTC"}}, rows)
        self.assertEqual(out["officialtrump"], {"TRUMP"})
        self.assertEqual(out["aster"], {"ASTER"})
        self.assertNotIn("collision", out)
        self.assertEqual(meta["ambiguous_ranked_keys"]["slug:collision"], ["AAA", "BBB"])

    def test_non_ascii_or_nonstandard_symbol_is_not_admitted(self):
        rows = [{"symbol": "币安人生", "slug": "binance-life", "name": "币安人生"}]
        slug_map, name_map = probe.ranked_identity_maps(rows)
        self.assertEqual(slug_map, {})
        self.assertEqual(name_map, {})

    def test_core_sentinels_exact(self):
        rows = [
            {"symbol": "TRUMP", "slug": "official-trump", "name": "OFFICIAL TRUMP"},
            {"symbol": "ASTER", "slug": "aster", "name": "Aster"},
            {"symbol": "PI", "slug": "pi", "name": "Pi"},
            {"symbol": "PUMP", "slug": "pump-fun", "name": "Pump.fun"},
            {"symbol": "KAITO", "slug": "kaito", "name": "KAITO"},
        ]
        report = probe.sentinel_report(rows)
        self.assertTrue(report["core_pass"])


if __name__ == "__main__":
    unittest.main()
