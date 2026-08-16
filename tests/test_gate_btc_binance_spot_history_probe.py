import hashlib
import io
import re
import unittest
import zipfile
from datetime import datetime, timedelta, timezone

from tools.gate_btc_binance_spot_history_probe import previous_months, recovery_leads, run, validate_monthly_zip


def month_zip(month: str, days: int = 30) -> bytes:
    start = datetime.strptime(month + "-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
    rows = []
    for index in range(days):
        ts = start + timedelta(days=index)
        if ts.strftime("%Y-%m") != month:
            break
        open_ms = int(ts.timestamp() * 1000)
        rows.append([str(open_ms), "1", "2", "0.5", "1.5", "10", str(open_ms + 86399999), "15", "5", "4", "6", "0"])
    raw = "".join(",".join(row) + "\n" for row in rows).encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"KASUSDT-1d-{month}.csv", raw)
    return buf.getvalue()


class BinanceSpotHistoryProbeTests(unittest.TestCase):
    def spot_report(self):
        return {
            "schema": "gate_btc.binance_spot_recovery_probe.v1",
            "feeds_frozen_engine": False,
            "source_substitution_performed": False,
            "results": [
                {"symbol": "KAS", "status": "PASS_CURRENT_DAY_ARCHIVE_PRESENT"},
                {"symbol": "NOPE", "status": "NOT_AVAILABLE"},
            ],
        }

    def test_previous_months_excludes_cutoff_month(self):
        self.assertEqual(previous_months("2026-08-06", 3), ["2026-05", "2026-06", "2026-07"])

    def test_recovery_leads_only_uses_validated_current_day(self):
        self.assertEqual(recovery_leads(self.spot_report()), ["KAS"])

    def test_monthly_zip_validation(self):
        info = validate_monthly_zip(month_zip("2026-07", 31), "2026-07")
        self.assertEqual(info["row_count"], 31)
        self.assertEqual(info["first_day"], "2026-07-01")
        self.assertEqual(info["last_day"], "2026-07-31")

    def test_run_proves_depth_without_engine_feed(self):
        def fetcher(url: str) -> bytes:
            match = re.search(r"-1d-(\d{4}-\d{2})\.zip", url)
            self.assertIsNotNone(match)
            month = match.group(1)
            raw = month_zip(month, 31)
            if url.endswith(".CHECKSUM"):
                return (hashlib.sha256(raw).hexdigest() + "  file.zip\n").encode()
            return raw

        report = run("2026-08-06", self.spot_report(), fetcher=fetcher, month_count=8, max_workers=1)
        self.assertEqual(report["lead_count"], 1)
        self.assertEqual(report["history_ge_200_count"], 1)
        self.assertEqual(report["results"][0]["status"], "PASS_HISTORY_DEPTH_GE_200")
        self.assertGreaterEqual(report["results"][0]["validated_unique_daily_rows"], 200)
        self.assertFalse(report["engine_feed"])
        self.assertFalse(report["feeds_frozen_engine"])
        self.assertFalse(report["source_substitution_performed"])
        self.assertFalse(report["denominator_changed"])
        self.assertEqual(report["methodology_changes"], 0)

    def test_unsafe_spot_report_fails_closed(self):
        bad = self.spot_report()
        bad["source_substitution_performed"] = True
        with self.assertRaisesRegex(RuntimeError, "safety boundary changed"):
            recovery_leads(bad)


if __name__ == "__main__":
    unittest.main()
