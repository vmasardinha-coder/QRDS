import unittest

from tools import gate_btc_v16b_executability_snapshot as e


class V16BExecutabilitySnapshotTests(unittest.TestCase):
    def test_merge_adds_adjacent_server_time_without_dropping_symbols(self):
        info = {"timezone": "UTC", "symbols": [{"symbol": "BTCUSDT"}]}
        out = e.merge_exchange_info(info, {"serverTime": 123456789})
        self.assertEqual(out["serverTime"], 123456789)
        self.assertEqual(out["symbols"], info["symbols"])
        self.assertEqual(out["v16b_server_time_source"], "ADJACENT_PUBLIC_TIME_ENDPOINT")
        self.assertNotIn("serverTime", info)

    def test_merge_fails_closed_without_symbols(self):
        with self.assertRaises(RuntimeError):
            e.merge_exchange_info({}, {"serverTime": 123})

    def test_merge_fails_closed_without_valid_server_time(self):
        with self.assertRaises(RuntimeError):
            e.merge_exchange_info({"symbols": [{"symbol": "BTCUSDT"}]}, {})
        with self.assertRaises(RuntimeError):
            e.merge_exchange_info({"symbols": [{"symbol": "BTCUSDT"}]}, {"serverTime": 0})


if __name__ == "__main__":
    unittest.main()
