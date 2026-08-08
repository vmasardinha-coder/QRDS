import gzip
import io
import unittest
import urllib.error

from tools.gate_btc_bybit_public_archive_probe import probe_pair, run, validate_gzip_csv


def archive_bytes():
    raw = b"timestamp,symbol,side,size,price\n1785974400,BTCUSDT,Buy,1,64300\n"
    return gzip.compress(raw, mtime=0)


class BybitPublicArchiveProbeTests(unittest.TestCase):
    def test_gzip_csv_validation(self):
        result = validate_gzip_csv(archive_bytes())
        self.assertEqual(result["sampled_data_rows"], 1)
        self.assertEqual(result["sampled_column_count"], 5)
        self.assertEqual(result["header"][0], "timestamp")

    def test_available_archive_is_pass_and_evidence_only(self):
        result = probe_pair("BTCUSDT", "2026-08-06", lambda url: archive_bytes())
        self.assertEqual(result["status"], "PASS_ARCHIVE_AVAILABLE")
        report = run("2026-08-06", ["BTCUSDT"], fetcher=lambda url: archive_bytes(), max_workers=1)
        self.assertEqual(report["status"], "PASS_PUBLIC_ARCHIVE_AVAILABLE")
        self.assertFalse(report["engine_feed"])
        self.assertFalse(report["feeds_frozen_engine"])
        self.assertFalse(report["source_substitution_performed"])
        self.assertFalse(report["proxy_or_geo_bypass_used"])
        self.assertFalse(report["authentication_used"])
        self.assertEqual(report["methodology_changes"], 0)

    def test_403_is_explicit_not_bypassed(self):
        def fetcher(url):
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)
        result = probe_pair("BTCUSDT", "2026-08-06", fetcher)
        self.assertEqual(result["status"], "GEO_BLOCKED")
        report = run("2026-08-06", ["BTCUSDT", "ETHUSDT"], fetcher=fetcher, max_workers=1)
        self.assertEqual(report["status"], "WARN_ARCHIVE_GEO_BLOCKED")
        self.assertFalse(report["proxy_or_geo_bypass_used"])

    def test_invalid_gzip_fails_integrity(self):
        result = probe_pair("BTCUSDT", "2026-08-06", lambda url: b"not-gzip")
        self.assertEqual(result["status"], "FAIL_INTEGRITY")


if __name__ == "__main__":
    unittest.main()
