import hashlib
import io
import unittest
import urllib.error
import zipfile

from tools.gate_btc_source_redundancy_probe import parse_checksum, run_probe, validate_daily_1d_zip


def make_zip(day="2026-08-06", close="123.45"):
    import datetime
    ts = int(datetime.datetime.fromisoformat(day).replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
    row = [str(ts), "100", "130", "90", close, "10", str(ts + 86399999), "1000", "20", "5", "500", "0"]
    raw = (",".join(row) + "\n").encode()
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"BTCUSDT-1d-{day}.csv", raw)
    return out.getvalue()


class SourceRedundancyProbeTests(unittest.TestCase):
    def test_checksum_parser(self):
        self.assertEqual(parse_checksum(("a" * 64 + "  file.zip\n").encode()), "a" * 64)
        with self.assertRaises(ValueError):
            parse_checksum(b"not-a-checksum")

    def test_zip_structure_and_day(self):
        payload = validate_daily_1d_zip(make_zip(), "2026-08-06")
        self.assertEqual(payload["row_count"], 1)
        self.assertEqual(payload["utc_days"], ["2026-08-06"])
        with self.assertRaisesRegex(ValueError, "day mismatch"):
            validate_daily_1d_zip(make_zip(), "2026-08-05")

    def test_full_probe_pass_and_never_feeds_engine(self):
        archive = make_zip()
        checksum = (hashlib.sha256(archive).hexdigest() + "  BTCUSDT.zip\n").encode()

        def fetcher(url):
            return checksum if url.endswith(".CHECKSUM") else archive

        result = run_probe("2026-08-06", ["BTCUSDT", "ETHUSDT"], fetcher)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["feeds_frozen_engine"])
        self.assertFalse(result["source_substitution_performed"])
        self.assertEqual(result["methodology_changes"], 0)
        self.assertEqual(result["orders_generated"], 0)
        self.assertEqual(result["real_capital_used"], 0)

    def test_integrity_failure_is_explicit(self):
        archive = make_zip()
        bad_checksum = ("0" * 64 + "  file.zip\n").encode()

        def fetcher(url):
            return bad_checksum if url.endswith(".CHECKSUM") else archive

        result = run_probe("2026-08-06", ["BTCUSDT"], fetcher)
        self.assertEqual(result["status"], "FAIL_INTEGRITY")
        self.assertEqual(result["results"][0]["status"], "FAIL_INTEGRITY")
        self.assertFalse(result["engine_feed"])

    def test_404_is_warning_not_fake_pass(self):
        def fetcher(url):
            raise urllib.error.HTTPError(url, 404, "missing", {}, None)

        result = run_probe("2026-08-06", ["BTCUSDT"], fetcher)
        self.assertEqual(result["status"], "WARN_UNAVAILABLE")
        self.assertEqual(result["results"][0]["status"], "NOT_AVAILABLE")


if __name__ == "__main__":
    unittest.main()
