import unittest
from types import SimpleNamespace

import pandas as pd

from tools.gate_btc_survivorship_definitive_pit import (
    identity_audit,
    parse_cmc_html,
    pit_block_override,
)


class FakeV2A:
    STABLES = {"USDT", "USDC"}
    AMBIGUOUS = {"BAD"}
    HIGH_NOISE = {"TRUMP"}
    BLACKLIST = {"FTT", "UST", "USTC", "LUNC"}

    @staticmethod
    def standard_ticker(value):
        import re
        return bool(re.fullmatch(r"[A-Z0-9]{2,12}", str(value or "")))


class DefinitivePITTests(unittest.TestCase):
    def test_cmc_parser_accepts_top150_table(self):
        rows = []
        for i in range(1, 151):
            rows.append(f"<tr><td>{i}</td><td>Coin {i}</td><td>C{i}</td><td>${i*1000}</td><td>${i}.0</td><td>${i*10}</td></tr>")
        html = "<table><thead><tr><th>Rank</th><th>Name</th><th>Symbol</th><th>Market Cap</th><th>Price</th><th>Volume (24h)</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        result = parse_cmc_html(html, pd.Timestamp("2026-07-31"))
        self.assertEqual(len(result), 150)
        self.assertEqual(int(result.iloc[0]["rank"]), 1)
        self.assertEqual(result.iloc[-1]["symbol"], "C150")

    def test_identity_blocks_reused_symbol(self):
        snapshots = pd.DataFrame([
            {"snapshot_date": pd.Timestamp("2020-06-30"), "rank": 10, "name": "Alpha One", "symbol": "AAA"},
            {"snapshot_date": pd.Timestamp("2021-06-30"), "rank": 20, "name": "Different Asset", "symbol": "AAA"},
            {"snapshot_date": pd.Timestamp("2020-06-30"), "rank": 1, "name": "Bitcoin", "symbol": "BTC"},
        ])
        coinlist = {"AAA": {"CoinName": "Alpha One"}, "BTC": {"CoinName": "Bitcoin"}}
        audit = identity_audit(snapshots, coinlist, FakeV2A())
        aaa = audit[audit["symbol"] == "AAA"].iloc[0]
        btc = audit[audit["symbol"] == "BTC"].iloc[0]
        self.assertFalse(bool(aaa["history_usable"]))
        self.assertTrue(bool(aaa["ambiguous_historical_symbol"]))
        self.assertTrue(bool(btc["history_usable"]))

    def test_ftt_is_not_retroactively_blocked(self):
        frame = pd.DataFrame({"symbol": ["FTT", "LUNC", "TRUMP", "BTC"], "is_blocked": [True, True, True, False]})
        before = pit_block_override(FakeV2A(), frame, pd.Timestamp("2022-06-30"))
        after = pit_block_override(FakeV2A(), frame, pd.Timestamp("2022-12-31"))
        self.assertFalse(bool(before.loc[before.symbol == "FTT", "is_blocked"].iloc[0]))
        self.assertTrue(bool(after.loc[after.symbol == "FTT", "is_blocked"].iloc[0]))
        self.assertTrue(bool(before.loc[before.symbol == "LUNC", "is_blocked"].iloc[0]))
        self.assertTrue(bool(before.loc[before.symbol == "TRUMP", "is_blocked"].iloc[0]))


if __name__ == "__main__":
    unittest.main()
