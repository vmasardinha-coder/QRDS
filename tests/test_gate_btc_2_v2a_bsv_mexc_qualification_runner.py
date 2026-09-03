import json
import unittest
from datetime import date

from tools.gate_btc_2_v2a_bsv_mexc_qualification_runner import (
    filter_rows_to_end,
    parse_payload,
)


class TestBSVMexcQualificationRunner(unittest.TestCase):
    def test_parse_payload_known_schema(self):
        raw = json.dumps([
            [1704067200000, "1", "2", "0.5", "1.5", "10", 1704153599999, "15"]
        ]).encode()
        rows = parse_payload(raw)
        self.assertEqual(rows[0]["day"], "2024-01-01")
        self.assertEqual(rows[0]["open"], 1.0)
        self.assertEqual(rows[0]["high"], 2.0)
        self.assertEqual(rows[0]["base_volume"], 10.0)
        self.assertEqual(rows[0]["quote_volume"], 15.0)

    def test_rows_after_requested_end_are_excluded(self):
        rows = [
            {"day": "2026-09-02", "timestamp_ms": 1},
            {"day": "2026-09-03", "timestamp_ms": 2},
        ]
        accepted, excluded = filter_rows_to_end(rows, date(2026, 9, 2))
        self.assertEqual([r["day"] for r in accepted], ["2026-09-02"])
        self.assertEqual(excluded, 1)

    def test_error_envelope_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_payload(json.dumps({"code": 400, "msg": "error"}).encode())

    def test_unknown_row_schema_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_payload(json.dumps([[1, 2]]).encode())

    def test_negative_volume_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_payload(json.dumps([
                [1704067200000, "1", "2", "0.5", "1.5", "-1", 1704153599999, "15"]
            ]).encode())

    def test_bad_ohlc_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_payload(json.dumps([
                [1704067200000, "1", "0.8", "0.5", "1.5", "10", 1704153599999, "15"]
            ]).encode())


if __name__ == "__main__":
    unittest.main()
