import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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

    def test_evidence_backed_pit_stables_are_exact(self):
        class DummyV2A:
            STABLES = set()

        v2a = DummyV2A()
        self.assertTrue(continuity._stable_symbol_with_evidence(v2a, "XTN", "Neutrino USD"))
        self.assertTrue(continuity._stable_symbol_with_evidence(v2a, "FEI", "Fei USD"))
        self.assertFalse(continuity._stable_symbol_with_evidence(v2a, "XTN", "Another Token"))
        self.assertFalse(continuity._stable_symbol_with_evidence(v2a, "ABC", "Neutrino USD"))

    def test_borg_chsb_recovery_is_hard_cut_before_migration(self):
        source = pd.DataFrame({
            "date": pd.to_datetime(["2023-10-15", "2023-10-16", "2023-10-17"]),
            "symbol": ["CHSB"] * 3,
            "close_usd": [1.0, 1.1, 1.2],
            "volume_usd": [100.0, 110.0, 120.0],
            "source": ["cryptodatadownload_bitfinex_usd"] * 3,
        })
        row = SimpleNamespace(first_snapshot="2020-06-30", last_snapshot="2023-01-31")
        with patch.object(continuity.staged.runner.cdd_multi, "fetch_symbol", return_value=(source, "cdd://CHSB", "PASS")):
            out, _, status = continuity._recover_borg(object(), row)
        self.assertEqual(status, "PASS")
        self.assertEqual(set(out["symbol"]), {"BORG"})
        self.assertTrue((out["date"] < continuity.BORG_MIGRATION_DATE).all())
        self.assertEqual(out["date"].max(), pd.Timestamp("2023-10-16"))
        self.assertTrue(out["source"].str.startswith("legacy_chsb_pre_borg_migration__").all())

    def test_borg_falls_back_to_bitfinex_trade_history_fail_closed_by_date(self):
        direct = pd.DataFrame({
            "date": pd.to_datetime(["2022-12-30", "2022-12-31"]),
            "symbol": ["BORG", "BORG"],
            "close_usd": [0.18, 0.19],
            "volume_usd": [1000.0, 1200.0],
            "source": ["bitfinex_public_trades_chsbusd", "bitfinex_public_trades_chsbusd"],
        })
        row = SimpleNamespace(first_snapshot="2020-06-30", last_snapshot="2023-01-31")
        with patch.object(
            continuity.staged.runner.cdd_multi,
            "fetch_symbol",
            return_value=(pd.DataFrame(), "cdd://CHSB", "NO_CDD_MULTI_EXCHANGE_DAILY"),
        ), patch.object(
            continuity.bitfinex_legacy,
            "fetch_chsb_pre_migration",
            return_value=(direct, "bitfinex://CHSBUSD", "PASS"),
        ) as fallback:
            out, url, status = continuity._recover_borg(object(), row)
        self.assertEqual(status, "PASS")
        self.assertEqual(url, "bitfinex://CHSBUSD")
        self.assertEqual(set(out["symbol"]), {"BORG"})
        self.assertTrue((out["date"] < continuity.BORG_MIGRATION_DATE).all())
        fallback.assert_called_once()

    def test_bttold_recovery_never_admits_new_btt_side(self):
        source = pd.DataFrame({
            "date": pd.to_datetime(["2021-12-25", "2021-12-26", "2021-12-27", "2022-01-02"]),
            "symbol": ["BTT"] * 4,
            "close_usd": [0.003, 0.0031, 0.0000031, 0.0000032],
            "volume_usd": [100.0, 100.0, 100.0, 100.0],
            "source": ["cryptodatadownload_poloniex_usdt"] * 4,
        })
        row = SimpleNamespace(first_snapshot="2020-06-30", last_snapshot="2021-12-31")
        with patch.object(continuity.staged.runner.cdd_multi, "fetch_symbol", return_value=(source, "cdd://BTT", "PASS")):
            out, _, status = continuity._recover_bttold(object(), row)
        self.assertEqual(status, "PASS")
        self.assertEqual(set(out["symbol"]), {"BTTOLD"})
        self.assertTrue((out["date"] < continuity.BTT_REDENOMINATION_DATE).all())
        self.assertEqual(out["date"].max(), pd.Timestamp("2021-12-26"))
        self.assertTrue(out["source"].str.startswith("legacy_btt_pre_redenomination__").all())

    def test_rev_uses_legacy_kucoin_api_identifier_only_post_swap(self):
        source = pd.DataFrame({
            "date": pd.to_datetime(["2020-04-08", "2020-04-09", "2020-04-10"]),
            "symbol": ["R"] * 3,
            "close_usd": [0.1, 0.11, 0.12],
            "volume_usd": [10.0, 11.0, 12.0],
            "source": ["kucoin_usdt"] * 3,
        })
        row = SimpleNamespace(first_snapshot="2020-09-30", last_snapshot="2022-03-31")
        with patch.object(continuity.staged.runner.exchange_history, "fetch_kucoin", return_value=(source, "PASS")) as mocked:
            out, _, status = continuity._recover_rev(object(), row)
        mocked.assert_called_once_with(unittest.mock.ANY, "R")
        self.assertEqual(status, "PASS")
        self.assertTrue((out["date"] >= continuity.REV_RENAME_COMPLETE_DATE).all())
        self.assertEqual(set(out["symbol"]), {"REV"})
        self.assertEqual(set(out["source"]), {"kucoin_legacy_api_r_usdt_post_rev_swap"})

    def test_mx_recovery_requires_post_2023_snapshot_and_quote_volume(self):
        class Response:
            status_code = 200
            def json(self):
                return [
                    [1682812800000, "2.0", "2.1", "1.9", "2.05", "100", 1682899199999, "205"],
                    [1682899200000, "2.05", "2.2", "2.0", "2.10", "110", 1682985599999, "231"],
                ]
        class Session:
            def get(self, *args, **kwargs):
                return Response()
        blocked = SimpleNamespace(first_snapshot="2022-12-31", last_snapshot="2023-01-31")
        out, _, status = continuity._recover_mx(Session(), blocked)
        self.assertTrue(out.empty)
        self.assertTrue(status.startswith("BLOCKED_"))
        valid = SimpleNamespace(first_snapshot="2023-04-30", last_snapshot="2023-05-31")
        out, _, status = continuity._recover_mx(Session(), valid)
        self.assertEqual(status, "PASS")
        self.assertEqual(out["volume_usd"].tolist(), [205, 231])
        self.assertEqual(set(out["source"]), {"mexc_spot_mxusdt"})

    def test_kucoin_uta_residuals_use_direct_usdt_quote_amount_and_listing_bounds(self):
        class Response:
            status_code = 200
            def json(self):
                return {
                    "code": "200000",
                    "data": [
                        [1622764800, "0.20", "0.22", "0.19", "0.21", "100", "21"],
                        [1622851200, "0.21", "0.23", "0.20", "0.22", "120", "26.4"],
                    ],
                }
        class Session:
            def get(self, url, params=None, timeout=None):
                self.url = url
                self.params = params
                return Response()

        session = Session()
        out, _, status = continuity.kucoin_uta_legacy.fetch_symbol(
            session, "ABBC", "2020-06-30", "2022-11-30"
        )
        self.assertEqual(status, "PASS")
        self.assertEqual(out["volume_usd"].tolist(), [21.0, 26.4])
        self.assertTrue((out["date"] >= pd.Timestamp("2021-06-04")).all())
        self.assertEqual(session.params["symbol"], "ABBC-USDT")
        self.assertEqual(session.params["tradeType"], "SPOT")
        self.assertEqual(session.params["interval"], "1day")

    def test_kucoin_uta_ampl_contract_spans_full_pit_window(self):
        contract = continuity.kucoin_uta_legacy.CONTRACTS["AMPL"]
        self.assertEqual(contract["pair"], "AMPL-USDT")
        self.assertLessEqual(contract["listing_date"], pd.Timestamp("2020-07-31") - pd.Timedelta(days=200))
        self.assertGreater(contract["delisting_date_exclusive"], pd.Timestamp("2021-02-28"))

    def test_kucoin_uta_residual_scope_is_exact(self):
        self.assertEqual(set(continuity.kucoin_uta_legacy.CONTRACTS), {"AMPL", "ABBC", "VLX"})
        out, _, status = continuity.kucoin_uta_legacy.fetch_symbol(object(), "MONA", "2020-06-30", "2021-01-31")
        self.assertTrue(out.empty)
        self.assertEqual(status, "BLOCKED_NOT_CURATED_KUCOIN_UTA_RESIDUAL")

    def test_migration_cases_are_not_promoted_to_same_token_continuities(self):
        self.assertNotIn("BORG", continuity.EVIDENCE_BACKED_CONTINUITIES)
        self.assertNotIn("BTTOLD", continuity.EVIDENCE_BACKED_CONTINUITIES)
        self.assertNotIn("REV", continuity.EVIDENCE_BACKED_CONTINUITIES)
        self.assertNotIn("MX", continuity.EVIDENCE_BACKED_CONTINUITIES)
        self.assertNotIn("AMPL", continuity.EVIDENCE_BACKED_CONTINUITIES)
        self.assertNotIn("ABBC", continuity.EVIDENCE_BACKED_CONTINUITIES)
        self.assertNotIn("VLX", continuity.EVIDENCE_BACKED_CONTINUITIES)

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
