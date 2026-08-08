import csv
import hashlib
import io
import unittest
import zipfile

from tools.gate_btc_binance_spot_cross_archive_equivalence import run


def make_zip(member, rows):
    raw = io.StringIO()
    writer = csv.writer(raw, lineterminator="\n")
    writer.writerows(rows)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member, raw.getvalue().encode())
    return out.getvalue()


def row_for_day(day, close="10", quote_volume="1000"):
    import datetime
    ts = int(datetime.datetime.fromisoformat(day).replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
    return [str(ts), "9", "11", "8", close, "100", str(ts + 86399999), quote_volume, "10", "50", "500", "0"]


class CrossArchiveEquivalenceTests(unittest.TestCase):
    def history(self):
        return {
            "schema": "gate_btc.binance_spot_history_depth_probe.v1",
            "feeds_frozen_engine": False,
            "source_substitution_performed": False,
            "results": [
                {
                    "symbol": "JASMY",
                    "pair": "JASMYUSDT",
                    "status": "PASS_HISTORY_DEPTH_GE_200",
                    "monthly_results": [
                        {"month": "2026-06", "archive_path": "/data/spot/monthly/klines/JASMYUSDT/1d/JASMYUSDT-1d-2026-06.zip", "status": "PASS"}
                    ],
                }
            ],
        }

    def test_exact_cross_archive_match_is_evidence_only(self):
        rows = [row_for_day("2026-06-01", "10", "1000"), row_for_day("2026-06-30", "12", "1200")]
        monthly = make_zip("JASMYUSDT-1d-2026-06.csv", rows)
        daily_by_day = {
            "2026-06-01": make_zip("JASMYUSDT-1d-2026-06-01.csv", [rows[0]]),
            "2026-06-30": make_zip("JASMYUSDT-1d-2026-06-30.csv", [rows[1]]),
        }

        def fetcher(url):
            if url.endswith(".CHECKSUM"):
                base = url[:-9]
                payload = fetcher(base)
                return (hashlib.sha256(payload).hexdigest() + "  x.zip\n").encode()
            if "monthly" in url:
                return monthly
            for day, payload in daily_by_day.items():
                if day in url:
                    return payload
            raise AssertionError(url)

        report = run(self.history(), months_to_check=1, samples_per_month=2, fetcher=fetcher, max_workers=1)
        self.assertEqual(report["status"], "PASS_CANDIDATE_CROSS_ARCHIVE_EQUIVALENCE")
        self.assertEqual(report["total_compared_samples"], 2)
        self.assertEqual(report["total_mismatches"], 0)
        self.assertEqual(report["fully_passed_symbols"], ["JASMY"])
        self.assertFalse(report["engine_feed"])
        self.assertFalse(report["feeds_frozen_engine"])
        self.assertFalse(report["source_substitution_performed"])
        self.assertFalse(report["strategy_inputs_changed"])
        self.assertEqual(report["methodology_changes"], 0)
        self.assertEqual(report["orders_generated"], 0)
        self.assertEqual(report["real_capital_used"], 0)

    def test_mismatch_fails_explicitly(self):
        monthly_row = row_for_day("2026-06-30", "12", "1200")
        daily_row = row_for_day("2026-06-30", "13", "1200")
        monthly = make_zip("JASMYUSDT-1d-2026-06.csv", [monthly_row])
        daily = make_zip("JASMYUSDT-1d-2026-06-30.csv", [daily_row])

        def fetcher(url):
            if url.endswith(".CHECKSUM"):
                base = url[:-9]
                payload = fetcher(base)
                return (hashlib.sha256(payload).hexdigest() + "  x.zip\n").encode()
            return monthly if "monthly" in url else daily

        report = run(self.history(), months_to_check=1, samples_per_month=1, fetcher=fetcher, max_workers=1)
        self.assertEqual(report["status"], "FAIL_CROSS_ARCHIVE_MISMATCH")
        self.assertEqual(report["total_mismatches"], 1)
        self.assertFalse(report["source_substitution_performed"])

    def test_safety_boundary_change_fails_closed(self):
        bad = self.history()
        bad["feeds_frozen_engine"] = True
        with self.assertRaisesRegex(RuntimeError, "engine-feed boundary changed"):
            run(bad, fetcher=lambda _: b"")


if __name__ == "__main__":
    unittest.main()
