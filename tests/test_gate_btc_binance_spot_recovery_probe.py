import hashlib
import io
import json
import unittest
import zipfile

from tools.gate_btc_binance_spot_recovery_probe import candidate_symbols, probe_spot_symbol, run


def make_daily_zip(day="2026-08-06"):
    # 2026-08-06 00:00:00 UTC in milliseconds
    open_ms = 1785974400000
    row = [str(open_ms), "1", "2", "0.5", "1.5", "10", str(open_ms + 86399999), "15", "5", "4", "6", "0"]
    raw_csv = (",".join(row) + "\n").encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("KASUSDT-1d-2026-08-06.csv", raw_csv)
    return buf.getvalue()


class BinanceSpotRecoveryProbeTests(unittest.TestCase):
    def diagnostic(self):
        return {
            "schema": "gate_btc.v2a_failure_diagnostic.v1",
            "advisory_only": True,
            "feeds_frozen_engine": False,
            "rows": [
                {"symbol": "KAS", "action_class": "SOURCE_RECOVERY_CANDIDATE"},
                {"symbol": "BUIDL", "action_class": "SEMANTIC_SCOPE_REVIEW"},
                {"symbol": "TAO", "action_class": "WAIT_FOR_HISTORY"},
            ],
        }

    def test_candidate_selection_only_uses_recovery_class(self):
        self.assertEqual(candidate_symbols(self.diagnostic()), ["KAS"])

    def test_spot_archive_probe_validates_checksum_and_day(self):
        raw_zip = make_daily_zip()
        checksum = hashlib.sha256(raw_zip).hexdigest().encode() + b"  KASUSDT-1d-2026-08-06.zip\n"
        def fetcher(url):
            return checksum if url.endswith(".CHECKSUM") else raw_zip
        result = probe_spot_symbol("KAS", "2026-08-06", fetcher)
        self.assertEqual(result["status"], "PASS_CURRENT_DAY_ARCHIVE_PRESENT")
        self.assertEqual(result["pair"], "KASUSDT")
        self.assertEqual(result["utc_days"], ["2026-08-06"])

    def test_run_is_evidence_only(self):
        raw_zip = make_daily_zip()
        checksum = hashlib.sha256(raw_zip).hexdigest().encode() + b" x\n"
        def fetcher(url):
            return checksum if url.endswith(".CHECKSUM") else raw_zip
        report = run("2026-08-06", self.diagnostic(), fetcher=fetcher, max_workers=1)
        self.assertEqual(report["candidate_count"], 1)
        self.assertEqual(report["current_day_archive_present_count"], 1)
        self.assertFalse(report["engine_feed"])
        self.assertFalse(report["feeds_frozen_engine"])
        self.assertFalse(report["source_substitution_performed"])
        self.assertFalse(report["strategy_inputs_changed"])
        self.assertFalse(report["denominator_changed"])
        self.assertEqual(report["methodology_changes"], 0)
        self.assertEqual(report["orders_generated"], 0)
        self.assertEqual(report["real_capital_used"], 0)

    def test_unsafe_diagnostic_is_rejected(self):
        bad = self.diagnostic()
        bad["feeds_frozen_engine"] = True
        with self.assertRaisesRegex(RuntimeError, "safety boundary changed"):
            candidate_symbols(bad)


if __name__ == "__main__":
    unittest.main()
