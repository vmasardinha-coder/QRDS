import csv
import io
import unittest
import zipfile

from tools.gate_btc_binance_vision_pit_history import parse_archive


class BinanceVisionPITTests(unittest.TestCase):
    def _archive(self, rows):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            text = io.StringIO()
            writer = csv.writer(text, lineterminator="\n")
            writer.writerows(rows)
            archive.writestr("TESTUSDT-1d.csv", text.getvalue())
        return buffer.getvalue()

    def test_parse_archive_uses_quote_volume_and_microsecond_timestamp(self):
        # 2025-01-02T00:00:00Z in microseconds. Binance Spot archive timestamps
        # moved to microseconds from 2025; quote asset volume is column 8 (index 7).
        rows = [[
            "1735776000000000", "1.0", "3.0", "0.5", "2.5", "100.0",
            "1735862399999999", "250.0", "10", "50.0", "125.0", "0"
        ]]
        frame = parse_archive(self._archive(rows), "TEST", "USDT")
        self.assertEqual(len(frame), 1)
        self.assertEqual(frame.iloc[0]["date"].date().isoformat(), "2025-01-02")
        self.assertEqual(float(frame.iloc[0]["close_usd"]), 2.5)
        self.assertEqual(float(frame.iloc[0]["volume_usd"]), 250.0)
        self.assertEqual(frame.iloc[0]["source"], "binance_data_vision_spot_usdt")

    def test_parse_archive_rejects_bad_kline_shape(self):
        with self.assertRaises(ValueError):
            parse_archive(self._archive([["1735776000000000", "1", "2"]]), "TEST", "USDT")


if __name__ == "__main__":
    unittest.main()
