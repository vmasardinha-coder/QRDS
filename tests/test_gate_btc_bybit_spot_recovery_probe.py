import gzip
import hashlib
import io
import unittest

from tools.gate_btc_bybit_spot_recovery_probe import candidates, run


def make_archive():
    raw = b"id,timestamp,price,volume,side,rpi\n1,1700000000,10,2,Buy,false\n"
    return gzip.compress(raw)


class BybitSpotRecoveryProbeTests(unittest.TestCase):
    def diagnostic(self):
        return {
            "schema": "gate_btc.v2a_failure_diagnostic.v1",
            "advisory_only": True,
            "feeds_frozen_engine": False,
            "source_substitution_performed": False,
            "data_as_of": "2026-08-06",
            "rows": [
                {"symbol": "JASMY", "action_class": "SOURCE_RECOVERY_CANDIDATE"},
                {"symbol": "NEXO", "action_class": "SOURCE_RECOVERY_CANDIDATE"},
                {"symbol": "BUIDL", "action_class": "SEMANTIC_SCOPE_REVIEW"},
            ],
        }

    def test_candidates_only_include_recovery_class(self):
        self.assertEqual(candidates(self.diagnostic()), ["JASMY", "NEXO"])

    def test_public_archives_are_recovery_leads_only(self):
        archive = make_archive()

        def fetcher(url):
            return archive

        report = run("2026-08-06", self.diagnostic(), fetcher=fetcher, max_workers=1)
        self.assertEqual(report["status"], "PASS_RECOVERY_LEADS_FOUND")
        self.assertEqual(report["archive_present_count"], 2)
        self.assertEqual(report["archive_present_symbols"], ["JASMY", "NEXO"])
        self.assertFalse(report["engine_feed"])
        self.assertFalse(report["feeds_frozen_engine"])
        self.assertFalse(report["source_substitution_performed"])
        self.assertFalse(report["proxy_or_geo_bypass_used"])
        self.assertFalse(report["authentication_used"])
        self.assertEqual(report["methodology_changes"], 0)
        self.assertEqual(report["orders_generated"], 0)
        self.assertEqual(report["real_capital_used"], 0)

    def test_safety_boundary_change_fails_closed(self):
        bad = self.diagnostic()
        bad["feeds_frozen_engine"] = True
        with self.assertRaisesRegex(RuntimeError, "engine-feed boundary changed"):
            candidates(bad)


if __name__ == "__main__":
    unittest.main()
