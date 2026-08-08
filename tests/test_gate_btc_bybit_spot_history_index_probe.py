import unittest

from tools.gate_btc_bybit_spot_history_index_probe import parse_dates, recovery_pairs, run


class BybitSpotHistoryIndexProbeTests(unittest.TestCase):
    def recovery_report(self):
        return {
            "schema": "gate_btc.bybit_spot_recovery_probe.v1",
            "feeds_frozen_engine": False,
            "source_substitution_performed": False,
            "day": "2026-08-06",
            "results": [
                {"pair": "JASMYUSDT", "status": "PASS_ARCHIVE_AVAILABLE"},
                {"pair": "NEXOUSDT", "status": "PASS_ARCHIVE_AVAILABLE"},
                {"pair": "NOPEUSDT", "status": "NOT_AVAILABLE"},
            ],
        }

    def test_parse_dates_filters_cutoff_and_duplicates(self):
        html = """
        <a href='JASMYUSDT_2026-08-05.csv.gz'>x</a>
        <a href='JASMYUSDT_2026-08-06.csv.gz'>x</a>
        <a href='JASMYUSDT_2026-08-06.csv.gz'>dup</a>
        <a href='JASMYUSDT_2026-08-07.csv.gz'>future</a>
        """
        self.assertEqual(parse_dates("JASMYUSDT", html, "2026-08-06"), ["2026-08-05", "2026-08-06"])

    def test_recovery_pairs_only_include_present(self):
        self.assertEqual(recovery_pairs(self.recovery_report()), ["JASMYUSDT", "NEXOUSDT"])

    def test_history_depth_is_evidence_only(self):
        jasmy_days = "".join(f"JASMYUSDT_2025-01-{d:02d}.csv.gz\n" for d in range(1, 29))
        # 210 unique synthetic dates across seven months.
        from datetime import date, timedelta
        start = date(2025, 1, 1)
        jasmy_days = "\n".join(f"JASMYUSDT_{(start + timedelta(days=i)).isoformat()}.csv.gz" for i in range(210))
        nexo_days = "\n".join(f"NEXOUSDT_{(start + timedelta(days=i)).isoformat()}.csv.gz" for i in range(50))

        def fetcher(url):
            return jasmy_days if "JASMYUSDT" in url else nexo_days

        report = run(self.recovery_report(), "2026-08-06", fetcher=fetcher, max_workers=1)
        self.assertEqual(report["status"], "PASS_HISTORY_INDEX_MEASURED")
        self.assertEqual(report["history_ge_200_count"], 1)
        self.assertEqual(report["history_ge_200_symbols"], ["JASMY"])
        self.assertFalse(report["engine_feed"])
        self.assertFalse(report["feeds_frozen_engine"])
        self.assertFalse(report["source_substitution_performed"])
        self.assertFalse(report["proxy_or_geo_bypass_used"])
        self.assertEqual(report["methodology_changes"], 0)
        self.assertEqual(report["orders_generated"], 0)
        self.assertEqual(report["real_capital_used"], 0)

    def test_safety_boundary_change_fails_closed(self):
        bad = self.recovery_report()
        bad["feeds_frozen_engine"] = True
        with self.assertRaisesRegex(RuntimeError, "engine-feed boundary changed"):
            recovery_pairs(bad)


if __name__ == "__main__":
    unittest.main()
