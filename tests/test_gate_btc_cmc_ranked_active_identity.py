import sys
import unittest
from unittest.mock import patch
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import gate_btc_cmc_ranked_active_identity as probe


class _Response:
    def __init__(self, data, status_code=200, headers=None):
        self._data = data
        self.status_code = status_code
        self.headers = headers or {}
    def raise_for_status(self):
        if self.status_code != 200:
            raise RuntimeError(f"HTTP {self.status_code}")
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


class _ThrottledSession(_Session):
    def __init__(self, data, status_codes):
        super().__init__(data)
        self.status_codes = iter(status_codes)

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params or {}), timeout))
        return _Response(self.data, next(self.status_codes), {"Retry-After": "1"})


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

    @patch.object(probe.time, "sleep")
    def test_keyless_429_retries_same_ranked_query(self, sleep):
        s = _ThrottledSession([{"symbol": "BTC"}], [429, 200])
        self.assertEqual(probe.fetch_ranked_active_rows(s), [{"symbol": "BTC"}])
        self.assertEqual(s.calls[0], s.calls[1])
        sleep.assert_called_once_with(1.0)

    @patch.object(probe.time, "sleep")
    def test_persistent_429_fails_closed(self, sleep):
        s = _ThrottledSession([], [429] * 5)
        with self.assertRaisesRegex(RuntimeError, "HTTP 429"):
            probe.fetch_ranked_active_rows(s)
        self.assertEqual(len(s.calls), 5)
        self.assertEqual(sleep.call_count, 4)

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
