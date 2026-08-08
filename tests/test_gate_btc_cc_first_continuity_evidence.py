import sys
import unittest
from pathlib import Path

import pandas as pd

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import gate_btc_survivorship_definitive_cc_first_continuity_runner as continuity


class CCFirstContinuityEvidenceTests(unittest.TestCase):
    def setUp(self):
        continuity.apply_continuity_evidence()

    def test_primary_source_backed_name_changes_are_admitted(self):
        cases = {
            "THETA": (["THETA", "Theta Network"], ["theta", "thetanetwork"]),
            "HBAR": (["Hedera Hashgraph", "Hedera"], ["hederahashgraph", "hedera"]),
            "FET": (["Fetch.ai", "Artificial Superintelligence Alliance"], ["fetch", "artificialsuperintelligencealliance"]),
            "INJ": (["Injective Protocol", "Injective"], ["injectiveprotocol", "injective"]),
            "SNX": (["Synthetix Network Token", "Synthetix"], ["synthetixnetworktoken", "synthetix"]),
            "SXP": (["SXP", "Swipe", "Solar"], ["swipe", "sxp", "solar"]),
        }
        for symbol, (names, slugs) in cases.items():
            with self.subTest(symbol=symbol):
                self.assertTrue(continuity.staged.runner._continuity_ok(symbol, names, slugs))

    def test_curated_single_char_exceptions_are_exact(self):
        self.assertTrue(continuity._single_char_evidence_ok("W", ["Wormhole"], ["wormhole"]))
        self.assertTrue(continuity._single_char_evidence_ok("T", ["Threshold"], ["threshold"]))
        self.assertFalse(continuity._single_char_evidence_ok("A", ["Asset"], ["asset"]))
        self.assertFalse(continuity._single_char_evidence_ok("W", ["Another W"], ["wormhole"]))
        self.assertFalse(continuity._single_char_evidence_ok("T", ["Threshold"], ["another-threshold"]))

    def test_xtn_uses_only_evidence_backed_usdn_source_alias(self):
        self.assertEqual(continuity.EVIDENCE_BACKED_SOURCE_ALIASES, {"XTN": "USDN"})

        def fake_fetch(_session, query_symbol):
            self.assertEqual(query_symbol, "USDN")
            frame = pd.DataFrame({
                "date": [pd.Timestamp("2021-05-30"), pd.Timestamp("2021-05-31")],
                "symbol": ["USDN", "USDN"],
                "close_usd": [1.0, 0.999],
                "volume_usd": [1000.0, 1200.0],
                "source": ["kucoin_usdt", "kucoin_usdt"],
            })
            return frame, "PASS"

        history, status = continuity._fetch_with_same_token_alias(fake_fetch, None, "XTN", "kucoin")
        self.assertEqual(status, "PASS")
        self.assertEqual(set(history["symbol"]), {"XTN"})
        self.assertTrue(history["source"].str.contains("same_token_alias_usdn_to_xtn").all())

    def test_unrelated_symbols_are_not_source_aliased(self):
        def fake_fetch(_session, query_symbol):
            self.assertEqual(query_symbol, "REV")
            return pd.DataFrame(columns=["date", "symbol", "close_usd", "volume_usd", "source"]), "NO_DATA"

        _, status = continuity._fetch_with_same_token_alias(fake_fetch, None, "REV", "kucoin")
        self.assertEqual(status, "NO_DATA")

    def test_unrelated_ticker_reuse_still_fails_closed(self):
        self.assertFalse(
            continuity.staged.runner._continuity_ok(
                "AAA", ["Alpha Asset", "Another Asset"], ["alphaasset", "anotherasset"]
            )
        )

    def test_fet_evidence_does_not_merge_other_premerger_assets(self):
        self.assertNotIn("AGIX", continuity.EVIDENCE_BACKED_CONTINUITIES)
        self.assertNotIn("OCEAN", continuity.EVIDENCE_BACKED_CONTINUITIES)

    def test_cross_token_migrations_remain_fail_closed(self):
        self.assertNotIn("DYDX", continuity.EVIDENCE_BACKED_CONTINUITIES)
        self.assertNotIn("KNC", continuity.EVIDENCE_BACKED_CONTINUITIES)
        self.assertNotIn("BORG", continuity.EVIDENCE_BACKED_SOURCE_ALIASES)
        self.assertNotIn("BTTOLD", continuity.EVIDENCE_BACKED_SOURCE_ALIASES)
        self.assertFalse(
            continuity.staged.runner._continuity_ok(
                "DYDX", ["dYdX", "dYdX (ethDYDX)"], ["dydx", "ethdydx"]
            )
        )
        self.assertFalse(
            continuity.staged.runner._continuity_ok(
                "KNC",
                ["Kyber Network Crystal Legacy", "Kyber Network Crystal v2"],
                ["kybernetworkcrystallegacy", "kybernetworkcrystalv2"],
            )
        )

    def test_bybit_archive_remains_staged_not_removed(self):
        self.assertTrue(callable(continuity.staged._defer_bybit_archive))
        self.assertTrue(hasattr(continuity.staged.runner, "bybit_archive"))
        self.assertTrue(callable(continuity.staged.runner.bybit_archive.collect))


if __name__ == "__main__":
    unittest.main()
