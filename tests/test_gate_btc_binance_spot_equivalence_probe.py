import hashlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.gate_btc_binance_spot_equivalence_probe import parse_spot_daily_row, run


def daily_zip(symbol="BTCUSDT", day="2026-08-06", close="64323.61", quote_volume="637366600"):
    open_ms = 1785974400000
    row = [str(open_ms), "64000", "65000", "63000", close, "10000", str(open_ms + 86399999), quote_volume, "10", "5", "100", "0"]
    raw = (",".join(row) + "\n").encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{symbol}-1d-{day}.csv", raw)
    return buf.getvalue()


class BinanceSpotEquivalenceProbeTests(unittest.TestCase):
    def test_parse_daily_row(self):
        parsed = parse_spot_daily_row(daily_zip(), "2026-08-06")
        self.assertAlmostEqual(parsed["archive_close"], 64323.61)
        self.assertAlmostEqual(parsed["archive_quote_volume"], 637366600.0)

    def test_run_matches_cdd_close_and_volume_without_engine_feed(self):
        with tempfile.TemporaryDirectory() as tmp:
            master = Path(tmp) / "master.csv"
            master.write_text(
                "date,symbol,close_usd,volume_usd,source\n"
                "2026-08-06,BTC,64323.61,637366600,cdd\n"
                "2026-08-06,ETH,1904.10,338698300,okx\n",
                encoding="utf-8",
            )
            raw = daily_zip()
            checksum = hashlib.sha256(raw).hexdigest().encode() + b"  file.zip\n"
            def fetcher(url):
                return checksum if url.endswith(".CHECKSUM") else raw
            report = run(master, "2026-08-06", fetcher=fetcher, max_workers=1)
            self.assertEqual(report["canonical_overlap_count"], 1)
            self.assertEqual(report["archive_available_count"], 1)
            self.assertEqual(report["close_match_1e_8_count"], 1)
            self.assertEqual(report["volume_match_1e_6_count"], 1)
            self.assertEqual(report["status"], "PASS_CLOSE_EQUIVALENCE")
            self.assertFalse(report["engine_feed"])
            self.assertFalse(report["feeds_frozen_engine"])
            self.assertFalse(report["source_substitution_performed"])
            self.assertFalse(report["denominator_changed"])
            self.assertEqual(report["methodology_changes"], 0)

    def test_only_cdd_rows_are_compared(self):
        with tempfile.TemporaryDirectory() as tmp:
            master = Path(tmp) / "master.csv"
            master.write_text(
                "date,symbol,close_usd,volume_usd,source\n"
                "2026-08-06,ETH,1904.10,338698300,okx\n",
                encoding="utf-8",
            )
            report = run(master, "2026-08-06", fetcher=lambda url: b"", max_workers=1)
            self.assertEqual(report["canonical_overlap_count"], 0)
            self.assertEqual(report["status"], "PASS_NO_OVERLAP_AVAILABLE")


if __name__ == "__main__":
    unittest.main()
